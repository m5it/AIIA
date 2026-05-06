"""
Commands - User command handling for AIIA
"""
import os
import re
from src.functions import *

class Commands():
	#
	def __init__(self, handle):
		#print("Commands.__init__() START")
		#
		self.handle = handle
		#
		self.cmds    = {
			"NEW_SESSION":{
				"name"       :"New Session",
				"description":"Like restarting program.",
				"regex"      :r"^!NEW.SESSION+$",
				"usage"      :"!NEW SESSION",
				"func"       :self.CMD_NEW_SESSION,
			},
			"BREAK_SESSION":{
				"name"       :"Break Session",
				"description":"Start new history...",
				"regex"      :r"^!BREAK.SESSION+$",
				"usage"      :"!BREAK SESSION",
				"func"       :self.CMD_BREAK_SESSION,
			},
			"STATS":{
				"name"       :"Stats",
				"description":"Display statistics for program",
				"regex"      :r"^!STATS+$",
				"usage"      :"!STATS",
				"func"       :self.CMD_STATS,
			},
			"ACTION_OPTION_SAVE":{
				"name"       :"Save action options",
				"description":"Save specific action options",
				"regex"      :r"^!AOS.[\d+]+$",
				"usage"      :"!AOS [action_option_num]",
				"func"       :self.CMD_ACTION_OPTION_SAVE,
			},
			"ACTION_OPTIONS_LIST":{
				"name"       :"List action options",
				"description":"List saved action options",
				"regex"      :r"^!AOL+$",
				"usage"      :"!AOL",
				"func"       :self.CMD_ACTION_OPTIONS_LIST,
			},
			"ACTION_OPTIONS":{
				"name"       :"Action Options",
				"description":"LIST, SET, GET action options",
				"regex"      :r"^(!AO)|(!AO.[\d+])|(!AO.[\d+].SET.[a-z]\=[\"\/a-zA-Z0-9])|(!AO.[\d+].GET.[a-z])+$",
				"usage"      :"\nLIST Ex.: !AO [action_num]\nGET Ex.: !AO [action_num] GET path\nSET Ex.: AO [action_num] SET path=/Memorize\n",
				"func"       :self.CMD_ACTION_OPTIONS,
			},
			"IMPORT_ACTIONS":{
				"name"       :"Import Actions",
				"description":"Import actions from classes/code",
				"regex"      :r"^!IA+$",
				"usage"      :"!IA",
				"func"       :self.CMD_IMPORT_ACTIONS,
			},
			"PREVIEW_ACTIONS":{
				"name"       :"Preview Imported Actions",
				"description":"Preview imported actions that are ready to get executed.",
				"regex"      :r"^!PA+$",
				"usage"      :"!PA",
				"func"       :self.CMD_PREVIEW_ACTIONS,
			},
			"EXEC_ACTION":{
				"name"       :"Execute Action",
				"description":"Execute specific action...",
				#"regex"      :r"^(!EA.[\d+])|(!EA.[\d+].DATA.[\d+])+$",
				"regex"      :r"^!EA.[\d+]+$",
				"usage"      :"!EA",
				"func"       :self.CMD_EXEC_ACTION,
			},
			"CLEAR_TOOLS":{
				"name"       :"Clear Tools",
				"description":"Clear loaded tools to start fresh chat or load new tools.",
				"regex"      :r"^!CT+$",
				"usage"      :"!CT",
				"func"       :self.CMD_CLEAR_TOOLS,
			},
			"TOOLS":{
				"name"       :"Tools",
				"description":"Choose tools to use with AIIA.",
				"regex"      :r"^!TOOLS+$",
				"usage"      :"!TOOLS",
				"func"       :self.CMD_TOOLS,
			},
			"PREVIEW_HISTORY":{
				"name"       :"Preview History",
				"description":"Preview current chat history",
				"regex"      :r"^!PH+$",
				"usage"      :"!PH",
				"func"       :self.CMD_PREVIEW_HISTORY,
			},
			"PREVIEW_MEMORY":{
				"name"       :"Preview Memory",
				"description":"Preview current chat memorized messages.",
				"regex"      :r"^!PM+$",
				"usage"      :"!PM",
				"func"       :self.CMD_PREVIEW_MEMORY,
			},
			"MEMORY_SPECIFIC":{
				"name"       :"Memory Specific",
				"description":"Memory specific message from history.",
				"regex"      :r"^!MS.[\d+]+$",
				"usage"      :"!MS [history_num]",
				"func"       :self.CMD_MEMORY_SPECIFIC,
			},
			"MEMORY_ALL_HISTORY":{
				"name"       :"Memory all history",
				"description":"Memory all rows from history.",
				"regex"      :r"^!MAH+$",
				"usage"      :"!MAH",
				"func"       :self.CMD_MEMORY_ALL_HISTORY,
			},
			"MEMORY_LAST":{
				"name"       :"Memory Last",
				"description":"Memory last message from assistant.",
				"regex"      :r"^!ML+$",
				"usage"      :"!ML",
				"func"       :self.CMD_MEMORY_LAST,
			},
			"MEMORY_DEL_ROW":{
				"name"       :"Memory Delete Row",
				"description":"Delete specific row from memory in use.",
				"regex"      :r"^!MDR.[\d+]+$",
				"usage"      :"!MDR [memory_num]",
				"func"       :self.CMD_MEMORY_DEL_ROW,
			},
			"MEMORY_DEL_ALL":{
				"name"       :"Memory Delete All",
				"description":"Delete all rows from memory in use.",
				"regex"      :r"^!MDA+$",
				"usage"      :"!MDA",
				"func"       :self.CMD_MEMORY_DEL_ALL,
			},
			"UPDATE_HANDLE":{
				"name"       :"Update Handle",
				"description":"Reinit code of program. Used after program update so there is no need to stop the program.",
				"regex"      :r"^!UPDATE.HANDLE+$",
				"usage"      :"!UPDATE HANDLE",
				"func"       :self.CMD_UPDATE_HANDLE,
			},
			"QUIT":{
				"name"       :"Quit",
				"description":"Stop the program",
				"regex"      :r"^!QUIT+$",
				"usage"      :"!QUIT",
				"func"       :self.CMD_QUIT,
			},
			"LOAD":{
				"name"       :"Load",
				"description":"Load text file as input to send to AIIA.",
				"regex"      :r"^!QUIT+$",
				"usage"      :"!LOAD textfile.txt Text of textfile.txt will be loaded with this text and sent to AIIA. This is example.",
				"func"       :self.CMD_LOAD,
			},
			"HELP":{
				"name"       :"Help",
				"description":"Display of available actions.",
				"regex"      :r"^!HELP+$",
				"usage"      :"!HELP",
				"func"       :self.CMD_HELP,
			},
		}
	#--
	#
	def CMD_HELP(self, inp=""):
		print("\nAvailable user commands (Ex.: !CMD): ")
		for k in self.cmds:
			print("{} - {} Usage: {}".format( self.cmds[k]['name'], self.cmds[k]['description'], self.cmds[k]['usage'] ))
		print("\n")
		return 2
	
	# ... (other command methods will be added here)
