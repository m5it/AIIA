# XML Tool Call Reference

All tools are invoked by writing XML blocks in your chat response to the AI. The format is:

```xml
<ToolName>
<param1>value1</param1>
<param2>value2</param2>
</ToolName>
```

---

## File Operations

### ReadFile
Read a plain text file from `workin/`.
```xml
<ReadFile>
<fileName>workin/config.json</fileName>
</ReadFile>
```

### ReadPDF
Extract text from PDF files. Supports page ranges and character limits.
```xml
<ReadPDF>
<fileName>book.pdf</fileName>
</ReadPDF>

<!-- With options -->
<ReadPDF>
<fileName>book.pdf</fileName>
<fromPage>5</fromPage>
<toPage>20</toPage>
<limit>5000</limit>
</ReadPDF>
```

### WriteFile
Write content to `workout/` (overwrites if exists). Use for content < 4096 bytes.
```xml
<WriteFile>
<fileName>hello.py</fileName>
<contentOfFile>print("Hello World")</contentOfFile>
</WriteFile>
```

### AppendFile
Append content to existing file in `workout/`. Use for content > 4096 bytes or adding to existing files.
```xml
<AppendFile>
<fileName>output.txt</fileName>
<contentOfFile>more data here</contentOfFile>
</AppendFile>

<!-- With line number -->
<AppendFile>
<fileName>output.txt</fileName>
<contentOfFile>insert this</contentOfFile>
<fromLineNumber>5</fromLineNumber>
</AppendFile>
```

### CreateFile
Create a new file in `workout/` (fails if exists). Use WriteFile instead to overwrite.
```xml
<CreateFile>
<fileName>newfile.sh</fileName>
<contentOfFile>#!/bin/bash
echo "new"</contentOfFile>
</CreateFile>
```

### ReplaceLine
Replace specific line(s) in a file. **TWO-STEP: preview first, then confirm.**
```xml
<!-- Step 1: Preview (no <confirmed>) -->
<ReplaceLine>
<fileName>config.py</fileName>
<fromLine>10</fromLine>
<toLine>12</toLine>
<replacement>DEBUG = True
LOG_LEVEL = "info"</replacement>
</ReplaceLine>

<!-- Step 2: Confirm -->
<ReplaceLine>
<fileName>config.py</fileName>
<fromLine>10</fromLine>
<toLine>12</toLine>
<replacement>DEBUG = True
LOG_LEVEL = "info"</replacement>
<confirmed>true</confirmed>
</ReplaceLine>
```

### Sed
Find/replace in a file. Supports regex patterns.
```xml
<Sed>
<pattern>old_text</pattern>
<replacement>new_text</replacement>
<fileName>file.txt</fileName>
<inplace>true</inplace>
</Sed>
```

---

## Navigation & Search

### List
List files in a directory.
```xml
<List/>
<List>
<path>src</path>
</List>
```

### TreeView
ASCII tree of directory structure.
```xml
<TreeView/>
<TreeView>
<path>.</path>
<depth>0</depth>
</TreeView>
<TreeView>
<path>src</path>
<depth>3</depth>
<pattern>*.py</pattern>
</TreeView>
```

### Find
Find files by glob pattern.
```xml
<Find>
<pattern>*.py</pattern>
</Find>
<Find>
<pattern>README*</pattern>
<path>docs</path>
</Find>
```

### Grep
Regex search within file contents.
```xml
<Grep>
<pattern>def main</pattern>
</Grep>
<Grep>
<pattern>import os</pattern>
<fileName>*.py</fileName>
<recursive>true</recursive>
</Grep>
```

### Diff
Compare two files.
```xml
<Diff>
<file1>old.txt</file1>
<file2>new.txt</file2>
</Diff>
<Diff>
<file1>v1.py</file1>
<file2>v2.py</file2>
<unified>5</unified>
</Diff>
```

---

## File Inspection

### Head
First N lines of a file.
```xml
<Head>
<fileName>log.txt</fileName>
<lines>20</lines>
</Head>
```

### Tail
Last N lines of a file.
```xml
<Tail>
<fileName>log.txt</fileName>
<lines>20</lines>
</Tail>
```

### Sort
Sort lines in a file.
```xml
<Sort>
<fileName>list.txt</fileName>
</Sort>
<Sort>
<fileName>numbers.txt</fileName>
<numeric>true</numeric>
<reverse>true</reverse>
<unique>true</unique>
</Sort>
```

---

## Execution

### Terminal
Execute shell commands (one-liners). Args are positional. Optional `<timeout>` param (seconds, default 30, 0 for no limit).
```xml
<Terminal>
<arg1>ls</arg1>
<arg2>-la</arg2>
</Terminal>
<Terminal>
<arg1>python3</arg1>
<arg2>-c</arg2>
<arg3>print(sum(range(100)))</arg3>
<timeout>60</timeout>
</Terminal>
```

### ExecuteScript
Run `.py`, `.sh`, `.js` scripts from anywhere.
```xml
<ExecuteScript>
<fileName>build.sh</fileName>
</ExecuteScript>
<ExecuteScript>
<fileName>test.py</fileName>
<args>--verbose</args>
</ExecuteScript>
```

### listTools
Show all available tools (cached 10 min).
```xml
<listTools/>
```

---

## Web & Browser

### WWW
Fetch a web page. Also invocable as `<www>` or `<WWWJS>`.
```xml
<!-- Basic text fetch -->
<WWW>
<url>https://example.com</url>
<text>true</text>
</WWW>

<!-- With JS rendering -->
<WWW>
<url>https://example.com/page</url>
<js>true</js>
<text>true</text>
</WWW>

<!-- Open in browser (for cookies/login) -->
<WWW>
<url>https://google.com</url>
<browser>true</browser>
</WWW>

<!-- Extract links -->
<WWW>
<url>https://example.com</url>
<links>true</links>
</WWW>

<!-- Take screenshot -->
<WWW>
<url>https://example.com</url>
<screenshot>true</screenshot>
</WWW>

<!-- Auto-execute site's support_load.js after page load -->
<WWW>
<url>https://google.com</url>
<siteScript>true</siteScript>
</WWW>
```

### WWWExec
Execute JavaScript on the currently loaded page (in the persistent browser).
```xml
<WWWExec>
<js>document.title</js>
</WWWExec>
<WWWExec>
<js>document.querySelectorAll('a').length</js>
<wait>1000</wait>
</WWWExec>
```

### SiteScript
Execute pre-built JS support scripts for specific websites.
```xml
<!-- List all supported sites -->
<SiteScript>
<action>list</action>
</SiteScript>

<!-- Show scripts for a specific site -->
<SiteScript>
<site>google.com</site>
<action>info</action>
</SiteScript>

<!-- Execute a script -->
<SiteScript>
<site>google.com</site>
<script>support_search</script>
<params>{"query":"python tutorials"}</params>
</SiteScript>
```

### UpdateSiteScript
Create or update a per-website JS support script. Old versions auto-backup to `_history/`.
```xml
<!-- Create/update a script -->
<UpdateSiteScript>
<site>example.com</site>
<script>get_data</script>
<content>// ==SiteScript==
// title: Example Data Extractor
// name: get_data
// site: example.com
// description: Extract structured data from example.com
// usage: <SiteScript site="example.com" script="get_data"/>
// params: none
// returns: JSON object with data
// ==/SiteScript==

var data = document.querySelectorAll('.item');
var results = [];
data.forEach(function(el) {
  results.push(el.innerText.trim());
});
return JSON.stringify(results);
</content>
</UpdateSiteScript>

<!-- Delete a script -->
<UpdateSiteScript>
<site>example.com</site>
<script>get_data</script>
<action>delete</action>
</UpdateSiteScript>
```

---

## Media

### ReadImage
Read an image file and pass it to the AI (vision model required, e.g. `qwen3-vl`).
```xml
<ReadImage>
<fileName>screenshot.png</fileName>
</ReadImage>
<ReadImage>
<fileName>photo.jpg</fileName>
<prompt>Describe what you see in this image</prompt>
</ReadImage>
```

### ImageTransform
Resize, crop, convert, flip, or rotate images.
```xml
<!-- Resize -->
<ImageTransform>
<fileName>photo.jpg</fileName>
<operation>resize</operation>
<params>{"maxWidth":800,"maxHeight":600}</params>
</ImageTransform>

<!-- Crop -->
<ImageTransform>
<fileName>photo.jpg</fileName>
<operation>crop</operation>
<params>{"x":100,"y":50,"width":400,"height":300}</params>
</ImageTransform>

<!-- Convert format -->
<ImageTransform>
<fileName>image.png</fileName>
<operation>convert</operation>
<params>{"format":"jpeg"}</params>
</ImageTransform>

<!-- Flip horizontal -->
<ImageTransform>
<fileName>photo.jpg</fileName>
<operation>flip</operation>
<params>{"direction":"horizontal"}</params>
</ImageTransform>

<!-- Rotate -->
<ImageTransform>
<fileName>photo.jpg</fileName>
<operation>rotate</operation>
<params>{"degrees":90}</params>
</ImageTransform>
```

---

## Time

### CurrentTime
Get the current date and time.
```xml
<CurrentTime/>
<CurrentTime>
<format>%Y-%m-%d %H:%M:%S</format>
</CurrentTime>
<CurrentTime>
<format>%A, %B %d</format>
<timezone>US/Eastern</timezone>
</CurrentTime>
```

---

## Memory (Tips)

Tips persist across sessions in `~/.config/aiia/tips/`.

### SaveTip
Save a note with title and content.
```xml
<SaveTip>
<title>character_john</title>
<content>John is a detective, age 45, cynical but fair. Lives alone, drives a 1967 Mustang. Key flaw: trusts no one.</content>
</SaveTip>
```

### GetTip
Retrieve a saved tip by title.
```xml
<GetTip>
<title>character_john</title>
</GetTip>
```

### ListTips
List all saved tips.
```xml
<ListTips/>
<ListTips>
<source>model_storage</source>
</ListTips>
```

### DeleteTip
Delete a tip by title.
```xml
<DeleteTip>
<title>character_john</title>
</DeleteTip>
```

### ReinsertTip
Reinsert a tip's content back into the current chat history (so the AI sees it).
```xml
<ReinsertTip>
<title>character_john</title>
</ReinsertTip>
```

---

## Plan Management

These control the plan/build loop — only available when a plan is active.

```xml
<!-- Create/update a plan -->
<createPlan>
<title>Implement feature X</title>
<instructions>Add search functionality to the app. Steps: 1) Add search bar component 2) Wire up backend endpoint 3) Add tests</instructions>
</createPlan>

<!-- Add task to current plan -->
<createTask>
<title>Add search bar</title>
<instruction>Create a search bar component in src/components/SearchBar.vue with debounced input</instruction>
</createTask>

<!-- View current plan -->
<viewTask/>

<!-- View specific task -->
<viewTask>
<id>task_1</id>
</viewTask>

<!-- List all tasks -->
<listTasks/>

<!-- Mark task completed/blocked -->
<nextTask>completed</nextTask>
<nextTask>blocked</nextTask>

<!-- Log progress on current task -->
<LogProgress>
<taskId>task_1</taskId>
<whatWasDone>Created SearchBar.vue with debounced input, styled with Tailwind</whatWasDone>
</LogProgress>

<!-- Signal planning is done, execute first pending task -->
<planDone/>

<!-- Finish the plan entirely -->
<jobDone/>

<!-- Cancel current plan -->
<cancelPlan/>
```

---

## Tips

- **ReplaceLine** is two-step: preview (no `<confirmed>`) → confirm (`<confirmed>true</confirmed>`). Always ReadFile first to get correct line numbers.
- **WWW** and **WWWExec** share a persistent browser session. Cookies are saved if `COOKIE_FILE` is configured.
- **SiteScript** scripts live in `wwwurljssupport/<domain>/` with a `// ==SiteScript==` metadata header.
- **listTools** result is cached for 10 minutes. Use `!CACHE_CLEAR` or `!NEW SESSION` to invalidate.
- All file tools operate on `workin/` (input) and `workout/` (output) directories, except ExecuteScript which can run scripts from anywhere.
