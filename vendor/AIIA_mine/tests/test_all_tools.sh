#!/bin/bash
# Test all tools comprehensively - now using work/ directory

echo "=== Testing All Tools ==="
echo ""

# Create test directory and files
mkdir -p work/test_tools
echo "Hello World" > work/test_tools/hello.txt
echo -e "Line1\nLine2\nLine3\nLine2\nLine4" > work/test_tools/lines.txt
echo -e "TODO: Fix this\nDONE: That\nTODO: Another" > work/test_tools/todo.txt
cp work/test_tools/hello.txt work/test_tools/hello_copy.txt

echo "1. Testing List tool..."
echo '<List><path>test_tools</path></List>'

echo ""
echo "2. Testing ReadFile tool..."
echo '<ReadFile><fileName>test_tools/hello.txt</fileName></ReadFile>'

echo ""
echo "3. Testing WriteFile tool..."
echo '<WriteFile><fileName>test_tools/write_test.txt</fileName><contentOfFile>This is written by WriteFile</contentOfFile></WriteFile>'

echo ""
echo "4. Testing AppendFile tool..."
echo '<AppendFile><fileName>test_tools/hello.txt</fileName><contentOfFile>Appended line</contentOfFile></AppendFile>'

echo ""
echo "5. Testing CreateFile tool..."
echo '<CreateFile><fileName>test_tools/new_file.txt</fileName><content>New file created</content></CreateFile>'

echo ""
echo "6. Testing Find tool (find directories)..."
echo '<Find><pattern>test_tools</pattern></Find>'

echo ""
echo "7. Testing Find tool (find files)..."
echo '<Find><pattern>*.txt</pattern><path>test_tools</path></Find>'

echo ""
echo "8. Testing Grep tool..."
echo '<Grep><pattern>TODO</pattern><fileName>test_tools/todo.txt</fileName></Grep>'

echo ""
echo "9. Testing Head tool..."
echo '<Head><fileName>test_tools/lines.txt</fileName><lines>3</lines></Head>'

echo ""
echo "10. Testing Tail tool..."
echo '<Tail><fileName>test_tools/lines.txt</fileName><lines>2</lines></Tail>'

echo ""
echo "11. Testing Sort tool..."
echo '<Sort><fileName>test_tools/lines.txt</fileName></Sort>'

echo ""
echo "12. Testing Diff tool..."
echo '<Diff><file1>test_tools/hello.txt</file1><file2>test_tools/hello_copy.txt</file2></Diff>'

echo ""
echo "13. Testing ExecuteScript tool..."
echo '<WriteFile><fileName>test_tools/test.sh</fileName><contentOfFile>#!/bin/bash\necho "Test script executed"</contentOfFile></WriteFile>'
echo '<ExecuteScript><fileName>test_tools/test.sh</fileName></ExecuteScript>'

echo ""
echo "14. Testing listTools tool..."
echo '<listTools/>'

echo ""
echo "=== Test file created ==="
echo "All tools now use work/ directory instead of workin/ and workout/"
echo "Run: python run.py -Y 'execute all tool tests'"
