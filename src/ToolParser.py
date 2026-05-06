"""
ToolParser - Handles parsing of XML tool invocations and job completion detection
"""
import re

class ToolParser:
	"""
	Parses AI responses for XML tool invocations and job_done tags
	"""
	
	def __init__(self, logger=None):
		self.logger = logger
	
	def ParseTextToolInvocation(self, text):
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
	
	def CheckJobDone(self, text):
		# Check if response contains <job_done/> or <job_done></job_done>
		pattern1 = r'<job_done\s*/?>'
		pattern2 = r'<job_done>.*?</job_done>'
		#
		if re.search(pattern1, text, re.IGNORECASE) or re.search(pattern2, text, re.IGNORECASE):
			return True
		return False
	
	def ExtractToolResult(self, text):
		# Remove all tool invocations from text, return clean text
		# Used to get the actual response without XML tool calls
		import re
		#
		# Remove self-closing tags
		text = re.sub(r'<\w+\s*/>', '', text)
		#
		# Remove opening and closing tags with content
		text = re.sub(r'<\w+>.*?</\w+>', '', text, flags=re.DOTALL | re.IGNORECASE)
		#
		return text.strip()
