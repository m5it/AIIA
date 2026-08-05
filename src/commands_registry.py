#--
# Commands registry — command metadata dict (name → info).
# build_registry(self) receives the Commands instance so the func
# fields can reference bound methods (self.CMD_*). Registry stays
# public via Commands.cmds (consumed by HandleChat.py).
#
# Entries are grouped by owner mixin in the *_commands() helpers;
# each command's regex matches exactly one command, so the merged
# key order does not affect command routing (it only sets the
# display order in !HELP).
def build_registry(self):
	registry = {}
	registry.update(_base_commands(self))
	registry.update(_session_commands(self))
	registry.update(_config_commands(self))
	registry.update(_tips_commands(self))
	registry.update(_persona_commands(self))
	registry.update(_sites_commands(self))
	registry.update(_plan_commands(self))
	registry.update(_timers_commands(self))
	registry.update(_workers_commands(self))
	return registry

	#

def _base_commands(self):
	return {
		"HELP":{
			"name"       :"Help",
			"description":"Display help and available commands.",
			"regex"      :r"^!HELP$",
			"usage"      :"!HELP",
			"func"       :self.CMD_HELP,
		},
	}

	#

def _session_commands(self):
	return {
		"NEW_SESSION":{
			"name"       :"New Session",
			"description":"Reset everything and start fresh with Prepare().",
			"regex"      :r"^!NEW_SESSION$",
			"usage"      :"!NEW SESSION",
			"func"       :self.CMD_NEW_SESSION,
		},
		"CLEAR":{
			"name"       :"Clear History",
			"description":"Clear chat history but keep system prompt and persona.",
			"regex"      :r"^!CLEAR$",
			"usage"      :"!CLEAR",
			"func"       :self.CMD_CLEAR,
		},
		"REHEAT":{
			"name"       :"Reheat",
			"description":"Re-run the startup warm-up: refresh tool infos and reload saved tips.",
			"regex"      :r"^!REHEAT$",
			"usage"      :"!REHEAT",
			"func"       :self.CMD_REHEAT,
		},
		"REMOVE":{
			"name"       :"Remove Row",
			"description":"Remove a specific row from chat history by number (use !PH to see row numbers).",
			"regex"      :r"^!RM\s+\d+$",
			"usage"      :"!RM <row_num>",
			"func"       :self.CMD_REMOVE,
		},
		"SUMMARIZE":{
			"name"       :"Summarize",
			"description":"Clear chat history (keeps system messages). Use when context gets too large.",
			"regex"      :r"^!SUMMARIZE$",
			"usage"      :"!SUMMARIZE",
			"func"       :self.CMD_SUMMARIZE,
		},
		"PREVIEW_HISTORY":{
			"name"       :"Preview History",
			"description":"Preview current chat history (optionally a specific row)",
			"regex"      :r"^!PH(\s+\d+)?$",
			"usage"      :"!PH [number]",
			"func"       :self.CMD_PREVIEW_HISTORY,
		},
		"NAME_HISTORY":{
			"name"       :"Name History",
			"description":"Give a human-readable name to the current history session.",
			"regex"      :r"^!NH\s+.+$",
			"usage"      :"!NH <name>",
			"func"       :self.CMD_NAME_HISTORY,
		},
		"VIEW_HISTORY":{
			"name"       :"Available History",
			"description":"List all available history files with sizes and display names.",
			"regex"      :r"^!AH$",
			"usage"      :"!AH",
			"func"       :self.CMD_VIEW_HISTORY,
		},
		"UPDATE_HANDLE":{
			"name"       :"Update Handle",
			"description":"Reinit code of program. Used after program update so there is no need to stop the program.",
			"regex"      :r"^!UPDATE_HANDLE$",
			"usage"      :"!UPDATE HANDLE",
			"func"       :self.CMD_UPDATE_HANDLE,
		},
		"QUIT":{
			"name"       :"Quit",
			"description":"Quit the program.",
			"regex"      :r"^!QUIT$",
			"usage"      :"!QUIT",
			"func"       :self.CMD_QUIT,
		},
	}

	#

def _config_commands(self):
	return {
		"STATS":{
			"name"       :"Stats",
			"description":"Display statistics for program",
			"regex"      :r"^!STATS$",
			"usage"      :"!STATS",
			"func"       :self.CMD_STATS,
		},
		"MODE":{
			"name"       :"Mode",
			"description":"Switch between plan and build mode. Shows current mode if no argument given.",
			"regex"      :r"^!MODE(\s+(plan|build))?$",
			"usage"      :"!MODE [plan|build]",
			"func"       :self.CMD_MODE,
		},
		"OLLAMA_LIST":{
			"name"       :"Models",
			"description":"List models on the active backend, with previously used ones at top.",
			"regex"      :r"^!MODELS$",
			"usage"      :"!MODELS",
			"func"       :self.CMD_OLLAMA_LIST,
		},
		"MODEL":{
			"name"       :"Model",
			"description":"Switch AI model. Shows current model if no argument.",
			"regex"      :r"^!MODEL(\s+\S+)?$",
			"usage"      :"!MODEL [model_name]",
			"func"       :self.CMD_MODEL,
		},
		"BACKEND":{
			"name"       :"Backend",
			"description":"Switch LLM backend (ollama|vllm). Shows current backend if no argument.",
			"regex"      :r"^!BACKEND(\s+\S+)?$",
			"usage"      :"!BACKEND [ollama|vllm]",
			"func"       :self.CMD_BACKEND,
		},
		"SET":{
			"name"       :"Set Config",
			"description":"Override any config option at runtime.",
			"regex"      :r"^!SET(\s+\S+.*)?$",
			"usage"      :"!SET <key> <value>  or  !SET (list all)",
			"func"       :self.CMD_SET,
		},
		"GET":{
			"name"       :"Get Config",
			"description":"Show the value of a config option.",
			"regex"      :r"^!GET(\s+\S+.*)?$",
			"usage"      :"!GET <key>",
			"func"       :self.CMD_GET,
		},
	}

	#

def _tips_commands(self):
	return {
		"TIP_LIST":{
			"name"       :"Tip List",
			"description":"List all saved tip titles with entry counts.",
			"regex"      :r"^!TL(\s+(user|model))?$",
			"usage"      :"!TL [user|model]",
			"func"       :self.CMD_TIP_LIST,
		},
		"TIP_SAVE":{
			"name"       :"Tip Save",
			"description":"Save the last exchange or a specific history row as a tip under a title.",
			"regex"      :r"^!TS(\s+\d+)?\s+\S+$",
			"usage"      :"!TS [history_num] <title>",
			"func"       :self.CMD_TIP_SAVE,
		},
		"TIP_VIEW":{
			"name"       :"Tip View",
			"description":"View saved tip entries under a title.",
			"regex"      :r"^!TV\s+\S+$",
			"usage"      :"!TV <title>",
			"func"       :self.CMD_TIP_VIEW,
		},
		"TIP_REINSERT":{
			"name"       :"Tip Reinsert",
			"description":"Reinsert saved tip entries into current chat history.",
			"regex"      :r"^!TR\s+\S+$",
			"usage"      :"!TR <title>",
			"func"       :self.CMD_TIP_REINSERT,
		},
		"TIP_DELETE":{
			"name"       :"Tip Delete",
			"description":"Delete all entries under a tip title.",
			"regex"      :r"^!TD\s+\S+$",
			"usage"      :"!TD <title>",
			"func"       :self.CMD_TIP_DELETE,
		},
		"TIP_DELETE_ENTRY":{
			"name"       :"Tip Delete Entry",
			"description":"Delete a specific tip entry by number under a title.",
			"regex"      :r"^!TDR\s+\S+\s+\d+$",
			"usage"      :"!TDR <title> <entry_num>",
			"func"       :self.CMD_TIP_DELETE_ENTRY,
		},
		"TIP_DELETE_ALL":{
			"name"       :"Tip Delete All",
			"description":"Delete all saved tips (optionally by source).",
			"regex"      :r"^!TDA(\s+(user|model))?$",
			"usage"      :"!TDA [user|model]",
			"func"       :self.CMD_TIP_DELETE_ALL,
		},
		"CACHE_CLEAR":{
			"name"       :"Clear Cache",
			"description":"Clear all cached tool results.",
			"regex"      :r"^!CACHE_CLEAR$",
			"usage"      :"!CACHE_CLEAR",
			"func"       :self.CMD_CACHE_CLEAR,
		},
	}

	#

def _persona_commands(self):
	return {
		"INSTRUCT_LIST":{
			"name"       :"Instruct List",
			"description":"List available instruct personas.",
			"regex"      :r"^!INSTRUCT_LIST$",
			"usage"      :"!INSTRUCT_LIST",
			"func"       :self.CMD_INSTRUCT_LIST,
		},
		"INSTRUCT_SWITCH":{
			"name"       :"Instruct Switch",
			"description":"Switch to a different instruct persona without clearing history.",
			"regex"      :r"^!INSTRUCT_SWITCH\s+\S+$",
			"usage"      :"!INSTRUCT_SWITCH <persona_name>",
			"func"       :self.CMD_INSTRUCT_SWITCH,
		},
		"INSTALL_DEPS":{
			"name"       :"Install Persona Dependencies",
			"description":"Install missing dependencies for the current persona.",
			"regex"      :r"^!INSTALL_DEPS(\s+\S+)?$",
			"usage"      :"!INSTALL_DEPS [persona_name]",
			"func"       :self.CMD_INSTALL_DEPS,
		},
		"PROJECT":{
			"name"       :"Project",
			"description":"View or modify project path approvals (directories/files the model can access).",
			"regex"      :r"^!PROJECT(\s+(ADD|DENY|REMOVE|RESET)(\s+(DIR|FILE))?\s*.+)?$",
			"usage"      :"!PROJECT [ADD DIR|FILE <path>] [DENY <path>] [REMOVE DIR|FILE <path>] [RESET]",
			"func"       :self.CMD_PROJECT,
		},
		"BUILD_THINK":{
			"name"       :"Build Think",
			"description":"Enable or disable thinking in build mode.",
			"regex"      :r"^!BUILD_THINK(\s+(true|false))?$",
			"usage"      :"!BUILD_THINK [true|false]",
			"func"       :self.CMD_BUILD_THINK,
		},
		"AUTO_CONTINUE":{
			"name"       :"Auto Continue",
			"description":"Enable or disable auto-continue (re-enter AI loop when plan tasks remain)",
			"regex"      :r"^!AUTO_CONTINUE(\s+(true|false))?$",
			"usage"      :"!AUTO_CONTINUE [true|false]",
			"func"       :self.CMD_AUTO_CONTINUE,
		},
		"TOOLS":{
			"name"       :"Tools",
			"description":"Show tool allow/disallow status.",
			"regex"      :r"^!TOOLS(\s+(ALLOWED|DISALLOWED))?$",
			"usage"      :"!TOOLS [ALLOWED|DISALLOWED]",
			"func"       :self.CMD_TOOLS,
		},
		"TOOL":{
			"name"       :"Tool Allow/Disallow",
			"description":"Allow or disallow a specific tool.",
			"regex"      :r"^!TOOL\s+(ALLOW|DISALLOW)\s+(\S+)$",
			"usage"      :"!TOOL ALLOW|DISALLOW <toolName>",
			"func"       :self.CMD_TOOL,
		},
	}

	#

def _sites_commands(self):
	return {
		"SITE_LIST":{
			"name"       :"Site List",
			"description":"List all websites with available JS support scripts.",
			"regex"      :r"^!SITE_LIST$",
			"usage"      :"!SITE_LIST",
			"func"       :self.CMD_SITE_LIST,
		},
		"SITE":{
			"name"       :"Site Info",
			"description":"Show available scripts for a specific website domain. Usage: !SITE <domain> or !SITE <url>",
			"regex"      :r"^!SITE\s+.+$",
			"usage"      :"!SITE <domain>",
			"func"       :self.CMD_SITE,
		},
		"SITE_UPDATE":{
			"name"       :"Site Script Update",
			"description":"Create or update a JS support script for a website. Usage: !SITE_UPDATE <domain> <script_name> [content or reads clipboard/file]",
			"regex"      :r"^!SITE_UPDATE\s+.+$",
			"usage"      :"!SITE_UPDATE <domain> <script_name>",
			"func"       :self.CMD_SITE_UPDATE,
		},
	}

	#

def _plan_commands(self):
	return {
		"PLAN":{
			"name"       :"Plan",
			"description":"View or modify plan status. Use LIST to see all plans, CLEAR/DELETE/RESET to remove, DONE to finalize.",
			"regex"      :r"^!PLAN(\s+[A-Za-z]+)?(\s+[\d\.]+)?$",
			"usage"      :"!PLAN [PREVIEW|VIEW|TASKS|STATUS|LIST|CLEAR|DELETE|RESET|DONE]",
			"func"       :self.CMD_PLAN,
		},
		"START_BUILD":{
			"name"       :"Start Build",
			"description":"Start building from current draft or specific plan by ID.",
			"regex"      :r"^!START_BUILD(\s+[\d\.]+)?$",
			"usage"      :"!START_BUILD [planId]",
			"func"       :self.CMD_START_BUILD,
		},
	}

	#

def _timers_commands(self):
	return {
		"TIMER_ONCE":{
			"name"       :"Timer Once",
			"description":"Set a one-shot timer. Fires after delay, injects text into chat.",
			"regex"      :r"^!TIMER_ONCE\s+\S+",
			"usage"      :"!TIMER_ONCE <time> [text after newline]",
			"func"       :self.CMD_TIMER_ONCE,
		},
		"TIMER_REPEAT":{
			"name"       :"Timer Repeat",
			"description":"Set a repeat timer. Fires N times at interval, injects text each time.",
			"regex"      :r"^!TIMER_REPEAT\s+\d+\s+\S+",
			"usage"      :"!TIMER_REPEAT <count> <interval> [text after newline]",
			"func"       :self.CMD_TIMER_REPEAT,
		},
		"TIMER_LOOP":{
			"name"       :"Timer Loop",
			"description":"Set a loop timer. Fires at interval until stopped.",
			"regex"      :r"^!TIMER_LOOP(\s+\S+(\s+\S+)?)?",
			"usage"      :"!TIMER_LOOP [delay] [duration] [text after newline]",
			"func"       :self.CMD_TIMER_LOOP,
		},
		"TIMER_STOP":{
			"name"       :"Timer Stop",
			"description":"Cancel a specific timer by index, or all if no index given.",
			"regex"      :r"^!TIMER_STOP(\s+\d+)?$",
			"usage"      :"!TIMER_STOP [index]",
			"func"       :self.CMD_TIMER_STOP,
		},
		"TIMER_LIST":{
			"name"       :"Timer List",
			"description":"List all active timers with details.",
			"regex"      :r"^!TIMER_LIST$",
			"usage"      :"!TIMER_LIST",
			"func"       :self.CMD_TIMER_LIST,
		},
	}

	#

def _workers_commands(self):
	return {
		"WORKERS":{
			"name"       :"Workers",
			"description":"List connected orchestra workers and their status.",
			"regex"      :r"^!WORKERS$",
			"usage"      :"!WORKERS",
			"func"       :self.CMD_WORKERS,
		},
		"DISPATCH":{
			"name"       :"Dispatch",
			"description":"Dispatch pending tasks to orchestra workers.",
			"regex"      :r"^!DISPATCH$",
			"usage"      :"!DISPATCH",
			"func"       :self.CMD_DISPATCH,
		},
		"PLAN_WORKER":{
			"name"       :"Plan Worker",
			"description":"Set or show which worker handles planning. Use 'off' to plan locally.",
			"regex"      :r"^!PLAN_WORKER(\s+\S+)?$",
			"usage"      :"!PLAN_WORKER <name|off>",
			"func"       :self.CMD_PLAN_WORKER,
		},
	}
