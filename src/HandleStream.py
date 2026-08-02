import json, queue, re, threading
#
class HandleStream():

	#

	def _convert_native_tool_calls(self, native_tool_calls):
		"""
		Convert native Ollama tool calls to internal XML-like tool invocation format
		Native format: tool_calls = [{'function': {'name': 'tool_name', 'arguments': {...}}}]
		Internal format: [{'name': 'ToolName', 'params': {...}}]
		"""
		converted = []
		for tool_call in native_tool_calls:
			try:
				# Extract function info from native tool call
				if hasattr(tool_call, 'function'):
					func = tool_call.function
					tool_name = func.name if hasattr(func, 'name') else str(func.get('name', ''))
					
					# Get arguments - might be dict or JSON string
					args = {}
					if hasattr(func, 'arguments'):
						args = func.arguments if isinstance(func.arguments, dict) else json.loads(func.arguments)
					
					# Convert to internal format (ToolParser expects 'parameters')
					converted.append({
						'name': tool_name,
						'parameters': args
					})
					self.hLG.echo("Converted native tool call: {} with params: {}".format(tool_name, args), {'color':True, 'colorValue':'cyan'})
				elif isinstance(tool_call, dict):
					# Handle dict format
					func = tool_call.get('function', {})
					tool_name = func.get('name', '')
					args = func.get('arguments', {})
					if isinstance(args, str):
						args = json.loads(args)
					
					converted.append({
						'name': tool_name,
						'parameters': args
					})
					self.hLG.echo("Converted native tool call (dict): {} with params: {}".format(tool_name, args), {'color':True, 'colorValue':'cyan'})
			except Exception as e:
				self.hLG.echo("Error converting native tool call: {}".format(str(e)), {'color':True, 'colorValue':'red','debugOnly':False,})
				continue
		
		return converted

	#

	def _stream_with_timeout(self, iterator, chunk_timeout):
		"""Yield items from `iterator` with a per-chunk timeout.
		Emits a waiting notification every 15s while stalled.
		If no chunk arrives within `chunk_timeout` seconds, raises
		TimeoutError so the caller can abort gracefully."""
		q = queue.Queue()
		def _reader():
			try:
				for item in iterator:
					q.put(item)
			except Exception as e:
				q.put(e)
			q.put(None)
		t = threading.Thread(target=_reader, daemon=True)
		t.start()
		ping_interval = 15
		while True:
			try:
				item = q.get(timeout=min(ping_interval, chunk_timeout))
			except queue.Empty:
				chunk_timeout -= ping_interval
				if chunk_timeout <= 0:
					raise TimeoutError(
						"Stream stalled — no chunk received within {}s".format(
							self.Options.get('STREAM_CHUNK_TIMEOUT', 120)))
				self.hLG.echo("Stream waiting... ({}s left)".format(chunk_timeout),
					{'color':True, 'colorValue':'yellow', 'debugOnly':False})
				continue
			if item is None:
				break
			if isinstance(item, Exception):
				raise item
			yield item

	#

	def Stream(self, res, color, stream_callback=None):
		response         = "" # speaking data
		thinking         = "" # thinking data
		native_tool_calls = []  # native Ollama tool calls
		if_thinking      = False
		if_speaking      = False
		last_chunk       = None
		abort_reason     = None
		#
		_stream_chunk_count = 0
		chunk_timeout = self.Options.get('STREAM_CHUNK_TIMEOUT', 120)
		try:
			for chunk in self._stream_with_timeout(res, chunk_timeout):
				_stream_chunk_count += 1
				# Periodic Ctrl+D check during streaming (every 5 chunks)
				if _stream_chunk_count % 5 == 0:
					if self._check_ai_interrupt():
						self.hLG.echo("\n[Ctrl+D detected — stream interrupted]",
							{'color':True, 'colorValue':'blue','debugOnly':False})
						if stream_callback:
							stream_callback({'type':'interrupt','reason':'ctrl_d'})
						return {'content': response, 'thinking': thinking,
								'native_tool_calls': native_tool_calls,
								'prompt_tokens': 0, 'response_tokens': 0,
								'ctrl_d_interrupt': True}
				last_chunk = chunk
				# thinking
				if chunk.message.thinking:
					#
					if not if_thinking:
						if_thinking = True
						if not self.Options.get('BUILD_THINKING_DISABLED', False):
							print('Thinking:\n', end='')
					#
					part = chunk.message.thinking
					thinking += part
					if not self.Options.get('BUILD_THINKING_DISABLED', False):
						print(part, end='', flush=True)
					if stream_callback:
						stream_callback({'type':'thinking','text':part})
				# Check for native tool calls
				elif hasattr(chunk.message, 'tool_calls') and chunk.message.tool_calls:
					# Collect native Ollama tool calls
					for tool_call in chunk.message.tool_calls:
						if tool_call not in native_tool_calls:
							native_tool_calls.append(tool_call)
					# Don't print tool calls, just collect them
				# speaking
				elif chunk.message.content:
					#
					if not if_speaking:
						print('\n\nAnswer:\n', end='')
						if_thinking = False
						if_speaking = True
					#
					part = chunk.message.content
					response += part
					# Early abort: detect misguided tool calls mid-stream
					abort_reason = self._check_stream_abort(response)
					if abort_reason:
						self.hLG.echo("\n[Aborted: {}]".format(abort_reason),
							{'color':True, 'colorValue':'red','debugOnly':False})
						if stream_callback:
							stream_callback({'type':'abort','reason':abort_reason})
						break
					if stream_callback:
						stream_callback({'type':'token','text':part})
					self.hLG.echo(part,{'color':color,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True,'speak':True})
			# Extract token counts from final chunk (done=True)
			prompt_tokens = 0
			response_tokens = 0
			if last_chunk and hasattr(last_chunk, 'done') and last_chunk.done:
				prompt_tokens = last_chunk.prompt_eval_count or 0
				response_tokens = last_chunk.eval_count or 0
		except Exception as e:
			self.hLG.echo("Stream error: {}".format(str(e)), {'color':True, 'colorValue':'red','debugOnly':False,})
			self.bg_log("Stream error: {} (got {} chunks, {} response chars)".format(
				str(e), _stream_chunk_count, len(response)), "WARN")
			return {'content':response, 'thinking':thinking, 'native_tool_calls':native_tool_calls, 'prompt_tokens':0, 'response_tokens':0, 'error':str(e), 'early_abort':abort_reason}
		return {'content':response, 'thinking':thinking, 'native_tool_calls':native_tool_calls, 'prompt_tokens':prompt_tokens, 'response_tokens':response_tokens, 'early_abort':abort_reason}

	#

	def _check_stream_abort(self, partial_response):
		"""Check if the partial response contains a tool invocation that should
		be aborted early. Returns a reason string or None."""
		mode = self.Options.get('MODE', '')

		# User-blocked tools — abort in both plan and build modes
		user_blocked = set(self.Options.get('TOOL_BLOCKED', []))
		if user_blocked:
			for m in re.finditer(r'<(\w+)[\s>]', partial_response):
				name = m.group(1)
				if name in user_blocked:
					return "'{}' is disallowed by user configuration".format(name)

		# In PLAN mode, abort on opening tag of blocked execution tools
		# (user's TOOL_ALLOWED overrides plan blocking)
		user_allowed = set(self.Options.get('TOOL_ALLOWED', []))
		if mode == 'plan':
			for m in re.finditer(r'<(\w+)[\s>]', partial_response):
				name = m.group(1)
				if name in self.hTP._plan_blocked and name not in user_allowed:
					return "'{}' cannot be used in PLAN mode".format(name)

		return None
