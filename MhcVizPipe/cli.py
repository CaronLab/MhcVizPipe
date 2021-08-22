import argparse
from argparse import RawDescriptionHelpFormatter
from MhcVizPipe.Tools.cl_tools import MhcToolHelper
from MhcVizPipe.Tools.utils import sanitize_sample_name, check_alleles,\
    clean_peptides, load_template_file, load_peptide_file, package_report
from MhcVizPipe.Reporting import report
from MhcVizPipe.parameters import Parameters, ROOT_DIR
from pathlib import Path
from os import getcwd
from datetime import datetime
from os.path import expanduser
import shutil


Parameters = Parameters()
TMP_DIR = Parameters.TMP_DIR

parser = argparse.ArgumentParser(description="Welcome to the MhcVizPipe command line interface (CLI). This "
                                             "CLI will allow you to generate MhcVizPipe reports using "
                                             "standard scripting practices.\n\n"
                                             "If you have not previously used the graphical interface on "
                                             "your computer, the first time you run the CLI a config file "
                                             f"will be created in one of two locations. If you are running MVP "
                                             f"from a standalone installation (i.e. not installed into Python "
                                             f"using PIP), the config file will be in the MhcVizPipe directory "
                                             f"and will be called mhcvizpipe.config. If you are running "
                                             f"MhcVizPipe from Python directly, the file will be created in "
                                             f"your home directory: {str(expanduser('~/.mhcvizpipe.config'))}.\n\n"
                                             f"If it is the first time you have run MhcVizPipe, be sure to check "
                                             f"the configuration in the above file.")

parser.add_argument('-f', '--files', type=str, nargs='+',
                    help='One or more files (space separated) containing peptide lists to analyze.')
parser.add_argument('-t', '--template', type=str,
                    help='A tab-separated file containing file paths and alleles. Can be used to process peptide lists '
                         'with different alleles at the same time. The first column must be the file paths, and the '
                         'respective alleles can be put in the following columns, up to 6 per sample.')
parser.add_argument('-d', '--delimiter', type=str, required=False, choices=['comma', 'tab'],
                    help='Delimiter if the file is delimited (e.g. for .csv use "comma").')
parser.add_argument('-H', '--column_header', type=str, required=False, help='The name of the column containing the peptide '
                                                                            'list, if it is a multi-column file.')
parser.add_argument('-a', '--alleles', type=str, nargs='+',
                    help='MHC alleles, spaces separated if more than one.')
parser.add_argument('-c', '--mhc_class', type=str, choices=['I', 'II'], required=True, help='MHC class')
parser.add_argument('-D', '--description', type=str, default='',
                    help='An optional description of the experiment/analysis. Enclose it in quotes, e.g. "This is '
                         'a description of my analysis".')
parser.add_argument('-n', '--name', type=str, default='',
                    help='Submitter name (optional).')
parser.add_argument('-p', '--publish_directory', type=str, required=False, default=getcwd(),
                    help='The directory where you want the report published. It should be an absolute path.')
parser.add_argument('-e', '--exp_info', type=str, default='',
                    help='Optional details to be added to the report (e.g. experimental conditions). Should be in '
                         'this format (including quotes): "A: Z; B: Y; C: X;" etc... where ABC(etc.) are field names '
                         '(e.g. cell line, # of cells, MS Instrument, etc) and ZYX(etc) are details describing the '
                         'field (e.g. JY cell line, 10e6, Orbitrap Fusion, etc.).')
parser.add_argument('--standalone', action='store_true', help='Run MVP in from a standalone installation (i.e. '
                                                              'not installed from PIP). You don\'t usually need to '
                                                              'invoke this as it is done automatically from the '
                                                              'bash script included in the standalone MhcVizPipe '
                                                              'distribution.')

if __name__ == '__main__':
    netmhcpan_alleles = []
    args = parser.parse_args()
    dir = getcwd()

    print(f'File(s): {args.files if args.files else args.template}')
    print(f'Output directory: {args.publish_directory}')

    if args.mhc_class == 'I':
        with open(Path(ROOT_DIR, 'assets', 'class_I_alleles.txt')) as f:
            for allele in f.readlines():
                allele = allele.strip()
                netmhcpan_alleles.append(allele)
    else:
        with open(Path(ROOT_DIR, 'assets', 'class_II_alleles.txt')) as f:
            for allele in f.readlines():
                allele = allele.strip()
                netmhcpan_alleles.append(allele)

    sample_info = []
    sample_peptides = {}
    time = str(datetime.now()).replace(' ', '_')
    analysis_location = str(Path(Parameters.TMP_DIR) / time)

    if args.template:
        files_alleles = load_template_file(args.template)
        for file in files_alleles:
            check_alleles(file['alleles'], netmhcpan_alleles)
            sample_name = sanitize_sample_name(Path(file['file']).name)
            sample_info.append({'sample-name': sample_name,
                                'sample-description': '',
                                'sample-alleles': ', '.join(file['alleles'])})
            sample_peptides[sample_name] = clean_peptides(load_peptide_file(file['file']))
    else:
        files = args.files
        alleles = args.alleles
        check_alleles(alleles, netmhcpan_alleles)
        for file in files:
            sample_name = sanitize_sample_name(Path(file).name)
            sample_info.append({'sample-name': sample_name,
                                'sample-description': '',
                                'sample-alleles': ', '.join(alleles)})
            sample_peptides[sample_name] = clean_peptides(load_peptide_file(file))
    cl_tools = MhcToolHelper(
        sample_info_datatable=sample_info,
        mhc_class=args.mhc_class,
        sample_peptides=sample_peptides,
        tmp_directory=analysis_location,
        min_length=8 if args.mhc_class == 'I' else 9,
        max_length=12 if args.mhc_class == 'I' else 22
    )

    exp_info = args.exp_info.replace('; ', '\n').replace(';', '\n')
    print(f'Running NetMHC{args.mhc_class if args.mhc_class == "II" else ""}pan')
    cl_tools.make_binding_predictions()
    print(f'Writing binding predictions')
    cl_tools.write_binding_predictions()
    print('Running GibbsCluster')
    cl_tools.make_cluster_with_gibbscluster_jobs()
    cl_tools.make_cluster_with_gibbscluster_by_allele_jobs()
    cl_tools.order_gibbs_runs()
    cl_tools.run_jobs()
    cl_tools.find_best_files()
    print('Creating report')
    analysis = report.mhc_report(cl_tools,
                                 args.mhc_class,
                                 Parameters.THREADS,
                                 args.description,
                                 args.name,
                                 exp_info)
    _ = analysis.make_report()
    print('Creating report archive')
    packaged_report = package_report(analysis_location)
    report_location = Path(args.publish_directory)
    if not report_location.exists():
        report_location.mkdir()
    report = Path(analysis_location) / 'report.html'
    shutil.copy(report, str(report_location / 'report.html'))
    shutil.copy(packaged_report, str(report_location / 'MVP_report_components.zip'))
    print('Done!\n')
