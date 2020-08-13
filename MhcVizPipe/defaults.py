from configparser import ConfigParser
import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = str(Path(ROOT_DIR)/'mhcvizpipe.config')
default_config_file = str(Path(ROOT_DIR)/'mhcvizpipe_defaults.config')
config = ConfigParser()
config.read(config_file)

# directories
TMP_DIR = config['DIRECTORIES']['temp directory']
NETMHCPAN = config['DIRECTORIES']['NetMHCpan path']
NETMHCPAN_VERSION = config['DIRECTORIES']['NetMHCpan version']
NETMHCIIPAN = config['DIRECTORIES']['NetMHCIIpan path']
GIBBSCLUSTER = config['DIRECTORIES']['GibbsCluster path']

# server
HOSTNAME = config['SERVER']['HOSTNAME']
PORT = config['SERVER']['PORT']
TIMEOUT = config['SERVER']['TIMEOUT']

# analysis options
HOBOHM = config['ANALYSIS']['hobohm clustering']
THRESHOLD = config['ANALYSIS']['clustering threshold']
WEIGHTONPRIOR = config['ANALYSIS']['weight on prior']
