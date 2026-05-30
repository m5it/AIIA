#!/usr/bin/python
# ptext.py
# ptext.py by w4d4f4k at gmail dot com
# ptext.py is used for generating tokens, 
#                      vocab files, 
#                      preparing datasets
#                      and more.
#
# Ex. usage: 
# time python ptext.py -F datasets/data/slo/ringaraja_forum/ -E ".*stats.*" -W 1 -d 10 -w out_vocab2
# 
# or output to another directory ex.:
# time python ptext.py -F datasets/data/slo/wikipedia/text/ -E ".*stats.*" -W 1 -d 20 -w datasets/data/slo/wikipedia/gen/data
#
# time python ptext.py -F datasets/data/slo/ringaraja_clanki/text/ -E ".*stats.*" -W 1 -d 20 -w datasets/data/slo/ringaraja_clanki/gen/data
# time python ptext.py -F datasets/data/slo/ringaraja_forum/text/ -E ".*stats.*" -W 1 -d 20 -w datasets/data/slo/ringaraja_forum/gen/data
# time python ptext.py -F datasets/data/slo/wikipedia/text/ -E ".*stats.*" -W 1 -d 20 -w datasets/data/slo/wikipedia/gen/data
#--
import getopt,json,os
from unidecode import unidecode # for removeAccents
from operator import itemgetter
from datasets.functions import *
#
Version = "0.7331.2"
# stats for word count
tmpWordsPerc   = {}
tmpTablePerc   = {}
WordsPercIndex = []
WordsPerc      = {}
#
tmpWordsUniq   = {}
WordsUniqIndex = []
WordsUniq      = {} # crc32b of words to get num of unique
WordsUrls      = []
#
tmpLines   = [] # crc32b or lines to get num of unique
Lines   = []
#
def HELP():
	global Options
	print("HELP....\n")
	for k in Options:
		o=Options[k]
		print("{} => {}".format( o['short'], o['name'] ))
#
def VERSION():
	global Version
	print("v{}".format(Version))
#
Options = {
	crc32b('-h'):{
		'name':'help',
		'short':'-h',
		'long':'--help',
		'accept':False, # accept value
		'value':False,
		'exec':HELP,
	},
	crc32b('-v'):{
		'name':'version',
		'short':'-v',
		'long':'--version',
		'accept':False, # accept value
		'value':False,
		'exec':VERSION,
	},
	crc32b('-f'):{
		'name':'file',
		'short':'-f',
		'long':'--file',
		'accept':True, # accept value
		'value':None,
	},
	crc32b('-F'):{
		'name':'filePath',
		'short':'-F',
		'long':'--file_path',
		'accept':True, # accept value
		'value':None,
	},
	crc32b('-m'):{
		'name':'maxLine',
		'short':'-m',
		'long':'--max_line',
		'accept':True, # accept value
		'value':512,
	},
	crc32b('-W'):{
		'name':'maxWord',
		'short':'-W',
		'long':'--max_word',
		'accept':True, # accept value
		'value':2,
	},
	crc32b('-g'):{
		'name':'generate',
		'short':'-g',
		'long':'--generate',
		'accept':True, # accept value
		'value':-1, # -1 = Nothing, 
					#  0 = vocab.txt line ex.: word
					#                          anotherword...
					#  1 = vocab.txt line ex.: word 0
					#                          anotherword 1...
					#  2 = vocab.txt organized by which words goes together and template style like option 0
					#  3 = vocab.txt organized by which words goes together and template style like option 1
	},
	crc32b('-M'):{ # match_file accept regex
		'name':'fileMatch',
		'short':'-M',
		'long':'--match_file',
		'accept':True, # accept value
		'value':None, # regex
	},
	crc32b('-E'):{ # match file to exclude it
		'name':'fileMatchExclude',
		'short':'-E',
		'long':'--exclude_match_file',
		'accept':True, # accept value
		'value':None, # regex
	},
	crc32b('-w'):{ # filename to write to
		'name':'writeToFile',
		'short':'-w',
		'long':'--write_to_file',
		'accept':True, # accept value
		'value':"", # regex
	},
	crc32b('-d'):{ # set num stats to display
		'name':'displayNumStats',
		'short':'-d',
		'long':'--display_num_stats',
		'accept':True, # accept value
		'value':20, # regex
	},
	crc32b('-R'):{ # set num stats to display
		'name':'removeAccents',
		'short':'-R',
		'long':'--remove_accents',
		'accept':False, # accept value
		'value':False, # True | False
	}
}
#
Stats = {
	'num_files':0, # num of files that was parsed
	'num_lines_before':0,
	'num_lines_after':0,
	'num_uniq_lines':0,
	'num_split':0,
	'num_words':0,
	'num_uniq_words':0,
	'largest_line':-1,
	'shortest_line':-1,
	#'skipped_by_W':0,
	#'skipped_perc':0,
	'parsed_perc':0,
	'same_word_count':0,
	'questions':[],    # ?
	'questions_uniq_check':[],    # ?
	'exclamations':[], # !
	'exclamations_uniq_check':[], # !
	'sentences':[],    # .
	'sentences_uniq_check':[],    # .
}

#
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

#
def prepareWords():
	global WordsUniqIndex,WordsUniq,tmpWordsUniq
	for k in tmpWordsUniq:
		o=tmpWordsUniq[k]
		if o['count'] not in WordsUniq:
			WordsUniq[ o['count'] ] = []
			WordsUniqIndex.append(o['count'])
		WordsUniq[ o['count'] ].append(o['name'])
#
def showWords():
	global Options
	#
	#print("Stats: ")
	#print(Stats)
	#
	prepareWords()
	WordsUniqIndex.sort(reverse=True)
	#
	print("By uniq/count len: {}".format(len(WordsUniqIndex)))
	fn=""
	if format(Options[crc32b('-w')]['value'])!="":
		fn = "{}_rand.txk".format(Options[crc32b('-w')]['value'])
		if fexists(fn):
			os.remove(fn)
	cnt=0
	for c in WordsUniqIndex:
		if Options[crc32b('-w')]['value']!="":
			for n in WordsUniq[c]:
				fwrite(fn,"{}\n".format(n),False)
		else:
			print("{}.) {}x => {}".format(cnt,c,WordsUniq[c]))
		if cnt>Options[crc32b('-d')]['value'] and Options[crc32b('-w')]['value']=="":
			break
		cnt+=1
#
def fixWord( word ):
	a=[]
	word = word.replace('\xa0','...')
	if rmatch(word,".*\.\.\..*"):
		tmp = word.split("...")
		word = tmp[0]
		if len(tmp)>1:
			a.append(tmp[1])
	if rmatch(word,".*\.\.*"):
		tmp = word.split("..")
		word = tmp[0]
		if len(tmp)>1:
			a.append(tmp[1])
	if rmatch(word,".*,.*"):
		tmp = word.split(",")
		word = tmp[0]
		if len(tmp)>1:
			a.append(tmp[1])
	if rmatch(word,".*\?.*"):
		tmp = word.split("?")
		word = tmp[0]
		if len(tmp)>1:
			a.append(tmp[1])
	if rmatch(word,".*\!.*"):
		tmp = word.split("!")
		word = tmp[0]
		if len(tmp)>1:
			a.append(tmp[1])
	nxt=None
	#
	word = word.strip(",.«»?!\r\n ()\"':[]*-_;…").lower()
	word = remove_emoji(word)
	return [word,a]

#
def fillPerc( word ):
	tmpw = word[0:3]
	if crc32b(tmpw) not in tmpTablePerc:
		tmpTablePerc[crc32b(tmpw)] = []
	tmpTablePerc[crc32b(tmpw)].append(word)
#
def preparePerc():
	global tmpWordsPerc, tmpWordsUniq,Stats,tmpTablePerc
	for k1 in tmpWordsUniq:
		w1     = tmpWordsUniq[k1]['name'].replace("-","\-").replace("(","").replace(")","").replace("?","").replace("+","").replace("*","")
		if rmatch(w1,".*([\=|\[|\]|\:]+).*"):
			continue
		w1crc3 = crc32b(w1[0:3])
		if w1crc3 not in tmpTablePerc:
			continue
		a = tmpTablePerc[w1crc3]
		for w in a:
			w2 = w
			b = []
			#
			if len(w1)>5 and len(w2)>=len(w1):
				try:
					#b = pmatch(w2,"(^{}+|^{}+|^{}+)".format(w1,w1[0:len(w1)-1],w1[0:len(w1)-2]))
					b = pmatch(w2,"(^{}+)".format(w1))
				except Exception as E:
					print("d1/{}: {}:{}/{}".format(len(w1),w1,w2,len(w2)))
					continue
			else:
				continue
			#
			if len(b)<=0:
				continue
			#
			if len(b[0]) < Options[crc32b('-W')]['value']:
			#if len(b[0]) <= 6:
				Stats['skipped_perc']+=1
				continue
			#
			perc = round((len(b[0])*100)/len(w2),0)
			# if smaller word in tmpWordsPerc
			if perc not in tmpWordsPerc:
				tmpWordsPerc[perc] = {}
			bcrc = crc32b(b[0])
			if bcrc not in tmpWordsPerc[perc]:
				tmpWordsPerc[perc][bcrc] = {'name':b[0],'names':[]}
			tmpWordsPerc[perc][bcrc]['names'].append( w2 )
			Stats['parsed_perc']+=1
#
def showPerc():
	global Options
	#
	preparePerc()
	#
	print("By percentage len {}, table: {}".format(len(tmpWordsPerc), len(tmpTablePerc)))
	cnt=0
	tmpa=[]
	fn=""
	if format(Options[crc32b('-w')]['value'])!="":
		fn = "{}_perc.txk".format(Options[crc32b('-w')]['value'])
		if fexists(fn):
			os.remove(fn)
	for c in tmpWordsPerc:
		#print("{}.) {} => {}".format(cnt,c,tmpWordsPerc[c]))
		#print("{} / {}) {} => ".format(cnt,len(tmpWordsPerc[c]),c))
		cnt1=0
		for data in tmpWordsPerc[c]:
			name = tmpWordsPerc[c][data]['name']
			crcn = crc32b(name)
			if crcn in tmpa:
				continue
			#print("{} - {}".format(data,tmpWordsPerc[c][data]))
			for c1 in tmpWordsPerc:
				if crcn not in tmpWordsPerc[c1]:
					continue
				if Options[crc32b('-w')]['value']!="":
					for n in tmpWordsPerc[c1][crcn]['names']:
						fwrite(fn,"{}\n".format(n),False)
				else:
					print("and on {}% {}".format(c1,tmpWordsPerc[c1][crcn]['names']))
			tmpa.append(crcn)
			if cnt1>10 and Options[crc32b('-w')]['value']=="":
				break
			cnt1+=1
		if cnt>5 and Options[crc32b('-w')]['value']=="":
			break
		cnt+=1

#
def splitWords( line ):
	global Stats, WordsUniq, WordsUniqIndex, tmpWordsUniq, Options, tmpWordsPerc, tmpTablePerc, WordsUrls
	#
	n=0
	a = line.split(" ")
	while len(a):
		word = a.pop()
		b = fixWord( word )
		word = b[0]
		if len(b[1]):
			a+=b[1]
		if len(word)<Options[crc32b('-W')]['value']:
			n+=1
			continue
		# skip urls and save them separately
		if rmatch(word,"^http.*"):
			WordsUrls.append(word)
			n+=1
			continue
		crcb = crc32b(word)
		# prepare/sort uniq and count
		if crcb not in tmpWordsUniq:
			tmpWordsUniq[crcb] = {'count':1,'name':word}
			Stats['num_uniq_words']+=1
			fillPerc( word )
		else:
			tmpWordsUniq[crcb]['count']+=1
			Stats['same_word_count']+=1
		n+=1
	Stats['num_words']+=n
	return n

#
def splitBy( s ):
	global Stats
	#
	def check( line, linei, word, wordi ):
		for j in range(0,len(word)):
			if (j+linei)>len(line)-1:
				return False
			p1 = j+linei
			p2 = j+wordi
			if line[p1]!=word[p2]:
				return False
		return True
	#
	tmps=""
	cfor=0 # Skip and continue for
	sfor=0
	for i in range(0,len(s)):
		#
		if (i+2)>=len(s) or (i+1)>=len(s):
			continue
		#
		c    = s[i]
		#-- Skip: [1] or [2] or [somenumber]
		if (c=='[' and s[i+1].isdigit() and s[i+2]==']') or (c.isdigit() and s[i+1]==']' and s[i-1]=='[') or c==']' and s[i-1].isdigit() and s[i-2]=='[':
			continue
		#
		#elif (c=='[' and s[i+1]=='o' and s[i+2]=='d'):
		elif (c=='[' and check(s,i,"[odgovori]",0)):
			cfor=len('[odgovori]')
		elif (c=='—' and check(s,i,"— Yerpo Ha?",0)):
			sfor=len('— Yerpo Ha?')
		elif sfor>0:
			sfor-=1
			continue
		elif cfor>0:
			cfor-=1
			if cfor==0:
				tmps=""
			continue
		#-- Append line - sentence
		elif (c=="." and s[i-1]!='i' and s[i-2]!=' ' and s[i-3]!='.' and s[i-4]!='t') and (s[i+1]!=')') and (s[i+1]!='.' and s[i+2]!='.' and s[i-1].isdigit()==False):
			line = "{}.".format( tmps.strip() )
			lcrc = crc32b( line )
			if lcrc not in Stats['sentences_uniq_check']:
				Stats['sentences'].append( line )
				Stats['sentences_uniq_check'].append( lcrc )
			tmps=""
		#-- Append line - questions
		elif (c=="?" and s[i-1]!='i' and s[i-2]!=' ' and s[i-3]!='.' and s[i-4]!='t') and (s[i+1]!=')') and (s[i+1]!='.' and s[i+2]!='.' and s[i-1].isdigit()==False):
			line = "{}?".format( tmps.strip() )
			lcrc = crc32b( line )
			if lcrc not in Stats['questions_uniq_check']:
				Stats['questions'].append( line )
				Stats['questions_uniq_check'].append( lcrc )
			tmps=""
		#-- Append line - exclamations
		elif (c=="!" and s[i-1]!='i' and s[i-2]!=' ' and s[i-3]!='.' and s[i-4]!='t') and (s[i+1]!=')') and (s[i+1]!='.' and s[i+2]!='.' and s[i-1].isdigit()==False):
			line = "{}!".format( tmps.strip() )
			lcrc = crc32b( line )
			if lcrc not in Stats['exclamations_uniq_check']:
				Stats['exclamations'].append( line )
				Stats['exclamations_uniq_check'].append( lcrc )
			tmps=""
		#-- Collect
		else:
			tmps += c
#
def splitLine( line ):
	a=[]
	for i in range(0,len(line),Options[crc32b('-m')]['value']):
		a.append(line[i:i+Options[crc32b('-m')]['value']])
	#
	return a

#
def removeAccents(l):
	#
	#with open( Options[crc32b('-f')]['value'] ) as tf:
	#	for l in tf:
	#		print(unidecode( l ))
	return unidecode( l )
#
def Run(fn=None):
	global Options, Stats, Lines, tmpLines, WordsUrls
	#
	ret = [] # generated lines in one
	#
	if fn==None:
		fn = Options[crc32b('-f')]['value']
	#print("Run() START on fn: {}".format(fn))
	#
	Stats['num_files']+=1
	#
	with open(fn, 'r', encoding='UTF-8') as file:
		while line := file.readline():
			#
			line = line.strip(" ")
			# replace accents for normal letters
			if Options[crc32b('-R')]['value']:
				#
				line = unidecode( line )
			#
			#if line=="\n" or len(line)<10 or rmatch(line,".*\.\.\.+$"):
			if line=="\n" or len(line)<10:
				continue
			# Set some stats: largest_line, shortest_line, 
			if len(line)>Stats['largest_line']:
				Stats['largest_line'] = len(line)
			elif Stats['shortest_line']==-1 or Stats['shortest_line']>len(line):
				Stats['shortest_line'] = len(line)
			#
			#splitBy( line )
			# Split too large line into lines
			if len(line) > Options[crc32b('-m')]['value']:
				tmpret = splitLine( line ) # array of lines divided by maxLine len
				ret += tmpret
				Stats['num_split']+=1
			else:
				ret.append( line )
			#
			Stats['num_lines_before']+=1
	#print("Result: ")
	for line in ret:
		crcl = crc32b( line.lower() )
		if crcl not in tmpLines:
			tmpLines.append(crcl)
			# skip urls and save them separately
			if rmatch(line,"^http.*"):
				WordsUrls.append(line)
				continue
			Lines.append(line)
			splitWords( line )
			splitBy(line)
			Stats['num_uniq_lines']+=1
		Stats['num_lines_after']+=1
	#
	#arrangeWords()

#
def List():
	global Options
	#print("List() START")
	pfn = Options[crc32b('-F')]['value']
	for fn in os.listdir(pfn):
		if Options[crc32b('-M')]['value']!=None and rmatch(fn,Options[crc32b('-M')]['value']):
			tmpfn = "{}{}".format(Options[crc32b('-F')]['value'],fn)
			Run(tmpfn)
		elif Options[crc32b('-E')]['value']!=None and rmatch(fn,Options[crc32b('-E')]['value'])==False:
			tmpfn = "{}{}".format(Options[crc32b('-F')]['value'],fn)
			Run(tmpfn)
		elif Options[crc32b('-E')]['value']==None and Options[crc32b('-M')]['value']==None:
			tmpfn = "{}{}".format(Options[crc32b('-F')]['value'],fn)
			Run(tmpfn)

#
def main(argv):
	global Options, Stats, WordsUniq, WordsUniqIndex, Lines, tmpLines, tmpWordsPerc, tmpWordsUniq, tmpTablePerc, WordsUrls
	opt_help=False
	#
	try:
		opts, args = getopt.getopt(argv,genShortArgs(Options),genLongArgs(Options))
		#
		for opt, arg in opts:
			if crc32b(opt) in Options:
				o = Options[crc32b(opt)]
				if 'accept' in o and o['accept']:
					if type(Options[crc32b(opt)]['value']).__name__ == "int":
						Options[crc32b(opt)]['value'] = int(arg)
					else:
						Options[crc32b(opt)]['value'] = arg
				elif "exec" in o:
					o['exec']()
					sys.exit(1)
				else:
					Options[crc32b(opt)]['value'] = True
	except getopt.GetoptError:
		opt_help = True
	if opt_help:
		print("HELp!")
		sys.exit(1)
	#
	if Options[crc32b('-f')]['value']==None and Options[crc32b('-F')]['value']==None:
		print("You should choose file to work on. Options: -f or -F")
		sys.exit(1)
	#
	if Options[crc32b('-F')]['value']!=None:
		List()
	else:
		Run(Options[crc32b('-f')]['value'])
	#
	#print("WordsUrls( {} ): {}".format(len(WordsUrls),WordsUrls))
	print("WordsUrls( {} )".format(len(WordsUrls)))
	showWords()
	#showPerc()
	#
	justLen=['sentences','exclamations','questions','questions_uniq_check','exclamations_uniq_check','sentences_uniq_check']
	print("Stats: ")
	for k in Stats:
		c=0
		if k in justLen:
			print("{} => justLen: {}".format(k,len(Stats[k])))
			#for k1 in Stats[k]:
			#	print("k1: {}".format(k1))
			#	if c>10:
			#		break
			#	c+=1
		else:
			print("{} => {}".format(k,Stats[k]))
	#print(Stats['sentences'])
	#--
	#
	if Options[crc32b('-w')]['value']!="":
		print("\n\nStarting write to files...\nTip: excat -V {}\n\nTo generate unique vocab from *_perc.txk and *_rand.txk\n\n".format( Options[crc32b('-w')]['value'] ))
		
		# write questions, exclamations, sentences
		fn1 = "{}_sentences.txk".format(Options[crc32b('-w')]['value'])
		if fexists(fn1):
			os.remove(fn1)
		fn2 = "{}_questions.txk".format(Options[crc32b('-w')]['value'])
		if fexists(fn2):
			os.remove(fn2)
		fn3 = "{}_exclamations.txk".format(Options[crc32b('-w')]['value'])
		if fexists(fn3):
			os.remove(fn3)
		#
		for line in Stats['sentences']:
			fwrite(fn1,"{}\n".format(line),False)
		for line in Stats['questions']:
			fwrite(fn2,"{}\n".format(line),False)
		for line in Stats['exclamations']:
			fwrite(fn3,"{}\n".format(line),False)
		
		# write lines to file
		print("writing lines to file/{}: {}".format( len(Lines), Options[crc32b('-w')]['value'] ))
		fn4 = "{}_lines.txk".format(Options[crc32b('-w')]['value'])
		if fexists(fn4):
			os.remove(fn4)
		for line in Lines:
			fwrite(fn4,"{}".format(line),False)
	
		# write vocabs
		showPerc()
		showWords()
	
	#
	del(WordsUrls)
	del(WordsUniq)
	del(WordsUniqIndex)
	del(tmpWordsUniq)
	del(tmpWordsPerc)
	del(tmpLines)
	del(Lines)
	del(Stats)

#--
if __name__ == "__main__":
	main(sys.argv[1:])
