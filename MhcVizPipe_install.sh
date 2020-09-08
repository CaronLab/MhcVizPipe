#!/bin/bash

function contains() {
    local n=$#
    local value=${!n}
    for ((i=1;i < $#;i++)) {
        if [ "${!i}" == "${value}" ]; then
            echo "y"
            return 0
        fi
    }
    echo "n"
    return 1
}

# get tar and tar.gz files in directory
ARCHIVES=(./*.tar*)
if [[ ${#ARCHIVES[@]} -ne 3 ]]; then
  echo "ERROR! There must be exactly three .tar or .tar.gz archives in the current directory. These correspond to NetMHCpan(4.0 or 4.1), NetMHCIIpan4.1, and GibbsCluster2.0"
  exit 1
fi

# check that they are the correct files
netMHCpanLinux=false
netMHCpanDarwin=false
netMHCIIpanLinux=false
netMHCIIpanDarwin=false
gibbsclusterLinux=false
gibbsclusterDarwin=false

if [[ "$OSTYPE" == "darwin"* ]]; then
  if [[ -f  "./netMHCpan-4.0a.Darwin.tar" ]]; then
    netMHCpanDarwin=true
    NETMHCPAN_VERSION="4.0"
  elif [[ -f "./netMHCpan-4.1b.Darwin.tar" ]]; then
    netMHCpanDarwin=true
    NETMHCPAN_VERSION="4.1"
  fi

  if [[ -f "./gibbscluster-2.0f.Darwin.tar" ]]; then
    gibbsclusterDarwin=true
  fi

  if [[ -f "./netMHCIIpan-4.0.Darwin.tar" ]]; then
    netMHCIIpanDarwin=true
  fi
fi

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  if [[ -f "./netMHCpan-4.0a.Linux.tar.gz" ]]; then
    netMHCpanLinux=true
    NETMHCPAN_VERSION="4.0"
  elif [[ -f "./netMHCpan-4.1b.Linux.tar.gz" ]]; then
    netMHCpanLinux=true
    NETMHCPAN_VERSION="4.1"
  fi

  if [[ -f "./gibbscluster-2.0f.Linux.tar.gz" ]]; then
    gibbsclusterLinux=true
  fi

  if [[ -f "./netMHCIIpan-4.0.Linux.tar.gz" ]]; then
    netMHCIIpanLinux=true
  fi
fi

if [[ "$OSTYPE" == "darwin"* ]] && [[ "$netMHCpanDarwin" == false || "$netMHCIIpanDarwin" == false || "$gibbsclusterDarwin" == false ]]; then
  echo " "
  echo "ERROR: You are missing one or more of the correct files. Make sure that the files from DTU Health Tech you have downloaded are in the following list (check version numbers and Linux vs Darwin in the name) and that you have one each of NetMHCpan, NetMHCIIpan and GibbsCluster:"
  echo " netMHCpan4.0a.Darwin.tar OR netMHCpan4.1b.Darwin.tar, gibbscluster-2.0f.Darwin.tar, netMHCIIpan4.0.Darwin.tar"
  echo " "
  echo "For help downloading the correct files, visit https://github.com/CaronLab/MhcVizPipe/wiki/Downloading-third-party-software"
  exit 1
fi

if [[ "$OSTYPE" == "linux-gnu"* ]] && [[ "$netMHCpanLinux" == false || "$netMHCIIpanLinux" == false || "$gibbsclusterLinux" == false ]]; then
  echo " "
  echo "ERROR: You are missing one or more of the correct files. Make sure that the files from DTU Health Tech you have downloaded are in the following list (check version numbers and Linux vs Darwin in the name) and that you have one each of NetMHCpan, NetMHCIIpan and GibbsCluster:"
  echo " netMHCpan4.0a.Linux.tar.gz OR netMHCpan4.1b.Linux.tar.gz, gibbscluster-2.0f.Linux.tar.gz, netMHCIIpan4.0.Linux.tar.gz"
  echo " "
  echo "For help downloading the correct files, visit https://github.com/CaronLab/MhcVizPipe/wiki/Downloading-third-party-software"
  exit 1
fi


# set installation directory
INSTALL_DIR="$HOME/MhcVizPipe"
printf "\nMhcVizPipe Installation Utility\n\n"
printf "This utility will help you install and set up MhcVizPipe on your Mac or Linux computer.\n\n"
printf "\n##### Installation Options #####\n\n"
echo "The default installation directory for MhcVizPipe is:"
echo " $INSTALL_DIR"
printf "\n"
echo "To install into the default directory, enter y. To specify a different location, enter n."
read -rp " [y/n]: " USE_DEFAULT

if [[ "$USE_DEFAULT" == "y"* ]]; then
  echo "Default directory selected."
else
  echo "Enter a new installation directory:"
  read -r INSTALL_DIR
  echo "MhcVizPipe will be installed into $INSTALL_DIR."
fi

printf "\n"

echo "Would you like to add MhcVizPipe to your PATH? This will make it much easier to start the program in the future."
read -rp "[y/n]: " MHCVIZPIPE_TO_PATH
if [[ "$MHCVIZPIPE_TO_PATH" == "y" ]]; then
  MHCVIZPIPE_TO_PATH="true"
else
  MHCVIZPIPE_TO_PATH="false"
fi

printf "\n"

echo "Would you like to add NetMHCpan, NetMHCIIpan and GibbsCluster to your PATH? This will make it easier to use these programs in the future. If you have existing installations of these programs, enter n."
read -rp "[y/n]: " TOOLS_TO_PATH
if [[ "$TOOLS_TO_PATH" == "y" ]]; then
  TOOLS_TO_PATH="true"
else
  TOOLS_TO_PATH="false"
fi

printf "\n"

printf "\n\nMhcVizPipe will be installed with the following options:\n\n"
echo " Installation directory: $INSTALL_DIR"
echo " Add MhcVizPipe to PATH: $MHCVIZPIPE_TO_PATH"
echo " Add NetMHCpan, NetMHCIIpan and GibbsCluster to PATH: $TOOLS_TO_PATH"
echo " NetMHCpan version: $NETMHCPAN_VERSION"
printf "\n"

read -rp "Procced? [y/n]:" PROCEED
if [[ "$PROCEED" == "y" ]]; then
  true
else
  echo "Exiting..."
  exit 1
fi

# replace ~ with $HOME if used
INSTALL_DIR="${INSTALL_DIR/#~/$HOME}"
# replace backslashes with slashes
INSTALL_DIR="${INSTALL_DIR//\\//}"

# set URLs for downloading the compiled Python distribution
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  URL="https://github.com/kevinkovalchik/python-build-standalone/releases/download/20200822-20200823/cpython-3.7.9-x86_64-unknown-linux-gnu-pgo-20200823T0036.tar.gz"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  URL="https://github.com/kevinkovalchik/python-build-standalone/releases/download/20200822-20200823/cpython-3.7.9-x86_64-apple-darwin-pgo-20200823T2228.tar.gz"
else
  echo "ERROR! MhcVizPipe is only compatible with Linux and Mac OS. Sorry!"
  exit 1
fi

# make directories
mkdir ./temp
mkdir "$INSTALL_DIR"
mkdir "$HOME/mhcvizpipe_tools"

# download python
printf "\n##### Downloading Python bundle #####\n\n"
curl -L -o ./temp/python.tar.gz "$URL" || (echo "ERROR: An error occurred while downloading Python! Please try again. If the problem persists, contact the developers." && exit 1)
printf "\n##### Done! #####\n"

# extract python
printf "\n##### Extracting Python bundle #####\n\n"
tar -xf ./temp/python.tar.gz --directory "$INSTALL_DIR" || (echo "ERROR: Python was not extracted successfully... Please try again. If the problem persists, contact the developers." && exit 1)
printf "\n##### Done! #####\n"

# the shebangs in the pyhton/install/bin folder are bad, so we need to replace them
find "$INSTALL_DIR"/python/install/bin/ -type f -exec sed -i "1 s/^#!.*python.*/#!$INSTALL_DIR/python/install/bin\/python3/" {} \;

printf "\n##### Installing MhcVizPipe #####\n\n"
"$INSTALL_DIR"/python/install/bin/python3 -m pip install wheel  || (echo "ERROR: An error occurred while installing Wheel... Please try again. If the problem persists, contact the developers." && exit 1)
"$INSTALL_DIR"/python/install/bin/python3 -m pip install MhcVizPipe  || (echo "ERROR: An error occurred while installing MhcVizPipe through Pip... Please try again. If the problem persists, contact the developers." && exit 1)
printf "\n##### Done! #####\n"

printf "\n##### Installing and configuring third-party tools #####\n\n"
"$INSTALL_DIR"/python/install/bin/python3 -m MhcVizPipe.Tools.install_tools || (echo "ERROR: An error occurred while installing the MhcVizPipe tools... Please try again. If the problem persists, contact the developers." && exit 1)
printf "##### Done! #####\n\n"

printf "#!/bin/bash\n%s/python/install/bin/python3 -m MhcVizPipe.gui" "$INSTALL_DIR"> "$INSTALL_DIR"/MhcVizPipe.sh
chmod +x "$INSTALL_DIR"/MhcVizPipe.sh

if [[ "$MHCVIZPIPE_TO_PATH" == "true" ]]; then
  echo "##### Placing MhcVizPipe in PATH #####"
  echo "Enter your user password to add MhcVizPipe to your PATH (Note that the password will not be visible as you type):"
  sudo cp "$INSTALL_DIR"/MhcVizPipe.sh /usr/local/bin/MhcVizPipe || (echo "ERROR: An error occurred while placing MhcVizPipe in the PATH. To do so manually copy the following file into the /usr/local/bin folder: $INSTALL_DIR/MhcVizPipe.sh")
  sudo chmod +x /usr/local/bin/MhcVizPipe
fi
if [[ "$TOOLS_TO_PATH" == "true" ]]; then
  printf "\n"
  echo "##### Placing NetMHCpan, NetMHCIIpan and GibbsCluster in PATH #####"
  sudo cp "$HOME/mhcvizpipe_tools/netMHCpan-$NETMHCPAN_VERSION/netMHCpan" /usr/local/bin/netMHCpan || (echo "ERROR: An error occurred while placing netMHCpan in the PATH. To do so manually copy the following file into the /usr/local/bin folder: $HOME/mhcvizpipe_tools/netMHCpan-$NETMHCPAN_VERSION/netMHCpan")
  sudo cp "$HOME/mhcvizpipe_tools/netMHCIIpan-4.0/netMHCIIpan" /usr/local/bin/netMHCIIpan || (echo "ERROR: An error occurred while placing netMHCIIpan in the PATH. To do so manually copy the following file into the /usr/local/bin folder: $HOME/mhcvizpipe_tools/netMHCIIpan-4.0/netMHCIIpan")
  sudo cp "$HOME/mhcvizpipe_tools/gibbscluster-2.0/gibbscluster" /usr/local/bin/gibbscluster || (echo "ERROR: An error occurred while placing gibbscluster in the PATH. To do so manually copy the following file into the /usr/local/bin folder: $HOME/mhcvizpipe_tools/gibbscluster-2.0/gibbscluster")
fi

echo "Would you like to delete the temporary files leftover from the installation?"
read -rp "[y/n]: " DELTEMP
if [[ "$DELTEMP" == 'y' ]]; then
  rm -R ./temp
elif [[ "$DELTEMP" == 'Y' ]]; then
  rm -R ./temp
elif [[ "$DELTEMP" == 'yes' ]]; then
rm -R ./temp
fi

printf "\nCongratulations! MhcVizPipe has been successfully installed!\n"
echo "If you had MhcVizPipe placed in your PATH, you may start it from any terminal by entering the command: MhcVizPipe"
echo "Would you like to run MhcVizPipe now?"
read -rp "[y/n]: " RUNMVP
if [[ "$RUNMVP" == 'y' ]]; then
  "$INSTALL_DIR"/python/install/bin/python3 -m MhcVizPipe.gui
elif [[ "$RUNMVP" == 'Y' ]]; then
  "$INSTALL_DIR"/python/install/bin/python3 -m MhcVizPipe.gui
elif [[ "$RUNMVP" == 'yes' ]]; then
  "$INSTALL_DIR"/python/install/bin/python3 -m MhcVizPipe.gui
else
  printf "\n"
  echo "Goodbye!"
  printf "\n"
  exit 0
fi
