import os

# Configuration for OurAI Agentic Framework
# Separated from run.py for easier preview and maintenance

Options         = {
	#
	"DEBUG"               :False, # print A lot of Additional informations
	"QUIET"               :False, # quite all prints and show only result. (used with -Y)
	"VERSION"             :0.6,
	"VERSION_NAME"        :"OurAI Agent",
	#
	"SPEAK"               :True,
	#
	#"AI_MODEL"            :"gemma4:latest",
	#"AI_MODEL"            :"ouai_v7:latest",
	#"AI_MODEL"            :"qwen3:latest",
	#"AI_MODEL"            :"llama3.2:latest",
	#"AI_MODEL"            :"gemma4:e4b",
	"AI_MODEL"            :"kimi-k2.5:cloud",
	"AI_FILE_SESSID"      :"{}/sessid.aiia".format(os.path.dirname(os.path.abspath(__file__))),
	"AI_FILE_MODE"        :"{}/mode.aiia".format(os.path.dirname(os.path.abspath(__file__))),
	"AI_FILE_USED_MODELS" :"{}/used_models.aiia".format(os.path.dirname(os.path.abspath(__file__))),
	"AI_FILE_TOKENS"      :"{}/tokens.aiia".format(os.path.dirname(os.path.abspath(__file__))),
	"AI_FILE_HISTORY"     :"history.aiia", # auto generated from AI_SESS_ID
	"AI_FILE_LOAD_HISTORY":False,
	"AI_SESS_ID"          :0,
	"AI_ROW_ID"           :0,
	"AI_MAX_CONTENT_LEN"  :20000,  # response content. if exceed, cancel response, append to chat history and append warning as role:user
	"AI_MAX_SESSION_LEN"  :200000, # whole session content
	"AI_LIVE"             :True,
	"AI_MAX_ITERATIONS"   :10, # max tool-call rounds per AI() turn (overridable by persona)
	"AI_CONTEXT_LIMIT"    :262144, # model's max context window in tokens (per-model)
	"AI_CLEAR_THRESHOLD"  :0.8,    # fraction of context limit that triggers summarization/clear
	"AI_MAX_FILE_SIZE"    :2097152, # 2MB — max file size for WriteFile/CreateFile/AppendFile/ReplaceLine
	"AUTO_CONTINUE_TASKS" :True,   # auto-advance to next task in build mode after tool usage
	"AI_THINK"            :True, # enable think/reasoning API for models that support it (e.g. DeepSeek R1)
	"AI_VISION_ENABLED"   :True, # enable vision/multimodal support (images in chat messages)
	"AI_MAX_IMAGE_SIZE"   :10485760, # 10MB — max image file size for ReadImage
	"AI_VISION_NOTE"      :"This model may not support vision. Use !MODEL qwen3-vl:latest or another vision model to analyze images.",
	"AI_QUICK"            :False,    # skip interactive Prepare prompts (auto for server mode, or via -Q)
	"AI_SYSTEM_MESSAGE"   :"",       # custom system message prefix, set via -P/--prompt CLI flag
	# Available options keys:
	# mirostat, mirostat_eta, mirostat_tau, num_ctx, repeat_last_n, repeat_penalty, temperature, seed, stop, num_predict, top_k, top_p, min_p
	"AI_OPTIONS"          : {
		"temperature" : 0.7,
	},
	#
	"MODE"                :"plan",  # "plan" or "build" mode
	"BUILD_THINKING_DISABLED":False, # disable thinking in build mode (set via !BUILD_THINK true|false)
	"CONTINUE"            :False,    # Continue from last session when True
	#
	"DRAFT_CONTENT"       : None,    # Used on CTRL+C to save draft to chat history
	#
	"INSTRUCT_CLASS"      :"Developer",  # persona class in instruct/ directory
	"INSTRUCT_PATH"       :"instruct",   # path to instruct modules
	#
	"path"                :"{}/".format(os.path.dirname(os.path.abspath(__file__))),
	"tools_path"          :"{}/tools/".format(os.environ.get('OURAI_PROJECT_DIR', os.path.dirname(__file__))),
	"history_path"        :"history",
	"plans_path"         :"plans",
	"working_dir"        :os.environ.get('OURAI_PROJECT_DIR', os.path.dirname(os.path.abspath(__file__))),
	#
	"COOKIE_FILE"        : None,    # Path to shared cookie file for www/wwwjs web tools (e.g., "tools/cookies.json")
	#
	"TIPS_PATH"           :"{}/tips".format(os.path.expanduser("~/.config/ourai")),
	#
	# Tool result caching (via tips storage)
	"TOOL_CACHE_ENABLED"  :True,     # Enable tool result caching
	"TOOL_CACHE_TTL"      :86400,    # Default cache TTL in seconds (1 day)
	#
	# Tool result format (priority: system > user > tool)
	"TOOL_RESULT_AS_SYSTEM": False, # When True, tool results use role: system instead of role: tool
	"TOOL_RESULT_AS_USER": False,   # When True, tool results use role: user instead of role: tool

	# Token counting (populated dynamically by Handle.py on each response)
	"NUM_PROMPT_TOKENS"       :0,  # cumulative prompt tokens across session
	"NUM_RESPONSE_TOKENS"     :0,  # cumulative response tokens across session
	"NUM_LAST_PROMPT_TOKENS"  :0,  # last request's prompt token count
	"NUM_LAST_RESPONSE_TOKENS":0,  # last request's response token count
}
