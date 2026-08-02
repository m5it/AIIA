#--
# class ToolXmlParser — parse XML tool invocations from AI responses
import re
class ToolXmlParser():
	#
	def ParseTextToolInvocation(self, text):
		# Parse XML-style tool invocations like: <ReadFile><fileName>test.txt</fileName></ReadFile>
		# Also handles self-closing tags: <listTools/>
		# Returns: [{'name':'ReadFile', 'parameters':{'fileName':'test.txt'}}, ...]
		#
		# Strip HTML comments first — the model may regurgitate HISTORY.md which
		# contains old tool calls embedded in <!-- ... --> blocks. These are NOT
		# new tool invocations and should not be detected.
		text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
		#
		# Strip <think>...</think> tags — the model may include these in the
		# content field (separate from the native thinking API).  They should
		# NOT be treated as tool calls.
		text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
		# Also strip orphan </think> closing tags that appear without openers
		text = re.sub(r'</think>', '', text)
		#
		results = []
		#
		# First, find all self-closing tags: <TagName/>
		self_closing_pattern = r'<(\w+)\s*/>'
		for match in re.finditer(self_closing_pattern, text):
			toolName = match.group(1)
			results.append({
				'name': toolName,
				'parameters': {}
			})
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
			start_pos = i + open_match.start()
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
			params = {}
			for pm in re.finditer(r'<(\w+)>(.*?)</\1>', inner_content, re.DOTALL | re.IGNORECASE):
				raw = pm.group(2)
				if pm.group(1) in ('replacement', 'contentOfFile'):
					params[pm.group(1)] = raw
				else:
					params[pm.group(1)] = raw.strip('\n').rstrip('\r')
			#
			results.append({
				'name': toolName,
				'parameters': params
			})
			#
			i = pos + len(close_tag)
		#
		return results
	
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
		if toolName == 'ReplaceLine':
			fileName = params.get('fileName', '?')
			fl = params.get('fromLine', '?')
			tl = params.get('toLine', fl)
			return "Editing '{}' lines {}-{}".format(fileName, fl, tl)
		elif toolName == 'WriteFile':
			fileName = params.get('fileName', '?')
			content = params.get('contentOfFile', '')
			return "Writing {} bytes to '{}'".format(len(content), fileName)
		elif toolName == 'AppendFile':
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
		elif toolName == 'CreateFile':
			fileName = params.get('fileName', '?')
			return "Creating new file '{}'".format(fileName)
		elif toolName == 'ReadFile':
			fileName = params.get('fileName', '?')
			return "Reading '{}'".format(fileName)
		elif toolName == 'Terminal':
			args = [params.get('arg{}'.format(i), '') for i in range(1, 6)]
			args = [a for a in args if a]
			return "$ {}".format(' '.join(args)) if args else "Running terminal command"
		elif toolName == 'WWW':
			url = params.get('url', '?')
			return "Fetching: {}".format(url)
		elif toolName == 'Grep':
			pat = params.get('pattern', '?')
			fn = params.get('fileName', '')
			return "Searching '{}' in {}".format(pat, fn if fn else 'all files')
		elif toolName == 'listTools':
			return "Listing available tools"
		elif toolName == 'TreeView':
			path = params.get('path', '.')
			depth = params.get('depth', '3')
			return "Tree view of '{}' (depth={})".format(path, depth)
		elif toolName == 'List':
			path = params.get('path', '.')
			return "Listing '{}'".format(path)
		elif toolName == 'Find':
			pat = params.get('pattern', '*')
			path = params.get('path', '.')
			return "Finding '{}' in '{}'".format(pat, path)
		elif toolName == 'ExecuteScript':
			fn = params.get('fileName', '?')
			args = params.get('args', '')
			return "Running script '{}' {}".format(fn, args)
		elif toolName == 'Head':
			fn = params.get('fileName', '?')
			n = params.get('lines', '10')
			return "First {} lines of '{}'".format(n, fn)
		elif toolName == 'Tail':
			fn = params.get('fileName', '?')
			n = params.get('lines', '10')
			return "Last {} lines of '{}'".format(n, fn)
		elif toolName == 'Sed':
			pat = params.get('pattern', '?')
			fn = params.get('fileName', '?')
			return "Replacing '{}' in '{}'".format(pat, fn)
		elif toolName == 'Diff':
			f1 = params.get('file1', '?')
			f2 = params.get('file2', '?')
			return "Comparing '{}' vs '{}'".format(f1, f2)
		elif toolName == 'Sort':
			fn = params.get('fileName', '?')
			return "Sorting '{}'".format(fn)
		elif toolName == 'SaveTip':
			title = params.get('title', '?')
			return "Saving tip '{}'".format(title)
		elif toolName == 'GetTip':
			title = params.get('title', '?')
			return "Loading tip '{}'".format(title)
		elif toolName == 'ListTips':
			return "Listing saved tips"
		elif toolName == 'DeleteTip':
			title = params.get('title', '?')
			return "Deleting tip '{}'".format(title)
		elif toolName == 'ReinsertTip':
			title = params.get('title', '?')
			return "Reinserting tip '{}' into context".format(title)
		elif toolName in ('createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks', 'nextTask', 'jobDone', 'planDone', 'startBuild', 'LogProgress'):
			title = params.get('title', params.get('instruction', ''))
			if title:
				return "{}: {}".format(toolName, title[:60])
			return "{}".format(toolName)
		else:
			params_str = ', '.join(['{}={}'.format(k, v) for k, v in params.items()])
			return "{} {}".format(toolName, params_str if params_str else '')
	#
