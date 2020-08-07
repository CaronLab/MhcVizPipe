# -*- coding: utf-8 -*-
import dash_core_components as dcc
import dash_table
import dash_html_components as html
import dash_bootstrap_components as dbc
from datetime import datetime
from typing import List
from MhcVizPipe.Tools.cl_tools import MhcPeptides, MhcToolHelper
import plotly.graph_objects as go
import numpy as np
from MhcVizPipe.Tools import plotly_venn
import base64
import itertools
import re
import pandas as pd
from upsetplot import UpSet, from_contents
import matplotlib.pyplot as plt
from matplotlib.text import Text as plotText


def generate_report(analysis_results: MhcToolHelper,
                    mhc_class: str,
                    experiment_description: str = None,
                    submitter_name: str = None) -> html.Div:

    alleles = analysis_results.alleles
    preds = analysis_results.predictions.drop_duplicates()
    samples = list(preds['Sample'].unique())
    binders = preds['Binder'].unique()

    #### SAMPLE TABLE
    min_len = 8 if analysis_results.mhc_class == 'I' else 12
    max_len = 12 if analysis_results.mhc_class == 'I' else 22
    columns = [{'name': '', 'id': 'peptides'}]
    for sample in samples:
        columns += [{'name': sample, 'id': f'{sample}'}]

    peps = []
    for s in analysis_results.samples:
        peps += s.peptides
    total_peptides = len(set(peps))
    peps = np.array(peps)
    lengths = np.vectorize(len)(peps)
    total_within_len = len(peps[(lengths >= min_len) & (lengths <= max_len)])

    #data for table

    peptide_numbers = {}
    for sample in samples:
        peptide_numbers[sample] = {}
        peptide_numbers[sample]['total'] = len(preds.loc[preds['Sample'] == sample, 'Peptide'].unique())
        for allele in alleles:
            peptide_numbers[sample][allele] = {}
            for strength in ['Strong', 'Weak', 'Non-binder']:
                peptide_numbers[sample][allele][strength] = len(
                    preds.loc[(preds['Sample'] == sample) &
                              (preds['Allele'] == allele) &
                              (preds['Binder'] == strength), 'Peptide'].unique()
                )

    tables = []

    for allele in alleles:
        table_header = [
            html.Thead(html.Tr([html.Th(f'Allele: {allele}', style={'text-align': 'right', 'padding-right': '10px'}),
                                *[html.Th(strength, style={'text-align': 'right', 'padding-right': '10px'}) for strength in
                                  ['All peptides', 'Strong binders', 'Weak binders', 'Non-binders']]]))]
        sample_data = []
        for sample in samples:
            row = html.Tr([
                html.Td(sample, style={'text-align': 'right'}),
                html.Td(peptide_numbers[sample]['total'], style={'text-align': 'right'}),
                *[html.Td(f"{peptide_numbers[sample][allele][strength]} "
                          f"({round(peptide_numbers[sample][allele][strength] * 100 / peptide_numbers[sample]['total'], 1)}%)",
                          style={'text-align': 'right', 'padding-right': '10px'})
                  for strength in ['Strong', 'Weak', 'Non-binder']]
            ])
            sample_data.append(row)

        table_body = [html.Tbody(sample_data)]
        table = dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True)
        tables.append(dbc.Row(dbc.Col(table, style={'margin': '10px'})))

    peptide_tables = dbc.Card(
        [
            dbc.CardHeader(html.B('Peptide counts')),
            html.Div(tables)
        ]
    )

    #### Figure for peptide counts

    def get_highest_binding(predictions):
        if 'Strong' in predictions.values:
            return 'Strong'
        elif 'Weak' in predictions.values:
            return 'Weak'
        else:
            return 'Non-binding'

    n_peps_fig = go.Figure()
    pep_binding_dict = {}
    for sample in samples:
        counts_df = preds.loc[preds['Sample'] == sample, :]
        counts_df = counts_df.pivot(index='Peptide', columns='Allele', values='Binder')
        pep_binding_dict[sample] = counts_df.copy(deep=True)  # this is for use later in the Venn table
        bindings = counts_df.apply(get_highest_binding, axis=1).values
        binders, counts = np.unique(bindings, return_counts=True)
        counts = [counts[list(binders).index('Strong') if 'Strong' in binders else 0],
                  counts[list(binders).index('Weak') if 'Weak' in binders else 0],
                  counts[list(binders).index('Non-binder') if 'Non-binder' in binders else 0]]
        binders = ['Strong', 'Weak', 'Non-binder']
        n_peps_fig.add_trace(go.Bar(x=binders, y=counts, name=sample))
    n_peps_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    n_peps_fig.update_yaxes(title_text='Number of peptides')
    n_peps_fig.update_xaxes(title_text='Binding strength')

    #### Figure for peptide lengths

    len_dist = go.Figure()
    for sample in samples:
        lengths, counts = np.unique(preds.loc[preds['Sample'] == sample, 'Peptide'].str.len().values,
                                    return_counts=True)
        len_dist.add_trace(go.Bar(name=sample, x=lengths, y=counts))
    len_dist.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    len_dist.update_yaxes(title_text='Number of peptides')
    len_dist.update_xaxes(title_text='Peptide length')

    #### Heatmaps
    ymax = np.max([peptide_numbers[sample]['total'] for sample in samples])
    heatmaps = dbc.Row(children=[])
    for sample in samples:
        pivot = preds.loc[preds['Sample'] == sample, :].pivot(index='Peptide', columns='Allele', values='Rank').astype(float)
        if mhc_class == 'I':
            pivot[pivot > 2.5] = 2.5
            #colorscale = [[0, '#f53b3b'], [0.4/2.5, '#bd0b0b'], [0.7/2.5, '#08870d'], [1.9/2.5, '#026b06'], [2.2/2.5, '#00234f'], [1, '#e5ecf6']]
            colorscale = [[0, '#ef553b'], [0.4 / 2.5, '#ef553b'], [0.7 / 2.5, '#636efa'], [1.9 / 2.5, '#636efa'],
                          [2.2 / 2.5, 'rgba(99, 110, 250, 0)'], [1, 'rgba(99, 110, 250, 0)']]
        else:
            pivot[pivot > 12] = 12
            # colorscale = [[0, '#f53b3b'], [0.4/2.5, '#bd0b0b'], [0.7/2.5, '#08870d'], [1.9/2.5, '#026b06'], [2.2/2.5, '#00234f'], [1, '#e5ecf6']]
            colorscale = [[0, '#ef553b'], [1.6 / 12, '#ef553b'], [2.4 / 12, '#636efa'], [9.8 / 12, '#636efa'],
                          [10.6 / 12, 'rgba(99, 110, 250, 0)'], [1, 'rgba(99, 110, 250, 0)']]
            # red #ef553b
            # blue #636efa
            # background #e5ecf6
        data = pivot.sort_values(list(pivot.columns), ascending=True)

        if mhc_class == 'I':
            colorbar=dict(title='%Rank',
                          tickmode='array',
                          tickvals=[0.5, 1, 1.5, 2, 2.5],
                          ticktext=['0.5', '1.0', '1.5', '2.0', '>2.5'])
        else:
            colorbar = dict(title='%Rank',
                          tickmode='array',
                          tickvals=[2, 4, 6, 8, 10, 12],
                          ticktext=['2', '4', '6', '8', '10', '>12'])

        fig = go.Figure(go.Heatmap(
            z=data,
            x=list(pivot.columns),
            colorscale=colorscale,
            colorbar=colorbar
        ))
        fig.layout.plot_bgcolor = '#e5ecf6'
        fig.layout.margin = dict(l=20, r=20, t=20, b=20)
        fig.update_yaxes(range=[0, ymax],
                         title_text='Number of peptides')
        fig.update_xaxes(title_text='Allele')

        heatmaps.children.append(dbc.Col(
            [
                dbc.Card([
                    dbc.CardHeader(html.B(sample)),
                    dbc.CardBody(dcc.Graph(figure=fig, style={'height': '350px'}))
                ])
            ],
            style={'display': 'block'},
            xs=12,
            sm=12,
            md=6,
            lg=4,
            xl=3
        ))

    #### VENN DIAGRAM

    if len(analysis_results.samples) > 1:
        fig = venn_diagram(analysis_results)
        venn_image = dbc.Card(
            [
                dbc.CardHeader(html.B('Venn Diagram')),
                dbc.CardBody(dcc.Graph(figure=fig))
            ]
        )
    else:
        venn_image = html.Div([])

    #### UPSET PLOT
    if len(samples) > 1:
        data = from_contents({s.sample_name: set(s.peptides) for s in analysis_results.samples})
        #total = np.sum(data)
        #data = data[data/total >= 1.0]
        upset = UpSet(data,
                      sort_by='cardinality',
                      sort_categories_by=None,
                      show_counts=True,
                      show_percentages=True,
                      orientation='vertical')
        plot = upset.plot()
        lim = plot['intersections'].get_xlim()
        plot['intersections'].set_xlim([0, lim[1] * 1.3])
        plot['totals'].grid(False)
        ylim = plot['totals'].get_ylim()[1]
        for c in plot['totals'].get_children():
            if isinstance(c, plotText):
                text = c.get_text()
                text = text.replace('\n', ' ')
                c.set_text(text)
                c.set_rotation('vertical')
                pos = c.get_position()
                pos = (pos[0], pos[1] + 0.1 * ylim)
                c.set_position(pos)
        upset_fig = f'{analysis_results.tmp_folder/"upsetplot.png"}'
        plt.savefig(upset_fig)
        encoded_upset_fig = base64.b64encode(open(upset_fig, 'rb').read()).decode()
    else:
        encoded_upset_fig = 'R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='

    #### SEQUENCE MOTIFS

    def cosine_similarity(x, y) -> int:
        x = np.array(x).flatten()
        y = np.array(y).flatten()
        return np.dot(x, y) / (np.sqrt(np.dot(x, x)) * np.sqrt(np.dot(y, y)))


    def arrange_logos(samples: List[str]):
        motifs = html.Div(children=[])
        first_set = {}
        n_motifs = {}
        gibbs_peps = {}
        for sample in samples:
            report = str(list(analysis_results.tmp_folder.glob(f'./{sample}_*/*_report.html'))[0])
            with open(report, 'r') as f:
                lines = ' '.join(f.readlines())
            n_motifs[sample] = (re.search('Identified ([0-9]*) sequence motifs', lines)[1])
            pep_groups_file = str(list(analysis_results.tmp_folder.glob(
                f'./{sample}_*/res/gibbs.{n_motifs[sample]}g.ds.out'))[0])
            with open(pep_groups_file, 'r') as f:
                pep_lines = f.readlines()[1:]
            gibbs_peps[sample] = {x: [] for x in range(int(n_motifs[sample]))}
            for line in pep_lines:
                line = [x for x in line.split(' ') if x != '']
                group = int(line[1])
                pep = line[3]
                gibbs_peps[sample][group].append(pep)

        n = np.max([int(n) for n in n_motifs.values()])

        samples.sort(key=lambda x: int(n_motifs[x]), reverse=True)

        for sample in samples:
            motifs.children.append(dbc.Card(
                [
                    dbc.CardHeader(html.B(f'{sample}')),
                    dbc.CardBody(children=[dbc.Row([])])
                ]))

            logos = list(analysis_results.tmp_folder.glob(f'./{sample}_*/logos/gibbs_logos_*.png'))
            logos = [str(l) for l in logos if f'of{n_motifs[sample]}' in str(l)]
            logos.sort()
            matrices = list(analysis_results.tmp_folder.glob(f'./{sample}_*/matrices/gibbs*.mat'))
            matrices = [str(m) for m in matrices if f'of{n_motifs[sample]}' in str(m)]
            matrices.sort()

            np_matrices = [np.loadtxt(matrix, dtype=float, delimiter=' ', skiprows=2, usecols=range(2, 22)) for matrix in matrices]
            if sample == samples[0]:
                first_set[0] = np_matrices.copy()
                order = range(len(first_set[0]))
            else:
                indices = list(range(len(np_matrices)))
                for i in range(len(first_set[0]) - len(np_matrices)):
                    indices += [None]
                possible_orders = list(itertools.permutations(indices))
                best_score = 0
                best_order = possible_orders[0]
                for order in possible_orders:
                    score = 0
                    for i in range(len(first_set[0])):
                        if order[i] is not None:
                            score += cosine_similarity(first_set[0][i], np_matrices[order[i]])
                    if score > best_score:
                        best_order = order
                        best_score = score
                order = best_order

            image_width = np.floor(95 / n) if n > 3 else np.floor(95 / 4)
            p: pd.DataFrame = pep_binding_dict[sample]
            for i in order:
                if i is not None:
                    g_peps = set(gibbs_peps[sample][i])
                    allele_composition = {allele: round(
                        len(g_peps & set(p[(p[allele] == "Strong") | (p[allele] == "Weak")].index)) * 100 / len(g_peps))
                        for allele in alleles}
                    non_binding_peps = [set(p[p[allele] == "Non-binder"].index) for allele in alleles]
                    non_binding_set = non_binding_peps[0]
                    for x in non_binding_peps[1:]:
                        non_binding_set = non_binding_set & x
                    non_binding_composition = round(len(non_binding_set & g_peps)*100/len(g_peps))
                    logo = logos[i]
                    image_filename = logo
                    encoded_motif_image = base64.b64encode(open(image_filename, 'rb').read())
                    motifs.children[-1].children[-1].children[0].children.append(
                        html.Div(
                            [
                                html.Img(src='data:image/png;base64,{}'.format(encoded_motif_image.decode()),
                                         style={'width': '100%',
                                                'display': 'block',
                                                'margin-left': 'auto',
                                                'margin-right': 'auto'}),
                                html.P(f'Peptides: {len(g_peps)}'),
                                html.P(f'Composition:'),
                                *[html.P(f'  {a}: {allele_composition[a]}%', style={'margin-left': '10px'})
                                  for a in allele_composition.keys()],
                                html.P(f'  Non-binding: {non_binding_composition}%', style={'margin-left': '10px'})
                            ],
                            style={'width': f'{image_width}%',
                                   'display': 'block',
                                   'margin-left': 'auto',
                                   'margin-right': 'auto',
                                   'font-size': '10pt'}
                        ),
                    )
                else:
                    motifs.children[-1].children[-1].children[0].children.append(
                        html.Img(src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==",
                                 style={'width': f'{image_width}%',
                                        'display': 'block',
                                        'margin-left': 'auto',
                                        'margin-right': 'auto'})
                    )
        return motifs

    motifs = arrange_logos((samples))

    layout = html.Div(
        [
            html.H2(
                'MhcVizPipe Report',
                style={
                    'background-color': '#4CAF50',
                    'color': 'white'
                }
            ),
            html.P([html.B('Date: '), str(datetime.now().date())]),
            html.P([html.B('Submitter: '), f'{submitter_name if submitter_name else "Anonymous"}']),
            html.Div(
                [
                    html.B('Desciption of experiment:', style={'margin-right': '5px', 'white-space': 'nowrap'}),
                    html.P(experiment_description if experiment_description else 'None provided')
                ],
                style={'display': 'flex'}
            ),
            html.P([html.B('Alleles: '), html.A(', '.join(analysis_results.alleles))]),
            html.B('Samples:'),
            html.Div(
                [
                    html.P([html.B(f'{name}: '), description]) for name, description in analysis_results.descriptions.items()
                ],
                style={'margin-left': '1em'}
            ),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col(peptide_tables),
                    dbc.Col(
                        html.Img(src='data:image/png;base64,{}'.format(encoded_upset_fig),
                                 style={'width': 'auto',
                                        'display': 'block',
                                        'margin-top': 'auto',
                                        'margin-bottom': 'auto'}),
                    )
                ]
            ),
            #peptide_tables,
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            venn_image
                        ]
                    )
                ]
            ),
            html.Hr(),
            html.H3('Peptide Properties'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.B('Peptide Counts')),
                                    dbc.CardBody(dcc.Graph(figure=n_peps_fig, style={'height': '350px'}))
                                ]
                            )
                        ],
                        width=12,
                        xl=6
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.B('Peptide Lengths')),
                                    dbc.CardBody(dcc.Graph(figure=len_dist, style={'height': '350px'}))
                                ]
                            )
                        ],
                        width=12,
                        xl=6
                    )
                ]
            ),
            html.Hr(),
            html.H3('Binding Heatmaps'),
            heatmaps,
            html.Hr(),
            html.H3('Sequence Motifs'),
            html.P('Sequence motifs identified by GibbsCluster. The number of peptides indicates the number of '
                   'peptides in each group. The composition is determined by the sets of peptides from a given '
                   'group which are identified as strong or weak binders by '
                   f'netMHC{"" if mhc_class == "I" else "II"}pan. Non-binding represents the set of peptides in '
                   f'a group that were not strong or weak binders for any allele. The percentages can add up to '
                   f'more than 100% because peptides can have affinity for more than one allele.'),
            motifs
        ]
    )

    return layout


def venn_diagram(analysis_results: MhcToolHelper):
    n_sets = len(analysis_results.samples)
    if n_sets == 2:
        venn_maker = plotly_venn.venn2
    elif n_sets == 3:
        venn_maker = plotly_venn.venn3
    elif n_sets == 4:
        venn_maker = plotly_venn.venn4
    elif n_sets == 5:
        venn_maker = plotly_venn.venn5
    elif n_sets == 6:
        venn_maker = plotly_venn.venn6
    else:
        return

    labels = plotly_venn.get_labels([s.peptides for s in analysis_results.samples])
    names = [s.sample_name for s in analysis_results.samples]
    fig = venn_maker(labels, names)
    return fig
