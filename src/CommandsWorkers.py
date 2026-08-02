#--
# class CommandsWorkers — orchestra worker commands
class CommandsWorkers():
	#
	def CMD_WORKERS(self, inp=""):
		if hasattr(self.handle, 'hOD') and self.handle.hOD:
			print(self.handle.hOD.get_status_str())
		else:
			print("Orchestra not available in this mode.")
		return 2

	def CMD_DISPATCH(self, inp=""):
		if not hasattr(self.handle, 'hOD') or not self.handle.hOD:
			print("Orchestra not available in this mode.")
			return 2
		self.handle.hOD.enter_dispatch_mode()
		return 2

	def CMD_PLAN_WORKER(self, inp=""):
		if not hasattr(self.handle, 'hOD') or not self.handle.hOD:
			print("Orchestra not available in this mode.")
			return 2
		parts = inp.strip().split()
		if len(parts) < 2:
			current = self.handle.Options.get('PLAN_WORKER', None)
			if current:
				print("Plan worker: {} (use !PLAN_WORKER off to disable)".format(current))
			else:
				print("No plan worker set. Director plans locally.")
			return 2
		name = parts[1].strip().lower()
		if name == 'off':
			self.handle.hOD.set_plan_worker(None)
			return 2
		ok = self.handle.hOD.set_plan_worker(name)
		if not ok:
			print("Worker '{}' not found. Use !WORKERS to see connected workers.".format(name))
		return 2

