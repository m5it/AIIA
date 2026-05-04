#!/usr/bin/env python3
import sys
import os

# Set Ollama host
os.environ['OLLAMA_HOST'] = '192.168.0.69:11434'

# Add current directory to path
sys.path.insert(0, '.')

from src.functions import *
from ollama import chat

# Initialize Handle
Options = {
	"DEBUG": False,
	"QUIET": True,
	"VERSION": 0.1,
	"VERSION_NAME": "AiiA",
	"SPEAK": False,
	"AI_MODEL": "gemma3:latest",
	"AI_FILE_SESSID": "sessid_test.aiia",
	"AI_USER_HISTORY": "huser_test.aiia",
	"AI_FILE_HISTORY": "history_test.aiia",
	"AI_FILE_LOAD_HISTORY": False,
	"AI_SESS_ID": 9999,
	"AI_ROW_ID": 0,
	"AI_MAX_CONTENT_LEN": 20000,
	"AI_LIVE": True,
	"AI_TEMPERATURE": 0.7,
	"path": "{}/".format(os.path.dirname(os.path.abspath(__file__))),
	"tools_path": "tools",
	"actions_path": "actions",
	"history_path": "history",
}

# Import and initialize Handle
from src.Handle import Handle

print("=" * 60)
print("FULL FLOW TEST: Create hello world program and execute it")
print("=" * 60)

hHA = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
hHA.Init()

# Override Prepare to skip interactive input
print("\n--- Step 1: Setting up system ---")
# Directly set system message with tool instructions
system_content = """
You can invoke tools by writing: !TOOL ToolName key=value

Available tools (use exact names):
- WriteFile: Write file to workout/ folder. Params: fileName, contentOfFile
- ExecuteScript: Run a script file (.py, .sh, .js, etc). Params: fileName, [args]

Examples:
!TOOL WriteFile fileName=hello.py contentOfFile="print('Hello World')"
!TOOL ExecuteScript fileName=hello.py
"""
hHA.Response('system',{'content':system_content,})
hHA.msgs.append(hHA.Response('system',{'content':system_content, 'return_object':True}))

# Auto-load all tools
print("Loading all tools...")
hHA.hTC.Choose(auto_load_all=True)
print(f"Loaded {len(hHA.hTC.handles)} tools: {list(hHA.hTC.handles.keys())}")

# Step 2: Send user request
print("\n--- Step 2: Asking model to create and execute hello world ---")
user_msg = "Create a Python hello world program called hello.py and execute it using tools. Use WriteFile to create the file, then ExecuteScript to run it."
hHA.Response('user',{'content':user_msg})
hHA.msgs.append(hHA.Response('user',{'content':user_msg, 'return_object':True}))

# Step 3: Get AI response
print("\n--- Step 3: Getting AI response ---")
res = chat(
	hHA.Options['AI_MODEL'],
	messages=hHA.msgs,
	stream=True,
	options={'temperature':hHA.Options['AI_TEMPERATURE']}
)

# Parse response (this will detect !TOOL and execute tools)
print("\n--- Step 4: Parsing response and executing tools ---")
result = hHA.Parse(res, {'return_object': True})

print("\n" + "=" * 60)
print("FINAL RESULT:")
print("=" * 60)
print(result)

# Cleanup
for f in ['sessid_test.aiia', 'huser_test.aiia', 'history_test.aiia']:
	if os.path.exists(f):
		os.remove(f)
