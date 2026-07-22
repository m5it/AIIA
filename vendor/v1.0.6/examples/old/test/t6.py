import re
#
def pmatch(input,regex):
	ret=[]
	a = re.findall( regex, input, flags=re.IGNORECASE )
	if a is not None:
		if type(a) is list and len(a)>0 and type(a[0]) is tuple:
			a = a[0]
		for v in a:
			ret.append( v )
	return ret

#test 1
a=[3,1,5,10,-1,2]
n = len(a)
dummy = object()
while True:
	tmp = dummy
	for i in range(n-1):
		if a[i]>a[i+1]:
			tmp = a[i]
			a[i] = a[i+1]
			a[i+1] = tmp
	if tmp is dummy:
		break
print("test 1: ")
print(a)



# test 2
a={
	'a':{'n':'a','c':1},
	'b':{'n':'b','c':7},
	'c':{'n':'c','c':5},
	'd':{'n':'d','c':2},
	'e':{'n':'e','c':0},
}

def sortDict(a,k):
	n=len(a)
	while True:
		nxt = None
		tmp = None
		b   = iter(a)
		i   = next(b,None)
		for j in range(n):
			nxt = next(b,None)
			if nxt==None:
				continue
			if a[i][k]>a[nxt][k]:
				tmp = a[i]
				a[i] = a[nxt]
				a[nxt] = tmp
			i=nxt
		if tmp==None:
			break
	return a

print("Test sortDict(): ")
sortDict(a,'c')
print(a)
b={}
b[1000]={'n':'t1','c':11}
b[192]={'n':'t1','c':11}
b[111]={'n':'t1','c':11}
c=[1000,192,111]
c.sort()
print(b)
print(c)
b="hello,world"
for i in reversed(range(0,len(b))):
	print(b[i])
b1="zanimanjem"
#b2="[z][a][n][i][m][a][l]"
b2="zanima"
#b2="[z][a][n][i][m][a][l]"
b2="zanimal"
r="(^{}+|^{}+|^{}+)".format(b2,b2[0:len(b2)-1],b2[0:len(b2)-2])
print("{}/{}, {}/{}".format(b1,len(b1),b2,len(b2)))
print(r)
print(pmatch(b1,r))
print()
print(round(12.555,1))
print()
print( b2[0:len(b2)-3] )
