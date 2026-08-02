#--
# class CommandsTimers — timer commands
class CommandsTimers():
	#
	def _parse_timer_input(self, inp):
		"""Parse timer command input. Returns (time_str, text)."""
		lines = inp.strip().split('\n', 1)
		first_line = lines[0].strip()
		text = lines[1].strip() if len(lines) > 1 else ''
		return first_line, text

	def CMD_TIMER_ONCE(self, inp=""):
		first_line, text = self._parse_timer_input(inp)
		parts = first_line.split(None, 1)
		if len(parts) < 2:
			print("Usage: !TIMER_ONCE <time> [text after newline]")
			print("  Examples: !TIMER_ONCE 5m")
			print("            !TIMER_ONCE 30s\nCheck server status")
			return 2
		tm = self.handle.hTMR
		delay = tm.parse_time(parts[1])
		if delay is None:
			print("Invalid time format: '{}'".format(parts[1]))
			print("  Examples: 5m, 30s, 1h, 1h30m, 1.5m")
			return 2
		name = tm.set_once(text, delay)
		print("Timer '{}' set: fires once in {}".format(name, self._format_duration(delay)))
		if text:
			print("  Text: {}".format(text[:80] + ('...' if len(text) > 80 else '')))
		return 2

	def CMD_TIMER_REPEAT(self, inp=""):
		first_line, text = self._parse_timer_input(inp)
		parts = first_line.split(None, 2)
		if len(parts) < 3:
			print("Usage: !TIMER_REPEAT <count> <interval> [text after newline]")
			print("  Examples: !TIMER_REPEAT 5 10m")
			print("            !TIMER_REPEAT 3 30s\nCheck status")
			return 2
		tm = self.handle.hTMR
		try:
			count = int(parts[1])
		except ValueError:
			print("Invalid count: '{}'".format(parts[1]))
			return 2
		interval = tm.parse_time(parts[2])
		if interval is None:
			print("Invalid interval: '{}'".format(parts[2]))
			print("  Examples: 5m, 30s, 1h, 1h30m")
			return 2
		name = tm.set_repeat(text, interval, count)
		print("Timer '{}' set: {}x every {}".format(name, count, self._format_duration(interval)))
		if text:
			print("  Text: {}".format(text[:80] + ('...' if len(text) > 80 else '')))
		return 2

	def CMD_TIMER_LOOP(self, inp=""):
		first_line, text = self._parse_timer_input(inp)
		parts = first_line.split(None, 1)[1:] if len(first_line.split()) > 1 else []
		tm = self.handle.hTMR
		default_interval = 60  # 1 minute default

		if not parts:
			# !TIMER_LOOP — no args, default interval, forever
			name = tm.set_loop(text, default_interval)
			print("Timer '{}' set: loops every 1m (use !TIMER_STOP to cancel)".format(name))
		elif len(parts) == 1:
			# !TIMER_LOOP 10m — delay before first fire
			delay = tm.parse_time(parts[0])
			if delay is None:
				print("Invalid time: '{}'".format(parts[0]))
				return 2
			name = tm.set_loop(text, default_interval, delay_sec=delay)
			print("Timer '{}' set: starts in {}, loops every 1m (use !TIMER_STOP to cancel)".format(
				name, self._format_duration(delay)))
		else:
			# !TIMER_LOOP 10m 30m — delay + duration
			delay = tm.parse_time(parts[0])
			duration = tm.parse_time(parts[1])
			if delay is None:
				print("Invalid start delay: '{}'".format(parts[0]))
				return 2
			if duration is None:
				print("Invalid duration: '{}'".format(parts[1]))
				return 2
			name = tm.set_loop(text, default_interval, delay_sec=delay, duration_sec=duration)
			print("Timer '{}' set: starts in {}, stops after {}, loops every 1m".format(
				name, self._format_duration(delay), self._format_duration(duration)))

		if text:
			print("  Text: {}".format(text[:60] + ('...' if len(text) > 60 else '')))
		return 2

	def CMD_TIMER_STOP(self, inp=""):
		tm = self.handle.hTMR
		parts = inp.strip().split()
		# !TIMER_STOP <index> — stop specific timer
		if len(parts) > 1:
			try:
				index = int(parts[1])
			except ValueError:
				print("Usage: !TIMER_STOP [index]")
				print("  Use !TIMER_LIST to see available indices.")
				return 2
			name, ok = tm.stop_by_index(index)
			if ok:
				print("Timer '{}' (index {}) stopped.".format(name, index))
			else:
				names = tm.list_active()
				if not names:
					print("No active timers.")
				else:
					print("Invalid index: {}. Use !TIMER_LIST to see available indices.".format(index))
			return 2
		# !TIMER_STOP — stop all
		active = tm.list_active()
		count = tm.stop_all()
		if count == 0:
			print("No active timers.")
		else:
			for name in active:
				print("Timer '{}' stopped.".format(name))
			print("{} timer(s) cancelled.".format(count))
		return 2

	def CMD_TIMER_LIST(self, inp=""):
		tm = self.handle.hTMR
		details = tm.list_active_details()
		if not details:
			print("No active timers.")
			return 2
		print("Active timers ({}):".format(len(details)))
		for i, d in enumerate(details):
			interval_str = self._format_duration(d['interval']) if d['interval'] else '?'
			type_str = d['type'].upper()
			fired = d['fired']
			total = d.get('total')
			if type_str == 'ONCE':
				status = "in {}".format(interval_str)
			elif type_str == 'REPEAT':
				status = "every {} (fired {}/{})".format(interval_str, fired, total)
			else:
				status = "every {}".format(interval_str)
			text_preview = d.get('text', '')
			print("  [{}] {} — {} {}".format(i, d['name'], type_str, status))
			if text_preview:
				preview = text_preview[:60] + ('...' if len(text_preview) > 60 else '')
				print("       Text: {}".format(preview))
		return 2

	def _format_duration(self, seconds):
		"""Format seconds into human-readable duration."""
		if seconds < 60:
			return "{}s".format(int(seconds))
		elif seconds < 3600:
			m = int(seconds // 60)
			s = int(seconds % 60)
			return "{}m{}s".format(m, s) if s else "{}m".format(m)
		else:
			h = int(seconds // 3600)
			m = int((seconds % 3600) // 60)
			return "{}h{}m".format(h, m) if m else "{}h".format(h)

