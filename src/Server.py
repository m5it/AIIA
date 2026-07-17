"""Server launcher — delegates to ServerFactory for profile-based server loading.

Usage:
	from src.Server import start_server
	start_server(host='127.0.0.1', port=9877, Options=...)
	start_server(host='127.0.0.1', port=9877, Options=..., profile='HTTP')
"""
from src.ServerFactory import ServerFactory


def start_server(host='127.0.0.1', port=9877, Options=None, profile=None):
	"""Start a server using the specified profile.
	
	Args:
		host: str — bind address
		port: int — bind port
		Options: dict — config options (uses config.Options if None)
		profile: str — profile name to load (default: "HTTP")
	"""
	if Options is None:
		from config import Options
	if profile is None:
		profile = Options.get('SERVER_PROFILE', 'HTTP')
	
	factory = ServerFactory(Options)
	return factory.create_server(profile, host, port)
