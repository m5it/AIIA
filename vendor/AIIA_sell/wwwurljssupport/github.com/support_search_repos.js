// ==SiteScript==
// title: GitHub Repository Search
// name: support_search_repos
// site: github.com
// description: Search GitHub repositories by keyword and return structured results with stars, description, and language.
// usage: <SiteScript site="github.com" script="support_search_repos" params='{"query":"machine learning"}'/>
// params: query (string) required — search keywords
// returns: JSON object with query, resultCount, results[{name, url, owner, description, stars, language, updated}]
// ==/SiteScript==

var query = PARAMS.query || "";
if (!query) {
	return JSON.stringify({error: "No query provided"});
}

window.location.href = "https://github.com/search?q=" + encodeURIComponent(query) + "&type=repositories";
await new Promise(function(r) { setTimeout(r, 5000); });

var results = [];
var items = document.querySelectorAll('[data-testid="results-list"] > div, .repo-list-item');
if (items.length === 0) {
	// Fallback: look for repo cards in the search results
	items = document.querySelectorAll('div[data-hpc] a[href*="/"]');
}

items.forEach(function(item) {
	var linkEl = item.querySelector('a[data-hydro-click][href], a[href^="/"][href*="/"]');
	if (!linkEl) return;
	var href = linkEl.getAttribute('href');
	if (!href || href.split('/').length < 3) return;
	var descEl = item.querySelector('.color-fg-muted, p, .description');
	var starsEl = item.querySelector('[aria-label*="star"], .star, .octicon-star');
	var langEl = item.querySelector('[itemprop="programmingLanguage"], .language, .repo-language-color + span');
	var updatedEl = item.querySelector('relative-time, [datetime]');
	results.push({
		name: linkEl.innerText.trim() || href,
		url: 'https://github.com' + href,
		owner: href.split('/')[1] || '',
		repo: href.split('/')[2] || '',
		description: descEl ? descEl.innerText.trim() : '',
		stars: starsEl ? starsEl.innerText.trim() : '',
		language: langEl ? langEl.innerText.trim() : '',
	});
});

var output = {
	query: query,
	url: window.location.href,
	resultCount: results.length,
	results: results,
};

return JSON.stringify(output, null, 2);
