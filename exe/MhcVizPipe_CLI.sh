#!/bin/bash

# This file is used to activate the command line interface of MhcVizPipe in standalone distributions.

# get directory housing script
CDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# check directory contents
if [[ ! "$CDIR" == *MhcVizPipe ]]; then
	echo "ERROR: It looks like the MhcVizPipe executable has been moved out of its installation directory or the \
installation directory has been renamed. The executable needs to remain inside the installation directory and the \
installation directory must not be renamed (i.e. it should still be called MhcVizPipe).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi

if [[ ! -e "$CDIR"/tools ]]; then
	echo "ERROR: The \"tools\" folder is missing from the MhcVizPipe folder. If you have moved it, please move it back to \
its original location. If it has been deleted or is missing, you will need to reinstall MhcVizPipe (or \
replace the tools folder by extracting it from the MhcVizPipe download).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi

if [[ ! -e "$CDIR"/python ]]; then
	echo "ERROR: The \"python\" folder is missing from the MhcVizPipe folder. If you have moved it, please move it back to \
its original location. If it has been deleted or is missing, you will need to reinstall MhcVizPipe (or replace the python \
folder by extracting it from the MhcVizPipe download).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi

if [[ ! (-e "$CDIR"/tools/gibbscluster && -e "$CDIR"/tools/netMHCIIpan && -e "$CDIR"/tools/netMHCpan4.1) ]]; then
	echo "One or more of the tool scripts are missing from the \"tools\" folder. It should have the following script files: \
netMHCpan4.1, netMHCIIpan, and gibbscluster. Please replace these files either by downloading them from \
https://github.com/CaronLab/MhcVizPipe/tree/master/tool_scripts or extracting them from your original MhcVizPipe download \
(if you still have it).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi



# make sure MVP will be able to execute the tool scripts and python
chmod +x "$CDIR"/tools/gibbscluster
chmod +x "$CDIR"/tools/netMHCIIpan
chmod +x "$CDIR"/tools/netMHCpan4.1
chmod -R +x "$CDIR"/python/bin

# if we're on a Mac, remove any quarantine attributes
if [[ $OSTYPE == *darwin* ]]; then
	echo "Preparing directory"
	xattr -r -s -d com.apple.quarantine "$CDIR"/tools "$CDIR"/python
fi

# start the program
"$CDIR"/python/bin/python3 -m MhcVizPipe.gui @$ --standalone