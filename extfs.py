import struct

group_descriptor_size = 32

EXT2_GOOD_OLD_INODE_SIZE = 128

EXT2_S_IFSOCK = 0xC000 #/* socket */
EXT2_S_IFLNK = 0xA000  #/* symbolic link */
EXT2_S_IFREG = 0x8000  #/* regular file */
EXT2_S_IFBLK = 0x6000  #/* block device */
EXT2_S_IFDIR = 0x4000  #/* directory */
EXT2_S_IFCHR = 0x2000  #/* character device */
EXT2_S_IFIFO = 0x1000  #/* fifo */
#    /*  process execution user/group override */
EXT2_S_ISUID = 0x0800 #/* Set process User ID */
EXT2_S_ISGID = 0x0400 #/* Set process Group ID */
EXT2_S_ISVTX = 0x0200 #/* sticky bit */
#    /*  access rights  */
EXT2_S_IRUSR = 0x0100 #/* user read */
EXT2_S_IWUSR = 0x0080 #/* user write */
EXT2_S_IXUSR = 0x0040 #/* user execute */
EXT2_S_IRGRP = 0x0020 #/* group read */
EXT2_S_IWGRP = 0x0010 #/* group write */
EXT2_S_IXGRP = 0x0008 #/* group execute */
EXT2_S_IROTH = 0x0004 #/* others read */
EXT2_S_IWOTH = 0x0002 #/* others write */
EXT2_S_IXOTH = 0x0001 #/* others execute */

EXT2_VALID_FS     = 1
EXT2_ERROR_FS     = 2
EXT2_SUPER_MAGIC  = 0xEF53
EXT2_GOOD_OLD_REV = 0
EXT2_DYNAMIC_REV  = 1

EXT2_BAD_INO          = 1 # /* bad blocks inode */
EXT2_ROOT_INO         = 2 # /* root directory inode */
EXT2_ACL_IDX_INO      = 3 # /* ACL index inode (deprecated?) */
EXT2_ACL_DATA_INO     = 4 # /* ACL data inode (deprecated?) */
EXT2_BOOT_LOADER_INO  = 5 # /* boot loader inode */
EXT2_UNDEL_DIR_INO    = 6 # /* undelete directory */

EXT2_INDEX_FL = 0x00001000 # Hash indexed directory

class EntryNotFound(Exception):
    def __init__(self, path):
        self.value = path
    def __str__(self):
        return "can't found: " + repr(self.value)
    
class FileEntryType(object):
    def __init__(self, mode):
        self._mode = mode
    def is_directory(self):
        return (self._mode & EXT2_S_IFDIR) == EXT2_S_IFDIR
    def is_regular_file(self):
        return (self._mode & EXT2_S_IFREG) == EXT2_S_IFREG
    
class FileStat(FileEntryType):
    def __init__(self, inode):
        FileEntryType.__init__(self, inode.i_mode)
        self.mode = inode.i_mode
        self.uid  = inode.i_uid
        self.gid  = inode.i_gid
        self._size = inode.i_dir_acl << 32 | inode.i_size
        self.atime = inode.i_atime
        self.ctime = inode.i_ctime
        self.mtime = inode.i_mtime
        self.dtime = inode.i_dtime
    def get_size(self):
        return self._size
    
class FileEntry(FileEntryType):
    def __init__(self, extfs, inode, name):
        self.filesys = extfs
        self.inode   = inode
        self.name    = name
        self._cur_pos = 0
        self._stat   = FileStat(inode)
        self.blksize = extfs.get_blksize()
        FileEntryType.__init__(self, self.inode.i_mode)
    def get_name(self):
        return self.name
    def get_inode(self):
        return self.inode
    def stat(self):
        return self._stat
    def _do_read(self, block, r, size):
        data = []
        for x in block:
            if x == 0:
                break
            b = self.filesys.read_block(x)
            assert(len(b) == self.blksize)
            if r > 0:
                b = b[r:]
                r = 0
            sz = min(size, len(b))
            data += b[:sz]
            size -= sz
            self._cur_pos += sz
            if size == 0:
                break
        return data
    def __read_low12(self, size):
        limit = self.blksize * 12
        blk = []
        if self._cur_pos < limit:
            s = self._cur_pos / self.blksize
            r = self._cur_pos % self.blksize
            low12 = self.inode.i_block[s:12]
            blk = self._do_read(low12, r, size)
        return blk
    
    def __read_block13(self, size):
        low = self.blksize * 12
        hi = self.blksize * (self.blksize / 4) + low
        blk = []
        if self._cur_pos >= low and self._cur_pos < hi:
            if self.inode.i_block[12] == 0:
                return blk
            block13 = buffer(bytearray(self.filesys.read_block(self.inode.i_block[12])))
            fmt = "<%dI" % (self.blksize / 4)
            block13 = struct.unpack(fmt, block13)
            cpos = self._cur_pos - low
            n = cpos / self.blksize
            r = cpos % self.blksize
            blk = self._do_read(block13[n:], r, size)
        return blk
    def __read_block14(self, size):
        low = self.blksize * (self.blksize / 4) + self.blksize * 12
        hi  = self.blksize * ((self.blksize / 4) ** 2) + self.blksize * 12
        blk = []
        if self._cur_pos >= low and self._cur_pos < hi:
            if self.inode.i_block[13] == 0:
                return blk
            cpos = self._cur_pos - low
            nblock = cpos / self.blksize
            n1 = nblock / (self.blksize / 4)
            n0 = n1 / (self.blksize / 4)
            block14 = buffer(bytearry(self.filesys.read_block(self.inode.i_block[13])))
            fmt = "<%dI" % (self.blksize / 4)

            block14 = struct.unpack_from(fmt, block14)
            r0 = cpos % self.blksize
            for x in block14[n0:]:
                assert(x > 0)
                indirect = self.filesys.read_block(x)
                indirect = struct.unpack(fmt, indirect)
                bk = self._do_read(indirect[n1:], r0, size)
                n1 = 0
                r0 = 0
                size -= len(bk)
                blk += bk
                if size == 0:
                    break
        return blk
    def __read_block15(self, size):
        low = self.blksize * ((self.blksize / 4) ** 2) + self.blksize * 12
        blk = []
        ndx = self.blksize / 4
        if self._cur_pos >= low:
            if self.inode.i_block[14] == 0:
                return blk
            cpos = self._cur_pos - low
            n3 = cpos / self.blksize
            r = cpos % self.blksize
            n2 = n3 / ndx
            n1 = n2 / ndx
            n0 = n1 / ndx
            fmt = "<%dI" % ndx
            b15 = struct.unpack_from(fmt, buffer(bytearray(self.filesys.read_block(self.inode.i_block[14]))))
            for x in b15[n0:]:
                assert(x > 0)
                c15 = struct.unpack_from(fmt, buffer(bytearray(self.filesys.read_block(x))))
                for y in c15[n1:]:
                    d15 = struct.unpack_from(fmt, buffer(bytearray(self.filesys.read_block(y))))
                    bk = self._do_read(d15[n2:], r, size)
                    r = 0
                    n2 = 0
                    blk += bk
                    size -= len(bk)
                    if size == 0:
                        break
                n1 = 0
                if size == 0:
                    break
        return blk          
    def read(self, size):
        blk = self.__read_low12(size)
        size -= len(blk)
        if size > 0:
            b13 = self.__read_block13(size)
            blk += b13
            size -= len(b13)
        if size > 0:
            b14 = self.__read_block14(size)
            blk += b14
            size -= len(b14)
        if size > 0:
            b15 = self.__read_block15(size)
            blk += b15
            size -= len(b15)
        return blk
    
class FileContext(FileEntry):
    def __init__(self, efs, fle, name):
        FileEntry.__init__(self, efs, fle, name)
        self.extfs   = efs
        self.inode = fle
    def readdir(self):
        sz = self.stat().get_size()
#        print "this_dir: ", self.get_name(), "size: ", sz
        contents = self.read(sz)
        b = buffer(bytearray(contents))
        while b:
            fmt = "<IH2B"
            sz = 0
            (i_node, rec_len, name_len,_) = struct.unpack_from(fmt, b, sz)
            sz = struct.calcsize(fmt)
            fmt = "%ds" % name_len     
            name = struct.unpack_from(fmt, b, sz)[0]
            sz += struct.calcsize(fmt)
            inode = self.extfs.get_inode(i_node)
            e = FileEntryType(inode.i_mode)
            if e.is_directory():
                den = FileContext(self.extfs, inode, name)
            else:
                den = FileEntry(self.extfs, inode, name)
            yield den
            b = b[rec_len:]
class GroupDescriptor(object):
    def __init__(self):
        super(GroupDescriptor, self).__init__()
    def make(self, buf):
        sb = "".join(map(str, buf))
        fmt = "<3I4H12s"
        (self.bg_block_bitmap,
         self.bg_inode_bitmap,
         self.bg_inode_table,
         self.bg_free_blocks_count,
         self.bg_free_inodes_count,
         self.bg_used_dirs_count,
         self.bg_pad,
         self.bg_reserved) = struct.unpack(fmt, sb)
        
class ExtInode(object):
    def __init__(self, idx, buf):
        self.inode_no = idx
        sb = buffer(bytearray(buf))
        sz = 0
        fmt = "<2H5I2H3I"
        (self.i_mode,
         self.i_uid,
         self.i_size,
         self.i_atime,
         self.i_ctime,
         self.i_mtime,
         self.i_dtime,
         self.i_gid,
         self.i_links_count,
         self.i_blocks,
         self.i_flags,
         self.i_osd1) = struct.unpack_from(fmt, sb, sz)
        sz += struct.calcsize(fmt)
        fmt = "<15I"
        self.i_block = struct.unpack_from(fmt, sb, sz)
        sz += struct.calcsize(fmt)
        fmt = "<4I12s"
        (self.i_gneration,
         self.i_file_acl,
         self.i_dir_acl,
         self.i_faddr,
         self.i_osd2) = struct.unpack_from(fmt, sb, sz)
    def get_inode_no(self):
        return self.inode_no
        
class ExtSuperblock:
    def __init__(self):
        pass
    def probe(self, partition):
        partition.seek(1024)
        sb = partition.read(1024)
        if len(sb) != 1024:
            return False
        sbs = buffer(bytearray(sb))
        sz = 0
        fmt = "<7Ii5I6H4I2HI2H3I"
        (self.s_inodes_count, 
         self.s_blocks_count,
         self.s_r_blocks_count,
         self.s_free_blocks_count,
         self.s_free_inodes_count,
         self.s_first_data_block,
         self.s_log_block_size,
         self.s_log_frag_size,
         self.s_blocks_per_group,
         self.s_frags_per_group,
         self.s_inodes_per_group,
         self.s_mtime,
         self.s_wtime,
         self.s_mnt_count,
         self.s_max_mnt_count,
         self.s_magic,
         self.s_state,
         self.s_errors,
         self.s_minor_rev_level,
         self.s_lastcheck,
         self.s_checkinterval,
         self.s_creator_os,
         self.s_rev_level,
         self.s_def_resuid,
         self.s_def_resgid,
         self.s_first_ino,
         self.s_inode_size,
         self.s_block_group_nr,
         self.s_feature_compat,
         self.s_feature_incompat,
         self.s_feature_ro_compat) = struct.unpack_from(fmt, sbs, sz)
        sz += struct.calcsize(fmt)
        fmt = "<16s16s64s"
        sz += struct.calcsize(fmt)
        (self.s_uudi, self.s_volume_name, self.s_last_mounted) = struct.unpack_from(fmt, sbs, sz)
        fmt = "<I2B2s16s3I16sB3s2I"
        (self.s_algo_bitmap, 
         self.s_prealloc_blocks,
         self.s_prealloc_dir_blocks,
         self.alignment,
         self.s_journal_uuid,
         self.s_journal_inum,
         self.s_journal_dev,
         self.s_last_orphan,
         self.s_hash_seed,
         self.s_def_hash_version,
         self.padding,
         self.s_default_mount_options,
         self.s_first_meta_bg) = struct.unpack_from(fmt, sbs, sz)
        sz += struct.calcsize(fmt)
        if self.s_magic == EXT2_SUPER_MAGIC:
            self.block_size = 1024 << self.s_log_block_size
            if self.s_rev_level == EXT2_GOOD_OLD_REV:
                self.s_inode_size = EXT2_GOOD_OLD_INODE_SIZE
            return True
        return False
    def get_blocksize(self):
        return self.block_size

class ExtFs:
    def __init__(self, part, sb):
        self.partition = part
        self.super_block = sb
        self.gdt = []
        self.inodes = []
    def get_group_descriptos(self):
        if self.gdt:
            return self.gdt
        n_groups = self.super_block.s_blocks_count / self.super_block.s_blocks_per_group;
        r = self.super_block.s_blocks_count % self.super_block.s_blocks_per_group;
        if r > 0:
            n_groups += 1
        sb = self.super_block
        size = n_groups * group_descriptor_size
        off = (sb.s_first_data_block + 1) * sb.get_blocksize()
        self.partition.seek(off)
        gdt = self.partition.read(size)
        if len(gdt) < size:
            print "read: ", len(gdt), "bytes, expected: ", size
            return []
        for x in range(n_groups):
            s = x * group_descriptor_size
            e = (x + 1) * group_descriptor_size
            d = GroupDescriptor()
            d.make(gdt[s:e])
            self.gdt.append(d)
        return self.gdt 
    
    def _find_inode(self, idx):
        for x in self.inodes:
            if x.get_inode_no() == idx:
                return x
        return None
    
    def get_inode(self, node_id):
        node = self._find_inode(node_id)
        if node:
            return node
        gid = (node_id - 1) / self.super_block.s_inodes_per_group
        gdts = self.get_group_descriptos()
        gdt = gdts[gid]
        itbid = gdt.bg_inode_table
        off = ((node_id - 1) % self.super_block.s_inodes_per_group) * self.super_block.s_inode_size
        n = off / self.super_block.get_blocksize()
        r = off % self.super_block.get_blocksize()
        blk = self.read_block(itbid + n)
        node = ExtInode(node_id, blk[r:])
        self.inodes.append(node)
        return node
    
    def read_block(self, bid):
        self.partition.seek(bid * self.super_block.get_blocksize())
        return self.partition.read(self.super_block.get_blocksize())
    def get_blksize(self):
        return self.super_block.get_blocksize()
    def opendir(self, path):
        root_inode = self.get_inode(EXT2_ROOT_INO)
        root = FileContext(self, root_inode, '/')
        if path == '/':
            return root
        dirs = path.split('/')
        while dirs[0] == '':
            dirs = dirs[1:]
        for x in dirs:
            for de in root.readdir():
                if de.get_name() == x:
                    root = FileContext(self, de.get_inode(), de.get_name())
                    break
            else:
                raise EntryNotFound(x)
        return root
