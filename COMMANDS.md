# COMMANDS.md — Quick Reference

## Quick Start

```bash
source .venv/bin/activate          # activate Python env
python run.py                       # interactive session (default: Developer, gemma3:12b)
python run.py -Q -p Developer       # quick mode — skip intro prompts
python run.py -Y "your prompt"      # single request, no session
python run.py -p BookSmithAnalyst   # use a specific persona
python run.py -m llama3:70b         # use a different Ollama model
python run.py -d                    # enable debug output
python run.py -T 0.8                # set temperature
```

## Personas

| Persona | Mode | Purpose |
|---------|------|---------|
| `Developer` (default) | plan | General software engineering |
| `DeveloperV2` | plan | Same + explicit stop signals |
| `DeveloperV3` | plan | Same + framework-awareness |
| `MediaAnalyst` | plan | Image/video analysis (uses qwen3-vl) |
| `BookSmith` | build | Book analysis & writing (original) |
| `BookSmithV2` | plan | Book analysis/writing + stop signals |
| `BookSmithV3` | plan | Book analysis/writing + long-context |
| `BookSmithAnalyst` | plan | Literary/critical analysis |
| `BookSmithNovelist` | build | Fiction writing |
| `BookSmithPoet` | build | Poetry writing |
| `BookSmithEditor` | build | Editing & revision |

## User Commands (interactive session)

| Command | What it does |
|---------|-------------|
| `!MODE plan` or `!MODE build` | Switch between plan and build mode |
| `!START_BUILD` | Switch to build mode (Enter for message prompt, Ctrl+X to skip) |
| `!MODELS` | List Ollama models (starred = used before) |
| `!MODEL <name>` | Switch model mid-session (e.g. `!MODEL llama3:70b`) |
| `!PLAN PREVIEW` / `VIEW` / `TASKS` / `STATUS` | View plan state |
| `!HELP` | Show all available commands |
| `!STATS` | Token usage stats |
| `!NEW SESSION` | Full reset (clears history, cache) |
| `!INSTALL_DEPS [persona]` | Install missing dependencies for a persona |
| `!SITE_LIST` | List all websites with JS support scripts |
| `!SITE <domain>` | Show scripts for a site (e.g. `!SITE google.com`) |
| `!SITE_UPDATE <domain> <script>` | Create/update a site script |

**In plan mode**, when the AI tries to write files, you'll see:
- `1` — let it proceed (switch to build)
- `2` — let AI continue planning
- `3` — cancel
- `4` — allow the blocked action

## Testing Site Scripts

### 1. List available sites
```xml
<SiteScript>
<action>list</action>
</SiteScript>
```

### 2. See what scripts a site has
```xml
<SiteScript>
<site>google.com</site>
<action>info</action>
</SiteScript>
```

### 3. Search Google
```xml
<SiteScript>
<site>google.com</site>
<script>support_search</script>
<params>{"query":"latest AI news 2026"}</params>
</SiteScript>
```

### 4. Search GitHub repos
```xml
<SiteScript>
<site>github.com</site>
<script>support_search_repos</script>
<params>{"query":"machine learning"}</params>
</SiteScript>
```

### 5. Get a GitHub README
```xml
<SiteScript>
<site>github.com</site>
<script>support_get_readme</script>
<params>{"repo":"torvalds/linux"}</params>
</SiteScript>
```

## Cookie Setup (for captcha/login)

```xml
<!-- Open a browser window to accept cookies / log in -->
<WWW>
<url>https://google.com</url>
<browser>true</browser>
</WWW>
```
Close the browser — cookies auto-save. Enable in `config.py`:
```python
"COOKIE_FILE": "tools/cookies.json",
```

## Common XML Tools

```xml
<!-- Read a file -->
<ReadFile>
<fileName>workin/somefile.txt</fileName>
</ReadFile>

<!-- Write a file -->
<WriteFile>
<fileName>output.py</fileName>
<contentOfFile>print("hello")</contentOfFile>
</WriteFile>

<!-- Run a shell command -->
<Terminal>
<arg1>ls</arg1>
<arg2>-la</arg2>
</Terminal>

<!-- Grep for text -->
<Grep>
<pattern>def main</pattern>
<fileName>*.py</fileName>
<recursive>true</recursive>
</Grep>

<!-- Search files by name -->
<Find>
<pattern>*.md</pattern>
</Find>

<!-- Save a tip (persists across sessions) -->
<SaveTip>
<title>api_key_notes</title>
<content>API base URL: https://api.example.com/v1</content>
</SaveTip>

<!-- Retrieve a tip -->
<GetTip>
<title>api_key_notes</title>
</GetTip>

<!-- Read a PDF -->
<ReadPDF>
<fileName>book.pdf</fileName>
<fromPage>1</fromPage>
<toPage>10</toPage>
</ReadPDF>
```

## Orchestra (multi-worker)

```bash
# Terminal 1: start the director
python run_orchestra.py --port 9876

# Terminal 2+: start workers
python run_worker.py --connect localhost:9876 --name w1 -m gemma3:12b
python run_worker.py --connect localhost:9876 --name w2 -m llama3:70b
```

## Per-Project Config

Place `aiia.json` in your project directory:

```json
{
  "AI_MODEL": "gemma3:12b",
  "AI_OPTIONS": {
    "temperature": 0.8,
    "num_ctx": 65536
  },
  "MODE": "build",
  "AI_MAX_ITERATIONS": 20,
  "AI_THINK": false
}
```

Override priority: CLI flags > `aiia.json` > `config.py`

## Auto-Versioning

```bash
git config core.hooksPath hooks
```
Auto-increments `AUTOVERSION.py` on every commit, appends to `CHANGELOG.md` (skips merge commits).

## Project Layout

```
.
├── run.py / run_orchestra.py / run_worker.py   # entry points
├── src/                  # core: Handle.py, Commands.py, ToolParser.py, ...
├── instruct/             # persona definitions (Developer, BookSmith*, ...)
├── tools/                # XML tool implementations (tool_*.py)
├── wwwurljssupport/      # per-site JS support scripts
│   ├── google.com/       #   support_search.js, support_load.js
│   └── github.com/       #   support_search_repos.js, support_get_readme.js
├── history/              # session chat history (gitignored)
├── workin/ / workout/    # tool I/O directories (gitignored)
└── config.py             # global defaults + options
```
