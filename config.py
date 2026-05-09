import os

# Configuration for AIIA
# Separated from run.py for easier preview and maintenance

# Options = {
	# #
	# "DEBUG"               :False, # print A lot of Additional informations
	# "QUIET"               :False, # quite all prints and show only result. (used with -Y)
	# "VERSION"             :0.1,
	# "VERSION_NAME"        :"AiiA",
	# #
	# "SPEAK"               :True,
	# #
	# "AI_MODEL"            :"qwen3-coder:30b",
	# "AI_FILE_SESSID"      :"{}/sessid.aiia".format(os.path.dirname(os.path.abspath(__file__))),
	# "AI_USER_HISTORY"     :"huser.aiia",
	# "AI_FILE_HISTORY"     :"history.aiia",
	# "AI_FILE_LOAD_HISTORY":False,
	# "AI_SESS_ID"          :0,
	# "AI_ROW_ID"           :0,
	# "AI_MAX_CONTENT_LEN"  :20000,
	# "AI_LIVE"             :True,
	# "AI_TEMPERATURE"      :0.7,
	# "AI_TASK_TIMEOUT"     :600,   # Task loop timeout in seconds (10 min)
	# #
	# "path"                :"{}/".format(os.path.dirname(os.path.abspath(__file__))),
	# "tools_path"          :"tools",
	# "actions_path"        :"actions",
	# "history_path"        :"history",
# }
#
Options         = {
	#
	"DEBUG"               :False, # print A lot of Additional informations
	"QUIET"               :False, # quite all prints and show only result. (used with -Y)
	"VERSION"             :0.2,
	"VERSION_NAME"        :"OurAI",
	#
	"SPEAK"               :True,
	#
	"AI_MODEL"            :"gemma4:26b",
	"AI_FILE_SESSID"      :"{}/sessid.aiia".format(os.path.dirname(os.path.abspath(__file__))),
	"AI_USER_HISTORY"     :"huser.aiia",
	"AI_FILE_HISTORY"     :"history.aiia",
	"AI_FILE_LOAD_HISTORY":False,
	"AI_SESS_ID"          :0,
	"AI_ROW_ID"           :0,
	"AI_MAX_CONTENT_LEN"  :20000,
	"AI_LIVE"             :True,
	"AI_TEMPERATURE"      :0.7,
	#
	"MODE"                :"build",  # "plan" or "build" mode
	#
	"path"                :"{}/".format(os.path.dirname(os.path.abspath(__file__))),
	"tools_path"          :"{}/tools/".format(os.environ.get('OURAI_PROJECT_DIR', os.path.dirname(__file__))),
	"actions_path"        :"{}/actions/".format(os.environ.get('OURAI_PROJECT_DIR', os.path.dirname(__file__))),
	#"history_path"        :"history",
	#"tools_path"          :"tools",
	#"actions_path"        :"actions",
	"history_path"        :"history",
	"plans_path"         :"plans",
}
