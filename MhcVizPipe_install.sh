#!/bin/bash

# get tar and tar.gz files in directory
ARCHIVES=(./*.tar*)
if [[ ${#ARCHIVES[@]} -ne 3 ]]; then
  echo "ERROR! There must be exactly three .tar or .tar.gz archives in the current directory. These correspond to NetMHCpan(4.0 or 4.1), NetMHCIIpan4.1, and GibbsCluster2.0"
  exit 1
fi

# set installation directory
INSTALL_DIR="$HOME/MhcVizPipe"
printf "MhcVizPipe Installation Utility\n\n"
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

echo "Which version of NetMHCpan are you installing? Please enter 4.0 or 4.1."
read -rp "[4.0/4.1]: " NETMHCPAN_VERSION
while [[ "$NETMHCPAN_VERSION" != "4.0" && "$NETMHCPAN_VERSION" != "4.1" ]]; do
  if [[ "$NETMHCPAN_VERSION" != "4.0" && "$NETMHCPAN_VERSION" != "4.1" ]]; then
    read -rp "You entered $NETMHCPAN_VERSION. Please enter 4.0 or 4.1: " NETMHCPAN_VERSION
  fi
done


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
elif
  [[ "$OSTYPE" == "darwin"* ]]; then
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
curl -L -o ./temp/python.tar.gz "$URL"
printf "\n##### Done! #####\n"

# extract python
printf "\n##### Extracting Python bundle #####\n\n"
tar -xf ./temp/python.tar.gz --directory "$INSTALL_DIR"
printf "\n##### Done! #####\n"

# the shebangs in the pyhton/install/bin folder are bad, so we need to replace them
find "$INSTALL_DIR"/python/install/bin/ -type f -exec sed -i "1 s/^#!.*python.*/#!$INSTALL_DIR/python/install/bin\/python3/" {} \;

printf "\n##### Installing MhcVizPipe #####\n\n"
"$INSTALL_DIR"/python/install/bin/python3 -m pip install wheel
"$INSTALL_DIR"/python/install/bin/python3 -m pip install MhcVizPipe
printf "\n##### Done! #####\n"

printf "\n##### Installing and configuring third-party tools #####\n\n"
"$INSTALL_DIR"/python/install/bin/python3 -m MhcVizPipe.Tools.install_tools
printf "##### Done! #####\n\n"

printf "#!/bin/bash\n%s/python/install/bin/python3 -m MhcVizPipe.gui" "$INSTALL_DIR"> "$INSTALL_DIR"/MhcVizPipe.sh
chmod +x "$INSTALL_DIR"/MhcVizPipe.sh

if [[ "$MHCVIZPIPE_TO_PATH" == "true" ]]; then
  echo "##### Placing MhcVizPipe in PATH #####"
  sudo cp "$INSTALL_DIR"/MhcVizPipe.sh /usr/local/bin/MhcVizPipe
  sudo chmod +x /usr/local/bin/MhcVizPipe
fi
if [[ "$TOOLS_TO_PATH" == "true" ]]; then
  printf "\n"
  echo "##### Placing NetMHCpan, NetMHCIIpan and GibbsCluster in PATH #####"
  sudo cp "$HOME/mhcvizpipe_tools/netMHCpan-$NETMHCPAN_VERSION/netMHCpan" /usr/local/bin/netMHCpan
  sudo cp "$HOME/mhcvizpipe_tools/netMHCIIpan-4.0/netMHCIIpan" /usr/local/bin/netMHCIIpan
  sudo cp "$HOME/mhcvizpipe_tools/gibbscluster-2.0/gibbscluster" /usr/local/bin/gibbscluster
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
