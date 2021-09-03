#!/bin/bash

# get directory housing script
CDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# check directory contents
if [[ ! "$CDIR" == *MhcVizPipe ]]
then
	echo "ERROR: It looks like the MhcVizPipe executable has been moved out of its installation directory or the \
installation directory has been renamed. The executable needs to remain inside the installation directory and the \
installation directory must not be renamed (i.e. it should still be called MhcVizPipe).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi

if [[ ! -e "$CDIR"/tools ]]
then
	echo "ERROR: The \"tools\" folder is missing from the MhcVizPipe folder. If you have moved it, please move it back to \
its original location. If it has been deleted or is missing, you will need to reinstall MhcVizPipe (or \
replace the tool folder by extracting it from the MhcVizPipe download).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi

if [[ ! -e "$CDIR"/python ]]
then
	echo "ERROR: The \"python\" folder is missing from the MhcVizPipe folder. If you have moved it, please move it back to \
its original location. If it has been deleted or is missing, you will need to reinstall MhcVizPipe (or replace the python \
folder by extracting it from the MhcVizPipe download).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi

if [[ ! (-e "$CDIR"/tools/gibbscluster && -e "$CDIR"/tools/netMHCIIpan && -e "$CDIR"/tools/netMHCpan4.1) ]]
then
	echo "One or more of the tool scripts are missing from the \"tools\" folder. It should have the following scipt files: \
netMHCpan4.0, netMHCpan4.1, netMHCIIpan, and gibbscluster. Please replace these files either by downloading them from \
https://github.com/CaronLab/MhcVizPipe/tree/master/tool_scripts or extracting them from your original MhcVizPipe download \
(if you still have it).";
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi

# check for the DTU Health Tech tools. if the folders are missing but the archives are there, extract them.
MISSING="NO";

if [[ ! (-e "$CDIR"/tools/gibbscluster-2.0) ]]; then
	if compgen -G "$CDIR"/tools/gibbscluster-2.0f*.tar.gz; then
		echo "Extracting GibbsCluster"
		tar -xzf "$CDIR"/tools/gibbscluster-2.0f*.tar.gz -C "$CDIR"/tools
	else
		MISSING="YES";
	fi
fi

if [[ ! (-e "$CDIR"/tools/netMHCIIpan-4.0) ]]; then
	if compgen -G "$CDIR"/tools/netMHCIIpan-4.0*.tar.gz; then
		echo "Extracting NetMHCIIpan"
		tar -xzf "$CDIR"/tools/netMHCIIpan-4.0*.tar.gz -C "$CDIR"/tools
	else
		MISSING="YES";
	fi
fi

if [[ ! (-e "$CDIR"/tools/netMHCpan-4.1) ]]
then
	if compgen -G "$CDIR"/tools/netMHCpan-4.1b*.tar.gz
	then
		echo "Extracting NetMHCpan"
		tar -xzf "$CDIR"/tools/netMHCpan-4.1b*.tar.gz -C "$CDIR"/tools
	else
		MISSING="YES";
	fi
fi

if [[ $MISSING == "YES" ]]
then
	echo "One or more of the tools are missing from the \"tools\" folder. It should have the following programs: \
netMHCpan-4.1, netMHCIIpan-4.0, and gibbscluster-2.0. Download these tools from DTU Health Tech and place them in \
the \"tools\" folder: $CDIR/tools. You can download the programs from here: \
https://services.healthtech.dtu.dk/software.php. Be sure you are getting these versions: GibbsCluster 2.0, \
NetMHCpan 4.1, NetMHCIIpan 4.0. If you are using a Mac, download the Mac versions. \
If you are using a Linux or Windows computer, download the Linux versions.";
	printf "\n"
	echo "Once you have downloaded the files, extract them if it is easy (i.e. if you are using MacOS or Linux). If \
you are using Windows, in which it is difficult to extract .tar.gz files, MhcVizPipe will attempt to do it for you."
  read -rsp "Press any key to exit..." -n1 key;
  printf "\n";
	exit 1
fi



# make sure MVP will be able to execute the tool scripts and python
chmod +x "$CDIR"/tools/gibbscluster
chmod +x "$CDIR"/tools/netMHCIIpan
chmod +x "$CDIR"/tools/netMHCpan4.1

if [[ $(uname -a) == *Microsoft* || $(uname -a) == *Windows* || $(uname -a) == *microsoft* || $(uname -a) == *windows* ]]
then
  python=$PWD/python/python.exe
  win_python=$(powershell.exe wsl wslpath -m "$python")
  powershell.exe -Command "$win_python -m MhcVizPipe.gui --standalone"
else
  chmod -R +x "$CDIR"/python/bin

  # if we're on a Mac, remove any quarantine attributes
  if [[ $OSTYPE == *darwin* ]]
  then
    echo "Preparing directory"
    xattr -r -s -d com.apple.quarantine "$CDIR"/tools "$CDIR"/python
  fi

  # start the program
  "$CDIR"/python/bin/python3 -m MhcVizPipe.gui --standalone
fi