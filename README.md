# MhcVizPipe (MVP)
A reporting pipeline for visualization of immunopeptidomics MS data.

Some more information will go here soon!

## Installation and usage

Below you will find a brief overview of the installation steps and usage of the tool. For
more details please [visit the wiki](https://github.com/kevinkovalchik/MhcVizPipe/wiki).

#### Quick installation
Below is a quick overview of the installation steps. For more details, [visit the wiki](https://github.com/kevinkovalchik/MhcVizPipe/wiki).
1. Right-click and choose "save link as" to download 
[this file](https://github.com/kevinkovalchik/MhcVizPipe/raw/master/MhcVizPipe_install.sh) and place
it in the same directory as the 
[NetMHCpan, NetMHCIIpan and GibbsCluster downloads](https://github.com/kevinkovalchik/MhcVizPipe/wiki/Downloading-third-party-software)
(do not extract the downloads).
2. Open a terminal and navigate to this directory
3. Invoke this command (i.e. type it in and hit enter): `chmod +x ./MhcVizPipe_install.sh`
4. Invoke this command: `./MhcVizPipe_install.sh`
5. During installation, choose to add MhcVizPipe to you PATH

#### Usage
From any terminal, enter the following command:
```
MhcVizPipe
```
You should see the following message:

     ========================================
     MhcVizPipe v0.3.1

     Welcome to MhcVizPipe! To open the GUI, open the following link
     in your web browser: http://0.0.0.0:8080
     (To do this, most likely right click the link and choose something
     like "Open URL" or "Open in browser". If that doesn't work,
     copy and paste it into your browser.)

     If this is you very first time running MVP, when you open the 
     link a window should appear which will help you install GibbsCluster,
     NetMHCpan and NetMHCIIpan if you have not already.

     For a brief introduction to using the GUI, click the link to
     "help and resources" near the top of the GUI. For more information
     and the latest updates please visit our GitHub repository:
     https://github.com/kevinkovalchik/MhcVizPipe.

     ========================================
You will notice this link in the message: `http://0.0.0.0:8080`. Right click and select "Open in browser" and
the MhcVizPipe will open up in your web browser.

For detailed usage, see the [wiki usage page.](https://github.com/kevinkovalchik/MhcVizPipe/wiki/Usage)

If you need further help please [open an issue!](https://github.com/kevinkovalchik/MhcVizPipe/issues)