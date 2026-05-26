import socket, json, time, os, sys

class OrchestraWorker():
	def __init__(self, handle, host, port, name=None):
		self.handle = handle
		self.host = host
		self.port = port
		self.name = name or socket.gethostname()
		self.sock = None
		self.f = None
		self.running = True
		self.current_task_id = None

	def connect(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((self.host, self.port))
		self.f = self.sock.makefile('r')
		model = self.handle.Options.get('AI_MODEL', 'unknown')
		persona = self.handle.Options.get('INSTRUCT_CLASS', 'unknown')
		register_msg = json.dumps({
			'type': 'register',
			'name': self.name,
			'model': model,
			'persona': persona,
		})
		self.sock.sendall((register_msg + '\n').encode())
		self.handle.hLG.echo("Connected to director at {}:{} as '{}'".format(self.host, self.port, self.name), {'color':True, 'colorValue':'green'})
		return True

	def send(self, msg):
		self.sock.sendall((json.dumps(msg) + '\n').encode())

	def task_loop(self):
		self.send({'type': 'ready'})
		while self.running:
			try:
				line = self.f.readline()
				if not line:
					self.handle.hLG.echo("Director disconnected.", {'color':True, 'colorValue':'red', 'debugOnly':False})
					break
				msg = json.loads(line.strip())
				self._handle_director_message(msg)
			except Exception as e:
				self.handle.hLG.echo("Error reading from director: {}".format(e), {'color':True, 'colorValue':'red'})
				break

	def _handle_director_message(self, msg):
		msg_type = msg.get('type', '')

		if msg_type == 'assign':
			task_id = msg.get('taskId', '')
			instruction = msg.get('instruction', '')
			self.current_task_id = task_id
			self._execute_task(task_id, instruction)
			self.current_task_id = None
			self.send({'type': 'ready'})

		elif msg_type == 'plan':
			message = msg.get('message', '')
			task_id = msg.get('taskId', '')
			self.current_task_id = task_id
			self._handle_plan_request(message)
			self.current_task_id = None

		elif msg_type == 'shutdown':
			self.handle.hLG.echo("Director requested shutdown.", {'color':True, 'colorValue':'orange'})
			self.running = False

	def _execute_task(self, task_id, instruction):
		self.handle.hLG.echo("Starting task {}: {}".format(task_id[:8], instruction[:80] if instruction else ''), {'color':True, 'colorValue':'cyan', 'debugOnly':False})

		# Try to log progress to plan if available
		try:
			if self.handle.hPM.draft:
				self.handle.hPM.LogProgress(task_id, "Task started by worker '{}'".format(self.name))
		except:
			pass

		self.send({'type': 'progress', 'taskId': task_id, 'log': 'Starting task...'})

		try:
			# Append instruction as user message
			self.handle.Response('user', {'content': instruction})
			# Run AI to execute with tools
			result = self.handle.AI({'return_object': True})

			response_text = str(result)[:500] if result else "Task completed"
			try:
				if self.handle.hPM.draft:
					self.handle.hPM.LogProgress(task_id, "Completed by worker '{}': {}".format(self.name, response_text[:100]))
			except:
				pass

			self.handle.hLG.echo("Task {} completed".format(task_id[:8]), {'color':True, 'colorValue':'green', 'debugOnly':False})
			self.send({'type': 'complete', 'taskId': task_id, 'result': response_text})
		except Exception as e:
			error = str(e)
			self.handle.hLG.echo("Task {} error: {}".format(task_id[:8], error), {'color':True, 'colorValue':'red', 'debugOnly':False})
			try:
				if self.handle.hPM.draft:
					self.handle.hPM.LogProgress(task_id, "Blocked: {}".format(error[:100]))
			except:
				pass
			self.send({'type': 'blocked', 'taskId': task_id, 'error': error})

	def _handle_plan_request(self, message):
		self.handle.hLG.echo("Received plan request: {}".format(message[:80]), {'color':True, 'colorValue':'cyan', 'debugOnly':False})

		prev_mode = self.handle.Options.get('MODE', 'build')

		self.handle.Options['MODE'] = 'plan'
		system_content = self.handle.hPP._get_mode_instructions('plan')

		if self.handle.hHM.msgs and self.handle.hHM.msgs[-1]['role'] == 'system':
			self.handle.hHM.msgs[-1]['content'] = system_content
		else:
			self.handle.Response('system', {'content': system_content})

		self.handle.Response('user', {'content': message})

		result = self.handle.AI({'return_object': True})

		response_text = str(result)[:500] if result else ""

		from src.PlanManager import PlanBase
		plan_data = None
		if PlanBase.draft:
			plan_data = PlanBase.draft.to_dict()

		self.send({
			'type': 'plan_result',
			'taskId': self.current_task_id or '',
			'plan': plan_data,
			'response': response_text,
		})

		self.handle.Options['MODE'] = prev_mode

		if plan_data:
			self.handle.hLG.echo("Plan created and sent to director ({} tasks)".format(len(PlanBase.draft.tasks)), {'color':True, 'colorValue':'green', 'debugOnly':False})
		else:
			self.handle.hLG.echo("Plan request completed (no plan data)".format(), {'color':True, 'colorValue':'orange', 'debugOnly':False})

	def disconnect(self):
		self.running = False
		try:
			self.sock.close()
		except:
			pass
