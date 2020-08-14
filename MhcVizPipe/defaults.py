from configparser import ConfigParser
import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = str(os.path.expanduser('~/.mhcvizpipe.config'))
default_config_file = str(Path(ROOT_DIR)/'mhcvizpipe_defaults.config')

if not Path(config_file).is_file():
    with open(default_config_file, 'r') as f:
        settings = ''.join(f.readlines())
    with open(str(config_file), 'w') as f:
        f.write(settings)

class Parameters():
    def __init__(self):
        c = ConfigParser()
        self.config = c

    @property
    def TMP_DIR(self) -> str:
        self.config.read(config_file)
        return self.config['DIRECTORIES']['temp directory']
    @property
    def NETMHCPAN(self) -> str:
        self.config.read(config_file)
        return self.config['DIRECTORIES']['NetMHCpan path']
    @property
    def NETMHCPAN_VERSION(self) -> str:
        self.config.read(config_file)
        return self.config['DIRECTORIES']['NetMHCpan version']
    @property
    def NETMHCIIPAN(self) -> str:
        self.config.read(config_file)
        return self.config['DIRECTORIES']['NetMHCIIpan path']
    @property
    def GIBBSCLUSTER(self) -> str:
        self.config.read(config_file)
        return self.config['DIRECTORIES']['GibbsCluster path']
    @property
    def HOSTNAME(self) -> str:
        self.config.read(config_file)
        return self.config['SERVER']['HOSTNAME']
    @property
    def PORT(self) -> str:
        self.config.read(config_file)
        return self.config['SERVER']['PORT']
    @property
    def TIMEOUT(self) -> str:
        self.config.read(config_file)
        return self.config['SERVER']['TIMEOUT']
    @property
    def HOBOHM(self) -> str:
        self.config.read(config_file)
        return self.config['ANALYSIS']['hobohm clustering']
    @property
    def THRESHOLD(self) -> str:
        self.config.read(config_file)
        return self.config['ANALYSIS']['clustering threshold']
    @property
    def WEIGHTONPRIOR(self) -> str:
        self.config.read(config_file)
        return self.config['ANALYSIS']['weight on prior']
    '''
    # directories
    TMP_DIR = property(_tmp_dir)
    NETMHCPAN = property(_netmhcpan)
    NETMHCPAN_VERSION = property(_netmhcpan_version)
    NETMHCIIPAN = property(netmhc2pan)
    GIBBSCLUSTER = property(_gibbs_cluster)

    # server
    HOSTNAME = property(_hostname)
    PORT = property(_port)
    TIMEOUT = property(_timeout)

    # analysis options
    HOBOHM = property(_clustering)
    THRESHOLD = property(_threshold)
    WEIGHTONPRIOR = property(_weight)'''
