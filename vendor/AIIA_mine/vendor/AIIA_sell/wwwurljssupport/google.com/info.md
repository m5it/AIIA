# google.com

Google Search — supports search queries and result extraction via JS support scripts.

## Scripts

### support_search
- **title**: Google Search
- **description**: Search Google and return structured results with pagination info. Handles cookie consent, text input, Enter key, captcha detection, result extraction, and page nav links all in one call.
- **usage**: `<SiteScript site="google.com" script="support_search" params='{"query":"text"}'/>`
- **params**: query (string) required — the search term
- **returns**: JSON object with query, url, title, captchaDetected (bool), captchaUrl (string|null), resultCount (int), results (array of {title, url, snippet}), pagination ({pages, nextUrl})

### support_load
- **title**: Google Load Handler
- **description**: Handles cookie consent popup and returns page metadata after loading. Auto-executed when `<WWW siteScript="true">` is used.
- **usage**: `<WWW url="https://www.google.com" siteScript="true"/>`
- **params**: (none)
- **returns**: JSON object with url, title, status, hasSearchBox

## Version History
When a script is updated via `<UpdateSiteScript>`, the old version is saved to `_history/<name>.v<N>.js` (last 10 versions kept).

## Notes
- Google may return CAPTCHA after repeated automated requests (check `captchaDetected` in response).
- Cookie file recommended — navigate once with `<WWW browser="true">`, solve CAPTCHA interactively, then cookies auto-save.
- Scripts rely on the page's DOM structure which may change over time. Use `<UpdateSiteScript>` to fix.
