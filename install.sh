#!/bin/bash
#
# Script to install(link) / uninstall(remove link) start.sh to /usr/local/bin/OurAI
# start.sh starts run.py as OurAI!
#
# OR
# Another approach will be to add program path to $PATH
#
OPT=$1
# LINK / INSTALL
if [[ "$OPT" == "-l" ]]; then
	if [[ -f "/usr/local/bin/OurAI" ]]; then
		echo "Already installed. Exiting."
		exit 1
	fi
	ln -s $(pwd)/start.sh /usr/local/bin/OurAI
# UNLINK / UNINSTALL
elif [[ "$OPT" == "-u" ]]; then
	rm /usr/local/bin/OurAI
# USAGE / HELP
else
	echo "Usage: "
	echo "  "$0" -l # To install to /usr/local/bin/OurAI"
	echo "  "$0" -u # To uninstall"
fi
