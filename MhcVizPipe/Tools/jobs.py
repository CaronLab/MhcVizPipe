from typing import Union, List, Tuple
import subprocess
from multiprocessing import Pool
import os
from pathlib import Path
from datetime import datetime


class Job:
    def __init__(self,
                 command: Union[str, List[str]],
                 working_directory: Union[str, Path, None],
                 id: Union[str, None],
                 sample=None):

        self.command = command
        self.working_directory = working_directory
        self.id = id
        self.returncode = None
        self.time_start = str(datetime.now()).replace(' ', '')
        self.time_end = ''
        self.stdout = ''
        self.stderr = ''
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
