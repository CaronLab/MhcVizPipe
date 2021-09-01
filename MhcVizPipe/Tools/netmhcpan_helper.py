from pathlib import Path
from typing import List, Union
import re
import os
import random
from itertools import islice
from datetime import datetime
import subprocess
from multiprocessing import Pool
from uuid import uuid4
import pandas as pd
import tempfile
import platform
from MhcVizPipe.Tools.utils import convert_win_2_wsl_path

common_aa = "ARNDCQEGHILKMFPSTWYV"
TMP_DIR = str(Path(tempfile.gettempdir(), 'pynetmhcpan').expanduser())


def chunk_list(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


class Job:
    def __init__(self,
                 command: Union[str, List[str]],
                 working_directory: Union[str, Path, None],
                 sample=None):

        self.command = command
        self.working_directory = working_directory
        self.returncode = None
        self.time_start = str(datetime.now()).replace(' ', '')
        self.time_end = ''
        self.stdout: bytes = b''
        self.stderr: bytes = b''
        self.sample = sample

    def run(self):
        if self.working_directory is not None:
            os.chdir(self.working_directory)

        command = self.command.split(' ') if isinstance(self.command, str) else self.command
        p = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.stdout, self.stderr = p.communicate()
        self.time_end = str(datetime.now()).replace(' ', '')
        self.returncode = p.returncode


def run(job: Job):
    job.run()
    return job


def _run_multiple_processes(jobs: List[Job], n_processes: int):
    pool = Pool(n_processes)
    returns = pool.map(run, jobs)
    pool.close()
    return returns


def remove_modifications(peptides: Union[List[str], str]):
    if isinstance(peptides, str):
        return ''.join(re.findall('[a-zA-Z]+', peptides))
    unmodified_peps = []
    for pep in peptides:
        pep = ''.join(re.findall('[a-zA-Z]+', pep))
        unmodified_peps.append(pep)
    return unmodified_peps


def remove_previous_and_next_aa(peptides: Union[List[str], str]):
    return_one = False
    if isinstance(peptides, str):
        peptides = [peptides]
        return_one = True
    for i in range(len(peptides)):
        if peptides[i][1] == '.':
            peptides[i] = peptides[i][2:]
        if peptides[i][-2] == '.':
            peptides[i] = peptides[i][:-2]
    if return_one:
        return peptides[0]
    return peptides


def replace_uncommon_aas(peptide):
    pep = peptide
    for aa in peptide:
        if aa not in common_aa:
            pep = pep.replace(aa, 'X')
    return pep


def create_netmhcpan_peptide_index(peptide_list):
    netmhcpan_peps = {}
    for i in range(len(peptide_list)):
        if len(peptide_list[i]) < 1:
            continue
        netmhc_pep = replace_uncommon_aas(peptide_list[i])
        netmhcpan_peps[peptide_list[i]] = netmhc_pep
    return netmhcpan_peps


class NetMHCpanHelper:
    """
    example usage:
    cl_tools.make_binding_prediction_jobs()
    cl_tools.run_jubs()
    cl_tools.aggregate_netmhcpan_results()
    cl_tools.clear_jobs()
    """
    def __init__(self,
                 peptides: List[str] = None,
                 alleles: List[str] = ('HLA-A03:02', 'HLA-A02:02'),
                 mhc_class: str = 'I',
                 n_threads: int = 0,
                 tmp_dir: str = TMP_DIR,
                 output_dir: str = None,
                 netmhcpan='netMHCpan',
                 netmhc2pan='netMHCIIpan',
                 min_length=8,
                 max_length=12):
        """
        Helper class to run NetMHCpan on multiple CPUs from Python. Can annotated a file with peptides in it.
        """

        self.NETMHCPAN = netmhcpan
        self.NETMHCIIPAN = netmhc2pan

        if isinstance(alleles, str):
            if ',' in alleles:
                alleles = alleles.split(',')
            elif ' ' in alleles:
                alleles = alleles.split(' ')
            else:
                alleles = [alleles]
        self.alleles = alleles
        self.peptides = []

        # keep only peptides with acceptable lengths
        peptides = [x for x in peptides if min_length <= len(x) <= max_length]

        if peptides is not None:
            self.add_peptides(peptides)
            self.netmhcpan_peptides = create_netmhcpan_peptide_index(self.peptides)
        else:
            self.netmhcpan_peptides = dict()
        self.predictions = {x: {} for x in self.peptides}
        self.wd = Path(output_dir) if output_dir else Path(os.getcwd())
        self.temp_dir = Path(tmp_dir) / 'PyNetMHCpan'
        if self.wd and not self.wd.exists():
            self.wd.mkdir(parents=True)
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True)
        self.predictions_made = False
        self.not_enough_peptides = []
        if n_threads < 1 or n_threads > os.cpu_count():
            self.n_threads = os.cpu_count()
        else:
            self.n_threads = n_threads
        self.jobs = []
        # self.add_peptides(peptides)
        self.mhc_class: str = mhc_class

    def add_peptides(self, peptides: List[str]):
        if not self.peptides:
            self.peptides = []
        peptides = remove_previous_and_next_aa(peptides)
        peptides = remove_modifications(peptides)

        self.peptides += peptides
        self.netmhcpan_peptides = create_netmhcpan_peptide_index(self.peptides)
        self.predictions = {pep: {} for pep in self.peptides}

    def _make_binding_prediction_jobs(self):
        if not self.peptides:
            print("ERROR: You need to add some peptides first!")
            return
        self.jobs = []

        # split peptide list into chunks
        if self.netmhcpan_peptides:
            peptides = list(self.netmhcpan_peptides.values())
        else:
            peptides = self.peptides
        peptides = list(set(peptides))  # remove any duplicate sequences
        random.shuffle(peptides)  # we need to shuffle them so we don't end up with files filled with peptide lengths that take a LONG time to compute (this actually is a very significant speed up)

        if len(peptides) > 100:
            chunks = chunk_list(peptides, int(len(peptides)/self.n_threads))
        else:
            chunks = [peptides]
        job_number = 1

        for chunk in chunks:
            if len(chunk) < 1:
                continue
            fname = Path(self.temp_dir, f'peplist_{job_number}.csv')

            # save the new peptide list, this will be given to netMHCpan
            with open(str(fname), 'w') as f:
                f.write('\n'.join(chunk))

            # if we are in windows, convert the filepath to the WSL path
            if platform.system().lower() == 'windows':
                fname = convert_win_2_wsl_path(fname)

            # run netMHCpan
            if self.mhc_class == 'I':
                command = f'{self.NETMHCPAN} -p -f {fname} -a {",".join(self.alleles)} -BA'.split(' ')
            else:
                command = f'{self.NETMHCIIPAN} -inptype 1 -f {fname} -a {",".join(self.alleles)} -BA'.split(' ')

            job = Job(command=command,
                      working_directory=self.temp_dir)
            self.jobs.append(job)
            job_number += 1

    def _run_jobs(self):
        self.jobs = _run_multiple_processes(self.jobs, n_processes=self.n_threads)
        for job in self.jobs:
            if job.returncode != 0:
                raise ChildProcessError(f'{job.stdout.decode()}\n\n{job.stderr.decode()}')
            out = (job.stdout.decode() + job.stderr.decode()).split('\n')
            if 'error' in (' '.join(out[-5:])).lower():
                raise ChildProcessError(f'{job.stdout.decode()}\n\n{job.stderr.decode()}')

    def _clear_jobs(self):
        self.jobs = []

    def _aggregate_netmhcpan_results(self):
        for job in self.jobs:
            if job.returncode != 0 or 'error' in job.stdout.decode().lower() or 'error' in job.stderr.decode().lower():
                print(job.stdout.decode())
                print(job.stderr.decode())
                raise ChildProcessError('ERROR: There was a problem in NetMHCpan. '
                                        'See the above output for possible information.')

            self._parse_netmhc_output(job.stdout.decode())

        #self.predictions.to_csv(str(Path(self.temp_dir) / f'netMHCpan_predictions.csv'))

    def _parse_netmhc_output(self, stdout: str):
        lines = stdout.split('\n')
        if self.mhc_class == 'I':
            allele_idx = 1
            peptide_idx = 2
            el_score_idx = 11
            el_rank_idx = 12
            aff_score_idx = 13
            aff_rank_idx = 14
            aff_nM_idx = 15
            strong_cutoff = 0.5
            weak_cutoff = 2.0
        else:
            allele_idx = 1
            peptide_idx = 2
            el_score_idx = 7
            el_rank_idx = 8
            aff_score_idx = 10
            aff_nM_idx = 11
            aff_rank_idx = 12
            strong_cutoff = 2.0
            weak_cutoff = 10.0
        for line in lines:
            line = line.strip()
            line = line.split()
            if not line or line[0] == '#' or not line[0].isnumeric():
                continue
            allele = line[allele_idx].replace('*', '')
            peptide = line[peptide_idx]
            el_rank = float(line[el_rank_idx])
            el_score = float(line[el_score_idx])
            aff_rank = float(line[aff_rank_idx])
            aff_score = float(line[aff_score_idx])
            aff_nM  = float(line[aff_nM_idx])

            if float(el_rank) <= strong_cutoff:
                binder = 'Strong'
            elif float(el_rank) <= weak_cutoff:
                binder = 'Weak'
            else:
                binder = 'Non-binder'

            self.predictions[peptide][allele] = {'el_rank': el_rank,
                                                 'el_score': el_score,
                                                 'aff_rank': aff_rank,
                                                 'aff_score': aff_score,
                                                 'aff_nM': aff_nM,
                                                 'binder': binder}

    def make_predictions(self):
        self.temp_dir = self.temp_dir / str(uuid4())
        self.temp_dir.mkdir(parents=True)
        self._make_binding_prediction_jobs()
        self._run_jobs()
        self._aggregate_netmhcpan_results()
        self._clear_jobs()

    def predict_df(self):
        self.make_predictions()
        df_columns = ['Peptide', 'Allele', 'EL_score', 'EL_Rank', 'Aff_Score', 'Aff_Rank', 'Aff_nM', 'Binder']
        data = []
        for allele in self.alleles:
            for pep in self.peptides:
                netmhc_pep = self.netmhcpan_peptides[pep]
                data.append([pep,
                             allele,
                             self.predictions[netmhc_pep][allele]['el_score'],
                             self.predictions[netmhc_pep][allele]['el_rank'],
                             self.predictions[netmhc_pep][allele]['aff_score'],
                             self.predictions[netmhc_pep][allele]['aff_rank'],
                             self.predictions[netmhc_pep][allele]['aff_nM'],
                             self.predictions[netmhc_pep][allele]['binder']])
        df = pd.DataFrame(data=data, columns=df_columns)
        if not self.check_prediction_peptides(list(df['Peptide'])):
            raise RuntimeError("Not all peptides were present in one or more of the NetMHCpan predictions. Check "
                               "the terminal window (console, command prompt, PowerShell, etc.) for any error "
                               "messages.")
        return df

    def predict_dict(self):
        self.make_predictions()
        predictions = {}
        for pep in self.peptides:
            predictions[pep] = {}
            for allele in self.alleles:
                predictions[pep][allele] = {}
                netmhc_pep = self.netmhcpan_peptides[pep]
                predictions[pep][allele]['EL_score'] = self.predictions[netmhc_pep][allele]['el_score']
                predictions[pep][allele]['EL_Rank'] = self.predictions[netmhc_pep][allele]['el_rank']
                predictions[pep][allele]['Aff_Score'] = self.predictions[netmhc_pep][allele]['aff_score']
                predictions[pep][allele]['Aff_Rank'] = self.predictions[netmhc_pep][allele]['aff_rank']
                predictions[pep][allele]['Aff_nM'] = self.predictions[netmhc_pep][allele]['aff_nM']
                predictions[pep][allele]['Binder'] = self.predictions[netmhc_pep][allele]['binder']
        if not self.check_prediction_peptides(list(predictions.keys())):
            raise RuntimeError("Not all peptides were present in one or more of the NetMHCpan predictions. Check "
                               "the terminal window (console, command prompt, PowerShell, etc.) for any error "
                               "messages.")
        return predictions

    def check_prediction_peptides(self, prediction_peptides: List[str]) -> bool:
        """
        Check that all peptides in self.peptides is present in the prediction dataframe
        :param prediction_peptides: The peptides present in the NetMHCpan predictions
        :return: bool indicating if all peptides are present in the dataframe
        """
        df_peps = set(list(prediction_peptides))
        initial_peps = set(list(self.peptides))
        for pep in initial_peps:
            if pep not in df_peps:
                return False
        return True
