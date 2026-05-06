#!/usr/bin/env python3
"""
Test script to debug WriteFile tool execution issue
"""
import sys
sys.path.insert(0, '.')

from src.ToolParser import ToolParser
from tools.tool_WriteFile import WriteFile

print("=" * 60)
print("Test: WriteFile XML Parsing and Execution")
print("=" * 60)

# Test 1: Parse the exact XML the AI sends
print("\nTest 1: Parse WriteFile XML")
print("-" * 60)

tp = ToolParser()

# This is the exact XML from the chat history
xml_text = """<WriteFile><fileName>TestProject/run.sh</fileName><contentOfFile>#!/bin/bash
# Simple menu
</contentOfFile></WriteFile>"""

print("Input XML:")
print(xml_text)
print()

result = tp.ParseTextToolInvocation(xml_text)
print(f"Number of tool invocations: {len(result)}")
for i, inv in enumerate(result):
    print(f"  [{i}] Tool: {inv['name']}")
    print(f"       Parameters: {inv['parameters']}")

# Test 2: Execute the parsed tool
print("\n" + "=" * 60)
print("Test 2: Execute WriteFile from parsed XML")
print("=" * 60)

if result:
    inv = result[0]
    toolName = inv['name']
    params = inv['parameters']
    
    print(f"Executing tool: {toolName}")
    print(f"Parameters: {params}")
    
    # Execute the tool
    wf = WriteFile()
    exec_result = wf.run(**params)
    print(f"Execution result: {exec_result}")
else:
    print("No tool invocations found!")

# Test 3: Check if file was created
print("\n" + "=" * 60)
print("Test 3: Verify file was created")
print("=" * 60)

import os
file_to_check = "work/TestProject/run.sh"
if os.path.exists(file_to_check):
    print(f"{file_to_check}: EXISTS")
    with open(file_to_check, 'r') as f:
        content = f.read()
        print(f"  Content preview: {content[:50]}...")
else:
    print(f"{file_to_check}: NOT FOUND")

print("\nTest completed!")
