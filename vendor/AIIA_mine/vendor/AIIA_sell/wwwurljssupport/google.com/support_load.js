// ==SiteScript==
// title: Google Load Handler
// name: support_load
// site: google.com
// description: Handles cookie consent popup and returns page metadata after loading.
// usage: <WWW url="https://www.google.com" siteScript="true"/>
// returns: JSON object with url, title, status, and whether search box was found
// ==/SiteScript==

await new Promise(r => setTimeout(r, 2000));

var cookieBtn = document.querySelector('button:contains("Reject all")') ||
                document.querySelector('[aria-label="Reject all"]') ||
                document.querySelector('#W0wltc') ||
                document.querySelector('form[action*="consent"] button');
if (cookieBtn) {
	cookieBtn.click();
	await new Promise(r => setTimeout(r, 1000));
}

var result = {
	url: window.location.href,
	title: document.title,
	status: 'loaded',
	hasSearchBox: !!document.querySelector('input[name="q"]'),
};

return JSON.stringify(result);
