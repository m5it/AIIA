from functions import crc32b,fwrite
from pyquery import PyQuery as pq
#
def action( G, url, text ):
	print("action() STARtinG, url: {}, text: \n{}".format(url,text))
	#
	urlfile = "{}.txk".format(crc32b(url))
	#
	if crc32b(url) not in G['stats']:
		G['stats'][crc32b(url)] = {
			"url"      :url,
			"num_posts":0,
			"posts_len":0,
			"tags":[],
		}
	# remove some html tags if anoy us
	d = pq(text)
	for item in d.items("script"):
		print("script tag: {}".format(item))
		item.remove()
	# get tags if available
	for item in d.items(".tags li"):
		print("tag: {}".format( item.text().lower() ))
		G['stats'][crc32b(url)]['tags'].append( item.text().lower() )
	#
	d(".tags").remove()
	#
	text = d.text()
	#print("text after: \n{}".format(text))
	#
	G['stats'][crc32b(url)]['num_posts']+=1
	G['stats'][crc32b(url)]['posts_len']+=len(text)
	#
	fwrite("{}{}".format(G['dir'],urlfile),"{}\n\x09\r\n".format(text), False)
#
G = {
	'dir':'data/slo/ringaraja_clanki2/',
	'url':'https://www.ringaraja.net',
	'start_query':'',
	'query':'',
	'stats':{},
}

#
C = [{
	'css':'a',
	'get_attr':'href',
	'get_check_http':True,
	'get_if_match':'.*\/clanki.*',
	'continue':[{
		'css':'a',
		'get_attr':'href',
		'get_check_http':True,
		'get_if_match':'.*\/clanek.*',
		'continue':[{
			'css':'#dr_article .visual-box',
			#'get_text':True,
			'get_html':True,
			'action':action,
			'loop':True,
		},
		{
			'css':'a',
			'get_attr':'href',
			'get_check_http':True,
			'get_if_match':'.*\/clanek.*',
			'continue':[{
				'css':'#dr_article .visual-box',
				#'get_text':True,
				'get_html':True,
				'action':action,
				'loop':True,
			}],
		}],
	}],
}
]
