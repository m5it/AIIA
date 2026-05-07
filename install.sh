#!/bin/bash
#
# Script to install(link) / uninstall(remove link) start.sh to /usr/local/bin/OurAI
# start.sh starts run.py as OurAI!
#

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_LINK_NAME="ourai"
OPT=$1

# Check for root privileges
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "ERROR: This operation requires root privileges."
        echo "Please run with: sudo $0 $1"
        exit 1
    fi
}

# LINK / INSTALL
if [[ "$OPT" == "-l" ]]; then
    check_root
    if [[ -f "/usr/local/bin/"$SCRIPT_LINK_NAME ]]; then
        echo "Already installed. Exiting."
        exit 1
    fi
    if [[ ! -f "$SCRIPT_DIR/start.sh" ]]; then
        echo "ERROR: start.sh not found in $SCRIPT_DIR"
        exit 1
    fi
    # Check if directory is a git repository
    if [[ ! -d "$SCRIPT_DIR/.git" ]]; then
        echo "ERROR: Not a git repository. OurAI requires git initialization."
        echo "Please initialize with: cd $SCRIPT_DIR && git init"
        exit 1
    fi
    ln -s "$SCRIPT_DIR/start.sh" "/usr/local/bin/"$SCRIPT_LINK_NAME
    echo "Installed successfully. You can now run '"$SCRIPT_LINK_NAME"' from anywhere."
# UNLINK / UNINSTALL
elif [[ "$OPT" == "-u" ]]; then
    check_root
    if [[ ! -f "/usr/local/bin/"$SCRIPT_LINK_NAME ]]; then
        echo "Not installed. Nothing to uninstall."
        exit 1
    fi
    rm "/usr/local/bin/"$SCRIPT_LINK_NAME
    echo "Uninstalled successfully."
# USAGE / HELP
else
    echo "Usage: "
    echo "  $0 -l  # To install to /usr/local/bin/"$SCRIPT_LINK_NAME
    echo "  $0 -u  # To uninstall"
    echo ""
    echo "Note: Installation requires root privileges (use sudo)"
fi
