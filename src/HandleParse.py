import hashlib, re
#
class HandleParse():

	#

	def One(self,data, opts=None):
		if opts is None:
			opts = {}
		
		opt_history_num    = opts.get('history_num')
		self.Init()
		#
		if opt_history_num!=None:
			# load specific history
			self.hHM.Update()
			self.hHM.history = self.hHM.available[opt_history_num]
			self.hHM.Get()
		#
		# Apply persona settings (model override, max_iterations, thinking)
		# so -Y mode behaves the same as interactive mode
		if self.Options.get('INSTRUCT_CLASS_OVERRIDE', False):
			self.hIM.ApplyPersonaModel(self.Options['INSTRUCT_CLASS'])
		# Apply model registry for -Y mode (covers -m flag without persona)
		from src.ModelRegistry import apply as apply_registry
		_model = self.Options.get('AI_MODEL', '')
		if _model:
			_changes = apply_registry(self.Options, _model)
			if _changes:
				for _c in _changes:
					self.hLG.echo("  Model config: {}".format(_c),
						{'color':True, 'colorValue':'cyan'})
		#
		# Add system message if not already present (for -Y flag mode)
		system_exists = False
		for msg in self.hHM.msgs:
			if msg['role'] == 'system':
				system_exists = True
				break
		if not system_exists:
			# Add mode instructions from config
			mode = self.Options.get('MODE', 'build')
			system_msg = self.hPP._get_mode_instructions(mode)
			self.Response('system',{'content':system_msg})
		#
		self.You( data, opts )
		#
		return self.AI( opts )
	

	#

	def Parse(self, res, opts=None):
		if opts is None:
			opts = {}
		
		#
		opt_skip_history  = opts['skip_history'] if 'skip_history' in opts else False
		opt_skip_color    = opts['skip_color'] if 'skip_color' in opts else False
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		opt_stream_cb     = opts.get('stream_callback')
		color             = True
		if opt_skip_color:
			color=False
		#
		stream_error = None
		response = self.Stream( res, color, opt_stream_cb )
		if 'error' in response:
			stream_error = response['error']
			if stream_error:
				self.hLG.echo("Stream error: {}".format(stream_error), {'color':True, 'colorValue':'red','debugOnly':False,})
				# Signal auto-clear for request-too-large errors
				err_lower = stream_error.lower()
				if ('too large' in err_lower or '400' in err_lower or '413' in err_lower or 'request body' in err_lower):
					if opt_return_object:
						return {'invocations': [], 'response': response.get('content', ''),
								'stream_error': stream_error, 'stream_too_large': True}
					return True

		# Ctrl+D interrupt — save partial response and signal caller
		if response.get('ctrl_d_interrupt'):
			self.Response('assistant', {
				'content': response.get('content', ''),
				'thinking': response.get('thinking', ''),
				'skip_history': opt_skip_history,
				'prompt_tokens': response.get('prompt_tokens', 0),
				'response_tokens': response.get('response_tokens', 0),
			})
			self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
			if opt_return_object:
				return {'invocations': [], 'response': response.get('content', ''),
						'stream_error': stream_error, 'ctrl_d_interrupt': True}
			return True

		# Early abort from Stream() — skip tool invocation detection
		early_abort = response.get('early_abort')
		if early_abort:
			self.hLG.echo("Stream aborted: {}".format(early_abort),
				{'color':True, 'colorValue':'red','debugOnly':False})
			self.Response('assistant',{
				'content': response.get('content', ''),
				'thinking': response.get('thinking', ''),
				'skip_history': opt_skip_history,
				'prompt_tokens': response.get('prompt_tokens', 0),
				'response_tokens': response.get('response_tokens', 0),
			})
			self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
			# Extract blocked tool name from early_abort message for user prompt
			plan_blocked = None
			if self.Options.get('MODE') == 'plan':
				m = re.search(r"'(\w+)'", early_abort)
				if m:
					plan_blocked = m.group(1)
			if opt_return_object:
				return {'invocations': [], 'response': response.get('content', ''),
						'stream_error': stream_error, 'plan_blocked': plan_blocked}
			return True

		# Strip <think>...</think> from content — the model may include these
		# in its content field (separate from native thinking API).  Stripping
		# early prevents spurious tool detection, hash mismatches, and history
		# pollution.
		response['content'] = re.sub(r'<think>.*?</think>', '', response.get('content', ''), flags=re.DOTALL)
		response['content'] = re.sub(r'</think>', '', response.get('content', ''))
		
		# Detect repeated responses (model looping)
		# _last_response_hash persists across AI() calls — only reset by new user input in You()
		# Skip check for thinking-only responses (empty content) — they all hash to the same
		# empty-string MD5 and flood false positives.
		current_content = response.get('content', '').strip()
		if current_content:
			current_hash = hashlib.md5(current_content.encode()).hexdigest()
			if self._last_response_hash is not None and current_hash == self._last_response_hash:
				self.hLG.echo("⚠ Model repeated itself — auto-cancelled", {'color':True, 'colorValue':'red','debugOnly':False,})
				if opt_return_object:
					return {'invocations': [], 'response': current_content, 'stream_error': stream_error }
				return True
			self._last_response_hash = current_hash
		else:
			# Reset hash on thinking-only — avoids false collisions from empty content
			self._last_response_hash = None

		#
		# Detect tool invocations before adding assistant response
		# (needs to be first so we can clean XML from assistant content if needed)
		tool_invocations = []
		native_tool_calls = response.get('native_tool_calls', [])
		
		if native_tool_calls:
			self.hLG.echo("Parse() detected {} native Ollama tool call(s)".format(len(native_tool_calls)), {'color':True, 'colorValue':'cyan'})
			tool_invocations = self._convert_native_tool_calls(native_tool_calls)
		
		if not tool_invocations:
			tool_invocations = self.hTP.ParseTextToolInvocation( response['content'] )
			if tool_invocations:
				self.hLG.echo("Parse() detected {} XML tool invocation(s)".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
		
		if tool_invocations and opt_stream_cb:
			for inv in tool_invocations:
				opt_stream_cb({'type':'tool_start','tool':inv['name'],'params':inv.get('parameters',{})})
		
		# Clean assistant content: strip XML tags when using system-role results
		# so the model doesn't see stale tool calls in its own history
		assistant_content = response['content']
		if tool_invocations and (self.Options.get('TOOL_RESULT_AS_SYSTEM', False) or self.Options.get('TOOL_RESULT_AS_USER', False)):
			assistant_content = self.hTP.ExtractToolResult(response['content'])
		#
		# Strip thinking from history when tool calls were made —
		# the reasoning describes planned actions and confuses the
		# model into re-issuing them on the next iteration.
		thinking_for_history = response['thinking'] if not tool_invocations else ''
		self.Response('assistant',{
			'content':assistant_content,
			'thinking':thinking_for_history,
			'skip_history':opt_skip_history,
			'prompt_tokens':response.get('prompt_tokens', 0),
			'response_tokens':response.get('response_tokens', 0),
		})
		#
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		#
		if tool_invocations:
			#
			job_done = any(inv['name'] == 'jobDone' for inv in tool_invocations)
			#
			result = self.hTP.FireToolInvocation(tool_invocations)
			#
			if opt_stream_cb:
				result_str = str(result) if result else ""
				for inv in tool_invocations:
					opt_stream_cb({'type':'tool_result','tool':inv['name'],'success':not result_str.startswith('Error:'),'result':result_str[:2000]})
			#
			plan_blocked = getattr(self, '_plan_blocked_tool', None)
			if plan_blocked:
				self._plan_blocked_tool = None
				return {'invocations': tool_invocations, 'response': response['content'],
						'job_done': job_done, 'stream_error': stream_error,
						'plan_blocked': plan_blocked}
			# Handle nextTask response in build mode - auto-add next task to history
			if self.Options.get('MODE') == 'build':
				for inv in tool_invocations:
					if inv['name'] == 'nextTask':
						result_str = str(result) if result else ""
						if result_str.startswith("NEXT_TASK:"):
							next_instruction = result_str[10:]
							self.Response('user', {'content': "<nextTask>\n\nYour task:\n{}".format(next_instruction)})
							self._write_current_task()
						elif result_str.startswith("ALL_COMPLETED:"):
							self.hLG.echo("Plan completed! All tasks finished.", {'color':True, 'colorValue':'green'})
						elif result_str.startswith("DONE_WITH_BLOCKED:"):
							self.hLG.echo("Plan has blocked tasks. Consider switching to PLAN mode to resolve.", {'color':True, 'colorValue':'orange'})
					elif inv['name'] == 'startBuild':
						result_str = str(result) if result else ""
						if result_str.startswith("START_BUILD|"):
							parts = result_str.split("|", 2)
							task_info = parts[1]
							instruction = parts[2]
							self.Response('user', {'content': "Mode changed to BUILD. You can now make changes.\n\n{} - {}".format(task_info, instruction)})
							self._write_current_task()
			# Handle planDone in any mode — inject user message and signal completion
			plan_done = any(inv['name'] == 'planDone' for inv in tool_invocations)
			if plan_done:
				result_str = str(result) if result else ""
				if result_str.startswith("PLAN_DONE|"):
					parts = result_str.split("|", 2)
					task_info = parts[1]
					instruction = parts[2]
					self.Response('user', {'content': "Plan is ready! Starting first task.\n\n{} - {}".format(task_info, instruction)})
					self._write_current_task()
			#
			# Return the original response so caller knows tools were executed
			return {'invocations': tool_invocations, 'response': response['content'],
					'job_done': job_done, 'stream_error': stream_error,
					'plan_done': plan_done}
		#
		if opt_return_object:
			return {'invocations': tool_invocations, 'response': response['content'], 'stream_error': stream_error }
		return True
