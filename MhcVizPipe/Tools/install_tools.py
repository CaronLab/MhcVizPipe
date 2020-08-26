import os
from pathlib import Path
import tarfile
from configparser import SafeConfigParser
import urllib.request
from platform import system as sys_platform
from typing import Tuple, List
import base64
from subprocess import Popen
from MhcVizPipe.defaults import ROOT_DIR


config_file = str(Path.home()/'.mhcvizpipe.config')
default_config_file = str(Path(ROOT_DIR) / 'mhcvizpipe_defaults.config')
mhc_tool_dir = str(Path.home()/'mhcvizpipe_tools')

if not Path(config_file).is_file():
    with open(default_config_file, 'r') as f:
        settings = ''.join(f.readlines())
    with open(str(config_file), 'w') as f:
        f.write(settings)


def extract_targz(directory: str, archive_type: str = 'auto'):
    d = Path(directory)
    os.chdir(str(d))

    files = list(d.glob('*.tar.gz')) + list(d.glob('*.tar'))

    for file in files:
        if archive_type == 'auto':
            if str(file).endswith('.gz'):
                tar = tarfile.open(file, 'r:gz')
            else:
                tar = tarfile.open(file, 'r')
        elif archive_type == '.tar.gz':
            tar = tarfile.open(file, 'r:gz')
        else:
            tar = tarfile.open(file, 'r')
        tar.extractall()
        tar.close()


def move_file_to_tool_location(filename: str, contents):
    _, contents = contents.split(',')
    file_content = base64.b64decode(contents)
    if not Path(mhc_tool_dir).exists():
        Path(mhc_tool_dir).mkdir()
    new_file = Path(mhc_tool_dir)/filename
    with open(new_file, 'wb') as f:
        f.write(file_content)


def update_variable_in_file(file: str, pattern: str, new_value: str):
    """
    replace a line in a bash script containing a pattern with a new line.
    :param file:
    :param variable_name:
    :param new_value:
    :return:
    """
    with open(file, 'r') as f:
        lines = f.readlines()

    for i in range(len(lines)):
        line = ' '.join(lines[i].split())
        if pattern in line:
            lines[i] = new_value + '\n'

    with open(file, 'w') as f:
        f.writelines(lines)


def update_config(setting: str, value: str):
    """
    Update a value in the MhcVizPipe config file
    :param setting:
    :param value:
    :return:
    """

    parser = SafeConfigParser()
    parser.read(config_file)
    parser.set('DIRECTORIES', setting, value)
    with open(config_file, 'w') as f:
        parser.write(f)


def copy_extract_data_file(tool: str, destination_dir: str):
    root = Path(ROOT_DIR)
    if tool == 'netMHCIIpan':
        location = str(root/'assets/data/NetMHCIIpan/data.tar.gz')
    elif tool == 'netMHCpan4.1':
        location = str(root/'assets/data/NetMHCpan4.1/data.tar.gz')
    elif tool == 'netMHCpan4.0' and sys_platform() == 'Linux':
        location = str(root/'assets/data/NetMHCpan4.0/data.Linux.tar.gz')
    elif tool == 'netMHCpan4.0' and sys_platform() == 'Darwin':
        location = str(root/'assets/data/NetMHCpan4.0/data.Darwin.tar.gz')
    else:
        raise ValueError('tool must be one of [netMHCIIpan, netMHCpan4.1, netMHCpan4.0]')
    tar = tarfile.open(location, 'r:gz')
    tar.extractall(destination_dir)
    tar.close()


def download_data_file(tool: str, destination_dir: str):
    os.chdir(destination_dir)
    if tool == 'netMHCIIpan':
        url = 'http://www.cbs.dtu.dk/services/NetMHCIIpan/data.tar.gz'
    elif tool == 'netMHCpan4.1':
        url = 'http://www.cbs.dtu.dk/services/NetMHCpan/data.tar.gz'
    elif tool == 'netMHCpan4.0' and sys_platform() == 'Linux':
        url = 'http://www.cbs.dtu.dk/services/NetMHCpan-4.0/data.Linux.tar.gz'
    elif tool == 'netMHCpan4.0' and sys_platform() == 'Darwin':
        url = 'http://www.cbs.dtu.dk/services/NetMHCpan-4.0/data.Darwin.tar.gz'
    else:
        raise ValueError('tool must be one of [netMHCIIpan, netMHCpan4.1, netMHCpan4.0]')
    urllib.request.urlretrieve(url, './data.tar.gz')
    tar = tarfile.open('./data.tar.gz', 'r:gz')
    tar.extractall()
    tar.close()


def update_tool_scripts_and_config():
    dlist = [x for x in Path(mhc_tool_dir).glob('*') if x.is_dir()]
    #four_point_zero = False
    #four_point_one = False
    for directory in dlist:
        directory = str(directory)
        if 'netmhc' in directory.lower():
            tmp_dir = Path(directory)/'tmp'
            if not tmp_dir.exists():
                tmp_dir.mkdir()
            if 'netmhciipan' in directory.lower():
                script = str(Path(directory) / 'netMHCIIpan')
                update_config('NetMHCIIpan path', script)
                download_data_file('netMHCIIpan', directory)
            else:
                script = str(Path(directory) / 'netMHCpan')
                update_config('NetMHCpan path', script)
            if '4.0' in Path(directory).name:
                update_config('NetMHCpan version', '4.0')
                download_data_file('netMHCpan4.0', directory)
            if '4.1' in Path(directory).name:
                update_config('NetMHCpan version', '4.1')
                download_data_file('netMHCpan4.1', directory)
            new_value = f'setenv NMHOME {directory}'
            update_variable_in_file(script, 'setenv NMHOME', new_value)
            update_variable_in_file(script, 'setenv TMPDIR', '\tsetenv TMPDIR $NMHOME/tmp')
        elif 'gibbscluster' in directory.lower():
            script = str(Path(directory) / 'gibbscluster')
            new_value = f'setenv GIBBS {directory}'
            update_variable_in_file(script, 'setenv GIBBS', new_value)
            update_config('GibbsCluster path', script)

        #if four_point_zero and four_point_one:
        #    update_config('NetMHCpan version', '4.0')


def associate_files_for_mac():
    install_brew = Popen(['ruby', '-e',
                          '"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"'])
    _ = install_brew.communicate()
    install_duti = Popen(['brew', 'install', 'duti'])
    _ = install_duti.communicate()
    Popen('duti -s com.apple.Terminal .Darwin_x86_64 all')
    Popen('duti -s com.apple.Terminal .freq_rownorm')


def run_all(files: List[Tuple[str, bytes]]):
    for file in files:
        move_file_to_tool_location(*file)
    extract_targz(mhc_tool_dir)
    update_tool_scripts_and_config()
