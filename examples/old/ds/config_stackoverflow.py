
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
			#"tags"     :[],
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
	'dir':'data/stackoverflow/html/',
	'url':'https://stackoverflow.com',
	#'start_query':'/questions/16597358/how-to-split-a-php-class-to-separate-files',
	#'start_query':'/questions/7372972/how-do-i-parse-a-html-page-with-node-js',
	'start_query':'/questions/4282413/sort-array-of-objects-by-one-property',
	# https://stackoverflow.com/questions/15414810/whats-the-difference-of-host-and-http-host-in-nginx
	'query':'',
	'stats':{},
}

#
C = [{
	'css':'a',
	'get_attr':'href',
	'get_check_http':True,
	'get_if_match':'^https...stackoverflow.com..*',
	'continue':[{
		'css':'a',
		'get_attr':'href',
		'get_check_http':True,
		'get_if_match':'^https...stackoverflow.com..*',
		},
		{ # open href and continue with next command
		'css':'div.inner-content',
		'get_html':True,
		'action':action,
		'loop':True,
	}],
}]
