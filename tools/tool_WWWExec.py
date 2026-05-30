from config import Options
from tools._koslenium_server import ensure_server, exec_script

_DEBUG = Options.get("DEBUG", False)
def _dbg(*a, **kw):
	if _DEBUG:
		print("WWWExec:", *a, file=__import__('sys').stderr, **kw)

class WWWExec():
	def __init__(self):
		self.info = {
			"name":"WWWExec",
			"description":"Execute JavaScript on the currently loaded page in the persistent browser window and return the result.",
			"parameters":{
				"returnType":"string",
				"required":["js"],
				"properties":{
					"js":{
						"type":"string",
						"description":"JavaScript code to execute on the current page (result is returned automatically; use 'return ...' for explicit return or just write the expression)"
					},
					"wait":{
						"type":"string",
						"description":"Extra wait time in milliseconds before executing the JS (default: 0)"
					},
				},
			},
		}

	def run(self, js, opts={}, wait=None):
		port = ensure_server()
		if not port:
			return "Error: wwwjs server not available"
		wait_ms = int(wait) if wait else 0
		_dbg("executing JS on port {} (wait={}ms)".format(port, wait_ms))
		result = exec_script(port, js, wait=wait_ms)
		if result is None:
			return "(no result)"
		return result
