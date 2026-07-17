# github.com

GitHub — repository search, README extraction, and user/profile lookups.

## Scripts

### support_search_repos
- **title**: GitHub Repository Search
- **description**: Search GitHub repositories by keyword and return structured results with stars, description, and language.
- **usage**: `<SiteScript site="github.com" script="support_search_repos" params='{"query":"machine learning"}'/>`
- **params**: query (string) required — search keywords
- **returns**: JSON object with query, resultCount, results[{name, url, owner, description, stars, language, updated}]

### support_get_readme
- **title**: GitHub Get README
- **description**: Load a repository page and extract the README content as markdown text.
- **usage**: `<SiteScript site="github.com" script="support_get_readme" params='{"repo":"torvalds/linux"}'/>`
- **params**: repo (string) required — full repo name like "owner/repo"
- **returns**: JSON object with repo, url, readme text (truncated), readmeLength

## Notes
- GitHub may rate-limit unauthenticated requests. Cookie file recommended.
- Navigate to github.com with `<WWW browser="true">` once to log in, cookies auto-save.
- README extraction relies on the rendered markdown body DOM structure.
