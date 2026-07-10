#!/bin/bash
# Test Terminal tool with various commands

echo "=== Testing Terminal Tool ==="
echo ""

echo "1. Simple ls command:"
echo '<Terminal><arg1>ls</arg1></Terminal>'

echo ""
echo "2. ls with arguments:"
echo '<Terminal><arg1>ls</arg1><arg2>-la</arg2><arg3>work/</arg3></Terminal>'

echo ""
echo "3. pwd command:"
echo '<Terminal><arg1>pwd</arg1></Terminal>'

echo ""
echo "4. echo command:"
echo '<Terminal><arg1>echo</arg1><arg2>Hello from Terminal tool</arg2></Terminal>'

echo ""
echo "5. Not allowed command (should fail):"
echo '<Terminal><arg1>rm</arg1><arg2>-rf</arg2><arg3>/tmp/test</arg3></Terminal>'

echo ""
echo "6. Date command:"
echo '<Terminal><arg1>date</arg1></Terminal>'

echo ""
echo "7. Multiple arguments:"
echo '<Terminal><arg1>find</arg1><arg2>work/</arg2><arg3>-name</arg3><arg4>*.py</arg4></Terminal>'

echo ""
echo "=== Test file created ==="
echo "Run: python run.py -Y 'test terminal tool with ls -la work/'"
