import argparse
from MhcVizPipe.Tools.cl_tools import MhcPeptides, MhcToolHelper
from MhcVizPipe.ReportTemplates import report
from MhcVizPipe.defaults import Parameters, ROOT_DIR
from pathlib import Path
from os import getcwd

"""
NOTE: This interface is out of date. It needs to be refactored before it will work.
"""

Parameters = Parameters()
TMP_DIR = Parameters.TMP_DIR

parser = argparse.ArgumentParser()

parser.add_argument('-f', '--files', type=str, nargs='+', required=True,
                    help='One or more files (space separated) containing peptide lists to analyze.')
parser.add_argument('-d', '--delimiter', type=str, required=False, choices=['comma', 'tab'],
                    help='Delimiter if the file is delimited (e.g. for .csv use "comma").')
parser.add_argument('-H', '--column_header', type=str, required=False, help='The name of the column containing the peptide '
                                                                            'list, if it is a multi-column file.')
parser.add_argument('-a', '--alleles', type=str, required=True, nargs='+',
                    help='MHC alleles, spaces separated if more than one.')
parser.add_argument('-c', '--mhc_class', type=str, choices=['I', 'II'], required=True, help='MHC class')
parser.add_argument('-D', '--description', type=str, required=False,
                    help='An optional description of the experiment/analysis. Enclose it in quotes, e.g. "This is '
                         'a description of my analysis".')
parser.add_argument('-n', '--name', type=str, required=False,
                    help='Submitter name (optional).')
parser.add_argument('-p', '--publish_directory', type=str, required=False, default=getcwd(),
                    help='The directory where you want the report published. It should be an absolute path.')
parser.add_argument('--f_out', type=str, required=False, default='report.html',
                    help='The filename you want for the report. Defaults to "report".')
parser.add_argument('-v', '--version', type=str, required=False, default='4.1', choices=['4.0', '4.1'],
                    help='Which version of NetMHCpan to use. For internal use during development.')
parser.add_argument('-e', '--exp_info', type=str, required=False,
                    help='Optional details to be added to the report (e.g. experimental conditions). Should be in '
                         'this format (including quotes): "A: Z; B: Y; C: X;" etc... where ABC(etc.) are field names '
                         '(e.g. cell line, # of cells, MS Instrument, etc) and ZYX(etc) are details describing the '
                         'field (e.g. JY cell line, 10e6, Orbitrap Fusion, etc.).')
parser.add_argument('--max', type=int, required=False, help='Maximum peptide length to run through NetMHCpan.')

if __name__ == '__main__':
    netmhcpan_alleles = []
    args = parser.parse_args()
    dir = getcwd()
    if len(args.alleles) == 1:
        args.alleles = args.alleles[0].split(' ')
    if args.mhc_class == 'I':
        if args.version == '4.1':
            with open(Path(ROOT_DIR, 'assets', 'class_I_alleles.txt')) as f:
                for allele in f.readlines():
                    allele = allele.strip()
                    netmhcpan_alleles.append(allele)
        else:
            with open(Path(ROOT_DIR, 'assets', 'class_I_alleles_4.0.txt')) as f:
                for allele in f.readlines():
                    allele = allele.strip()
                    netmhcpan_alleles.append(allele)
    else:
        with open(Path(ROOT_DIR, 'assets', 'class_II_alleles.txt')) as f:
            for allele in f.readlines():
                allele = allele.strip()
                netmhcpan_alleles.append(allele)

    for a in args.alleles:
        if a not in netmhcpan_alleles:
            print(f'ERROR: {a} is not a recognized allele by the chosen software.')
            raise SystemExit

    file_names = args.files
    peptide_data = {}
    for file in args.files:
        sample_name = Path(file).name
        peptide_data[sample_name] = {}
        with open(file, 'r') as f:
            lines = f.readlines()
            peptides = []
            if args.delimiter:
                if args.delimiter == 'comma':
                    delimiter = ','
                else:
                    delimiter = '\t'
                header_index = lines[0].strip().index(args.column_header)
                for line in lines[1:]:
                    peptides.append(line.strip().split(delimiter)[header_index])
            else:
                for line in lines:
                    peptides.append(line.strip())
        peptide_data[sample_name] = {'description': '', 'peptides': peptides}

    samples = []
    for sample_name in peptide_data.keys():
        samples.append(
            MhcPeptides(sample_name=sample_name,
                        sample_description=peptide_data[sample_name]['description'],
                        peptides=peptide_data[sample_name]['peptides'])
        )
    #time = str(datetime.now()).replace(' ', '_')
    analysis_location = args.publish_directory

    if args.mhc_class == 'I':
        min_length = 8
    else:
        min_length = 9

    if args.max:
        max_length = args.max
    elif args.mhc_class == 'I':
        max_length = 12
    else:
        max_length = 22

    exp_info = args.exp_info.replace('; ', '\n').replace(';', '\n')

    cl_tools = MhcToolHelper(
        samples=samples,
        mhc_class=args.mhc_class,
        alleles=args.alleles,
        tmp_directory=analysis_location,
        min_length=min_length,
        max_length=max_length
    )
    cl_tools.make_binding_prediction_jobs()
    cl_tools.run_jubs()
    cl_tools.aggregate_netmhcpan_results()
    cl_tools.clear_jobs()

    cl_tools.make_cluster_with_gibbscluster_jobs()
    cl_tools.make_cluster_with_gibbscluster_by_allele_jobs()
    cl_tools.order_gibbs_runs()
    cl_tools.run_jubs()
    cl_tools.find_best_files()
    analysis = report.mhc_report(cl_tools, args.mhc_class, args.description, args.name, exp_info)
    _ = analysis.make_report()
    report = Path(analysis_location) / 'report.html'
    if args.f_out.endswith('.html'):
        f_out = args.f_out
    else:
        f_out = args.f_out + '.html'
    Path(report).rename(f_out)
    print('Done!')
