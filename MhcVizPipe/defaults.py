from configparser import ConfigParser
import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = str(os.path.expanduser('~/.mhcvizpipe.config'))
default_config_file = str(Path(ROOT_DIR)/'mhcvizpipe_defaults.config')

class Parameters():

    def config(self):
        c = ConfigParser()
        c.read(config_file)
        return c
    @property
    def TMP_DIR(self) -> str:
        return self.config()['DIRECTORIES']['temp directory']
    @property
    def NETMHCPAN(self) -> str:
        return self.config()['DIRECTORIES']['NetMHCpan path']
    @property
    def NETMHCPAN_VERSION(self) -> str:
        return self.config()['DIRECTORIES']['NetMHCpan version']
    @property
    def NETMHCIIPAN(self) -> str:
        return self.config()['DIRECTORIES']['NetMHCIIpan path']
    @property
    def GIBBSCLUSTER(self) -> str:
        return self.config()['DIRECTORIES']['GibbsCluster path']
    @property
    def HOSTNAME(self) -> str:
        return self.config()['SERVER']['HOSTNAME']
    @property
    def PORT(self) -> str:
        return self.config()['SERVER']['PORT']
    @property
    def TIMEOUT(self) -> str:
        return self.config()['SERVER']['TIMEOUT']
    @property
    def HOBOHM(self) -> str:
        return self.config()['ANALYSIS']['hobohm clustering']
    @property
    def THRESHOLD(self) -> str:
        return self.config()['ANALYSIS']['clustering threshold']
    @property
    def WEIGHTONPRIOR(self) -> str:
        return self.config()['ANALYSIS']['weight on prior']
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
