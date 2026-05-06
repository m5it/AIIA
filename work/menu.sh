#!/bin/bash
#
# Simple key:value menu system
# 1.) Add key:value
# 2.) Del key
# 3.) View all
#

SAVE_TO="saveddata.txt"

echo "=== Key-Value Menu ==="
echo "1.) Add key:value"
echo "2.) Delete by key"
echo "3.) View all"
echo "4.) Exit"
echo "====================="

read -p "Enter option: (1-4) " CHOOSE

case $CHOOSE in
    1)
        echo "Adding key:value"
        read -p "Enter key: " KEY
        read -p "Enter value: " VALUE
        echo "${KEY}:${VALUE}" >> "$SAVE_TO"
        echo "✓ Added ${KEY}=${VALUE}"
        ;;
    2)
        echo "Deleting by key"
        read -p "Enter key to delete: " KEY
        if grep -q "^${KEY}:" "$SAVE_TO"; then
            sed -i "/^${KEY}:/d" "$SAVE_TO"
            echo "✓ Deleted ${KEY}"
        else
            echo "✗ Key not found"
        fi
        ;;
    3)
        echo "Previewing..."
        if [[ -f "$SAVE_TO" ]]; then
            cat "$SAVE_TO"
        else
            echo "No data saved yet"
        fi
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Unknown option"
        ;;
esac

# Run again
echo ""
read -p "Press Enter to continue..."
bash "$0"