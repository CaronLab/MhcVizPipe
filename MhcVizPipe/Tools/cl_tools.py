import pandas as pd
import os
import numpy as np
from pathlib import Path
from MhcVizPipe.Tools.utils import clean_peptides
from typing import List
from MhcVizPipe.Tools.jobs import Job, _run_multiple_processes
from MhcVizPipe.Tools.netmhcpan_helper import NetMHCpanHelper
import re
import shutil
from MhcVizPipe.Tools.utils import convert_win_2_wsl_path
import platform


class MhcToolHelper:
    def __init__(self,
                 sample_info_datatable: List[dict],
                 sample_peptides: dict,
                 tmp_directory: str,
                 mhc_class: str = 'I',
                 min_length: int = 8,
                 max_length: int = 12):

        if mhc_class == 'I' and min_length < 8:
            raise ValueError('Class I peptides must be 8 mers and longer for NetMHCpan')
        if mhc_class == 'II' and min_length < 9:
            raise ValueError('Class II peptides must be 8 mers and longer for NetMHCIIpan')
        self.mhc_class = mhc_class
        self.min_length = min_length
        self.max_length = max_length

        self.sample_info = sample_info_datatable
        #self.sample_info_datatable = pd.DataFrame(data=self.sample_info,
        #                                          columns=['sample-name', 'sample-description', 'sample-alleles'])
        self.original_peptides = sample_peptides
        self.all_original_peptides = set()
        self.all_original_peptides.update(*[set(p) for p in list(sample_peptides.values())])
        self.sample_peptides = {}
        for sample, peptides in sample_peptides.items():
            self.sample_peptides[sample] = [p for p in peptides if min_length <= len(p) <= max_length]
        self.samples = list(sample_peptides.keys())
        self.sample_alleles = {}

        from MhcVizPipe.parameters import Parameters
        self.Parameters = Parameters()

        if platform.system().lower() != 'windows':
            self.GIBBSCLUSTER = self.Parameters.GIBBSCLUSTER
            self.NETMHCPAN = self.Parameters.NETMHCPAN
            self.NETMHCIIPAN = self.Parameters.NETMHCIIPAN
        else:
            self.GIBBSCLUSTER = 'wsl ' + convert_win_2_wsl_path(self.Parameters.GIBBSCLUSTER)
            self.NETMHCPAN = 'wsl ' + convert_win_2_wsl_path(self.Parameters.NETMHCPAN)
            self.NETMHCIIPAN = 'wsl ' + convert_win_2_wsl_path(self.Parameters.NETMHCIIPAN)

        self.tmp_folder = Path(tmp_directory)
        if not self.tmp_folder.exists():
            self.tmp_folder.mkdir(parents=True)
        self.predictions_made = False
        self.binding_predictions: pd.DataFrame = pd.DataFrame(columns=['Sample', 'Peptide', 'Allele', 'Rank', 'Binder'])
        self.prediction_dict: dict = None
        self.gibbs_directories = []
        self.supervised_gibbs_directories = {}
        self.gibbs_cluster_lengths = {}
        self.gibbs_files = {}
        self.not_enough_peptides = []
        self.n_threads = int(self.Parameters.THREADS)
        if self.n_threads < 1 or self.n_threads > os.cpu_count():
            self.n_threads = os.cpu_count()
        self.jobs = []

        # make directories to store the GibbsCluster analyses
        if Path(self.tmp_folder / 'gibbs').exists() and Path(self.tmp_folder / 'gibbs').is_dir():
            # this shouldn't exist because a new tmp_folder is made each time. But possibly it could occur durring
            # debugging, so if found remove it to avoid having multiple GibbsCluster analyses in any folders.
            shutil.rmtree(f'{Path(self.tmp_folder / "gibbs")}')
        Path(self.tmp_folder / 'gibbs').mkdir()
        for sample in self.sample_info:
            sample_name = sample['sample-name']
            alleles = [x.strip() for x in sample['sample-alleles'].split(',')]
            self.sample_alleles[sample_name] = alleles
            Path(self.tmp_folder / 'gibbs' / sample_name).mkdir()
            Path(self.tmp_folder / 'gibbs' / sample_name / 'unsupervised').mkdir()
            Path(self.tmp_folder / 'gibbs' / sample_name / 'unannotated').mkdir()
            for allele in alleles:
                Path(self.tmp_folder / 'gibbs' / sample_name / allele).mkdir()

    def make_binding_predictions(self):
        """
        Run NetMHCpan or NetMHCIIpan to make binding predictions for all samples. Peptide lists are grouped by allele
        rather than sample to reduce processing time when peptides exist in multiple samples.
        :return:
        """
        # get the list of unique alleles
        alleles = []
        for sample in self.sample_info:
            alleles += [x.strip() for x in sample['sample-alleles'].split(',')]
        alleles = set(alleles)

        # get sets of peptides per allele
        allele_peptides = {}
        for allele in alleles:
            allele_peps = []
            for sample in self.sample_info:
                if allele in sample['sample-alleles']:
                    allele_peps += self.sample_peptides[sample['sample-name']]
            allele_peptides[allele] = list(set(allele_peps))

        # run the prediction tool
        all_predictions = {}
        for allele, peptides in allele_peptides.items():
            netmhcpan = NetMHCpanHelper(peptides=peptides,
                                        alleles=[allele],
                                        mhc_class=self.mhc_class,
                                        n_threads=self.Parameters.THREADS,
                                        tmp_dir=str(self.tmp_folder),
                                        netmhcpan=self.NETMHCPAN,
                                        netmhc2pan=self.NETMHCIIPAN,
                                        min_length=self.min_length,
                                        max_length=self.max_length)

            predictions = netmhcpan.predict_dict()
            all_predictions[allele] = {pep: {} for pep in peptides}
            for pep in peptides:
                all_predictions[allele][pep] = predictions[pep][allele]
        self.prediction_dict = all_predictions

        # add all predictions to the self.binding_predictions DataTable
        for sample in self.sample_info:
            rows = []
            for allele, peptides in allele_peptides.items():
                if allele not in sample['sample-alleles']:
                    continue
                for pep in peptides:
                    if pep not in self.sample_peptides[sample['sample-name']]:
                        continue
                    rows.append([sample['sample-name'],
                                 pep,
                                 allele,
                                 all_predictions[allele][pep]['EL_Rank'],
                                 all_predictions[allele][pep]['Binder']])
            self.binding_predictions = self.binding_predictions.append(
                pd.DataFrame(columns=['Sample', 'Peptide', 'Allele', 'Rank', 'Binder'], data=rows),
                ignore_index=True
            )

    def write_binding_predictions(self):
        samples = self.binding_predictions['Sample'].unique()
        for sample in samples:
            peptides = list(self.binding_predictions.loc[self.binding_predictions['Sample'] == sample, 'Peptide'].unique())
            alleles = list(self.binding_predictions.loc[self.binding_predictions['Sample'] == sample, 'Allele'].unique())
            with open(self.tmp_folder / f'{sample}_netMHC{"II" if self.mhc_class == "II" else ""}pan_predictions.tsv', 'w') as f:
                keys = list(self.prediction_dict[alleles[0]][peptides[0]].keys())
                header = ['Allele', 'Peptide'] + keys
                f.write('\t'.join(header) + '\n')
                for allele in alleles:
                    for peptide in peptides:
                        keys = self.prediction_dict[allele][peptide].keys()
                        to_write = [allele, peptide] + [str(self.prediction_dict[allele][peptide][k]) for k in keys]
                        f.write('\t'.join(to_write) + '\n')

    def make_cluster_with_gibbscluster_jobs(self):
        os.chdir(self.tmp_folder)
        for sample in self.samples:
            fname = Path(self.tmp_folder, f'{sample}_forgibbs.csv')
            peps = np.array(clean_peptides(self.sample_peptides[sample]))
            if len(peps) < 20:
                self.not_enough_peptides.append(sample)
                continue
            lengths = np.vectorize(len)(peps)
            peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]
            peps.tofile(str(fname), '\n', '%s')

            # if we are in windows, convert the filepath to the WSL path
            if platform.system().lower() == 'windows':
                fname = convert_win_2_wsl_path(fname)

            n_groups = 6  # search for up to 6 motifs
            for groups in range(1, n_groups+1):
                if self.mhc_class == 'I':
                    command = f'{self.GIBBSCLUSTER} -f {fname} -P {groups}groups ' \
                              f'-g {groups} -k 1 -T -j 2 -C -D 4 -I 1 -G'.split(' ')
                else:
                    command = f'{self.GIBBSCLUSTER} -f {fname} -P {groups}groups ' \
                              f'-g {groups} -k 1 -T -j 2 -G'.split(' ')

                job = Job(command=command,
                          working_directory=self.tmp_folder/'gibbs'/sample/'unsupervised',
                          id=f'gibbscluster_{groups}groups')
                self.jobs.append(job)

    def make_cluster_with_gibbscluster_by_allele_jobs(self):
        os.chdir(self.tmp_folder)
        for sample in self.samples:
            alleles = self.sample_alleles[sample]
            self.supervised_gibbs_directories[sample] = {}
            sample_peps = self.binding_predictions.loc[self.binding_predictions['Sample'] == sample, :]
            allele_peps = {}
            for allele in alleles:
                allele_peps[allele] = set(list(sample_peps.loc[(sample_peps['Allele'] == allele) &
                                                               ((sample_peps['Binder'] == 'Strong') |
                                                                (sample_peps['Binder'] == 'Weak')), 'Peptide'].unique()))

            allele_peps['unannotated'] = set(list(sample_peps['Peptide']))
            for allele in alleles:
                allele_peps['unannotated'] = allele_peps['unannotated'] - allele_peps[allele]

            for allele, peps in allele_peps.items():
                fname = Path(self.tmp_folder, f"{allele}_{sample}_forgibbs.csv")

                peps = np.array(list(allele_peps[allele]))
                if len(peps) < 20:
                    self.not_enough_peptides.append(f'{allele}_{sample}')
                else:
                    lengths = np.vectorize(len)(peps)
                    peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]

                    peps.tofile(str(fname), '\n', '%s')

                    # if we are in windows, convert the filepath to the WSL path
                    if platform.system().lower() == 'windows':
                        fname = convert_win_2_wsl_path(fname)

                    n_groups = 2 if allele == 'unannotated' else 1
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
                                  working_directory=self.tmp_folder/'gibbs'/sample/allele,
                                  id=f'gibbscluster_{g}groups')
                        self.jobs.append(job)

    def find_best_files(self):
        for sample in self.samples:
            self.gibbs_files[sample] = {}
            for run in ['unannotated', 'unsupervised']:
                sample_dirs = list(Path(self.tmp_folder/'gibbs'/sample/run).glob('*'))
                if len(sample_dirs) == 0: # no gibbscluster runs happened, probably because there weren't enough peptides
                    self.gibbs_files[sample][run] = None
                    continue
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
                    self.gibbs_files[sample][run] = None
                    continue
                self.gibbs_files[sample][run] = {}
                self.gibbs_files[sample][run]['n_groups'] = best_grouping
                self.gibbs_files[sample][run]['directory'] = best_grouping_dir
                self.gibbs_files[sample][run]['n_motifs'] = best_n_motifs
                self.gibbs_files[sample][run]['cores'] = [x for x in
                                                                      list(Path(best_grouping_dir / 'cores').glob('*'))
                                                                      if 'of' in x.name]
                self.gibbs_files[sample][run]['pep_groups_file'] = best_grouping_dir/'res'/f'gibbs.{best_grouping}g.ds.out'
                with open(best_grouping_dir/'res'/f'gibbs.{best_grouping}g.out', 'r') as f:
                    contents = f.read()
                    self.gibbs_files[sample][run]['n_outliers'] = \
                        re.findall('# Trash cluster: removed ([0-9]*) outliers', contents)[0]
        for sample in self.samples:
            for allele in self.sample_alleles[sample]:
                self.gibbs_files[sample][allele] = {}
                ls = list(Path(self.tmp_folder/'gibbs'/sample/allele).glob('*'))
                if len(ls) == 0:
                    self.gibbs_files[sample][allele] = None
                    continue
                self.gibbs_files[sample][allele]['n_groups'] = '1'
                self.gibbs_files[sample][allele]['directory'] = list(Path(self.tmp_folder/'gibbs'/sample/allele).glob('*'))[0]
                self.gibbs_files[sample][allele]['n_motifs'] = 1
                self.gibbs_files[sample][allele]['cores'] = \
                    self.gibbs_files[sample][allele]['directory'] / 'cores' / 'gibbs.1of1.core'
                self.gibbs_files[sample][allele]['pep_groups_file'] = \
                    self.gibbs_files[sample][allele]['directory'] / 'res' / f'gibbs.1g.ds.out'

    def order_gibbs_runs(self):
        self.jobs.sort(key=lambda x: x.id, reverse=True)

    def run_jobs(self):
        self.jobs = _run_multiple_processes(self.jobs, n_processes=int(self.Parameters.THREADS))

    def clear_jobs(self):
        self.jobs = []
