import subprocess
import pandas as pd
import os
from numpy import array_split
import numpy as np
from pathlib import Path
from MhcVizPipe.Tools.unmodify_peptides import remove_modifications
from typing import List
from multiprocessing import Pool
from MhcVizPipe.Tools.jobs import Job, _run_multiple_processes
import re


class MhcPeptides:
    def __init__(self,
                 sample_name: str,
                 sample_description: str,
                 peptides: List[str]):
        self.sample_name = sample_name.replace(' ', '_')
        self.sample_description = sample_description
        self.peptides = peptides

class MhcToolHelper:
    """
    example usage:
    cl_tools.make_binding_prediction_jobs()
    cl_tools.run_jubs()
    cl_tools.aggregate_netmhcpan_results()
    cl_tools.clear_jobs()

    cl_tools.cluster_with_gibbscluster()
    cl_tools.cluster_with_gibbscluster_by_allele()
    cl_tools.order_gibbs_runs()
    cl_tools.run_jubs()
    cl_tools.find_gibbs_files()
    cl_tools.find_gibbs_grouping()
    """
    def __init__(self,
                 tmp_directory: str,
                 samples: List[MhcPeptides],
                 mhc_class: str = 'I',
                 alleles: List[str] = ('HLA-A03:02', 'HLA-A02:02'),
                 min_length: int = 8,
                 max_length: int = 12):

        if mhc_class == 'I' and min_length < 8:
            raise ValueError('Class I peptides must be 8 mers and longer for NetMHCpan')
        if mhc_class == 'II' and min_length < 9:
            raise ValueError('Class II peptides must be 8 mers and longer for NetMHCIIpan')

        from MhcVizPipe.defaults import Parameters
        self.Parameters = Parameters()
        self.GIBBSCLUSTER = self.Parameters.GIBBSCLUSTER
        self.NETMHCPAN = self.Parameters.NETMHCPAN
        self.NETMHCIIPAN = self.Parameters.NETMHCIIPAN
        self.NETMHCPAN_VERSION = self.Parameters.NETMHCPAN_VERSION

        if isinstance(alleles, str):
            if ',' in alleles:
                alleles = alleles.split(',')
            elif ' ' in alleles:
                alleles = alleles.split(' ')
            else:
                alleles = [alleles]
        self.samples: List[MhcPeptides] = samples
        self.descriptions = {sample.sample_name: sample.sample_description for sample in samples}
        self.alleles = alleles
        self.mhc_class = mhc_class
        self.min_length = min_length
        self.max_length = max_length
        self.predictions = pd.DataFrame(
            columns=['Sample', 'Peptide', 'Allele', 'Rank', 'Binder']
        )
        self.tmp_folder = Path(tmp_directory)
        if not self.tmp_folder.exists():
            self.tmp_folder.mkdir(parents=True)
        self.predictions_made = False
        self.gibbs_directories = []
        self.supervised_gibbs_directories = {}
        self.gibbs_cluster_lengths = {}
        self.gibbs_files = {}
        self.not_enough_peptides = []
        self.n_threads = int(self.Parameters.THREADS)
        if self.n_threads < 1 or self.n_threads > os.cpu_count():
            self.n_threads = os.cpu_count()
        self.jobs = []

        for sample in self.samples:
            with open(str(self.tmp_folder / f'{sample.sample_name}.peptides'), 'w') as f:
                for pep in sample.peptides:
                    f.write(pep + '\n')

        if Path(self.tmp_folder / 'gibbs').exists() and Path(self.tmp_folder / 'gibbs').is_dir():
            os.system(f'rm -R {Path(self.tmp_folder / "gibbs")}')
        Path(self.tmp_folder / 'gibbs').mkdir()
        for sample in self.samples:
            Path(self.tmp_folder / 'gibbs' / sample.sample_name).mkdir()
            Path(self.tmp_folder / 'gibbs' / sample.sample_name / 'unsupervised').mkdir()
            Path(self.tmp_folder / 'gibbs' / sample.sample_name / 'unannotated').mkdir()
            for allele in self.alleles:
                Path(self.tmp_folder / 'gibbs' / sample.sample_name / allele).mkdir()

    def make_binding_prediction_jobs(self):
        # split peptide list into chunks
        for sample in self.samples:
            peptides = np.array(remove_modifications(sample.peptides))
            lengths = np.vectorize(len)(peptides)
            peptides = peptides[(lengths >= self.min_length) & (lengths <= self.max_length)]
            np.random.shuffle(peptides)  # we need to shuffle them so we don't end up with files filled with peptide lengths that take a LONG time to compute (this actually is a very significant speed up)

            if len(peptides) > 100:
                chunks = array_split(peptides, self.n_threads)
            else:
                chunks = [peptides]
            job_number = 1
            results = []

            for chunk in chunks:
                if len(chunk) < 1:
                    continue
                fname = Path(self.tmp_folder, f'{sample.sample_name}_{job_number}.csv')
                # save the new peptide list, this will be given to netMHCpan
                chunk.tofile(str(fname), '\n', '%s')
                # run netMHCpan
                if self.mhc_class == 'I':
                    command = f'{self.NETMHCPAN} -p -f {fname} -a {",".join(self.alleles)}'.split(' ')
                else:
                    command = f'{self.NETMHCIIPAN} -inptype 1 -f {fname} -a {",".join(self.alleles)}'.split(' ')
                job = Job(command=command,
                          working_directory=self.tmp_folder,
                          id=f'netmhc_{job_number}',
                          sample=sample.sample_name)
                self.jobs.append(job)
                job_number += 1

    def make_cluster_with_gibbscluster_jobs(self):
        os.chdir(self.tmp_folder)
        for sample in self.samples:
            fname = Path(self.tmp_folder, f'{sample.sample_name}_forgibbs.csv')
            peps = np.array(remove_modifications(sample.peptides))
            lengths = np.vectorize(len)(peps)
            peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]
            peps.tofile(str(fname), '\n', '%s')
            n_groups = len(self.alleles)
            n_groups = n_groups if n_groups >= 5 else 5
            for groups in range(1, n_groups+1):
                if self.mhc_class == 'I':
                    command = f'{self.GIBBSCLUSTER} -f {fname} -P {groups}groups ' \
                              f'-g {groups} -k 1 -T -j 2 -C -D 4 -I 1 -G'.split(' ')
                else:
                    command = f'{self.GIBBSCLUSTER} -f {fname} -P {groups}groups ' \
                              f'-g {groups} -k 1 -T -j 2 -G'.split(' ')

                job = Job(command=command,
                          working_directory=self.tmp_folder/'gibbs'/sample.sample_name/'unsupervised',
                          id=f'gibbscluster_{groups}groups')
                self.jobs.append(job)

    def make_cluster_with_gibbscluster_by_allele_jobs(self):
        os.chdir(self.tmp_folder)
        for sample in self.samples:
            self.supervised_gibbs_directories[sample.sample_name] = {}
            sample_peps = self.predictions.loc[self.predictions['Sample'] == sample.sample_name, :]
            allele_peps = {}
            for allele in self.alleles:
                allele_peps[allele] = set(list(sample_peps.loc[(sample_peps['Allele'] == allele) &
                                                               ((sample_peps['Binder'] == 'Strong') |
                                                                (sample_peps['Binder'] == 'Weak')), 'Peptide'].unique()))

            allele_peps['unannotated'] = set(list(sample_peps['Peptide']))
            for allele in self.alleles:
                allele_peps['unannotated'] = allele_peps['unannotated'] - allele_peps[allele]

            for allele, peps in allele_peps.items():
                fname = Path(self.tmp_folder, f"{allele}_{sample.sample_name}_forgibbs.csv")
                peps = np.array(list(allele_peps[allele]))
                if len(peps) < 20:
                    self.not_enough_peptides.append(f'{allele}_{sample.sample_name}')
                else:
                    lengths = np.vectorize(len)(peps)
                    peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]

                    peps.tofile(str(fname), '\n', '%s')
                    n_groups = 5 if allele == 'unannotated' else 1
                    for g in range(1, n_groups+1):
                        if self.mhc_class == 'I':
                            if 'kb' in allele.lower():
                                length = 8
                            else:
                                length = 9
                            command = f'{self.GIBBSCLUSTER} -f {fname} -P {g}groups ' \
                                      f'-l {str(length)} -g {g} -k 1 -T -j 2 -C -D 4 -I 1 -G'.split(' ')
                        else:
                            command = f'{self.GIBBSCLUSTER} -f {fname} -P {g}groups ' \
                                      f'-g {g} -k 1 -T -j 2 -G'.split(' ')

                        job = Job(command=command,
                                  working_directory=self.tmp_folder/'gibbs'/sample.sample_name/allele,
                                  id=f'gibbscluster_{g}groups')
                        self.jobs.append(job)

    def find_best_files(self):
        for sample in self.samples:
            self.gibbs_files[sample.sample_name] = {}
            for run in ['unannotated', 'unsupervised']:
                sample_dirs = list(Path(self.tmp_folder/'gibbs'/sample.sample_name/run).glob('*'))
                high_score = 0
                best_grouping = ''
                best_n_motifs = 0
                best_grouping_dir = ''
                for grouping in sample_dirs:
                    with open(grouping/'images'/'gibbs.KLDvsClusters.tab', 'r') as f:
                        klds = np.array(f.readlines()[1].strip().split()[1:], dtype=float)
                        score = np.sum(klds)
                        n_motifs = np.sum(klds != 0)
                    if score > high_score:
                        best_grouping = grouping.stem[0]
                        best_grouping_dir = Path(grouping)
                        high_score = score
                        best_n_motifs = n_motifs
                if best_grouping == '':
                    self.gibbs_files[sample.sample_name][run] = None
                    continue
                self.gibbs_files[sample.sample_name][run] = {}
                self.gibbs_files[sample.sample_name][run]['n_groups'] = best_grouping
                self.gibbs_files[sample.sample_name][run]['directory'] = best_grouping_dir
                self.gibbs_files[sample.sample_name][run]['n_motifs'] = best_n_motifs
                self.gibbs_files[sample.sample_name][run]['cores'] = [x for x in
                                                                      list(Path(best_grouping_dir / 'cores').glob('*'))
                                                                      if 'of' in x.name]
                self.gibbs_files[sample.sample_name][run]['pep_groups_file'] = best_grouping_dir/'res'/f'gibbs.{best_grouping}g.ds.out'
                with open(best_grouping_dir/'res'/f'gibbs.{best_grouping}g.out', 'r') as f:
                    contents = f.read()
                    self.gibbs_files[sample.sample_name][run]['n_outliers'] = \
                        re.findall('# Trash cluster: removed ([0-9]*) outliers', contents)[0]
        for sample in self.samples:
            for allele in self.alleles:
                self.gibbs_files[sample.sample_name][allele] = {}
                ls = list(Path(self.tmp_folder/'gibbs'/sample.sample_name/allele).glob('*'))
                if len(ls) == 0:
                    self.gibbs_files[sample.sample_name][allele] = None
                    continue
                self.gibbs_files[sample.sample_name][allele]['n_groups'] = '1'
                self.gibbs_files[sample.sample_name][allele]['directory'] = list(Path(self.tmp_folder/'gibbs'/sample.sample_name/allele).glob('*'))[0]
                self.gibbs_files[sample.sample_name][allele]['n_motifs'] = 1
                self.gibbs_files[sample.sample_name][allele]['cores'] = \
                    self.gibbs_files[sample.sample_name][allele]['directory'] / 'cores' / 'gibbs.1of1.core'
                self.gibbs_files[sample.sample_name][allele]['pep_groups_file'] = \
                    self.gibbs_files[sample.sample_name][allele]['directory'] / 'res' / f'gibbs.1g.ds.out'

    def order_gibbs_runs(self):
        self.jobs.sort(key=lambda x: x.id, reverse=True)

    def run_jubs(self):
        self.jobs = _run_multiple_processes(self.jobs, n_processes=int(self.Parameters.THREADS))

    def clear_jobs(self):
        self.jobs = []

    def aggregate_netmhcpan_results(self):
        for job in self.jobs:
            if 'netmhc' in job.id:
                self.parse_netmhc_output(job.stdout.decode(), sample=job.sample)

        for sample in list(self.predictions['Sample'].unique()):
            p = self.predictions.loc[self.predictions['Sample'] == sample, :]
            p.to_csv(str(Path(self.tmp_folder)/f'{sample}_netMHC'
                                               f'{"II" if self.mhc_class == "II" else ""}'
                                               f'pan_predictions.csv'))

    def parse_netmhc_output(self, stdout: str, sample: str):
        rows = []
        lines = stdout.split('\n')
        if self.mhc_class == 'I':  # works for 4.0 and 4.1, will need to keep an eye on future releases
            allele_idx = 1
            peptide_idx = 2
            rank_idx = 12
        else:  # works for NetMHCIIpan4.0
            allele_idx = 1
            peptide_idx = 2
            rank_idx = 8
        for line in lines:
            line = line.strip()
            line = line.split()
            if not line or line[0] == '#' or not line[0].isnumeric():
                continue
            allele = line[allele_idx].replace('*', '')
            peptide = line[peptide_idx]
            rank = line[rank_idx]
            if self.mhc_class == 'I':
                if float(rank) <= 0.5:
                    binder = 'Strong'
                elif float(rank) <= 2.0:
                    binder = 'Weak'
                else:
                    binder = 'Non-binder'
            else:
                if float(rank) <= 2:
                    binder = 'Strong'
                elif float(rank) <= 10:
                    binder = 'Weak'
                else:
                    binder = 'Non-binder'
            rows.append((sample, peptide, allele, rank, binder))
        self.predictions = self.predictions.append(
            pd.DataFrame(columns=['Sample', 'Peptide', 'Allele', 'Rank', 'Binder'], data=rows),
            ignore_index=True
        )
        if len(rows) == 0:
            print(stdout)
