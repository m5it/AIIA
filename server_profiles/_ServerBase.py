import abc


class ServerProfile(abc.ABC):
	"""Abstract base for all server profiles.
	
	Each profile defines a server type that can be started via -S flag.
	Profiles are auto-discovered from server_profiles/ directory.
	"""
	
	name = ""
	description = ""
	default_port = 9877
	
	@classmethod
	@abc.abstractmethod
	def create_server(cls, host, port, Options):
		"""Create and return a server instance.
		
		Args:
			host: str — bind address
			port: int — bind port
			Options: dict — config options
		
		Returns:
			An object with serve_forever() and shutdown() methods.
		"""
		raise NotImplementedError
	
	@classmethod
	def get_endpoints(cls):
		"""Return list of endpoint descriptions.
		
		Each entry: {"method": "GET", "path": "/health", "description": "..."}
		"""
		return []
	
	@classmethod
	def get_info(cls):
		"""Return full info dict about this profile."""
		return {
			'name': cls.name,
			'description': cls.description,
			'default_port': cls.default_port,
			'endpoints': cls.get_endpoints(),
		}