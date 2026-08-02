#--
# class Commands — user-command entry point.
# Per-domain logic lives in mixins; registry built by
# src/commands_registry.build_registry(self). Public API preserved:
# loaded by name via importmodule() from Handle.py.
from src.commands_registry import build_registry
from src.CommandsConfig import CommandsConfig
from src.CommandsSession import CommandsSession
from src.CommandsPersona import CommandsPersona
from src.CommandsTips import CommandsTips
from src.CommandsTimers import CommandsTimers
from src.CommandsSites import CommandsSites
from src.CommandsPlan import CommandsPlan
from src.CommandsWorkers import CommandsWorkers
class Commands(CommandsConfig, CommandsSession, CommandsPersona, CommandsTips,
	CommandsTimers, CommandsSites, CommandsPlan, CommandsWorkers):
	#
	def __init__(self, opts={}):
		#print("Handle.Commands.__init__() START")
		#
		self.handle = opts['handle'] if 'handle' in opts else None # to master class / Handle()
		#
		self.cmds    = build_registry(self)
	#--
	#
	def CMD_HELP(self, inp=""):
		print("\nAvailable user commands (Ex.: !CMD): ")
		#self.handle.hLG.echo("\nAvailable user commands (Ex.: !CMD): \n",{'color':True,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True})
		for k in self.cmds:
			print("{} - {} Usage: {}".format( self.cmds[k]['name'], self.cmds[k]['description'], self.cmds[k]['usage'] ))
			#self.handle.hLG.echo("{} - {} Usage: {}".format( self.cmds[k]['name'], self.cmds[k]['description'], self.cmds[k]['usage'] ),{'color':True,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True})
		print("\n")
		return 2
	#
	#
