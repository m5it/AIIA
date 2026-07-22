import os
from src.functions import *


class ServerFactory():
	"""Discovers and loads server profiles from server_profiles/ directory.
	
	Analogous to InstructManager but for server types.
	Profiles are Python classes in server_profiles/*.py that extend _ServerBase.
	"""
	
	def __init__(self, Options):
		self.Options = Options
		self.profiles_path = Options.get('SERVER_PROFILES_PATH', 'server_profiles')
		self.base_path = Options.get('path', '')
		self._cache = None
	
	def list_profiles(self):
		"""Return list of {name, description, default_port} for all discovered profiles."""
		self._discover()
		return [p.get_info() for p in self._profiles.values()]
	
	def get_profile_names(self):
		"""Return list of available profile name strings."""
		self._discover()
		return list(self._profiles.keys())
	
	def get_profile(self, name):
		"""Get a profile class by name (case-insensitive). Returns None if not found."""
		self._discover()
		name_lower = name.lower()
		for key, cls in self._profiles.items():
			if key.lower() == name_lower:
				return cls
		# Fallback: try direct module load
		return self._load_single(name)
	
	@classmethod
	def resolve_profile_spec(cls, spec, Options):
		"""Parse a profile spec string like 'http:0.0.0.0:9877' or just 'ws'.
		
		Returns:
			(profile_name, host, port) — port defaults to profile's default_port,
			host defaults to 127.0.0.1.
			If no profile name is given (bare host:port), returns ("HTTP", host, port).
		"""
		from config import Options as DefaultOptions
		default_host = Options.get('SERVER_HOST', DefaultOptions.get('SERVER_HOST', '127.0.0.1'))
		default_port = Options.get('SERVER_PORT', DefaultOptions.get('SERVER_PORT', 9877))
		
		if not spec:
			return ("HTTP", default_host, default_port)
		
		parts = spec.split(':')
		
		# Try to detect if first part is a profile name or a host
		# Profile names are alpha-ish, hosts can be IPs or hostnames
		first = parts[0]
		
		# If it looks like a host:port (no alpha profile name), treat as default HTTP
		if first.replace('.', '').replace('-', '').isdigit() or first == 'localhost':
			# Bare host:port or just host
			host = first if first else default_host
			port = int(parts[1]) if len(parts) > 1 else default_port
			return ("HTTP", host, port)
		
		# First part is a profile name
		profile_name = first
		host = default_host
		port = Options.get('SERVER_PORT', DefaultOptions.get('SERVER_PORT', 9877))
		
		if len(parts) >= 2 and parts[1]:
			host = parts[1]
		if len(parts) >= 3 and parts[2]:
			port = int(parts[2])
		
		return (profile_name, host, port)
	
	def create_server(self, name, host, port):
		"""Create a server instance from a profile name.
		
		Args:
			name: str — profile name (e.g. "HTTP", "WS")
			host: str — bind address
			port: int — bind port
		
		Returns:
			Server object with serve_forever() and shutdown().
		"""
		cls = self.get_profile(name)
		if not cls:
			raise ValueError("Unknown server profile: '{}'. Available: {}".format(
				name, ', '.join(self.get_profile_names())))
		return cls.create_server(host, port, self.Options)
	
	def _discover(self):
		if self._cache is not None:
			return
		self._profiles = {}
		profiles_dir = os.path.join(self.base_path, self.profiles_path)
		if not os.path.isdir(profiles_dir):
			return
		for f in sorted(os.listdir(profiles_dir)):
			if f.endswith('.py') and f != '__init__.py' and not f.startswith('_'):
				name = f[:-3]
				cls = self._load_single(name)
				if cls:
					self._profiles[name] = cls
	
	def _load_single(self, name):
		try:
			mod = importmodule(name, False, {'path': self.profiles_path})
			if mod:
				cls = getattr(mod, name, None)
				if cls and hasattr(cls, 'create_server') and hasattr(cls, 'name'):
					return cls
		except Exception:
			pass
		return None
