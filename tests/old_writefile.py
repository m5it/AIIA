#!/usr/bin/env python3
"""
Test script to debug WriteFile tool parsing and execution
"""
import sys
sys.path.insert(0, '.')

from src.ToolParser import ToolParser
from tools.tool_WriteFile import WriteFile
from src.functions import fwrite, initmodule, importmodule

print("=" * 60)
print("Test: WriteFile Tool Execution")
print("=" * 60)

# Test 1: Check if WriteFile tool works directly
print("\nTest 1: Direct WriteFile execution")
wf = WriteFile()
result = wf.run("test_output.txt", "Hello World!\nThis is a test.")
print("Result:", result)
print("File should be at: work/test_output.txt")

# Test 2: Parse XML with WriteFile
print("\n" + "=" * 60)
print("Test 2: Parse WriteFile XML")
print("=" * 60)

tp = ToolParser()

# This is the XML format the AI uses
xml_text = """<WriteFile><fileName>test_output2.txt</fileName><contentOfFile>Hello from XML!</contentOfFile></WriteFile>"""

print("Input XML:")
print(xml_text)
print()

result = tp.ParseTextToolInvocation(xml_text)
print("Number of tool invocations:", len(result))
for inv in result:
    print("  Tool:", inv['name'])
    print("  Parameters:", inv['parameters'])

# Test 3: Execute the parsed tool
print("\n" + "=" * 60)
print("Test 3: Execute WriteFile from parsed XML")
print("=" * 60)

if result:
    inv = result[0]
    toolName = inv['name']
    params = inv['parameters']
    
    print("Executing tool:", toolName)
    print("Parameters:", params)
    
    # Execute the tool
    wf2 = WriteFile()
    exec_result = wf2.run(**params)
    print("Execution result:", exec_result)

# Test 4: Check if file was created
print("\n" + "=" * 60)
print("Test 4: Check if files were created")
print("=" * 60)

import os
files_to_check = ["work/test_output.txt", "work/test_output2.txt"]
for f in files_to_check:
    if os.path.exists(f):
        print(f"{f}: EXISTS")
        with open(f, 'r') as fp:
            content = fp.read()
            print(f"  Content: {content[:50]}...")
    else:
        print(f"{f}: NOT FOUND")

print("\nTest completed!")
