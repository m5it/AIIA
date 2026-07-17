// ==SiteScript==
// title: GitHub Get README
// name: support_get_readme
// site: github.com
// description: Load a repository page and extract the README content as markdown text.
// usage: <SiteScript site="github.com" script="support_get_readme" params='{"repo":"torvalds/linux"}'/>
// params: repo (string) required — full repo name like "owner/repo"
// returns: JSON object with repo, url, readme text (truncated to 10000 chars), readmeLength
// ==/SiteScript==

var repo = PARAMS.repo || "";
if (!repo) {
	return JSON.stringify({error: "No repo provided. Use params: {\"repo\":\"owner/name\"}"});
}

window.location.href = "https://github.com/" + repo;
await new Promise(function(r) { setTimeout(r, 5000); });

var readmeEl = document.querySelector('article.markdown-body, div#readme .markdown-body, div.Box-body .markdown-body');
var text = readmeEl ? readmeEl.innerText.trim() : '';
var truncated = text;
var wasTruncated = false;
if (truncated.length > 10000) {
	truncated = truncated.substring(0, 10000) + "\n\n... (truncated at 10000 chars, full length: " + text.length + ")";
	wasTruncated = true;
}

var output = {
	repo: repo,
	url: window.location.href,
	readme: truncated,
	readmeLength: text.length,
	truncated: wasTruncated,
};

return JSON.stringify(output, null, 2);
