import re,os
#
def rmatch(input,regex):
	x = re.match( regex, input )
	if x != None:
		return x
	else:
		return False

def pmatch(input,regex):
	ret=[]
	a = re.findall( regex, input, flags=re.IGNORECASE )
	if a is not None:
		if type(a) is list and len(a)>0 and type(a[0]) is tuple:
			a = a[0]
		for v in a:
			ret.append( v )
	return ret

#
con = "!DATE abc.txt"
if rmatch(con,"\!DATE"):
	print("Looks ollama wana see current date...")
	ollama_cmd = "date"
else:
	print("Not!")

#
a = pmatch("!READ abc.txt","\!READ.(.*)")
print("pmatch: {}".format(a))
if len(a)>0:
	print("pmatch 0: {}".format(a[0]))
