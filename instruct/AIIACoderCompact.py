class AIIACoderCompact():
	name = "AIIACoderCompact"
	description = "AIIA coding agent — compact tool reference in prompt"
	category = "aiia"
	tool_training = False
	mode = "plan"
	build_thinking_disabled = False
	max_iterations = 10
	blocks = {
		'[--#THINKING#--ID1--]': {
			'plan': 'Thinking ENABLED',
			'build_enabled': 'Thinking ENABLED - you can reason step by step',
			'build_disabled': 'Thinking DISABLED - be concise and direct',
		},
	}
	# Terse one-line tool reference — model knows the XML format, just needs names+params.
	_tools = (
		"ReadFile <fileName offset lines lineNumbers> · ReadPDF <fileName> · ReadImage <fileName> · "
		"WriteFile <fileName contentOfFile> · CreateFile <fileName content> · "
		"AppendFile <fileName contentOfFile> · ReplaceLine <fileName fromLine toLine replacement> · "
		"Sed <pattern replacement fileName> · TreeView <path depth> · List <path> · "
		"Find <pattern path> · Grep <pattern fileName> · Head <fileName lines> · "
		"Tail <fileName lines> · Sort <fileName> · Diff <file1 file2> · CurrentTime · "
		"ExecuteScript <fileName args> · GenerateImage <prompt> · WWW <url text js> · "
		"WWWExec <js> · ParsePage <fileName action> · SiteScript <site script> · "
		"UpdateSiteScript <site script content> · SaveTip <title content> · "
		"GetTip <title> · ListTips · DeleteTip <title> · ReinsertTip <title> · "
		"listTools (no params)"
	)

	def plan(self):
		return """
You are in PLAN MODE. You are the architect.

MODE: PLAN ([--#THINKING#--ID1--])

WORKFLOW: Explore with TreeView/ReadFile, then <createPlan>, <createTask> per step,
<planDone/> when ready.

TOOLS (XML format — use <listTools> for full details if unsure):
{}
""".format(self._tools)

	def build(self):
		return """
You are in BUILD MODE. You are the code agent.

MODE: BUILD ([--#THINKING#--ID1--])

WORKFLOW: Execute the current task, then <nextTask>completed</nextTask> /
<nextTask>blocked</nextTask>; <jobDone/> when all done.

TOOLS (XML format — use <listTools> for full details if unsure):
{}
""".format(self._tools)
