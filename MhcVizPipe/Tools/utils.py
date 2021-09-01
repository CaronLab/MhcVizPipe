import re
from typing import Union
from os import PathLike
import zipfile
from pathlib import Path
from os import walk as os_walk

common_aa = "ARNDCQEGHILKMFPSTWYV"


def remove_previous_and_next_aa(peptide: str):
    """
    If the peptide has previous and next amino acids (e.g. A.AKLNCNAA.K) they get removed (e.g. returns AKLNCNAA)
    :param peptide: A string representing one peptide
    :return:
    """
    if peptide[1] == '.':
        peptide = peptide[2:]
    if peptide[-2] == '.':
        peptide = peptide[:-2]
    return peptide


def clean_peptides(peptide_list, verbose=False):
    unmodified_peps = []
    if verbose:
        print('Removing peptide modifications')
    for pep in peptide_list:
        pep = remove_previous_and_next_aa(pep)
        pep = ''.join(re.findall('[a-zA-Z]+', pep))
        pep = pep.upper()
        incompatible_aa = False
        for aa in pep:
            if aa not in common_aa:
                incompatible_aa = True
                break
        if not incompatible_aa:
            unmodified_peps.append(pep)
    return unmodified_peps


def sanitize_sample_name(sample_name: str):
    for bad_character in [' ', ':', ';', '/', '\\', '$', '@', '*', '!', '^', '(', ')', '{', '}', '[', ']']:
        sample_name = sample_name.replace(bad_character, '_')
    sample_name = sample_name.replace('&', 'AND').replace('%', 'percent')
    return sample_name


def load_peptide_file(filepath: Union[str, PathLike], peptide_column: str = None, delimiter: str = None):
    """
    Load a peptide list from a text file. If the file has multiple columns, you must indicate if it
    is comma- or tab-delimited and the header of the column containing the peptides.
    :param filepath: Path to the file
    :param peptide_column: (optional) The header of the column containing the peptides
    :param delimiter: (optional) The delimiter, if it is a multi-column file.
    :return: List of strings - the peptide sequences.
    """
    if not peptide_column == delimiter and None in [peptide_column, delimiter]:
        raise ValueError('Both peptide_column and delimiter must be defined for multi-column files.')

    peptides = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
        if delimiter:
            if delimiter == 'comma':
                delimiter = ','
            else:
                delimiter = '\t'
            header_index = lines[0].strip().index(peptide_column)
            for line in lines[1:]:
                peptides.append(line.strip().split(delimiter)[header_index])
        else:
            for line in lines:
                peptides.append(line.strip())

    return peptides


def load_template_file(filepath: Union[str, PathLike]):
    """
    Load a template file for use with MhcVizPipe command line interface.
    :param filepath: Path to the file.
    :return: List of dictionaries of form [{'file': filepath, 'alleles': [list of alleles]}, ... ]
    """
    with open(filepath, 'r') as f:
        lines = [l.strip().split() for l in f.readlines()]
    samples = []
    for line in lines:
        if len(line) == 1:
            raise ValueError('Each file in the template must have at least one alleles assigned to it.')
        if line == '':
            continue
        samples.append({'file': line[0], 'alleles': line[1:]})
    return samples


def package_report(analysis_location):
    zip_out = f'{analysis_location}/MVP_report_components.zip'
    with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_STORED) as zipf:
        netmhcpan_files = [str(x) for x in Path(analysis_location).glob('*_predictions.tsv')]
        for f in netmhcpan_files:
            zipf.write(f, arcname=Path(f).name)
        zipf.write(str(Path(analysis_location) / 'sample_metrics.txt'), arcname='sample_metrics.txt')
        for root, dirs, files in os_walk(f'{analysis_location}/gibbs'):
            for file in files:
                p = Path(root, file)
                zipf.write(str(p), p.relative_to(analysis_location))
        zipf.write(f'{analysis_location}/report.html', 'report.html')

        for root, dirs, files in os_walk(f'{analysis_location}/figures'):
            for file in files:
                p = Path(root, file)
                zipf.write(str(p), p.relative_to(analysis_location))

    return zip_out


def check_alleles(allele_list, good_alleles):
    for a in allele_list:
        if a not in good_alleles:
            raise ValueError(f'ERROR: {a} is not a recognized allele by the chosen software.')


def convert_win_2_wsl_path(path: Union[str, Path]):
    """
    Convert a windows path to the respective Windows Subsystem for Linux path.

    :param path: The Windows path.
    :return: The WSL path as a string.
    """
    parts = Path(path).parts
    wsl_path = "/mnt/"
    wsl_path += parts[0][0].lower() + "/"
    if len(parts) > 1:
        wsl_path += '/'.join(parts[1:])
    return wsl_path


