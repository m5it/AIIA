//
const https = require('https');
//
var crc32b=function(r){for(var a,o=[],c=0;c<256;c++){a=c;for(var f=0;f<8;f++)a=1&a?3988292384^a>>>1:a>>>1;o[c]=a}for(var n=-1,t=0;t<r.length;t++)n=n>>>8^o[255&(n^r.charCodeAt(t))];return((-1^n)>>>0).toString(16).toLowerCase();};
//
var arga = [crc32b('-u')];
var argv={}
for(var i=0; i<arga.length; i++) {
	argv[arga[i]] = {'short_arg':'-u','desc':'Set url to retrive source...','value':'',}
}
const args = process.argv.slice(2); // Slice to remove the first two elements
//
for(var i=0; i<args.length; i++) {
	var arg = args[i];
	for(j=0; j<arga.length; j++) {
		if(arg==argv[arga[j]]['short_arg']) {
			argv[crc32b('-u')].value = args[i+1];
		}
	}
}
//
if( argv[crc32b('-u')].value=="" ) {
	console.log("Error: missing -u as url to open!");
	return false;
}
// prepare hostname and path from -u
var host=""; //'www.example.com'
var path=""; // /
var url = decodeURIComponent(argv[crc32b('-u')].value);
if(url.match(".*\%3A.*")) {
	url = decodeURIComponent(url);
}
if(url.match("#")) {
	url = url.split("#")[0];
}
url = url.replace("\n","").replace("\r","").replace(" ","");
//console.log("url: ",url);

var a = url.match("(^http[s]?\:\/\/).*");
if(a!=null && a.length>1) {
	host = url.replace(a[1],"");
	a = host.match("\/");
	if(a!=null && a.length) {
		path = host.substr(a.index);
		host = host.substr(0,a.index);
	} else {
		path = "/";
	}
}
else return false;
//
const options = {
	hostname: host,
	path: path,
	headers: {
		'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
	}
};
//console.info("options: ",options);
//return false;
//
try {
	https.get(options, function(res) {
	    console.log(res.statusCode);
	    if( res.statusCode==301 ) {
		    console.log("301:"+res.headers.location);
		}
	    //console.log(res.location);
	    res.setEncoding('utf8');
	    res.on('data', function(data) {
	        console.log(data);
	    });
	}).on('error', function(err) {
	    console.log(err);
	});
} catch(err) {
	console.log("400");
}

