import subprocess
import pandas as pd
import os
from numpy import array_split
import numpy as np
from pathlib import Path
from MhcVizPipe.Tools.unmodify_peptides import remove_modifications
from typing import List
from MhcVizPipe.defaults import GIBBSCLUSTER, NETMHCPAN, NETMHCIIPAN, NETMHCPAN_VERSION

class MhcPeptides:
    def __init__(self,
                 sample_name: str,
                 sample_description: str,
                 peptides: List[str]):
        self.sample_name = sample_name.replace(' ', '_')
        self.sample_description = sample_description
        self.peptides = peptides
'''
tester_a = MhcPeptides(
    sample_name='Test A',
    sample_description='first test sample',
    peptides=['ALITQQDLAPQQRAAP', 'ALPGQLKPFETLLSQN', 'ALQNIIPASTGAAK', 'ALQNIIPASTGAAKA', 'ALQNIIPASTGAAKAVG',
                'AMSYVKDDIFRIYIK', 'AMSYVKDDIFRIYIKE', 'ANVIRYFPTQALN', 'APDQDEIQRLPGLAKQPS', 'APDQDEIQRLPGLAKQPSFR',
                'APEPSTVQILHSP', 'APEPSTVQILHSPA', 'APEPSTVQILHSPAVE', 'APFSPDENSLVLFE', 'APGHRDFIKNMITGTSQ',
                'APGHRDFIKNMITGTSQA', 'APGHRDFIKNMITGTSQAD', 'APGLIIATGSVGKN', 'APGPGRLVAQLDTEGVG']
)
tester_b = MhcPeptides(
    sample_name='Test B',
    sample_description='second test sample',
    peptides=['AGLNVLRIINEPTAAAIA', 'AIFLFVDKTVPQSS', 'AIFLFVDKTVPQSSL', 'AIKELGDHVTNLRKMG', 'AIKELGDHVTNLRKMGAPE',
               'AIVVDPVHGF', 'AIVVDPVHGFM', 'AKRVIISAPSADAP', 'AKRVIISAPSADAPM']
)
test_samples = [tester_a, tester_b]
'''


class MhcToolHelper:
    def __init__(self,
                 tmp_directory: str,
                 samples: List[MhcPeptides],
                 mhc_class: str = 'I',
                 alleles: List[str] = ('HLA-A03:02', 'HLA-A02:02'),
                 min_length: int = 8,
                 max_length: int = 12):

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
        self.tmp_folder.mkdir(parents=True)
        self.predictions_made = False
        self.gibbs_directories = []
        self.supervised_gibbs_directories = {}
        self.gibbs_cluster_lengths = {}

    def make_binding_predictions(self, score: str = 'EL'):
        n = int(os.cpu_count())

        # split peptide list into chunks
        for sample in self.samples:
            peptides = np.array(remove_modifications(sample.peptides))

            lengths = np.vectorize(len)(peptides)
            peptides = peptides[(lengths >= self.min_length) & (lengths <= self.max_length)]

            np.random.shuffle(peptides)  # we need to shuffle them so we don't end up with files filled with peptide lengths that take a LONG time to compute (this actually is a very significant speed up)

            if len(peptides) > 100:
                chunks = array_split(peptides, n)
            else:
                chunks = [peptides]
            jobs = []
            job_number = 1
            results = []

            for chunk in chunks:
                if len(chunk) < 1:
                    continue
                fname = Path(self.tmp_folder, f'{sample.sample_name}_{job_number}.csv')
                fout = Path(self.tmp_folder, f'{sample.sample_name}_netmhcpan_results_{job_number}.tsv')
                results.append(fout)
                # save the new peptide list, this will be given to netMHCpan
                if self.mhc_class == 'I':
                    chunk = chunk[np.vectorize(len)(chunk) >= 8]
                if self.mhc_class == 'II':
                    chunk = chunk[np.vectorize(len)(chunk) >= 9]
                chunk.tofile(str(fname), '\n', '%s')
                job_number += 1
                # run netMHCpan
                if self.mhc_class == 'I':
                    command = f'{NETMHCPAN} -p -f {fname} -a {",".join(self.alleles)} -BA -xls -xlsfile {fout}'.split(' ')
                else:
                    command = f'{NETMHCIIPAN} -inptype 1 -f {fname} -a {",".join(self.alleles)} -BA -xls -xlsfile {fout}'.split(' ')
                jobs.append(subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            # finish jobs and check return values
            for job in jobs:
                stdout, stderr = job.communicate()
                out = stdout.split(b'\n')[-2]
                if b'error' in out:
                    raise subprocess.SubprocessError(f"Error in running: {job.args}\n\n{out}")

            for f in results:
                sample_name = str(Path(f).stem).split('_netmhcpan_results_')[0]
                rows = []
                with open(f, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                alleles = [a.strip() for a in lines[0].split('\t') if a != '']
                headers = lines[1].split('\t')
                if self.mhc_class == 'I':
                    if NETMHCPAN_VERSION == '4.1':
                        rank_header = f'{score}_Rank'
                    else:
                        rank_header = 'Rank'
                else:
                    if score == 'BA':
                        rank_header = 'Rank_BA'
                    else:
                        rank_header = 'Rank'
                rank_indices = [i for i in range(len(headers)) if headers[i] == rank_header]
                for line in lines[2:]:
                    line = line.split('\t')
                    for a in self.alleles:
                        pep = line[1]
                        allele = a
                        rank = line[rank_indices[alleles.index(a)]]
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
                        rows.append((sample_name, pep, allele, rank, binder))

                self.predictions = self.predictions.append(
                    pd.DataFrame(columns=['Sample', 'Peptide', 'Allele', 'Rank', 'Binder'], data=rows),
                    ignore_index=True
                )
            #self.predictions.to_csv(str(Path(self.tmp_folder)/'predictions.csv'))

    def cluster_with_gibbscluster(self):
        n_cpus = int(os.cpu_count())
        # split peptide list into chunks
        n_samples = len(self.samples)
        cpus_per_job = [len(x) if len(x) > 0 else 1 for x in array_split(range(n_cpus), n_samples)]
        jobs = []
        os.chdir(self.tmp_folder)

        for sample in self.samples:
            i = self.samples.index(sample)
            k = cpus_per_job[i]
            n = len(self.alleles)
            fname = Path(self.tmp_folder, f'{sample.sample_name}_forgibbs.csv')
            peps = np.array(remove_modifications(sample.peptides))
            lengths = np.vectorize(len)(peps)
            peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]

            peps.tofile(str(fname), '\n', '%s')
            if self.mhc_class == 'I':
                command = f'{GIBBSCLUSTER} -f {fname} -P {sample.sample_name} -k {k} ' \
                          f'-g 1-{n if n>5 else 5} -T -j 2 -C -D 4 -I 1 -G'.split(' ')
            else:
                command = f'{GIBBSCLUSTER} -f {fname} -P {sample.sample_name} -k {k} ' \
                          f'-g 1-{n if n>5 else 5} -T -j 2 -G'.split(' ')

            #jobs.append(subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
            job = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            job.communicate()
        for job in jobs:
            job.communicate()
            if job.returncode != 0:
                raise subprocess.SubprocessError(f"Error in running: {job.args}\n\n{job.stderr}")
        ls = list(self.tmp_folder.glob('*'))
        for f in ls:
            if Path(f).is_dir():
                self.gibbs_directories.append(f)

    def cluster_with_gibbscluster2(self):
        n_cpus = int(os.cpu_count())
        # split peptide list into chunks
        n_samples = len(self.samples)
        n_alleles = len(self.alleles)
        n_jobs = n_samples + (n_alleles + 1)*n_samples
        cpus_per_job = []
        cpus_per_job += [5 for x in range(n_samples)]  # for all-peptide runs
        cpus_per_job += [1 for x in range(n_samples*n_alleles)]  # for allele-specific runs
        cpus_per_job += [5 for x in range(n_samples)]  # for non-binder runs

        cpus_per_job = [len(x) if len(x) > 0 else 1 for x in array_split(range(n_cpus), n_samples)]
        jobs = []
        os.chdir(self.tmp_folder)

        # first by sample

        for sample in self.samples:
            i = self.samples.index(sample)
            k = cpus_per_job[i]
            n = len(self.alleles)
            fname = Path(self.tmp_folder, f'{sample.sample_name}_forgibbs.csv')
            peps = np.array(remove_modifications(sample.peptides))
            lengths = np.vectorize(len)(peps)
            peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]

            peps.tofile(str(fname), '\n', '%s')
            if self.mhc_class == 'I':
                command = f'{GIBBSCLUSTER} -f {fname} -P {sample.sample_name} -k 24 ' \
                          f'-g 1-{n if n>5 else 5} -T -j 2 -C -D 4 -I 1 -G'.split(' ')
            else:
                command = f'{GIBBSCLUSTER} -f {fname} -P {sample.sample_name} -k 24 ' \
                          f'-g 1-{n if n>5 else 5} -T -j 2 -G'.split(' ')

            jobs.append(subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))

        # now by allele

        alleles = list(self.predictions['Allele'].unique())
        samples = list(self.predictions['Sample'].unique())
        n_cpus = int(os.cpu_count())
        n_samples = len(samples) * (len(alleles) + 1)
        cpus_per_job = [len(x) if len(x) > 0 else 1 for x in array_split(range(n_cpus), n_samples)]
        jobs = []
        os.chdir(self.tmp_folder)
        i = 0
        for sample in self.samples:
            self.supervised_gibbs_directories[sample.sample_name] = {}
            sample_peps = self.predictions.loc[self.predictions['Sample'] == sample.sample_name, :]
            allele_peps = {}
            for allele in alleles:
                allele_peps[allele] = set(list(sample_peps.loc[(sample_peps['Allele'] == allele) &
                                                               ((sample_peps['Binder'] == 'Strong') |
                                                                (sample_peps[
                                                                     'Binder'] == 'Weak')), 'Peptide'].unique()))
            allele_sets = allele_peps
            allele_sets['unannotated'] = set(list(sample_peps['Peptide']))
            for allele in alleles:
                allele_sets['unannotated'] = allele_sets['unannotated'] - allele_sets[allele]

            for allele, peps in allele_sets.items():
                n_cpus = cpus_per_job[i]
                i += 1
                fname = Path(self.tmp_folder, f"{allele}_{sample.sample_name}_forgibbs.csv")
                peps = np.array(list(allele_sets[allele]))
                if len(peps) < 10:
                    self.supervised_gibbs_directories[sample.sample_name][allele] = None
                else:
                    lengths = np.vectorize(len)(peps)
                    peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]

                    peps.tofile(str(fname), '\n', '%s')
                    g = "1-5" if allele == "unannotated" else "1"
                    if self.mhc_class == 'I':
                        if 'kb' in allele.lower():
                            length = 8
                        else:
                            length = 9
                        command = f'{GIBBSCLUSTER} -f {fname} -P {allele}_{sample.sample_name} -k 24 -l {str(length)} ' \
                                  f'-g {g} -T -j 2 -C -D 4 -I 1 -G'.split(' ')
                    else:
                        command = f'{GIBBSCLUSTER} -f {fname} -P {allele}_{sample.sample_name} -k 24 ' \
                                  f'-g {g} -T -j 2 -G'.split(' ')

                    jobs.append(subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
        for job in jobs:
            job.communicate()
            if job.returncode != 0:
                raise subprocess.SubprocessError(f"Error in running: {job.args}\n\n{job.stderr}")
        ls = list(self.tmp_folder.glob('*'))
        for f in ls:
            if Path(f).is_dir():
                self.gibbs_directories.append(f)

    def cluster_with_gibbscluster_by_allele(self):
        alleles = list(self.predictions['Allele'].unique())
        samples = list(self.predictions['Sample'].unique())
        n_cpus = int(os.cpu_count())
        n_samples = len(samples) * (len(alleles) + 1)
        cpus_per_job = [len(x) if len(x) > 0 else 1 for x in array_split(range(n_cpus), n_samples)]
        jobs = []
        os.chdir(self.tmp_folder)
        i = 0
        for sample in self.samples:
            self.supervised_gibbs_directories[sample.sample_name] = {}
            sample_peps = self.predictions.loc[self.predictions['Sample'] == sample.sample_name, :]
            allele_peps = {}
            for allele in alleles:
                allele_peps[allele] = set(list(sample_peps.loc[(sample_peps['Allele'] == allele) &
                                                               ((sample_peps['Binder'] == 'Strong') |
                                                                (sample_peps['Binder'] == 'Weak')), 'Peptide'].unique()))
            '''allele_sets = {}
            for allele1 in alleles:
                allele1_set = allele_peps[allele1]
                for allele2 in alleles:
                    if allele1 == allele2:
                        continue
                    allele1_set = allele1_set - allele_peps[allele2]
                allele_sets[allele1] = allele1_set
            '''
            allele_sets = allele_peps
            allele_sets['unannotated'] = set(list(sample_peps['Peptide']))
            for allele in alleles:
                allele_sets['unannotated'] = allele_sets['unannotated'] - allele_sets[allele]

            for allele, peps in allele_sets.items():
                n_cpus = cpus_per_job[i]
                i += 1
                fname = Path(self.tmp_folder, f"{allele}_{sample.sample_name}_forgibbs.csv")
                peps = np.array(list(allele_sets[allele]))
                if len(peps) < 20:
                    self.supervised_gibbs_directories[sample.sample_name][allele] = None
                else:
                    lengths = np.vectorize(len)(peps)
                    peps = peps[(lengths >= self.min_length) & (lengths <= self.max_length)]

                    peps.tofile(str(fname), '\n', '%s')
                    g = "1-5" if allele == "unannotated" else "1"
                    if self.mhc_class == 'I':
                        if 'kb' in allele.lower():
                            length = 8
                        else:
                            length = 9
                        command = f'{GIBBSCLUSTER} -f {fname} -P {allele}_{sample.sample_name} -k {n_cpus} -l {str(length)} ' \
                                  f'-g {g} -T -j 2 -C -D 4 -I 1 -G'.split(' ')
                    else:
                        command = f'{GIBBSCLUSTER} -f {fname} -P {allele}_{sample.sample_name} -k {n_cpus} ' \
                                  f'-g {g} -T -j 2 -G'.split(' ')

                    jobs.append(subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
                    # job = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    # job.communicate()
        for job in jobs:
            job.communicate()
            if job.returncode != 0:
                raise subprocess.SubprocessError(f"Error in running: {job.args}\n\n{job.stderr}")
        for sample in self.samples:
            for allele in alleles + ['unannotated']:
                ls = list(self.tmp_folder.glob(allele+'_'+sample.sample_name+'*'))
                for f in ls:
                    if Path(f).is_dir():
                        self.supervised_gibbs_directories[sample.sample_name][allele] = f
