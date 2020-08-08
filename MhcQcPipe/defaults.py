from configparser import ConfigParser
import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
config = ConfigParser()
config.read(Path(ROOT_DIR)/'mhcvizpipe.config')

TMP_DIR = config['DEFAULTS']['temp directory']
NETMHCPAN = config['DEFAULTS']['NetMHCpan path']
NETMHCPAN_VERSION = config['DEFAULTS']['NetMHCpan version']
NETMHCIIPAN = config['DEFAULTS']['NetMHCIIpan path']
GIBBSCLUSTER = config['DEFAULTS']['GibbsCluster path']
