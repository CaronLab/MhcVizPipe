import re
import argparse
from pathlib import Path


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


def remove_modifications(peptide_list, verbose=False):
    unmodified_peps = []
    if verbose:
        print('Removing peptide modifications')
    for pep in peptide_list:
        pep = remove_previous_and_next_aa(pep)
        pep = ''.join(re.findall('[a-zA-Z]+', pep))
        pep = pep.upper()
        unmodified_peps.append(pep)
    return unmodified_peps


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=
                                     "Remove modifications from a list of peptides and write the unmodified versions "
                                     "to a new file.")
    parser.add_argument('-f', required=True, type=str, default='peptide.csv',
                        help='File containing a peptide list to unmodify. Can be a single column or multiple columns '
                             'with headers.')

    parser.add_argument('-c', type=str, help='Header of the column containing peptides, if applicable.')
    parser.add_argument('-d', type=str, choices=['comma', 'tab'], help='Delimiter if file has multiple columns.')

    args = parser.parse_args()

    if (args.c and not args.d) or (args.d and not args.c):
        parser.error('-c and -d are mutually dependent.')

    if args.d == 'comma':
        args.d = ','
    elif args.d == 'tab':
        args.d = '\t'

    if not Path(args.f).exists():
        parser.error(f'{args.f} does not appear to exist. Check file name/path.')

    with open(args.f) as f:
        print("Reading file")
        peps = f.readlines()

    pep_file = Path(args.f)
    with open(str(pep_file.parent/pep_file.stem)+'_unmodified.csv', 'w') as f:
        if args.c:
            index = peps[0].split(args.d).index(args.c)
        modified = []
        for p in peps[1:]:
            if args.c:
                p = p.split(args.d)[index]
            modified.append(p)

        unmodified = remove_modifications(modified, verbose=True)
        print('Writing unmodified file to disk')
        for p in unmodified:
            f.write(p + '\n')
