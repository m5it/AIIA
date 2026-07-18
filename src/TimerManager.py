"""TimerManager — background timer system for AIIA.

Supports:
  !TIMER_ONCE  5m            — fire once after delay
  !TIMER_ONCE  5m\ntext      — fire once, inject text
  !TIMER_REPEAT 5 10m        — fire 5 times, 10m interval
  !TIMER_REPEAT 3 30s\ntext  — fire 3 times, 30s interval, inject text
  !TIMER_LOOP  5m            — loop every 5m until stopped
  !TIMER_LOOP  30s\ntext     — loop every 30s, inject text
  !TIMER_LIST                — list all active timers
  !TIMER_STOP                — cancel all active timers
  !TIMER_STOP 0              — cancel specific timer by index
"""

import re
import time
import threading
import queue


class TimerManager:
	"""Manages background timers that inject messages into the chat."""

	def __init__(self, handle):
		self.handle = handle
		self._timers = {}       # name -> threading.Timer
		self._meta = {}         # name -> {type, interval, count, created_at, fired}
		self._lock = threading.Lock()
		self._queue = queue.Queue()
		self._counter = 0       # auto-incrementing name counter

	def parse_time(self, time_str):
		"""Parse time string like '5m', '30s', '1h30m', '1.5m' -> seconds."""
		time_str = time_str.strip().lower()
		total = 0.0
		pattern = re.findall(r'(\d+\.?\d*)\s*(h|m|s)?', time_str)
		if not pattern:
			return None
		for val, unit in pattern:
			val = float(val)
			if unit == 'h':
				total += val * 3600
			elif unit == 'm':
				total += val * 60
			elif unit == 's':
				total += val
			else:
				total += val  # no unit = seconds
		return total if total > 0 else None

	def _next_name(self):
		"""Generate auto-incrementing timer name."""
		self._counter += 1
		return "timer_{}".format(self._counter)

	def _fire(self, name, text, timer_type, interval_sec, count=None):
		"""Timer callback — puts message in queue, reschedules if repeat/loop."""
		# Track fired count
		with self._lock:
			if name in self._meta:
				self._meta[name]['fired'] = self._meta[name].get('fired', 0) + 1
		self._queue.put({
			'type': timer_type,
			'name': name,
			'text': text,
			'timestamp': time.time(),
		})
		# Reschedule repeat/loop timers
		if timer_type == 'repeat' and count is not None and count > 1:
			with self._lock:
				self._schedule(name, text, interval_sec, 'repeat', count - 1)
		elif timer_type == 'loop':
			with self._lock:
				self._schedule(name, text, interval_sec, 'loop', None)
		# One-shot or final repeat — remove metadata
		elif name in self._meta:
			with self._lock:
				if timer_type == 'once':
					del self._meta[name]

	def _schedule(self, name, text, delay_sec, timer_type, count=None):
		"""Schedule a timer. Internal — caller must hold _lock."""
		# Cancel existing timer with same name
		if name in self._timers:
			self._timers[name].cancel()
		timer = threading.Timer(delay_sec, self._fire, args=[name, text, timer_type, delay_sec, count])
		timer.daemon = True
		self._timers[name] = timer
		# Store metadata
		self._meta[name] = {
			'type': timer_type,
			'interval': delay_sec,
			'total': count if count else (1 if timer_type == 'once' else None),
			'fired': self._meta.get(name, {}).get('fired', 0),
			'created_at': time.time(),
			'text': text,
		}
		timer.start()

	def set_once(self, text, delay_sec, name=None):
		"""Set a one-shot timer."""
		if name is None:
			name = self._next_name()
		with self._lock:
			self._schedule(name, text, delay_sec, 'once', None)
		return name

	def set_repeat(self, text, interval_sec, count, name=None):
		"""Set a repeat timer (fires count times)."""
		if name is None:
			name = self._next_name()
		with self._lock:
			self._schedule(name, text, interval_sec, 'repeat', count)
		return name

	def set_loop(self, text, interval_sec, name=None, delay_sec=None, duration_sec=None):
		"""Set a loop timer (fires until stopped or duration reached).
		
		Args:
			text: Message to inject on each fire.
			interval_sec: Seconds between fires.
			name: Optional timer name.
			delay_sec: Seconds to wait before first fire (default: interval_sec).
			duration_sec: Total seconds before auto-stop (default: None = forever).
		"""
		if name is None:
			name = self._next_name()
		first_fire = delay_sec if delay_sec else interval_sec
		with self._lock:
			self._schedule(name, text, first_fire, 'loop', None)
		# Schedule auto-stop after duration
		if duration_sec:
			stop_timer = threading.Timer(duration_sec, self._auto_stop, args=[name])
			stop_timer.daemon = True
			stop_timer.start()
			with self._lock:
				if name in self._meta:
					self._meta[name]['duration'] = duration_sec
					self._meta[name]['stop_at'] = time.time() + duration_sec
		return name

	def _auto_stop(self, name):
		"""Auto-stop a timer by name (called by duration timer)."""
		with self._lock:
			if name in self._timers:
				self._timers[name].cancel()
				del self._timers[name]
				self._meta.pop(name, None)

	def stop_all(self):
		"""Cancel all active timers. Returns count of stopped timers."""
		with self._lock:
			count = len(self._timers)
			for name, timer in self._timers.items():
				timer.cancel()
			self._timers.clear()
			self._meta.clear()
		return count

	def stop_by_index(self, index):
		"""Cancel a specific timer by its list index (0-based). Returns (name, True) or (None, False)."""
		with self._lock:
			names = list(self._timers.keys())
			if index < 0 or index >= len(names):
				return None, False
			name = names[index]
			self._timers[name].cancel()
			del self._timers[name]
			self._meta.pop(name, None)
		return name, True

	def list_active(self):
		"""Return list of active timer names."""
		with self._lock:
			return list(self._timers.keys())

	def list_active_details(self):
		"""Return list of dicts with timer details."""
		with self._lock:
			result = []
			for name, meta in self._meta.items():
				elapsed = time.time() - meta.get('created_at', time.time())
				result.append({
					'name': name,
					'type': meta.get('type', 'once'),
					'interval': meta.get('interval', 0),
					'fired': meta.get('fired', 0),
					'total': meta.get('total'),
					'elapsed': elapsed,
					'text': meta.get('text', ''),
				})
			return result

	def poll(self):
		"""Drain queue and inject messages. Called from poll_callback in user_input()."""
		injected = False
		while not self._queue.empty():
			try:
				msg = self._queue.get_nowait()
			except queue.Empty:
				break
			text = msg['text']
			if not text:
				text = "[Timer '{}' fired]".format(msg['name'])
			self.handle.Response('user', {'content': text})
			injected = True
		if injected:
			self.handle._timer_skip_you = True
		return injected

	def check_interrupt(self):
		"""Check queue at AI iteration boundaries. For TIMER_INTERRUPT mode."""
		if not self.handle.Options.get('TIMER_INTERRUPT', False):
			return False
		injected = False
		while not self._queue.empty():
			try:
				msg = self._queue.get_nowait()
			except queue.Empty:
				break
			text = msg['text']
			if not text:
				text = "[Timer '{}' fired]".format(msg['name'])
			self.handle.Response('user', {'content': text})
			injected = True
		return injected
