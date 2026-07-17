// ==SiteScript==
// title: Google Search
// name: support_search
// site: google.com
// description: Search Google and return structured results with pagination info. Handles cookie consent, text input, Enter key, captcha detection, result extraction, and page nav links all in one call.
// usage: <SiteScript site="google.com" script="support_search" params='{"query":"python programming"}'/>
// params: query (string) required — the search term
// returns: JSON object with query, url, title, captchaDetected, captchaUrl, results[], pagination{}
// ==/SiteScript==

var query = PARAMS.query || "";
if (!query) {
	return JSON.stringify({error: "No query provided"});
}

// Helper: dispatch keyboard event
function pressEnter(el) {
	el.focus();
	var events = ['keydown', 'keypress', 'input', 'keyup'];
	for (var i = 0; i < events.length; i++) {
		el.dispatchEvent(new KeyboardEvent(events[i], {
			key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
			bubbles: true, cancelable: true, composed: true
		}));
	}
}

// Helper: extract results from current page
function extractResults() {
	var results = [];
	var items = document.querySelectorAll('#search .g, #rso .g, [data-hveid] .g');
	items.forEach(function(item) {
		var linkEl = item.querySelector('a[href^="http"]');
		var titleEl = item.querySelector('h3');
		var snippetEl = item.querySelector('.VwiC3b, [data-sncf], .lEBKkf span, .st');
		if (linkEl && titleEl) {
			results.push({
				title: titleEl.innerText.trim(),
				url: linkEl.href,
				snippet: snippetEl ? snippetEl.innerText.trim() : ''
			});
		}
	});
	return results;
}

// Helper: extract pagination info
function extractPagination() {
	var pages = [];
	var pageLinks = document.querySelectorAll('.AaVjTc .NKTSme a.fl, .AaVjTc td a.fl');
	pageLinks.forEach(function(a) {
		var pageNum = a.innerText.trim();
		if (pageNum && !isNaN(parseInt(pageNum))) {
			pages.push({page: parseInt(pageNum), url: a.href});
		}
	});
	var nextBtn = document.getElementById('pnnext');
	return {
		pages: pages,
		nextUrl: nextBtn ? nextBtn.href : null,
	};
}

// Check if already on search results (from WWW siteScript auto-exec)
var isSearchPage = window.location.href.indexOf('/search?') !== -1;

if (isSearchPage) {
	// Already on a search page — check if query matches
	var currentQuery = (new URLSearchParams(window.location.search)).get('q') || '';
	if (currentQuery.toLowerCase() !== query.toLowerCase()) {
		// Different query — need to search
		var searchBox = document.getElementById('APjFqb');
		if (searchBox) {
			searchBox.value = query;
			pressEnter(searchBox);
		} else {
			window.location.href = "https://www.google.com/search?q=" + encodeURIComponent(query) + "&num=10";
		}
	}
} else {
	// On homepage or other page — navigate or fill search
	var searchBox = document.getElementById('APjFqb');
	if (searchBox) {
		searchBox.value = query;
		pressEnter(searchBox);
	} else {
		window.location.href = "https://www.google.com/search?q=" + encodeURIComponent(query) + "&num=10";
	}
}

// Wait for results to load
await new Promise(function(r) { setTimeout(r, 4000); });

// Check for captcha
var captchaDetected = window.location.href.indexOf('/sorry/') !== -1;

// Extract results
var results = extractResults();
var pagination = extractPagination();

var output = {
	query: query,
	url: window.location.href,
	title: document.title,
	captchaDetected: captchaDetected,
	captchaUrl: captchaDetected ? window.location.href : null,
	resultCount: results.length,
	results: results,
	pagination: pagination,
};

return JSON.stringify(output, null, 2);
