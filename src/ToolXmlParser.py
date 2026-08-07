#--
# class ToolXmlParser — parse XML tool invocations from AI responses
import re
class ToolXmlParser():
	def ParseTextToolInvocation(self, text):
		# Parse XML-style tool invocations like: <ReadFile><fileName>test.txt</fileName></ReadFile>
		# Also handles self-closing tags: <listTools/>
		# Returns: [{'name':'ReadFile', 'parameters':{'fileName':'test.txt'}}, ...]
		#
		# Strip comments/think blocks first — they are NOT new tool invocations
		text = self._strip_ignored_xml(text)
		#
		results = self._parse_self_closing(text)
		#
		# Then, find all regular tags with content: <TagName>...</TagName>
		i = 0
		text_lower = text.lower()
		#
		while i < len(text):
			# Find next opening tag (case-insensitive)
			open_match = re.search(r'<(\w+)>', text[i:])
			if not open_match:
				break
			#
			toolName = open_match.group(1)
			inner_start = i + open_match.end()
			#
			# Find matching closing tag (case-insensitive)
			close_tag = '</{}>'.format(toolName)
			close_tag_lower = '</{}>'.format(toolName.lower())
			#
			pos = text_lower.find(close_tag_lower, inner_start)
			if pos == -1:
				pos = text.find(close_tag, inner_start)
			#
			if pos == -1:
				i = inner_start
				continue
			#
			# Extract inner content and parse parameters
			inner_content = text[inner_start:pos]
			params = self._parse_inner_params(inner_content)
			#
			results.append({
				'name': toolName,
				'parameters': params
			})
			#
			i = pos + len(close_tag)
		#
		return results

	def _strip_ignored_xml(self, text):
		# Strip HTML comments first — the model may regurgitate HISTORY.md which
		# contains old tool calls embedded in <!-- ... --> blocks. These are NOT
		# new tool invocations and should not be detected.
		text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
		#
		# Strip <think>...</think> tags — the model may include these in the
		# content field (separate from the native thinking API).  They should
		# NOT be treated as tool calls.  Once <think> opens, everything until
		# </think> is concatenated into the buffer (nested <think> is data);
		# only the closing tag stops it.  Handles case variants, attributes,
		# orphan closers, and unclosed blocks at the end.
		text = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', text, flags=re.I | re.DOTALL)
		text = re.sub(r'</think\s*>', '', text, flags=re.I)
		text = re.sub(r'<think\b[^>]*>.*', '', text, flags=re.I | re.DOTALL)
		return text

	def _parse_self_closing(self, text):
		# Find all self-closing tags: <TagName/>
		results = []
		self_closing_pattern = r'<(\w+)\s*/>'
		for match in re.finditer(self_closing_pattern, text):
			toolName = match.group(1)
			results.append({
				'name': toolName,
				'parameters': {}
			})
		return results

	def _parse_inner_params(self, inner_content):
		params = {}
		for pm in re.finditer(r'<(\w+)>(.*?)</\1>', inner_content, re.DOTALL | re.IGNORECASE):
			raw = pm.group(2)
			if pm.group(1) in ('replacement', 'contentOfFile'):
				params[pm.group(1)] = raw
			else:
				params[pm.group(1)] = raw.strip('\n').rstrip('\r')
		return params
	
	#
	def CheckJobDone(self, text):
		# Check if response contains <job_done/> or <job_done></job_done>
		pattern1 = r'<job_done\s*/?>'
		pattern2 = r'<job_done>.*?</job_done>'
		#
		if re.search(pattern1, text, re.IGNORECASE) or re.search(pattern2, text, re.IGNORECASE):
			return True
		return False
	
	#
	def ExtractToolResult(self, text):
		# Remove all tool invocations from text, return clean text
		# Used to get the actual response without XML tool calls
		#import re
		#
		# Remove self-closing tags
		text = re.sub(r'<\w+\s*/>', '', text)
		#
		# Remove opening and closing tags with content (greedy match to handle nested same-name tags)
		text = re.sub(r'<(\w+)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
		# Remove any remaining orphaned closing tags
		text = re.sub(r'</\w+>', '', text)
		#
		return text.strip()
	
	#
	def _format_action(self, toolName, params):
		"""Return a human-readable action description for a tool invocation."""
		formatter = _ACTION_FORMATTERS.get(toolName)
		if formatter:
			return formatter(params)
		if toolName in _PLAN_TOOLS:
			title = params.get('title', params.get('instruction', ''))
			if title:
				return "{}: {}".format(toolName, title[:60])
			return "{}".format(toolName)
		params_str = ', '.join(['{}={}'.format(k, v) for k, v in params.items()])
		return "{} {}".format(toolName, params_str if params_str else '')

#

def _format_ReplaceLine(params):
	fileName = params.get('fileName', '?')
	fl = params.get('fromLine', '?')
	tl = params.get('toLine', fl)
	return "Editing '{}' lines {}-{}".format(fileName, fl, tl)

def _format_WriteFile(params):
	fileName = params.get('fileName', '?')
	content = params.get('contentOfFile', '')
	return "Writing {} bytes to '{}'".format(len(content), fileName)

def _format_AppendFile(params):
	fileName = params.get('fileName', '?')
	fl = params.get('fromLineNumber', '-1')
	if fl is None or fl == -1 or str(fl) == '-1':
		fl = 'end'
	elif str(fl) == '0':
		fl = 'start'
	else:
		fl = 'line {}'.format(fl)
	content = params.get('contentOfFile', '')
	return "Appending {} bytes to '{}' at {}".format(len(content), fileName, fl)

def _format_CreateFile(params):
	fileName = params.get('fileName', '?')
	return "Creating new file '{}'".format(fileName)

def _format_ReadFile(params):
	fileName = params.get('fileName', '?')
	return "Reading '{}'".format(fileName)

def _format_Terminal(params):
	args = [params.get('arg{}'.format(i), '') for i in range(1, 6)]
	args = [a for a in args if a]
	return "$ {}".format(' '.join(args)) if args else "Running terminal command"

def _format_WWW(params):
	url = params.get('url', '?')
	return "Fetching: {}".format(url)

def _format_Grep(params):
	pat = params.get('pattern', '?')
	fn = params.get('fileName', '')
	return "Searching '{}' in {}".format(pat, fn if fn else 'all files')

def _format_listTools(params):
	return "Listing available tools"

def _format_TreeView(params):
	path = params.get('path', '.')
	depth = params.get('depth', '3')
	return "Tree view of '{}' (depth={})".format(path, depth)

def _format_List(params):
	path = params.get('path', '.')
	return "Listing '{}'".format(path)

def _format_Find(params):
	pat = params.get('pattern', '*')
	path = params.get('path', '.')
	return "Finding '{}' in '{}'".format(pat, path)

def _format_ExecuteScript(params):
	fn = params.get('fileName', '?')
	args = params.get('args', '')
	return "Running script '{}' {}".format(fn, args)

def _format_Head(params):
	fn = params.get('fileName', '?')
	n = params.get('lines', '10')
	return "First {} lines of '{}'".format(n, fn)

def _format_Tail(params):
	fn = params.get('fileName', '?')
	n = params.get('lines', '10')
	return "Last {} lines of '{}'".format(n, fn)

def _format_Sed(params):
	pat = params.get('pattern', '?')
	fn = params.get('fileName', '?')
	return "Replacing '{}' in '{}'".format(pat, fn)

def _format_Diff(params):
	f1 = params.get('file1', '?')
	f2 = params.get('file2', '?')
	return "Comparing '{}' vs '{}'".format(f1, f2)

def _format_Sort(params):
	fn = params.get('fileName', '?')
	return "Sorting '{}'".format(fn)

def _format_SaveTip(params):
	title = params.get('title', '?')
	return "Saving tip '{}'".format(title)

def _format_GetTip(params):
	title = params.get('title', '?')
	return "Loading tip '{}'".format(title)

def _format_ListTips(params):
	return "Listing saved tips"

def _format_DeleteTip(params):
	title = params.get('title', '?')
	return "Deleting tip '{}'".format(title)

def _format_ReinsertTip(params):
	title = params.get('title', '?')
	return "Reinserting tip '{}' into context".format(title)

_ACTION_FORMATTERS = {
	'ReplaceLine'    : _format_ReplaceLine,
	'WriteFile'      : _format_WriteFile,
	'AppendFile'     : _format_AppendFile,
	'CreateFile'     : _format_CreateFile,
	'ReadFile'       : _format_ReadFile,
	'Terminal'       : _format_Terminal,
	'WWW'            : _format_WWW,
	'Grep'           : _format_Grep,
	'listTools'      : _format_listTools,
	'TreeView'       : _format_TreeView,
	'List'           : _format_List,
	'Find'           : _format_Find,
	'ExecuteScript'  : _format_ExecuteScript,
	'Head'           : _format_Head,
	'Tail'           : _format_Tail,
	'Sed'            : _format_Sed,
	'Diff'           : _format_Diff,
	'Sort'           : _format_Sort,
	'SaveTip'        : _format_SaveTip,
	'GetTip'         : _format_GetTip,
	'ListTips'       : _format_ListTips,
	'DeleteTip'      : _format_DeleteTip,
	'ReinsertTip'    : _format_ReinsertTip,
}

_PLAN_TOOLS = ('createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft',
	'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks', 'nextTask',
	'jobDone', 'planDone', 'startBuild', 'LogProgress', 'CreatePlan', 'CreateTask', 'AppendTask')
	#
