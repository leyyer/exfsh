import os

def fs_cat(fs, path):
	dp = path.split()
	if not dp or not fs: return "execute [cat %s] failed.\n" % path
	(dn,fn) = os.path.split(str(dp[0]))
	dr = fs.opendir(dn)
	result = "can't read " + path + "\n"
	for x in dr.readdir():
		if x.get_name() == fn:
			sz = x.stat().get_size()
			if x.is_regular_file():
				result = "".join(map(str, x.read(sz)))
			break
	return result

def fs_ls(fs, path):
    result = ""
    dp = path.split()
    if not dp or not fs: return "execute [ ls %s ] failed.\n" % path
    dr = fs.opendir(dp[0])
    result += dr.get_name() + ":\n"
    for d in dr.readdir():
        result += d.get_name() + "\n"
    return result
def fs_copy(fs, path):
	print path
	dp = path.split()
	print dp
	fr,to = dp[0],dp[1]
	(dn, fn) = os.path.split(fr)
	result = "copy failed.\n"
	print "from (%s), to (%s), dn (%s), fn (%s)\n" % (fr, to, dn, fn)
	dr = fs.opendir(dn)
	for x in dr.readdir():
		if x.get_name() == fn:
			sz = x.stat().get_size()
			if x.is_regular_file():
				with open(to, "wb") as f:
					while sz > 0:
						t = min(sz, 8192)
						r = x.read(t)
						f.write(buffer(bytearray(r)))
						sz -= len(r)
				result = "copy done.\n"
			break
	return result
