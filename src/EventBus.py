"""EventBus — pub/sub event system for multi-client broadcast.

Clients subscribe to receive real-time events (tool calls, file writes, etc.)
via persistent SSE connections. The server publishes events when activity occurs.

Usage:
	bus = EventBus()
	bus.subscribe("client_123", callback)
	bus.publish({"type": "tool_started", "name": "WriteFile"}, session="default")
	bus.unsubscribe("client_123")
"""

import threading
import time
import json
import collections


class EventBus:
	"""Thread-safe pub/sub event bus for broadcasting to multiple SSE clients."""

	def __init__(self, max_history=100):
		self._lock = threading.Lock()
		# client_id -> list of queue objects (one per SSE connection)
		self._subscribers = {}
		# ring buffer of recent events per session for new subscribers
		self._history = collections.defaultdict(lambda: collections.deque(maxlen=max_history))
		self._max_history = max_history

	def subscribe(self, client_id, q=None):
		"""Register a client for events. Returns a queue to read from.

		Args:
			client_id: unique client identifier
			q: optional queue.Queue to use (creates one if None)

		Returns:
			queue.Queue that will receive event dicts
		"""
		import queue as _queue
		if q is None:
			q = _queue.Queue()
		with self._lock:
			if client_id not in self._subscribers:
				self._subscribers[client_id] = []
			self._subscribers[client_id].append(q)
		return q

	def unsubscribe(self, client_id, q=None):
		"""Remove a client's subscription.

		Args:
			client_id: client identifier
			q: specific queue to remove (removes all if None)
		"""
		with self._lock:
			if client_id in self._subscribers:
				if q is not None:
					try:
						self._subscribers[client_id].remove(q)
					except ValueError:
						pass
					if not self._subscribers[client_id]:
						del self._subscribers[client_id]
				else:
					del self._subscribers[client_id]

	def publish(self, event, session="default"):
		"""Publish an event to all subscribers.

		Args:
			event: dict to broadcast (will get timestamp + event_id added)
			session: session name for history (default: "default")

		Returns:
			number of subscribers that received the event
		"""
		event = dict(event)
		event.setdefault("timestamp", time.time())
		event.setdefault("event_id", "{}_{}".format(
			int(time.time() * 1000), id(event) % 10000))

		# Store in history
		with self._lock:
			self._history[session].append(event)

		# Broadcast to all subscribers
		sent = 0
		with self._lock:
			all_queues = []
			for client_queues in self._subscribers.values():
				all_queues.extend(client_queues)

		for q in all_queues:
			try:
				q.put_nowait(event)
				sent += 1
			except Exception:
				pass
		return sent

	def publish_to(self, client_id, event):
		"""Publish an event to a specific client only.

		Args:
			client_id: target client
			event: dict to send

		Returns:
			True if delivered, False otherwise
		"""
		event = dict(event)
		event.setdefault("timestamp", time.time())
		with self._lock:
			queues = self._subscribers.get(client_id, [])
		for q in queues:
			try:
				q.put_nowait(event)
				return True
			except Exception:
				continue
		return False

	def get_history(self, session="default", limit=50):
		"""Get recent events for a session (for new subscribers to catch up).

		Args:
			session: session name
			limit: max events to return

		Returns:
			list of event dicts
		"""
		with self._lock:
			hist = self._history.get(session, collections.deque())
			items = list(hist)
		return items[-limit:]

	def get_subscriber_count(self):
		"""Return total number of active subscriber queues."""
		with self._lock:
			return sum(len(qs) for qs in self._subscribers.values())

	def get_client_ids(self):
		"""Return list of client IDs with active subscriptions."""
		with self._lock:
			return list(self._subscribers.keys())

	def has_client(self, client_id):
		"""Check if a client has any active subscriptions."""
		with self._lock:
			return client_id in self._subscribers and len(self._subscribers[client_id]) > 0

	def clear_session_history(self, session="default"):
		"""Clear event history for a session."""
		with self._lock:
			if session in self._history:
				self._history[session].clear()
