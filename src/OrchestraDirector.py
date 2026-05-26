import socket, threading, json, queue, time, os, sys
from src.functions import importmodule, initmodule

class OrchestraDirector():
	def __init__(self, handle, port=9876, host="0.0.0.0"):
		self.handle = handle
		self.port = port
		self.host = host
		self.server_sock = None
		self.running = False
		self.server_thread = None
		self.workers = {}
		self.msg_queue = queue.Queue()
		self.lock = threading.Lock()
		self.dispatch_mode = False

	def start(self):
		self.running = True
		self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
		self.server_thread.start()
		self.handle.hLG.echo("Orchestra director listening on {}:{}".format(self.host, self.port), {'color':True, 'colorValue':'cyan'})

	def stop(self):
		self.running = False
		if self.server_sock:
			try:
				self.server_sock.close()
			except:
				pass

	def _server_loop(self):
		self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server_sock.bind((self.host, self.port))
		self.server_sock.listen(5)
		self.server_sock.settimeout(1.0)

		while self.running:
			try:
				client, addr = self.server_sock.accept()
				t = threading.Thread(target=self._worker_handler, args=(client, addr), daemon=True)
				t.start()
			except socket.timeout:
				continue
			except Exception as e:
				if self.running:
					print("Orchestra server error:", e)

	def _worker_handler(self, sock, addr):
		f = sock.makefile('r')
		try:
			line = f.readline()
			if not line:
				return
			msg = json.loads(line.strip())
			if msg.get('type') == 'register':
				name = msg.get('name', '{}:{}'.format(addr[0], addr[1]))
				model = msg.get('model', 'unknown')
				persona = msg.get('persona', 'unknown')
				with self.lock:
					self.workers[name] = {
						'sock': sock,
						'f': f,
						'addr': addr,
						'model': model,
						'persona': persona,
						'status': 'idle',
						'busy_since': None,
					}
				self.handle.hLG.echo("Worker '{}' connected (model: {}, persona: {})".format(name, model, persona), {'color':True, 'colorValue':'green'})
				while self.running:
					line = f.readline()
					if not line:
						break
					msg = json.loads(line.strip())
					msg['_worker'] = name
					self.msg_queue.put(msg)
					if msg.get('type') == 'ready':
						with self.lock:
							if name in self.workers:
								self.workers[name]['status'] = 'idle'
								self.workers[name]['busy_since'] = None
					elif msg.get('type') in ('complete', 'blocked'):
						with self.lock:
							if name in self.workers:
								self.workers[name]['status'] = 'idle'
								self.workers[name]['busy_since'] = None
		except Exception as e:
			if self.running:
				print("Worker handler error:", e)
		finally:
			with self.lock:
				for n, w in list(self.workers.items()):
					if w['sock'] == sock:
						del self.workers[n]
						self.handle.hLG.echo("Worker '{}' disconnected".format(n), {'color':True, 'colorValue':'orange'})
						break
			try:
				sock.close()
			except:
				pass

	def set_plan_worker(self, name):
		if name is None:
			self.handle.Options['PLAN_WORKER'] = None
			self.handle.hLG.echo("Plan worker disabled. Director will plan locally.", {'color':True, 'colorValue':'cyan'})
			return True
		with self.lock:
			if name not in self.workers:
				return False
		self.handle.Options['PLAN_WORKER'] = name
		self.handle.hLG.echo("Plan worker set to '{}'".format(name), {'color':True, 'colorValue':'green'})
		return True

	def route_to_plan_worker(self, message):
		name = self.handle.Options.get('PLAN_WORKER', None)
		if not name:
			return None
		with self.lock:
			if name not in self.workers:
				self.handle.hLG.echo("Plan worker '{}' not connected.".format(name), {'color':True, 'colorValue':'red'})
				return None
			worker = self.workers[name]
			if worker['status'] != 'idle':
				self.handle.hLG.echo("Plan worker '{}' is busy.".format(name), {'color':True, 'colorValue':'orange'})
				return None
			worker['status'] = 'busy'
			worker['busy_since'] = time.time()
			sock = worker['sock']

		task_id = str(time.time())
		msg = json.dumps({'type': 'plan', 'taskId': task_id, 'message': message})
		try:
			sock.sendall((msg + '\n').encode())
		except Exception as e:
			self.handle.hLG.echo("Failed to send plan request: {}".format(e), {'color':True, 'colorValue':'red'})
			with self.lock:
				if name in self.workers:
					self.workers[name]['status'] = 'idle'
					self.workers[name]['busy_since'] = None
			return None

		self.handle.hLG.echo("Sent plan request to '{}'...".format(name), {'color':True, 'colorValue':'cyan'})

		found = None
		timeout = 300
		start = time.time()
		while time.time() - start < timeout and self.running:
			while not self.msg_queue.empty():
				try:
					qmsg = self.msg_queue.get_nowait()
					if qmsg.get('type') == 'plan_result' and qmsg.get('_worker') == name:
						found = qmsg
						break
					self._handle_worker_message(qmsg)
				except queue.Empty:
					break
			if found:
				break
			time.sleep(0.2)

		with self.lock:
			if name in self.workers:
				self.workers[name]['status'] = 'idle'
				self.workers[name]['busy_since'] = None

		if found:
			from src.PlanManager import PlanBase, Plan
			plan_data = found.get('plan')
			response_text = found.get('response', '')
			if plan_data:
				plan = Plan.from_dict(plan_data)
				PlanBase.draft = plan
				if hasattr(plan, 'save'):
					plan.save()
				self.handle.hLG.echo("Plan '{}' loaded from worker '{}' ({} tasks)".format(
					plan.title, name, len(plan.tasks)), {'color':True, 'colorValue':'green'})
			if response_text:
				self.handle.Response('assistant', {'content': response_text})
			self.handle.hLG.echo("Planning from worker complete.", {'color':True, 'colorValue':'green'})
			return plan_data

		self.handle.hLG.echo("Plan request to '{}' timed out.".format(name), {'color':True, 'colorValue':'red'})
		return None

	def poll_workers(self):
		processed = False
		while not self.msg_queue.empty():
			try:
				msg = self.msg_queue.get_nowait()
				self._handle_worker_message(msg)
				processed = True
			except queue.Empty:
				break
		return processed

	def _handle_worker_message(self, msg):
		msg_type = msg.get('type', '')
		worker = msg.get('_worker', '?')
		task_id = msg.get('taskId', '')

		if msg_type == 'progress':
			log = msg.get('log', '')
			self.handle.hLG.echo("[{}] {}: {}".format(worker, task_id[:8] if task_id else '', log), {'color':True, 'colorValue':'blue', 'debugOnly':False})
		elif msg_type == 'complete':
			result = msg.get('result', '')
			self.handle.hLG.echo("[{}] Task {} completed: {}".format(worker, task_id[:8] if task_id else '', result[:120] if result else ''), {'color':True, 'colorValue':'green', 'debugOnly':False})
		elif msg_type == 'blocked':
			error = msg.get('error', '')
			self.handle.hLG.echo("[{}] Task {} blocked: {}".format(worker, task_id[:8] if task_id else '', error), {'color':True, 'colorValue':'red', 'debugOnly':False})
		elif msg_type == 'ready':
			if self.dispatch_mode:
				self.handle.hLG.echo("[{}] Ready for next task".format(worker), {'color':True, 'colorValue':'cyan', 'debugOnly':False})

	def dispatch_task(self, task_id, instruction):
		with self.lock:
			idle_workers = [(n, w) for n, w in self.workers.items() if w['status'] == 'idle']
			if not idle_workers:
				return None
			name, worker = idle_workers[0]
			worker['status'] = 'busy'
			worker['busy_since'] = time.time()

		msg = json.dumps({'type': 'assign', 'taskId': task_id, 'instruction': instruction})
		try:
			worker['sock'].sendall((msg + '\n').encode())
			self.handle.hLG.echo("Dispatched task {} to '{}'".format(task_id[:8], name), {'color':True, 'colorValue':'cyan', 'debugOnly':False})
			return name
		except Exception as e:
			self.handle.hLG.echo("Failed to dispatch to '{}': {}".format(name, e), {'color':True, 'colorValue':'red'})
			with self.lock:
				if name in self.workers:
					self.workers[name]['status'] = 'idle'
					self.workers[name]['busy_since'] = None
			return None

	def enter_dispatch_mode(self):
		from src.PlanManager import PlanBase
		if not PlanBase.draft:
			self.handle.hLG.echo("No active plan to dispatch.", {'color':True, 'colorValue':'orange'})
			return
		if self.get_idle_count() == 0:
			self.handle.hLG.echo("No idle workers available.", {'color':True, 'colorValue':'orange'})
			status = self.get_status_str()
			self.handle.hLG.echo("Workers:\n{}".format(status), {'color':True, 'colorValue':'cyan'})
			return

		self.dispatch_mode = True
		self.handle.hLG.echo("Entering dispatch mode. Dispatching tasks to workers...", {'color':True, 'colorValue':'cyan', 'debugOnly':False})

		plan = PlanBase.draft
		pending = [(tid, t) for tid, t in plan.tasks.items() if t.status == 'pending']
		if not pending:
			self.handle.hLG.echo("No pending tasks in plan.", {'color':True, 'colorValue':'orange'})
			self.dispatch_mode = False
			return

		# Dispatch all pending tasks
		for tid, task in pending:
			# Wait for idle worker
			while self.get_idle_count() == 0 and self.running:
				self.poll_workers()
				time.sleep(0.1)

			if not self.running:
				break

			task.status = 'in_progress'
			task.startTimestamp = time.time()
			plan.save()

			worker_name = self.dispatch_task(tid, task.instruction)
			if worker_name is None:
				self.handle.hLG.echo("Failed to dispatch task {}. No workers available.".format(tid[:8]), {'color':True, 'colorValue':'red'})
				break

		# Wait for all busy workers to complete
		while self.get_busy_count() > 0 and self.running:
			self.poll_workers()
			time.sleep(0.2)

		# Process any remaining messages
		self.poll_workers()

		self.dispatch_mode = False
		self.handle.hLG.echo("\nDispatch complete. All tasks dispatched.", {'color':True, 'colorValue':'green', 'debugOnly':False})

	def get_idle_count(self):
		with self.lock:
			return sum(1 for w in self.workers.values() if w['status'] == 'idle')

	def get_busy_count(self):
		with self.lock:
			return sum(1 for w in self.workers.values() if w['status'] == 'busy')

	def get_worker_count(self):
		with self.lock:
			return len(self.workers)

	def get_status_str(self):
		with self.lock:
			if not self.workers:
				return "No workers connected."
			lines = []
			for name, w in sorted(self.workers.items()):
				status = w['status']
				model = w['model']
				persona = w['persona']
				if status == 'busy' and w['busy_since']:
					elapsed = int(time.time() - w['busy_since'])
					lines.append("  {} | {} | {} | busy {}s".format(name, model, persona, elapsed))
				else:
					lines.append("  {} | {} | {} | idle".format(name, model, persona))
			return "\n".join(lines)
