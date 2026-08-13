import os

try:
	from AUTOVERSION import VERSION as _VERSION
	_VERSION = str(_VERSION)
except Exception:
	_VERSION = "0.0.0"

# Configuration for OurAI Agentic Framework
# Separated from run.py for easier preview and maintenance

Options         = {
	#
	"DEBUG"               :False, # print A lot of Additional informations
	"QUIET"               :False, # quite all prints and show only result. (used with -Y)
	"VERSION"             :_VERSION,
	"VERSION_NAME"        :"AIIA Agent",
	#
	"SPEAK"               :True,
	#
	#"AI_MODEL"            :"gemma4:latest",
	#"AI_MODEL"            :"ouai_v7:latest",
	#"AI_MODEL"            :"qwen3:latest",
	#"AI_MODEL"            :"llama3.2:latest",
	#"AI_MODEL"            :"gemma4:e4b",
	"AI_MODEL"            :"kimi-k2.7-code:cloud",
	"AI_BACKEND"          :"ollama",  # LLM backend: "ollama" or "vllm" (OpenAI-compatible)
	"VLLM_HOST"           :"http://localhost:8000/v1",  # vLLM OpenAI-compatible base URL. HF Inference API: "https://router.huggingface.co/v1"
	"VLLM_API_KEY"        :"",        # optional API key for vLLM server; for HF use your hf_<token>
	"VLLM_TIMEOUT"        :120,       # vLLM request timeout in seconds
	"AI_IMAGE_BACKEND"    :"auto",    # image generation backend: "auto" (follow AI_BACKEND) | "ollama" | "vllm" | "local" (diffusers)
	"AI_FILE_STATE"       :"{}/state.aiia".format(os.path.dirname(os.path.abspath(__file__))),
	"AI_FILE_HISTORY"     :"history.aiia", # auto generated from AI_SESS_ID
	"AI_FILE_LOAD_HISTORY":False,
	"AI_SESS_ID"          :0,
	"AI_ROW_ID"           :0,
	"AI_MAX_CONTENT_LEN"  :20000,  # response content. if exceed, cancel response, append to chat history and append warning as role:user
	"AI_MAX_SESSION_LEN"  :200000, # whole session content
	"AI_THINK_LIMIT"      :8192,   # max characters of thinking/reasoning output per response (0 = no limit)
	"AI_LIVE"             :True,
	"AI_MAX_ITERATIONS"   :10, # max tool-call rounds per AI() turn (overridable by persona)
	"AI_FREEZE_HISTORY"   :0,  # testing: 1 = skip ALL chat-history appends until reset to 0 (model keeps seeing the frozen context)
	"AI_FREEZE_LOOP"      :0,  # testing: 1 = repeat the last user turn instead of prompting (Ctrl+C "Stop AI" to break out)
	"AI_PLANBUILD_AUTOCLEAN":0,  # 1 = auto-prune finished plan/build task work from the model context (sliding window between task anchors)
	"AI_PLANBUILD_WAIT"   :5,   # assistant responses after the latest task anchor before an autoclean triggers (min 1)
	"SUMMARIZE_LEAVE"     :4,   # 0 = current behavior (keep system msgs + last 5 exchanges), N = keep last N rows of history when summarizing
	"AI_MODEL_TIMEOUT"    :120, # seconds before model API call times out (0 = no timeout)
	"STREAM_CHUNK_TIMEOUT":120, # seconds — abort stream if no chunk arrives (prevents indefinite hangs)
	"ALTERNATIVE_MODELS"  :["kimi-k2.7-code:cloud"], # fallback models on stream stall (empty = disabled)
	"AI_MODEL_RETRIES"    :3,   # max retries on failed model calls before recommending switch
	"AI_CONTEXT_LIMIT"    :262144, # model's max context window in tokens (per-model)
	"AI_CLEAR_THRESHOLD"  :0.8,    # fraction of context limit that triggers summarization/clear
	"AI_MAX_FILE_SIZE"    :2097152, # 2MB — max content size for WriteFile/CreateFile/AppendFile/ReplaceLine (text files)
	"AI_MAX_IMAGE_INJECT" :3145728, # 3MB — max base64 size for image injection into chat (ReadImage)
	"AUTO_CONTINUE_TASKS" :True,   # auto-advance to next task in build mode after tool usage
	"AUTO_CONTINUE_ALL_TASKS" :True,   # re-enter AI() loop until plan is done (requires AUTO_CONTINUE_TASKS)
	"AUTO_CONTINUE_REMIND_AFTER" :20,  # remind model to call <nextTask> after N iterations without one
	"PLAN_COMPLETE_TEXT_SCAN" :True,  # scan assistant text for plan-completion phrases (set False to only use <planDone/> tool flag)
	"WWW_SOURCE_MAX_SIZE"  :80000,  # chars. Source output above this saved to workout/ and warning returned (prevents context overflow)
	"WWW_CACHE_DIR"        :"workout/www_cache",  # where cached pages are stored (relative to project root)
	"WWW_CACHE_TTL_H"      :24,   # hours before cached page expires (0=no expiry)
	"TOOL_TRAINING" :True,   # on fresh sessions, let AI demonstrate tool usage once before user input
	"TOOL_TRAINING_PLAN" :True,   # re-inject tool training when switching to plan mode
	"TIMER_INTERRUPT" :False,     # if True, timers can inject during AI() iteration loop (default: only during You() prompt)
	"PERSONA_AUTO_INSTALL_DEPS" :True,   # check and prompt to install persona dependencies
	"AI_THINK"            :True, # enable think/reasoning API for models that support it (e.g. DeepSeek R1). Set false when using the HF Inference API via vllm backend
	"AI_VISION_ENABLED"   :True, # enable vision/multimodal support (images in chat messages)
	"AI_MAX_IMAGE_SIZE"   :10485760, # 10MB — max image file size for ReadImage
	"AI_VISION_NOTE"      :"",  # set dynamically by ModelRegistry on model change; warns if model is not vision-capable
	"AI_IMAGE_GEN_MODEL"  :"x/flux2-klein", # default model for GenerateImage tool
	"AI_QUICK"            :False,    # skip interactive Prepare prompts (auto for server mode, or via -Q)
	"AI_SYSTEM_MESSAGE"   :"",       # custom system message prefix, set via -P/--prompt CLI flag
	"LOAD_AGENTS_MD"      :True,     # auto-load AGENTS.md from working_dir into system prompt
	"AI_INSTRUCT_OPTION"  :2,        # 1=persona classes (system prompt), 2=short prompt + tips
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
	"tools_path"          :"{}/tools/".format(os.environ.get('AIIA_PROJECT_DIR', os.environ.get('OURAI_PROJECT_DIR', os.path.dirname(os.path.abspath(__file__))))),
	"history_path"        :"history",
	"plans_path"         :"plans",
	"working_dir"        :os.environ.get('AIIA_PROJECT_DIR', os.environ.get('OURAI_PROJECT_DIR', os.path.dirname(os.path.abspath(__file__)))),
	#
	"COOKIE_FILE"        : None,    # Path to shared cookie file for www/wwwjs web tools (e.g., "tools/cookies.json")
	#
	"WWW_USER_AGENT"     :"Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0", # User-Agent for koslenium web requests (overridable via aiia.json, !SET, or state.aiia)
	#
	"SITE_SCRIPTS_PATH"  : None,    # Path to per-website JS support scripts (default: project wwwurljssupport/ or ~/.config/aiia/wwwurljssupport/)
	"SITE_SCRIPT_AUTO_TIP" : True, # Auto-save a tip entry when UpdateSiteScript creates/updates a script
	#
	"SERVER_PROFILE"      :"HTTP",      # default server profile (HTTP, HTTPS, WS, V1, V2, ...)
	"SERVER_HOST"         :"127.0.0.1", # default bind address for -S
	"SERVER_PORT"         :9877,        # default port for -S
	"SERVER_PROFILES_PATH":"server_profiles", # path to server profile modules
	"SERVER_TLS_CERT"     :None,        # path to TLS cert (for HTTPS profile)
	"SERVER_TLS_KEY"      :None,        # path to TLS key (for HTTPS profile)
	#
	# Server Authentication Settings
	"SERVER_AUTH_ENABLED" :False,       # Enable Basic Auth for HTTP server
	"SERVER_USERNAME"     :"admin",      # Default username (change in production!)
	"SERVER_PASSWORD"     :"aiia",       # Default password (change in production!)
	#
	# Multi-client / Event Broadcast Settings
	"SERVER_MAX_CLIENTS"  :10,           # Max simultaneous registered clients
	"SERVER_EVENT_HISTORY":100,          # Max events kept in history buffer per session
	#
	"BACKGROUND_LOG"      :None,     # Path to background.log (per-project, set in Handle.Init)
	#
	"TIPS_PATH"           :"{}/tips".format(os.path.expanduser("~/.config/aiia")),
	#
	# Tool result caching (via tips storage)
	"TOOL_CACHE_ENABLED"  :True,     # Enable tool result caching
	"TOOL_CACHE_TTL"      :86400,    # Default cache TTL in seconds (1 day)
	"TOOL_SHOW_LOAD"      :True,     # Show detailed tool loading/executing/Loaded messages instead of compact ⚙️ line
	"AI_TOOL_PREVIEW"     :1,        # Echo tool results to console: 0 = only in DEBUG (see only model), 1 = always show tool output to the user
	#
	# File buffer cache — in-memory cache of write-tool targets (WriteFile/CreateFile/
	# AppendFile/ReplaceLine/Sed) that is reinjected after a context auto-clear so the
	# model can continue chunked writes on small-context models. Only populated while a
	# plan is active (project work).
	"TOOL_FILE_CACHE"            :True,      # master toggle for the write-tool file buffer cache
	"TOOL_FILE_CACHE_ON_PLAN"    :True,      # only cache when a plan exists
	"TOOL_FILE_CACHE_MAX_FILE"   :100000,    # skip caching files larger than this (chars)
	"TOOL_FILE_CACHE_MAX_FILES"  :20,        # evict the oldest entries beyond this many cached files
	"TOOL_FILE_CACHE_REINJECT"   :True,      # append the cache to context after auto-clear/summarize
	"TOOL_FILE_CACHE_REINJECT_MAX"   :5000,  # per-file cap when reinjecting (chars)
	"TOOL_FILE_CACHE_REINJECT_TOTAL" :30000, # total cap for the reinjected block (chars)
	#
	# Transient tool results — a read tool call may carry <transient>N</transient> so the
	# tool result (and the assistant row that made the call) auto-removes from history
	# after N AI-loop iterations. Lets small-context models page through large data in
	# bounded chunks without re-filling the context window.
	"TOOL_TRANSIENT_ENABLED"    :True,   # allow <transient>N</transient> on read tools
	"TOOL_TRANSIENT_MAX_STEPS"  :10,     # clamp N (auto-removal after N model calls)
	#
	# Read-tool deduplication — when a read tool returns content identical to a
	# previous result still in the current context, replace the duplicate with a
	# reference to the existing row and inject a user reminder not to re-read.
	"TOOL_DEDUPLICATE_READS"    :True,
	#
	# ReplaceLine indexing
	"REPLACELINE_ZERO_INDEXED": False, # False=1-indexed (first line=1, default), True=0-indexed (first line=0)
	"REPLACELINE_SIMPLE_MODE": True, # True=ReplaceLine applies directly without preview/confirm/finalize
	"READFILE_LINENUMBERS"    : True, # True=ReadFile prepends 1-based line numbers by default; False=plain text
	#
	# Image injection limits
	"MAX_INJECT_IMAGE_DIMENSION" :1024, # max pixel dimension when ReadImage injects into conversation (0=no limit)
	"AI_IMAGE_CACHE_PATH"        :"",   # custom path for image cache (default: ~/.config/aiia/img_cache)
	"AI_IMAGE_CACHE_CLEANUP_H"   :24,   # auto-cleanup cache files older than N hours (0=disable)
	#
	# Tool result format (priority: system > user > tool)
	"TOOL_RESULT_AS_SYSTEM": False, # When True, tool results use role: system instead of role: tool
	"TOOL_RESULT_AS_USER": False,   # When True, tool results use role: user instead of role: tool
	#
	# Post-write syntax validation (runs after ReplaceLine, WriteFile, AppendFile, Sed)
	"TOOL_CODE_VALIDATE"    :True,   # enable post-write syntax checking
	"TOOL_CODE_VALIDATE_EXT":{       # extension -> validator type mapping
		".py" :"python",
		".js" :"javascript",
		".sh" :"bash",
	},
	#
	# aiia_work marketplace client (python run.py --work) — separate, opt-in feature
	"AIIA_WORK_BASE_URL"  :"https://apis.aiia-frame.work/rest/aiia_work", # marketplace API base URL (local dev: http://localhost:8006/rest/aiia_work)
	"AIIA_WORK_API_KEY"   :"",   # API key (X-Api-Key). Priority: env AIIA_WORK_API_KEY > config > stored key file
	"AIIA_WORK_SSO_TOKEN" :"",   # SSO bearer token (required for !WORK KEYGEN)
	"AIIA_WORK_KEY_FILE"  :None, # stored API key file (default: ~/.config/aiia/aiia_work.json)
	"AIIA_WORK_ROLE"      :"both", # default role for keygen: giver | worker | both
	"AIIA_WORK_TIMEOUT"   :30,     # HTTP timeout (seconds)
	"AIIA_WORK_RETRIES"   :2,      # retries on transient 500s / network errors

	# Token counting (populated dynamically by Handle.py on each response)
	"NUM_PROMPT_TOKENS"       :0,  # cumulative prompt tokens across session
	"NUM_RESPONSE_TOKENS"     :0,  # cumulative response tokens across session
	"NUM_LAST_PROMPT_TOKENS"  :0,  # last request's prompt token count
	"NUM_LAST_RESPONSE_TOKENS":0,  # last request's response token count
}
