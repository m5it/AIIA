import os,re,sys

#
def rmatch(input,regex):
	x = re.match( regex, input )
	if x != None:
		return x
	else:
		return False
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


s="Povédkovnik je polnopomenska besedna vrsta, katere skladenjska vloga je povedkovo določilo: všeč, rad, mraz ...[1] Nekateri so mogoči le v vlogi povedkovega določila (všeč, bot ...), vendar med povedkovnike sodijo tudi opisni deležniki na -n, -l, -t ter nedoločniki ob naklonskih in večstopenjskih glagolih. Lahko so osebni (tiho v tiho sem, všeč v všeč sem) oziroma neosebni (hudo v hudo je, deževno v deževno je). Večinoma so nepregibni, obstajajo pa tudi pregibni povedkovniki (deležniki, ràd ráda -o).[2]Pogostokrat štejejo povedkovnike med prislove – tudi v prvi izdaji Slovarja slovenskega knjižnega jezika. Kot samostojno besedno vrsto je povedkovnik (in tudi členek) vpeljal Jože Toporišič v osemdesetih letih 20. stoletja.Glede na to, katere slovnične kategorije vsebujejo, bi jih lahko nadalje delili na pridevniške, prislovne in samostalniške:[3]Pravi povedkovniki so lahko tudi medmeti (joj/prejoj v To bo joj/prejoj.) in tudi sklopi tipa boglonaj (v On jim je boglonaj.), bogpomagaj (v Z njim je bogpomagaj.) ipd. Zaradi svoje tvorjenosti in tudi sicer so slednji besednovrstno nejasni.[3]Povedkovniki so praviloma nepregibni, s tem da se t. i. pridevniški povedkovniki lahko pregibajo po spolu in številu ter stopnjujejo, t. i. samostalniški povedkovniki pa se pregibajo le po številu.[3]Kako ti je ime? Povédkovnik je polnopomenska besedna vrsta, katere skladenjska vloga je povedkovo določilo: všeč, rad, mraz ...[1] Nekateri so mogoči le v vlogi povedkovega določila (všeč, bot ...), vendar med povedkovnike sodijo tudi opisni deležniki na -n, -l, -t ter nedoločniki ob naklonskih in večstopenjskih glagolih. Lahko so osebni (tiho v tiho sem, všeč v všeč sem) oziroma neosebni (hudo v hudo je, deževno v deževno je). Večinoma so nepregibni, obstajajo pa tudi pregibni povedkovniki (deležniki, ràd ráda -o).[2]Pogostokrat štejejo povedkovnike med prislove – tudi v prvi izdaji Slovarja slovenskega knjižnega jezika. Kot samostojno besedno vrsto je povedkovnik (in tudi členek) vpeljal Jože Toporišič v osemdesetih letih 20. stoletja.Glede na to, katere slovnične kategorije vsebujejo, bi jih lahko nadalje delili na pridevniške, prislovne in samostalniške:[3]Pravi povedkovniki so lahko tudi medmeti (joj/prejoj v To bo joj/prejoj.) in tudi sklopi tipa boglonaj (v On jim je boglonaj.), bogpomagaj (v Z njim je bogpomagaj.) ipd. Zaradi svoje tvorjenosti in tudi sicer so slednji besednovrstno nejasni.[3]Povedkovniki so praviloma nepregibni, s tem da se t. i. pridevniški povedkovniki lahko pregibajo po spolu in številu ter stopnjujejo, t. i. samostalniški povedkovniki pa se pregibajo le po številu.[3]Povédkovnik je polnopomenska besedna vrsta, katere skladenjska vloga je povedkovo določilo: všeč, rad, mraz ...[1] Nekateri so mogoči le v vlogi povedkovega določila (všeč, bot ...), vendar med povedkovnike sodijo tudi opisni deležniki na -n, -l, -t ter nedoločniki ob naklonskih in večstopenjskih glagolih. Lahko so osebni (tiho v tiho sem, všeč v všeč sem) oziroma neosebni (hudo v hudo je, deževno v deževno je). Večinoma so nepregibni, obstajajo pa tudi pregibni povedkovniki (deležniki, ràd ráda -o).[2]Pogostokrat štejejo povedkovnike med prislove – tudi v prvi izdaji Slovarja slovenskega knjižnega jezika. Kot samostojno besedno vrsto je povedkovnik (in tudi členek) vpeljal Jože Toporišič v osemdesetih letih 20. stoletja.Glede na to, katere slovnične kategorije vsebujejo, bi jih lahko nadalje delili na pridevniške, prislovne in samostalniške:[3]Pravi povedkovniki so lahko tudi medmeti (joj/prejoj v To bo joj/prejoj.) in tudi sklopi tipa boglonaj (v On jim je boglonaj.), bogpomagaj (v Z njim je bogpomagaj.) ipd. Zaradi svoje tvorjenosti in tudi sicer so slednji besednovrstno nejasni.[3]Povedkovniki so praviloma nepregibni, s tem da se t. i. pridevniški povedkovniki lahko pregibajo po spolu in številu ter stopnjujejo, t. i. samostalniški povedkovniki pa se pregibajo le po številu.[3] "

news=[]
newq=[]
tmps=""
# config={
	# 'append':[{
		# 'char':'.',
		# 'type':'equal', # equal | unequal
		# 'check':[
			# [{'n':-1, 'chr':'i'},{'n':-2, 'chr':' '},{'n':-3, 'chr':'.'},{'n':-4, 'chr':'t'}],
			# [{'n':+1, 'chr':')'}],
			# [{'n':-1,'chr':'ISDIGIT'}]
		# ],
	# }]
# }
#
print("text.len: {}".format( len(s) ))
for i in range(0,len(s)):
	c = s[i]
	#-- Skip
	if (c=='[' and s[i+1].isdigit() and s[i+2]==']') or (c.isdigit() and s[i+1]==']' and s[i-1]=='[') or c==']' and s[i-1].isdigit() and s[i-2]=='[':
		continue
	#-- Append line
	elif (c=="." and s[i-1]!='i' and s[i-2]!=' ' and s[i-3]!='.' and s[i-4]!='t') and (s[i+1]!=')') and (s[i+1]!='.' and s[i+2]!='.' and s[i-1].isdigit()==False):
	# append=False
	# for o in config['append']:
		# if o['type']=='equal' and o['char']==c:
			# #phk=False
			# for chk in o['check']:
				# phk=False
				# for nhk in chk:
					# if nhk['chr']=='ISDIGIT' and s[i+nhk['n']].isdigit()==False:
						# append=True
						# phk=True
					# elif s[i+nhk['n']]!=nhk['chr']:
						# append=True
						# phk=True
					# #if phk==False:
					# else:
						# phk=False
						# append=False
						# break
				# if phk==False:
					# break
			# #if phk==False:
			# #	break
	# if append:
		news.append("{}.".format( tmps.strip() ))
		tmps=""
	#-- Append line
	elif (c=="?" and s[i-1]!='i' and s[i-2]!=' ' and s[i-3]!='.' and s[i-4]!='t') and (s[i+1]!=')') and (s[i+1]!='.' and s[i+2]!='.' and s[i-1].isdigit()==False):
		newq.append("{}?".format( tmps.strip() ))
		tmps=""
	#-- Collect
	else:
		tmps += c

print("tmps.len: {}".format(len(tmps)))
print("news.len: {}".format(len(news)))
print("newq.len: {}".format(len(newq)))
for l in news:
	print("l: {}".format(l))
for l in newq:
	print("q: {}".format(l))
#
print("Old lines: ")
print(s)
