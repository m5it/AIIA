#!/bin/bash
#
# Lets create simple menu.
# 1.) Add key:value
# 2.) Del key
# 3.) View all
SAVE_TO="saveddata.txt"
echo "Enter option: (1-3) "
read CHOOSE
if [[ "$CHOOSE" == "1" ]]; then
	echo "Adding key:value"
elif [[ "$CHOOSE" == "2" ]]; then
	echo "Deleting by key"
elif [[ "$CHOOSE" == "3" ]]; then
	echo "Previewing.."
else
	echo "Unknown option"
fi