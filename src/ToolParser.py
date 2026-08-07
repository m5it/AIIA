"""
ToolParser - Handles parsing of XML tool invocations and job completion detection
"""
import os
from src.ToolXmlParser import ToolXmlParser
from src.ToolExecutor import ToolExecutor
from src.PlanToolHandler import PlanToolHandler

class ToolParser(ToolXmlParser, ToolExecutor, PlanToolHandler):
	"""
	Parses AI responses for XML tool invocations and job_done tags
	"""
	_current_handle = None  # Set before tool.run() for tools that need handle access
	_plan_blocked = {
		'WriteFile', 'CreateFile', 'AppendFile', 'ReplaceLine', 'Sed',
		'Sort', 'Terminal', 'ExecuteScript',
		'WWW', 'WWWExec', 'WWWJS', 'WWWScript',
		'SiteScript', 'UpdateSiteScript',
		'startBuild',
	}
	_plan_tools = {
		'addTask', 'createTask', 'createPlan', 'deleteTask', 'deletePlan',
		'deleteDraft', 'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks',
		'nextTask', 'jobDone', 'planDone', 'startBuild', 'LogProgress',
		'CreatePlan', 'CreateTask', 'AppendTask',
	}
	#--
	def __init__(self, opts={}):
		self.logger = opts['logger'] if 'logger' in opts else None
		self.handle = opts['handle'] if 'handle' in opts else None # to master class / Handle()
		self._known_tools = None

	def get_known_tools(self):
		"""Return set of all known tool names (file-based + built-in plan/blocked)."""
		if self._known_tools is not None:
			return self._known_tools
		tools = set()
		tools.update(self._plan_blocked)
		tools.update(self._plan_tools)
		tools_path = self.handle.Options.get('tools_path', 'tools') if self.handle else 'tools'
		if os.path.exists(tools_path):
			for f in os.listdir(tools_path):
				if f.startswith("tool_") and f.endswith(".py"):
					tools.add(f[5:-3])
		self._known_tools = tools
		return tools
	#--
