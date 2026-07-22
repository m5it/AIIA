from functions import crc32b,fwrite
#
def action( G, url, text ):
	print("Firing action(), url: {}, text: {}".format(url, text))
	#
	if crc32b(url) not in G['stats']:
		G['stats'][crc32b(url)] = {
			"url"      :url,
			"num_posts":0,
			"posts_len":0,
			"tags"     :[],
		}
	#
	G['stats'][crc32b(url)]['num_posts']+=1
	G['stats'][crc32b(url)]['posts_len']+=len(text)
	#
	urlfile = "{}.txk".format(crc32b(url))
	fwrite("{}{}".format(G['dir'],urlfile),"{}\n\x09\r\n".format(text), False)

#
G = {
	'dir':'data/slo/ringaraja_forum/',
	'url':'https://www.ringaraja.net',
	#'start_query':'/forum/Zanositev/forumid_202/tt.htm',
	#'start_query':'/forum/Nosečnost/forumid_204/tt.htm',
	#'start_query':'/forum/Dojenček/forumid_205/tt.htm',
	#'start_query':'/forum/Otrok/forumid_206/tt.htm',
	#'start_query':'/forum/Fit/forumid_264/tt.htm',
	#'start_query':'/forum/Partnerstvo/forumid_207/tt.htm',
	#'start_query':'/forum/Dru%C5%BEinsko%20%C5%BEivljenje/forumid_208/tt.htm',
	#'start_query':'/forum/Skupnost%20RR/forumid_209/tt.htm',
	'query':'',
	'stats':{},
}

#
C = [{
	'css':'a.subhead',
	'get_attr':'href',
	'get_check_http':True,
	'continue':[{
		'css':'a.subhead',
		'get_attr':'href',
		'get_check_http':True,
		'continue':[{
			'css':'a',
			'get_attr':'href',
			'get_check_http':True,
			'get_if_match':'.*tm.htm',
			#'continue_if_match':'.*mpage\_.*',
			'continue':[{
				'css':'.msg',
				'get_text':True,
				'action':action,
			}],
		}],
	}],
}]
