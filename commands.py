
def fs_ls(fs, path):
    result = ""
    dp = path.split()
    if not dp or not fs: return "execute [ ls %s ] failed.\n" % path
    dr = fs.opendir(dp[0])
    result += dr.get_name() + ":\n"
    for d in dr.readdir():
        result += d.get_name() + "\n"
    return result
    
def fs_copy(*args):
    print "fs_copy"