from configparser import ConfigParser
import os
from pathlib import Path
from sys import executable, argv
import platform
from tempfile import gettempdir

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if '--standalone' in argv:
    default_config_file = str(Path(ROOT_DIR) / 'mhcvizpipe_standalone_defaults.config')
else:
    default_config_file = str(Path(ROOT_DIR) / 'mhcvizpipe_defaults.config')
EXECUTABLE = executable

if platform.system().lower() == "windows":
    TOOLS = str((Path(executable) / '../../tools').resolve())
else:
    TOOLS = str((Path(executable) / '../../../tools').resolve())

if '--standalone' in argv:
    config_file = str((Path(TOOLS) / '../mhcvizpipe.config').resolve())
else:
    config_file = str(Path('~/.mhcvizpipe.config').expanduser())

if not Path(config_file).exists():
    with open(default_config_file, 'r') as f:
        settings = ''.join(f.readlines())
    with open(str(config_file), 'w') as f:
        f.write(settings)


class Parameters:
    def __init__(self):
        c = ConfigParser()
        self.config = c
        self.config_file = config_file

    @property
    def TMP_DIR(self) -> str:
        if platform.system().lower() != "windows":
            self.config.read(config_file)
            return str(Path(self.config['DIRECTORIES']['temp directory']).expanduser())
        else:
            return str(Path(gettempdir()) / 'mhcvizpipe')

    @property
    def NETMHCPAN(self) -> str:
        self.config.read(config_file)
        if self.config['DIRECTORIES']['NetMHCpan path'].lower() == 'auto':
            return str((Path(TOOLS) / 'netMHCpan4.1').resolve())
        else:
            return str(Path(self.config['DIRECTORIES']['NetMHCpan path']).expanduser())

    @property
    def NETMHCIIPAN(self) -> str:
        self.config.read(config_file)
        if self.config['DIRECTORIES']['NetMHCIIpan path'].lower() == 'auto':
            return str((Path(TOOLS) / 'netMHCIIpan').resolve())
        return str(Path(self.config['DIRECTORIES']['NetMHCIIpan path']).expanduser())

    @property
    def GIBBSCLUSTER(self) -> str:
        self.config.read(config_file)
        if self.config['DIRECTORIES']['GibbsCluster path'].lower() == 'auto':
            return str((Path(TOOLS) / 'gibbscluster').resolve())
        return str(Path(self.config['DIRECTORIES']['GibbsCluster path']).expanduser())

    @property
    def HOSTNAME(self) -> str:
        self.config.read(config_file)
        return self.config['SERVER']['HOSTNAME']

    @property
    def PORT(self) -> str:
        self.config.read(config_file)
        return self.config['SERVER']['PORT']

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
