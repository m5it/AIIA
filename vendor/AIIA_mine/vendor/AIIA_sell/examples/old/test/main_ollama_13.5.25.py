#from ollama import chat
#import ollama
from ollama import ChatResponse, chat
from datetime import date
import select
import json, sys, time, os
import signal
#import importlib
from src.functions import *
from src.ToolChooser import ToolChooser
from src.HistoryManager import HistoryManager
#import src.ToolChooser as ToolChooser
#from tools.list import List
#res = ollama.generate(model='llama3.2', prompt='Show me example for hello world app in python.')
#print("ollama response: {}".format( res ))

#--
#
msgs                 = [] # so we save history.
#
AI_MODEL             = 'llama3.2'
AI_SESS_ID           = 0
AI_FILE_LOAD_HISTORY = False
AI_FILE_HISTORY      = 'history.aiia'
AI_FILE_SESSID       = 'sessid.aiia'
AI_MAX_CONTENT_LEN   = 20000
#
Options         = {
	"AI_RUNNING"     :False,
	"AI_LIVE"        :True,
	"modules_path"   :"tools",
	"system_message" :"", # current system message
	"handle_tools"   :{},
	"current_tools"  :[],
}
#
hTC = None # handle to class ToolChooser()
hHM = None # handle to class HistoryManager()
hHA = None # handle to class Handle()
#handleTools = {} # all tools
#currentTools   = [] # tools passed to AI
#--
#
def signal_handler(sig, frame):
	#global AI_SESS_ID, AI_FILE_SESSID
	#print("OurAIIA is quiting with sessionId: {}".format( AI_SESS_ID ))
	#fwrite(AI_FILE_SESSID,AI_SESS_ID,True)
	print("Ctrl-D to Quit!")
	print("You: ", end='', flush=True)
signal.signal(signal.SIGINT, signal_handler)
#--
# tokenize system message so it can be used with file name
def gen_history_filename():
	global Options, AI_FILE_HISTORY, AI_SESS_ID
	#if Options["system_message"]!="":
	#	AI_FILE_HISTORY = "{}_{}.dbk".format(AI_SESS_ID, urlencode(Options["system_message"]))
	#else:
	AI_FILE_HISTORY = "{}.dbk".format(AI_SESS_ID, AI_FILE_HISTORY)
#
def response_object(role='user',opts=[]):
	global AI_SESS_ID, AI_FILE_HISTORY
	#
	opt_content  = opts['content']
	opt_name     = opts['name'] if 'name' in opts else None
	opt_rowId    = opts['row'] if 'row' in opts else None
	#
	if rmatch(opt_content,"^\{.*"):
		print("response_object() PARSING json!")
		try:
			opt_content  = content.replace("\\\\\\","\\")
			content = json.loads( opt_content )
			if 'text' in content:
				opt_content = content['text']
		except Exception as E:
			print("response_object() PARSING ERROR: {} on content: {}".format(E,opt_content))
	
	#
	if role!='user':
		print("{} => {}".format( role, opt_content ))
	
	# generate response object
	obj = {
		'role'     :role,
		#'content'  :opts['content'],
		# lets change content string for object! AIIA get more infos! ole!
		'content':json.dumps({
			'text'     :opt_content,
			'sessionId':AI_SESS_ID,
			'timestamp':time.time(),
			'date'     :"{}".format(date.today()),
		})
	}
	
	#
	if opt_name != None:
		obj["name"] = opt_name
	#
	if opt_rowId != None:
		obj['rowId'] = opt_rowId
	
	# write history here
	fwrite("history/{}".format(AI_FILE_HISTORY),"{}\n".format(json.dumps(obj)),False)
	return obj

#
def run():
	global AI_SESS_ID, AI_FILE_SESSID, AI_FILE_HISTORY, AI_MODEL, hTC, msgs, AI_FILE_LOAD_HISTORY, AI_MAX_CONTENT_LEN, Options
	
	print("DEBUG run() START")
	
	if Options['AI_RUNNING']==False:
		# load session id
		tmp = fread( AI_FILE_SESSID )
		if tmp!=False:
			AI_SESS_ID = int(tmp)
		AI_SESS_ID = AI_SESS_ID+1
		print("DEBUG AI_SESS_ID: {}".format( AI_SESS_ID ))
		fwrite(AI_FILE_SESSID,AI_SESS_ID,True)
		
		# generate history file name depend on session and system message
		if AI_FILE_LOAD_HISTORY==False:
			gen_history_filename()
			print("DEBUG generating new history name: {}".format(AI_FILE_HISTORY))
		else:
			print("DEBUG using old history name: {}".format(AI_FILE_HISTORY))
		#
		if Options["system_message"] != "":
			print("Appending system message...: {}".format( Options["system_message"] ))
			#
			#gen_history_filename()
			#
			msgs.append( response_object('system',{'content':Options["system_message"]}) )
			Options["system_message"]=""
		else:
			print("DEBUG! Skipping system_message???")
		
		# load history
		if len(msgs)<=0 and os.path.exists( "history/{}".format( AI_FILE_HISTORY ) ):
			print("DEBUG loading history!")
			with open ( "history/{}".format(AI_FILE_HISTORY) ) as tmp:
				for line in tmp:
					print("DEBUG Loading history: {}".format(line))
					jsonobj = json.loads(line)
					msgs.append( jsonobj )
	#
	Options['AI_RUNNING']=True
	#
	while Options['AI_RUNNING']:
		# VARS
		con      = "" # response content
		inp      = "" # user input or data for AI
		# Prepare user content
		print("You: ", end='', flush=True)
		inp = user_input({'quit_with_ctrlx':True})
		if rmatch(inp,r"^\!.*"):
			if rmatch(inp,r"^\!NEW.SESSION+$"):
				Options['AI_RUNNING']=False
				break
			elif rmatch(inp,r"^\!BREAK.SESSION+$"):
				break
			elif rmatch(inp,r"^\!QUIT+$"):
				Options['AI_RUNNING']=False
				Options['AI_LIVE']=False
				break
			elif rmatch(inp,r"^\!LOAD.*"):
				print("DEBUG LOAD FILE...")
				a = pmatch(inp,"^\!LOAD\x20([a-zA-Z0-9\/\_\-\.]+)[\x20]?(.*)?")
				try:
					filedata = fread(a[0])
					print("DEBUG filedata({}): {}".format(len(filedata),filedata))
					# gen user content for AI
					inp = "{}\n\nData: \n\n{}".format(a[1],filedata)
				except Exception as E:
					print("ERROR LOAD File {}".format(E))
					continue
			else:
				print("no match, repeat...")
				continue
		#
		if len(inp)>AI_MAX_CONTENT_LEN:
			print("FAILED: content length {} / {}".format( len(inp), AI_MAX_CONTENT_LEN ))
			continue
		
		# Append user content
		if inp != "":
			msgs.append( response_object('user',{'content':inp}) )
		
		# Nothing to send to AIIA, continue to repeat input!
		if len(msgs)<=0:
			print("WARNING: msgs len is 0, repeating user_input!")
			continue
		
		# Prepare tools for AIIA
		if len(hTC.selected)>0:
			for tool in hTC.selected:
				a=tool.split("_")
				h = initmodule(importmodule(tool,True,{'path':'tools'}),a[1])
				Options['handle_tools'][h.info['name']] = {
					'handle':h,
				}
				Options['current_tools'].append( h.info )
		
		#------------------------
		#-- Initialize ollama
		#------------------------
		# Chat with tools
		if len(Options['current_tools'])>0:
			print("DEBUG preparing chat with tools, {}".format(Options['current_tools']))
			res: ChatResponse = chat(
				AI_MODEL,
				messages=msgs,
				tools=Options['current_tools'],
			)
		# Chat without tools, normal chat
		else:
			print("DEBUG preparing chat without tools")
			res: ChatResponse = chat(
				AI_MODEL,
				messages=msgs,
			)
		
		#------------------------
		#-- Handle ollama response
		#------------------------
		# Handle tool response
		if res.message.tool_calls:
			for tool in res.message.tool_calls:
				toolName = "{}".format(tool.function.name)
				toolData = ""
				failed   = False
				tmph     = None
				#
				if toolName in Options['handle_tools']:
					#
					try:
						tmpo = Options['handle_tools'][toolName]
						tmph = tmpo['handle']
						toolData = tmph.run( **tool.function.arguments )
					except Exception as E:
						toolData = {'ERROR':'Executing {} - {}'.format(toolName,E)}
						failed   = True
					
					print("DEBUG tool data type: {}, len: {}, data: {}".format( type(toolData), len(toolData), toolData ))
					
					#
					if failed == False:
						msgs.append( res.message )
					#
					if failed:
						msgs.append( response_object('tool',{'content':json.dumps(toolData),'name':tool.function.name}) )
					elif tmph.info['parameters']['type']=='object':
						msgs.append( response_object('tool',{'content':json.dumps(toolData),'name':tool.function.name}) )
					elif tmph.info['parameters']['type']=='string':
						msgs.append( response_object('tool',{'content':toolData,'name':tool.function.name}) )
					else:
						print("FAILED, unknown return type: {}".format( type(toolData) ))
					
					#
					res = chat( AI_MODEL, messages=msgs )
					print("DEBUG final response: {}".format( res.message.content ))
					msgs.append( response_object('assistant',{'content':res.message.content}) )
				else:
					print("DEBUG tool {} don't exists".format(tool.function.name))
					if res.message.content:
						print("DEBUG in content...: {}".format( res.message.content ))
						msgs.append( response_object('assistant',{'content':res.message.content}) )
					else:
						print("DEBUG content dont exists either... :x")
		# Handle normal chat response
		elif res.message.content:
			#print("DEBUG in content...: {}".format( res.message.content ))
			msgs.append(response_object('assistant',{'content':res.message.content}))
		# Unknown response or none
		else:
			print("DEBUG something went wrong... no content and no func...")
			msgs.append(response_object('assistant',{'content':"Error: no content?"}))

#
def main(argv):
	global Options, msgs, hTC, AI_FILE_HISTORY, AI_FILE_LOAD_HISTORY, currentTools, handleTools
	# Initialize base classes
	hHM = initmodule(importmodule("HistoryManager",True,{'path':'src'}),"HistoryManager")
	hTC = initmodule(importmodule("ToolChooser",True,{'path':'src'}),"ToolChooser")
	hHA = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle")
	#
	hHA.Test()
	#
	while Options['AI_LIVE']:
		#
		Options['handle_tools']  = {}
		Options['current_tools'] = []
		# 1.) Set history from before
		while hHM.choosed==False:
			hHM.data=[]
			hHM.display_available()
			hHM.choose()
			if hHM.history!="":
				AI_FILE_HISTORY      = hHM.history
				AI_FILE_LOAD_HISTORY = True
		
		# 2.) Define system message/job for AIIA
		print("Set system message or leave empty: ")
		Options["system_message"] = user_input({'quit_with_ctrlx':True})
		
		# 3.) Set which tools to use
		hTC.selected  = []
		while hTC.choosed==False:
			hTC.available = []
			hTC.display_available()
			hTC.choose()
		print("Loaded tools: {}".format( hTC.selected ))
		
		# 4.) Set additional actions. Ex.: 
		#  - load somefile.php data into user content to make some changes
		#  - loop all files *.php and load each file data into user content
		#sys.exit(1)
		#--- START
		#try:
		run()
		#except Exception as E:
		#	print("ERROR in run(): {}".format(E))

#
if __name__ == "__main__":
	#try:
	main(sys.argv[1:])
	#except Exception as E:
	#	print("Failed, {}".format(E))

