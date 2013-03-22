import os
import struct
import extfs

class Partition:
    def __init__(self, disk):
        self.disk   = disk
        self.status = 0
        self.type   = 0
        self.offset = 0
        self.length = 0
        
    def make(self, s, t, o, l):
        self.status = s
        self.type = t
        self.offset = o
        self.length = l
        
    def get_offset(self):
        return self.offset * Disk.SECTOR_SIZE
    
    def get_length(self):
        return self.length * Disk.SECTOR_SIZE
       
    def read(self, size):
        return self.disk.read(size)
    
    def seek(self, offset):
        return self.disk.seek(self.get_offset() + offset)
    
class Disk:
    SECTOR_SIZE = 512
    def __init__(self, drive):
        self.dh = open(drive, "rb")
        self.sector = []
    def read(self, size):
        b = []
        rem = len(self.sector)
        if rem > 0 :
            s = min(rem, size)
            b += self.sector[:s]
            size -= s
            rem -= s
            if rem > 0 :
                self.sector = self.sector[s:]
        if size == 0:
            return b
        r = size % Disk.SECTOR_SIZE
        b1 = self.dh.read(size - r)
        b += b1
        if r > 0:
            self.sector = self.dh.read(Disk.SECTOR_SIZE)
            b += self.sector[:r]
            self.sector = self.sector[r:]
        return b
    def seek(self, offset, whence = os.SEEK_SET):
        self.sector = []
        return self.dh.seek(offset, whence)
    def close(self):
        self.dh.close()
        
    def get_partitions(self):
        return self._parse_xbr([], 0)
    
    def _parse_logic_part(self, parts, logic_off, offset):
        self.seek((offset + logic_off) * Disk.SECTOR_SIZE)
        ebr = self.read(Disk.SECTOR_SIZE)
        if len(ebr) != Disk.SECTOR_SIZE:
            return parts
        for x in range(2):
            start = x * 16 + 446
            end  = x * 16 + 446 + 16
            (status,_,_,t,_,_,off, length) = struct.unpack('BBHBBHII', "".join(map(str,ebr[start:end])))
#            print "logic: ",status,"\t",t,"\t",off,"\t",length
            if t == 0x5 or t == 0xf:
                self._parse_logic_part(parts, logic_off, off)
            elif t != 0:
                p = Partition(self)
                p.make(status, t, logic_off + off + offset, length)
                parts.append(p)      
        
    def _parse_xbr(self, parts, offset):
        self.seek(offset * Disk.SECTOR_SIZE)
        xbr = self.read(Disk.SECTOR_SIZE)
        if len(xbr) != Disk.SECTOR_SIZE:
            return parts
        for x in range(4):
            start = x * 16 + 446
            end = x * 16 + 446 + 16
            (status,_,_,t,_,_,off, length) = struct.unpack('BBHBBHII', "".join(map(str,xbr[start:end])))
            if t != 0:
                p = Partition(self)
                p.make(status, t, off + offset, length)
                if t == 0xf or t == 0x5 :
                    self._parse_logic_part(parts, off + offset, 0)
                else:
                    parts.append(p)
        return parts

def read_fstab(fstab):
    name = fstab.get_name()
    if name == 'fstab' or name == 'profile':
        st = fstab.stat()
        print name, ": ", st.get_size(), "bytes."
        b = fstab.read(st.get_size())
        print "".join(map(str, b))
if __name__ == '__main__':
    disk = Disk(r'\\.\PhysicalDrive1')
    s = disk.read(Disk.SECTOR_SIZE)
    p = disk.get_partitions()
    for x in range(len(p)):
        print p[x].status, p[x].type, p[x].offset, p[x].length
        e = extfs.ExtSuperblock()
        r = e.probe(p[x])
        if r:
            print "is ext2 filesystem"
            fs = extfs.ExtFs(p[x], e)
            dr = fs.opendir('/')
            for de in dr.readdir():
                if de.get_name() == 'etc':
                    xe = fs.opendir('/etc')
                    print "batman: opened: inode[ ", xe.inode.get_inode_no(), "]"
                    for xde in xe.readdir():
                        read_fstab(xde)
        else:
            print "unknown filesystem"
    disk.close()
