"""
ToolParser - Handles parsing of XML tool invocations and job completion detection
"""
import re
import os
from src.functions import initmodule,importmodule,splitFileNameExtension

class ToolParser:
	"""
	Parses AI responses for XML tool invocations and job_done tags
	"""
	#--
	def __init__(self, opts={}):
		self.logger = opts['logger'] if 'logger' in opts else None
		self.handle = opts['handle'] if 'handle' in opts else None # to master class / Handle()
	#--
	def ParseTextToolInvocation(self, text):
		print("ToolParser().ParseTextToolInvocation() START! text.len: {}".format( len(text) ))
		# Parse XML-style tool invocations like: <ReadFile><fileName>test.txt</fileName></ReadFile>
		# Also handles self-closing tags: <listTools/>
		# Returns: [{'name':'ReadFile', 'parameters':{'fileName':'test.txt'}}, ...]
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
				params[pm.group(1)] = pm.group(2).strip()
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
		print("ToolParser().CheckJobDone() START!")
		# Check if response contains <job_done/> or <job_done></job_done>
		pattern1 = r'<job_done\s*/?>'
		pattern2 = r'<job_done>.*?</job_done>'
		#
		if re.search(pattern1, text, re.IGNORECASE) or re.search(pattern2, text, re.IGNORECASE):
			return True
		return False
	
	#
	def ExtractToolResult(self, text):
		print("ToolParser().ExtractToolResult() START! text.len: {}".format( len(text) ))
		# Remove all tool invocations from text, return clean text
		# Used to get the actual response without XML tool calls
		#import re
		#
		# Remove self-closing tags
		text = re.sub(r'<\w+\s*/>', '', text)
		#
		# Remove opening and closing tags with content
		text = re.sub(r'<\w+>.*?</\w+>', '', text, flags=re.DOTALL | re.IGNORECASE)
		#
		return text.strip()
	
	#
	def ExecuteTextTool(self, toolName, params):
		print("DEBUG ExecuteTextTool START, toolName: {}".format( toolName ))
		# Execute a tool based on XML invocation
		#
		# ROUTING: If ExecuteScript is called with a non-script file, route to Terminal
		if toolName.lower() == 'executescript':
			fileName = params.get('fileName', '')
			script_extensions = ['.py', '.sh', '.js', '.bash', '.zsh', '.fish', '.bat', '.cmd', '.ps1']
			is_script = any(fileName.lower().endswith(ext) for ext in script_extensions)
			#
			if not is_script and fileName:
				# Route to Terminal tool
				print("Routing ExecuteScript({}) to Terminal tool".format(fileName))
				# Build args for Terminal: arg1=fileName, arg2=args, etc.
				terminal_args = {}
				terminal_args['arg1'] = fileName
				#
			# Add additional args if provided
			if 'args' in params:
				args = params['args']
				# Handle if args is a string (could be JSON array, Python list repr, or space-separated)
				if isinstance(args, str):
					import json
					# Try to parse as JSON array first
					try:
						parsed_args = json.loads(args)
						if isinstance(parsed_args, list):
							for i, arg in enumerate(parsed_args, start=2):
								terminal_args['arg{}'.format(i)] = str(arg)
							args = None  # Mark as processed
					except:
						pass
					#
					if args:  # Not JSON, try other formats
						# Check if it looks like a Python list representation: [item1, item2, ...]
						if args.strip().startswith('[') and args.strip().endswith(']'):
							# Strip brackets and split by comma
							inner = args.strip()[1:-1].strip()
							if inner:  # Not empty
								# Split by comma and clean up
								parts = [p.strip().strip('"\'') for p in inner.split(',')]
								for i, arg in enumerate(parts, start=2):
									if arg:  # Skip empty parts
										terminal_args['arg{}'.format(i)] = arg
							args = None
					#
					if args:  # Still not processed, treat as space-separated
						import shlex
						try:
							parsed_args = shlex.split(args)
							for i, arg in enumerate(parsed_args, start=2):
								terminal_args['arg{}'.format(i)] = arg
						except:
							terminal_args['arg2'] = args
				elif isinstance(args, list):
					for i, arg in enumerate(args, start=2):
						terminal_args['arg{}'.format(i)] = str(arg)
				#
				toolName = 'Terminal'
				params = terminal_args
		#
		# Load tool dynamically if not already loaded
		if toolName not in self.handle.hTC.handles:
			self.handle.hLG.echo("Tool {} not loaded, loading dynamically...".format(toolName), {'color':True, 'colorValue':'orange'})
			#
			try:
				# Find tool file by name
				tool_file = None
				for f in os.listdir(self.handle.Options['tools_path']):
					# Check if file matches tool_XXX.py pattern
					if f.startswith("tool_") and f.endswith(".py"):
						file_tool_name = f[5:-3]  # Extract name from tool_XXX.py
						# Try to match with toolName (case-insensitive)
						if file_tool_name.lower() == toolName.lower():
							tool_file = f
							break
				#
				if tool_file is None:
					return "Tool `{}` not found in tools/".format(toolName)
				#
				# Load the tool
				tmp = splitFileNameExtension(tool_file)
				mod = importmodule(tmp['name'], True, {'path':self.handle.Options['tools_path']})
				#
				# Initialize with proper class name (try toolName or file name)
				h = None
				for cls_name in [toolName, tmp['name']]:
					try:
						h = initmodule(mod, cls_name)
						if h:
							break
					except:
						continue
				#
				if h is None:
					return "Failed to initialize tool `{}`".format(toolName)
				#
				# Store in handles
				self.handle.hTC.handles[toolName] = {'handle': h}
				self.handle.hLG.echo("Tool {} loaded successfully".format(toolName), {'color':True, 'colorValue':'green'})
			except Exception as E:
				return "Error loading tool {}: {}".format(toolName, E)
		#
		# Execute the tool
		try:
			h = self.handle.hTC.handles[toolName]['handle']
			result = h.run(**params)
			return result
		except Exception as E:
			return "Error executing {}: {}".format(toolName, E)
	
	#
	def FireToolInvocation(self, tool_invocations):
		print("DEBUG FireToolInvocation() START, tool_invocations: {}".format(tool_invocations))
		#
		for inv in tool_invocations:
			print("DEBUG FireToolInvocation() name: {}".format(inv['name']))
			toolName = inv['name']
			params   = inv['parameters']
			#
			# Show user what tool is being called (preview)
			params_str = ', '.join(['{}={}'.format(k, v) for k, v in params.items()])
			self.handle.hLG.echo("🔧 Executing: {} ({})".format(toolName, params_str if params_str else 'no params'), {'color':True, 'colorValue':'cyan'})
			#
			result = self.ExecuteTextTool(toolName, params)
			print("DEBUG FireToolInvocation() result: ",result)
			#
			# Truncate result if too long
			MAX_PREVIEW = 500
			result_str = str(result)
			if len(result_str) > MAX_PREVIEW:
				result_str = result_str[:MAX_PREVIEW] + "... (truncated, {} chars total)".format(len(str(result)))
			#
			self.handle.hLG.echo("✓ Result: {}".format(result_str), {'color':True, 'colorValue':'green'})
			#
			self.handle.Response('tool',{'content':str(result),'name':toolName})
