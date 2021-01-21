from configparser import ConfigParser
import os
from pathlib import Path
from sys import executable, argv

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
default_config_file = str(Path(ROOT_DIR)/'mhcvizpipe_defaults.config')
EXECUTABLE = executable
TOOLS = str((Path(executable) / '../../../tools').resolve())

if '--standalone' in argv:
    config_file = str(Path(TOOLS) / '../mhcvizpipe.config')
else:
    config_file = str(os.path.expanduser('~/.mhcvizpipe.config'))

if not Path(config_file).exists():
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
        if self.config['DIRECTORIES']['NetMHCpan path'].lower() == 'auto':
            if self.config['DIRECTORIES']['NetMHCpan version'] == '4.1':
                return str((Path(TOOLS) / 'netMHCpan4.1').resolve())
            else:
                return str((Path(TOOLS) / 'netMHCpan4.0').resolve())
        return self.config['DIRECTORIES']['NetMHCpan path']
    @property
    def NETMHCPAN_VERSION(self) -> str:
        self.config.read(config_file)
        if '--standalone' in argv:
            tools = [x.name for x in Path(TOOLS).glob('*') if x.is_dir()]
            if 'netMHCpan-4.0' in tools and 'netMHCpan-4.1' in tools:
                pass
            elif 'netMHCpan-4.0' in tools and self.config['DIRECTORIES']['NetMHCpan version'] == '4.1':
                self.config.set('DIRECTORIES', 'NetMHCpan version', '4.0')
                with open(config_file, 'w+') as config:
                    self.config.write(config)
            elif 'netMHCpan-4.1' in tools and self.config['DIRECTORIES']['NetMHCpan version'] == '4.0':
                self.config.set('DIRECTORIES', 'NetMHCpan version', '4.1')
                with open(config_file, 'w+') as config:
                    self.config.write(config)
            else:
                pass
        return self.config['DIRECTORIES']['NetMHCpan version']
    @property
    def NETMHCIIPAN(self) -> str:
        self.config.read(config_file)
        if self.config['DIRECTORIES']['NetMHCIIpan path'].lower() == 'auto':
            return str((Path(TOOLS) / 'tools/netMHCIIpan').resolve())
        return self.config['DIRECTORIES']['NetMHCIIpan path']
    @property
    def GIBBSCLUSTER(self) -> str:
        self.config.read(config_file)
        if self.config['DIRECTORIES']['GibbsCluster path'].lower() == 'auto':
            return str((Path(TOOLS) / 'gibbscluster').resolve())
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

    @property
    def THREADS(self) -> int:
        self.config.read(config_file)
        threads = int(self.config['ANALYSIS']['max threads'])
        if threads < 1 or threads > os.cpu_count():
            threads = os.cpu_count()
        return threads
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
