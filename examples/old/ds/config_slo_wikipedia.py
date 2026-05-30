from functions import crc32b,fwrite,fexists
#
def action( G, url, text ):
	print("Firing action(), url: {}, text.len: {}".format(url, len(text)))
	#
	#
	urlfile = "{}.txk".format(crc32b(url))
	urlfp   = "{}{}".format(G['dir'],urlfile)
	if fexists( urlfp ):
		return False
	#
	if crc32b(url) not in G['stats']:
		G['stats'][crc32b(url)] = {
			"url"      :url,
			"num_posts":0,
			"posts_len":0,
			"tags"     :[],
		}
	else:
		print("ACTION() url exists! {}".format(url))
		return False
	#
	G['stats'][crc32b(url)]['num_posts']+=1
	G['stats'][crc32b(url)]['posts_len']+=len(text)
	#
	fwrite(urlfp,"{}".format(text), False)
	return True

#
G = {
	'dir':'data/slo/wikipedia/',
	'url':'https://sl.wikipedia.org',
	#'start_query':'/wiki/Glagol',
	'start_query':'/wiki/Besedna_vrsta',
	'query':'',
	'stats':{},
}

#
C = [{
	'css':'a',
	'get_attr':'href',
	'get_check_http':True,
	'get_if_match':'^https...sl\..*',
	'continue':[{ # open href and continue with next command
		'css':'#mw-content-text',
		'get_html':True,
		'action':action,
		'loop':True,
	}],
}]
