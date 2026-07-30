#!/usr/bin/env python3
"""
Test the full flow: AI responds with WriteFile XML, Parse() executes it
"""
import sys
sys.path.insert(0, '.')

from src.ToolParser import ToolParser
from src.Handle import Handle
from config import Options
from tools.tool_WriteFile import WriteFile

print("=" * 60)
print("Test: Full Flow - WriteFile Execution")
print("=" * 60)

# Step 1: Create a test scenario
print("\nStep 1: Setup Handle")
Options['QUIET'] = True
h = Handle(Options)
h.Prepared = False
h.Prepare()
print(f"After Prepare(), msgs len: {len(h.msgs)}")

# Step 2: Simulate AI response with WriteFile XML
print("\nStep 2: AI responds with WriteFile XML")
xml_response = """<WriteFile><fileName>TestProject/test.sh</fileName><contentOfFile>#!/bin/bash\necho "Hello"</contentOfFile></WriteFile>"""
print(f"AI response: {xml_response[:100]}...")

# Step 3: Call Parse() which should execute the tool
print("\nStep 3: Call Parse() to handle XML")
parse_result = h.Parse(xml_response, {'return_object': True, 'skip_history': False})
print(f"Parse() returned type: {type(parse_result)}")

# Step 4: Check if tool was executed
print("\nStep 4: Check results")
print(f"Messages in history: {len(h.msgs)}")
for i, msg in enumerate(h.msgs):
    role = msg['role']
    content = str(msg['content'])[:80]
    print(f"  [{i}] {role}: {content}...")

# Step 5: Verify file was created
print("\nStep 5: Verify file was created")
import os
test_file = "work/TestProject/test.sh"
if os.path.exists(test_file):
    print(f"{test_file}: EXISTS")
    with open(test_file, 'r') as f:
        content = f.read()
        print(f"  Content: {content[:50]}...")
else:
    print(f"{test_file}: NOT FOUND")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
