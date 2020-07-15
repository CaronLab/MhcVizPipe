# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List
from MhcQcPipe.Tools.cl_tools import MhcPeptides, MhcToolHelper
import plotly.graph_objects as go
import numpy as np
from MhcQcPipe.Tools import plotly_venn
import base64
import itertools
import re
import pandas as pd
from upsetplot import UpSet, from_contents
import matplotlib.pyplot as plt
from matplotlib.text import Text as plotText
from pathlib import Path

from dominate.util import raw
from dominate.tags import *
from dominate import document
import PlotlyLogo.logo as pl
from MhcQcPipe.app import ROOT_DIR

class mhc_report:
    def __init__(self,
                 analysis_results: MhcToolHelper,
                 mhc_class: str,
                 experiment_description: str = None,
                 submitter_name: str = None
                 ):
        self.results = analysis_results
        self.mhc_class = mhc_class
        self.experiment_description = experiment_description
        self.submitter_name = submitter_name
        self.alleles = analysis_results.alleles
        self.preds = analysis_results.predictions.drop_duplicates()
        self.samples = list(self.preds['Sample'].unique())

        peptide_numbers = {}
        for sample in self.samples:
            peptide_numbers[sample] = {}
            peptide_numbers[sample]['total'] = len(self.preds.loc[self.preds['Sample'] == sample, 'Peptide'].unique())
            for allele in self.alleles:
                peptide_numbers[sample][allele] = {}
                for strength in ['Strong', 'Weak', 'Non-binder']:
                    peptide_numbers[sample][allele][strength] = len(
                        self.preds.loc[(self.preds['Sample'] == sample) &
                                  (self.preds['Allele'] == allele) &
                                  (self.preds['Binder'] == strength), 'Peptide'].unique()
                    )
        self.peptide_numbers = peptide_numbers

        pep_binding_dict = {}
        for sample in self.samples:
            counts_df = self.preds.loc[self.preds['Sample'] == sample, :]
            counts_df = counts_df.pivot(index='Peptide', columns='Allele', values='Binder')
            pep_binding_dict[sample] = counts_df.copy(deep=True)
        self.pep_binding_dict = pep_binding_dict

        lab_logo = base64.b64encode(open(str(Path(ROOT_DIR)/'assets/logo_CARONLAB_horizontal.jpg'), 'rb').read()).decode()
        self.lab_logo = img(src='data:image/jpg;base64,{lab_logo}', className='img-fluid',
                            style="max-width:100%; max-height:100%; opacity: 50%; margin-left: 10px;"
                                  "margin-bottom: 8px")

    def gen_peptide_tables(self, className=None):

        t = table(className=f'table table-hover table-bordered',
                  style="text-align: center",
                  id='peptidetable')
        t.add(
            thead(
                tr(
                    [
                        th('Allele', style="padding: 5px"),
                        th('Sample', style="padding: 5px"),
                        th('Number of peptides', style="padding: 5px"),
                        th('Strong binders', style="padding: 5px"),
                        th('Weak binders', style="padding: 5px"),
                        th('Non-binders', style="padding: 5px")
                    ]
                )
            )
        )

        for allele in self.alleles:
            tablebody = tbody()
            for sample in self.samples:
                tablerow = tr()
                if sample == self.samples[0]:
                    tablerow.add(td(p(allele, style='writing-mode: vertical-rl;'
                                                    'font-weight: bold'),
                                    rowspan=len(self.samples),
                                    style="vertical-align : middle;text-align:center;"
                                    )
                                 )
                tablerow.add(td(sample))
                tablerow.add(td(self.peptide_numbers[sample]['total']))
                tablerow.add(
                    [
                        td(f"{self.peptide_numbers[sample][allele][strength]} "
                           f"({round(self.peptide_numbers[sample][allele][strength] * 100 / self.peptide_numbers[sample]['total'], 1)}%)")
                        for strength in ['Strong', 'Weak', 'Non-binder']
                    ]
                )
                tablebody.add(tablerow)
            t.add(tablebody)

        card = div(className='card', style='height: 100%')
        card.add(
            [
                div([b('Peptide Counts')], className='card-header'),
                div(div(t, className='table-responsive'), className='card-body')
            ]
        )
        return div(card, className=className)

    def gen_binding_histogram(self, className=None):
        def get_highest_binding(predictions):
            if 'Strong' in predictions.values:
                return 'Strong'
            elif 'Weak' in predictions.values:
                return 'Weak'
            else:
                return 'Non-binding'

        n_peps_fig = go.Figure()
        for sample in self.samples:
            counts_df = self.preds.loc[self.preds['Sample'] == sample, :]
            counts_df = counts_df.pivot(index='Peptide', columns='Allele', values='Binder')
            bindings = counts_df.apply(get_highest_binding, axis=1).values
            binders, counts = np.unique(bindings, return_counts=True)
            counts = [counts[list(binders).index('Strong')] if 'Strong' in binders else 0,
                      counts[list(binders).index('Weak')] if 'Weak' in binders else 0,
                      counts[list(binders).index('Non-binding')] if 'Non-binding' in binders else 0]
            binders = ['Strong', 'Weak', 'Non-binder']
            n_peps_fig.add_trace(go.Bar(x=binders, y=counts, name=sample))
        n_peps_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20),
                                 hovermode='x')
        n_peps_fig.update_yaxes(title_text='Number of peptides')
        n_peps_fig.update_xaxes(title_text='Binding strength')
        card = div(div(b('Binding Affinities'), className='card-header'), className='card')
        card.add(div(raw(n_peps_fig.to_html(full_html=False, include_plotlyjs='cdn')), className='card-body'))

        return div(card, className=className)

    def gen_length_histogram(self, className=None):
        len_dist = go.Figure()
        for sample in self.samples:
            lengths, counts = np.unique(self.preds.loc[self.preds['Sample'] == sample, 'Peptide'].str.len().values,
                                        return_counts=True)
            len_dist.add_trace(go.Bar(name=sample, x=lengths, y=counts))
        len_dist.update_layout(margin=dict(l=20, r=20, t=20, b=20),
                               hovermode='x')
        len_dist.update_yaxes(title_text='Number of peptides')
        len_dist.update_xaxes(title_text='Peptide length')
        card = div(div(b('Peptide Length Disctribution'), className='card-header'), className='card')
        card.add(div(raw(len_dist.to_html(full_html=False, include_plotlyjs='cdn')), className='card-body'))
        return div(card, className=className)

    def sample_heatmap(self, sample: str):
        ymax = np.max([self.peptide_numbers[sample]['total'] for sample in self.samples])
        pivot = self.preds.loc[self.preds['Sample'] == sample, :].pivot(index='Peptide', columns='Allele',
                                                                        values='Rank').astype(float)
        if self.mhc_class == 'I':
            pivot[pivot > 2.5] = 2.5
            colorscale = [[0, '#ef553b'], [0.4 / 2.5, '#ef553b'], [0.7 / 2.5, '#636efa'], [1.9 / 2.5, '#636efa'],
                          [2.2 / 2.5, 'rgba(99, 110, 250, 0)'], [1, 'rgba(99, 110, 250, 0)']]
        else:
            pivot[pivot > 12] = 12
            colorscale = [[0, '#ef553b'], [1.6 / 12, '#ef553b'], [2.4 / 12, '#636efa'], [9.8 / 12, '#636efa'],
                          [10.6 / 12, 'rgba(99, 110, 250, 0)'], [1, 'rgba(99, 110, 250, 0)']]
        data = pivot.sort_values(list(pivot.columns), ascending=True)

        if self.mhc_class == 'I':
            colorbar = dict(title='%Rank',
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
        fig.layout.title = sample
        fig.layout.plot_bgcolor = '#e5ecf6'
        fig.layout.margin = dict(l=20, r=20, t=20, b=20)
        fig.update_yaxes(range=[0, ymax],
                         title_text='Number of peptides')
        fig.update_xaxes(title_text='Allele')

        return raw(fig.to_html(full_html=False, include_plotlyjs='cdn'))

    def gen_heatmaps(self, className=None):
        ymax = np.max([self.peptide_numbers[sample]['total'] for sample in self.samples])
        heatmaps = div(className=f'row')
        for sample in self.samples:
            pivot = self.preds.loc[self.preds['Sample'] == sample, :].pivot(index='Peptide', columns='Allele',
                                                                  values='Rank').astype(float)
            if self.mhc_class == 'I':
                pivot[pivot > 2.5] = 2.5
                colorscale = [[0, '#ef553b'], [0.4 / 2.5, '#ef553b'], [0.7 / 2.5, '#636efa'], [1.9 / 2.5, '#636efa'],
                              [2.2 / 2.5, 'rgba(99, 110, 250, 0)'], [1, 'rgba(99, 110, 250, 0)']]
            else:
                pivot[pivot > 12] = 12
                colorscale = [[0, '#ef553b'], [1.6 / 12, '#ef553b'], [2.4 / 12, '#636efa'], [9.8 / 12, '#636efa'],
                              [10.6 / 12, 'rgba(99, 110, 250, 0)'], [1, 'rgba(99, 110, 250, 0)']]
            data = pivot.sort_values(list(pivot.columns), ascending=True)

            if self.mhc_class == 'I':
                colorbar = dict(title='%Rank',
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
            fig.layout.title = sample
            fig.layout.plot_bgcolor = '#e5ecf6'
            fig.layout.margin = dict(l=20, r=20, t=40, b=20)
            fig.update_yaxes(range=[0, ymax],
                             title_text='Number of peptides')
            fig.update_xaxes(title_text='Allele')

            heatmaps.add(
                div(raw(fig.to_html(full_html=False, include_plotlyjs='cdn')), className='col-4',  # NOTE HERE IS WHERE YOU SPECIFY WIDTH OF HEATMAPS IF I NEED TO CHANGE IT BACK TO COL-4
                    style="margin-left: auto; margin-right: auto")
            )

        card = div(className='card')
        card.add(div(b('Binding Specificity Heatmaps'), className='card-header'))
        card.add(div(heatmaps, className='container'))

        return div(card, className=className)

    def gen_venn_diagram(self, className=None):
        fig = venn_diagram(self.results)

        venn = div(className='card')
        with venn:
            div(b('Venn Diagram'), className='card-header')
            div(raw(fig.to_html(full_html=False, include_plotlyjs='cdn')), className='card-body')

        return div(venn, className=className)

    def gen_upset_plot(self, className=None):
        # total_peps = len([pep for s in self.results.samples for pep in s.peptides])
        total_peps = np.sum([len(s.peptides) for s in self.results.samples])
        data = from_contents({s.sample_name: set(s.peptides)
                              for s in self.results.samples})
        for intersection in data.index.unique():
            if len(data.loc[intersection, :])/total_peps < 0.005:
                data.drop(index=intersection, inplace=True)
        data['peptide_length'] = np.vectorize(len)(data['id'])
        n_sets = len(data.index.unique())
        if n_sets <= 100:  # Plot horizontal
            upset = UpSet(data,
                          sort_by='cardinality',
                          sort_categories_by=None,
                          show_counts=True,
                          totals_plot_elements=4,
                          intersection_plot_elements=10)
            upset.add_catplot(value='peptide_length', kind='boxen', color='gray')
            plot = upset.plot()
            plot['totals'].grid(False)
            ylim = plot['intersections'].get_ylim()[1]
            plot['intersections'].set_ylim((0, ylim * 1.1))
            for c in plot['intersections'].get_children():
                if isinstance(c, plotText):
                    text = c.get_text()
                    text = text.replace('\n', ' ')
                    c.set_text(text)
                    c.set_rotation('vertical')
                    pos = c.get_position()
                    pos = (pos[0], pos[1] + 0.02 * ylim)
                    c.set_position(pos)
        else:  # plot vertical
            upset = UpSet(data, subset_size='count',
                          orientation='vertical',
                          sort_by='cardinality',
                          sort_categories_by=None,
                          show_counts=True)
            upset.add_catplot(value='peptide_length', kind='boxen', color='gray')
            plot = upset.plot()
            lim = plot['intersections'].get_xlim()
            plot['intersections'].set_xlim([0, lim[1] * 1.6])
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
            plt.draw()
        upset_fig = f'{self.results.tmp_folder / "upsetplot.svg"}'
        plt.savefig(upset_fig, bbox_inches="tight")
        encoded_upset_fig = base64.b64encode(open(upset_fig, 'rb').read()).decode()
        card = div(className='card', style="height: 100%")
        card.add(div([b('UpSet Plot'), p('Only intersections > 0.5% are displayed')], className='card-header'))
        plot_body = div(img(src=f'data:image/svg+xml;base64,{encoded_upset_fig}',
                            className='img-fluid',
                            style=f'width: 100%; height: auto'),
                        className='card-body')
        card.add(plot_body)
        #if plot['intersections'].get_xlim()[1] > 2:
        #    className = 'col-12'
        return div(card, className=className)

    def logo_order(self):
        def cosine_similarity(x, y) -> int:
            x = np.array(x).flatten()
            y = np.array(y).flatten()
            return np.dot(x, y) / (np.sqrt(np.dot(x, x)) * np.sqrt(np.dot(y, y)))

        first_set = {}
        n_motifs = {}
        gibbs_peps = {}
        ordered_logos = {}
        for sample in self.samples:
            report = str(list(self.results.tmp_folder.glob(f'./{sample}_*/*_report.html'))[0])
            with open(report, 'r') as f:
                lines = ' '.join(f.readlines())
            n_motifs[sample] = (re.search('Identified ([0-9]*) sequence motifs', lines)[1])
            pep_groups_file = str(list(self.results.tmp_folder.glob(
                f'./{sample}_*/res/gibbs.{n_motifs[sample]}g.ds.out'))[0])
            with open(pep_groups_file, 'r') as f:
                pep_lines = f.readlines()[1:]
            gibbs_peps[sample] = {x: [] for x in range(int(n_motifs[sample]))}
            for line in pep_lines:
                line = [x for x in line.split(' ') if x != '']
                group = int(line[1])
                pep = line[3]
                gibbs_peps[sample][group].append(pep)
        ordered_logos['max_n_logos'] = np.max([int(n) for n in n_motifs.values()])
        sorted_samples = self.samples
        sorted_samples.sort(key=lambda x: int(n_motifs[x]), reverse=True)

        for sample in sorted_samples:
            matrices = list(self.results.tmp_folder.glob(f'./{sample}_*/matrices/gibbs*.mat'))
            matrices = [str(m) for m in matrices if f'of{n_motifs[sample]}' in str(m)]
            matrices.sort()

            np_matrices = [np.loadtxt(matrix, dtype=float, delimiter=' ', skiprows=2, usecols=range(2, 22)) for
                           matrix in matrices]
            if sample == sorted_samples[0]:
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
            ordered_logos[sample] = order
        return ordered_logos, gibbs_peps

    def sample_logos(self, sample: str, logo_orders: dict, gibbs_peptides: dict, className=None):

        motifs = div(className=className)
        n = logo_orders['max_n_logos']
        for sample in list(logo_orders.keys()):
            motifs_row = div(className='row')
            order = logo_orders[sample]
            image_width = np.floor(95 / n) if n > 3 else np.floor(95 / 4)
            p_df: pd.DataFrame = self.pep_binding_dict[sample]
            for i in order:
                if i is not None:
                    g_peps = set(gibbs_peptides[sample][i])
                    strong_binders = {allele: round(len(g_peps & set(p_df[p_df[allele] == "Strong"].index)) * 100 /
                                                    len(g_peps)) for allele in self.alleles}
                    non_binding_peps = [set(p_df[(p_df[allele] == "Non-binder") | (p_df[allele] == "Weak")].index) for allele in self.alleles]
                    non_binding_set = non_binding_peps[0]
                    for x in non_binding_peps[1:]:
                        non_binding_set = non_binding_set & x
                    non_binding_composition = round(len(non_binding_set & g_peps) * 100 / len(g_peps))
                    logo = logo_orders[i]
                    image_filename = logo
                    encoded_motif_image = base64.b64encode(open(image_filename, 'rb').read())
                    composition = "\n  ".join([str(a)+": "+str(strong_binders[a])+"%" for a in strong_binders.keys()])
                    motifs_row.add(
                        div(
                            [
                                img(src='data:image/png;base64,{}'.format(encoded_motif_image.decode()),
                                    style='width: 100%;'
                                          'display: block;'
                                          'margin-left: auto;'
                                          'margin-right: auto;'),
                                p(f'Peptides: {len(g_peps)}\n'
                                  f'Strong binders:\n'
                                  f'  {composition}\n'
                                  f'Non/weak binders: {non_binding_composition}%',
                                  style='white-space: pre'),
                                #p('Composition:'),
                                #*[p(f'{a}: {allele_composition[a]}%', style='margin-left: 10px')
                                #  for a in allele_composition.keys()],
                                #p(f'Non-binding: {non_binding_composition}%', style='margin-left: 10px')
                            ],
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
                else:
                    motifs_row.add(
                        div(
                            img(
                                src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==",
                                style=f'width: 100%;'
                                      f'display: block;'
                                      f'margin-left: auto;'
                                      f'margin-right: auto;'
                            ),
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
            motifs.add(
                div(
                    [
                        div(b(f'{sample} sequence motif(s)'),
                            className='card-header'),
                        div(motifs_row, className='card-body')
                    ],
                    className='card'
                )
            )
        return motifs

    #def sample_heatmap_and_logos(self, sample:str):


    def sequence_logos(self, className=None):
        def cosine_similarity(x, y) -> int:
            x = np.array(x).flatten()
            y = np.array(y).flatten()
            return np.dot(x, y) / (np.sqrt(np.dot(x, x)) * np.sqrt(np.dot(y, y)))

        motifs = div(className=className)
        first_set = {}
        n_motifs = {}
        gibbs_peps = {}
        for sample in self.samples:
            report = str(list(self.results.tmp_folder.glob(f'./{sample}_*/*_report.html'))[0])
            with open(report, 'r') as f:
                lines = ' '.join(f.readlines())
            n_motifs[sample] = (re.search('Identified ([0-9]*) sequence motifs', lines)[1])
            pep_groups_file = str(list(self.results.tmp_folder.glob(
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
        sorted_samples = self.samples
        sorted_samples.sort(key=lambda x: int(n_motifs[x]), reverse=True)

        for sample in sorted_samples:
            motifs_row = div(className='row')

            logos = list(self.results.tmp_folder.glob(f'./{sample}_*/logos/gibbs_logos_*.png'))
            logos = [str(l) for l in logos if f'of{n_motifs[sample]}' in str(l)]
            logos.sort()
            matrices = list(self.results.tmp_folder.glob(f'./{sample}_*/matrices/gibbs*.mat'))
            matrices = [str(m) for m in matrices if f'of{n_motifs[sample]}' in str(m)]
            matrices.sort()

            np_matrices = [np.loadtxt(matrix, dtype=float, delimiter=' ', skiprows=2, usecols=range(2, 22)) for
                           matrix in matrices]
            if sample == sorted_samples[0]:
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
            p_df: pd.DataFrame = self.pep_binding_dict[sample]
            for i in order:
                if i is not None:
                    g_peps = set(gibbs_peps[sample][i])
                    strong_binders = {allele: round(len(g_peps & set(p_df[p_df[allele] == "Strong"].index)) * 100 /
                                                    len(g_peps)) for allele in self.alleles}
                    non_binding_peps = [set(p_df[(p_df[allele] == "Non-binder") | (p_df[allele] == "Weak")].index) for allele in self.alleles]
                    non_binding_set = non_binding_peps[0]
                    for x in non_binding_peps[1:]:
                        non_binding_set = non_binding_set & x
                    non_binding_composition = round(len(non_binding_set & g_peps) * 100 / len(g_peps))
                    logo = logos[i]
                    image_filename = logo
                    encoded_motif_image = base64.b64encode(open(image_filename, 'rb').read())
                    composition = "\n  ".join([str(a)+": "+str(strong_binders[a])+"%" for a in strong_binders.keys()])
                    motifs_row.add(
                        div(
                            [
                                img(src='data:image/png;base64,{}'.format(encoded_motif_image.decode()),
                                    style='width: 100%;'
                                          'display: block;'
                                          'margin-left: auto;'
                                          'margin-right: auto;'),
                                p(f'Peptides: {len(g_peps)}\n'
                                  f'Strong binders:\n'
                                  f'  {composition}\n'
                                  f'Non/weak binders: {non_binding_composition}%',
                                  style='white-space: pre'),
                                #p('Composition:'),
                                #*[p(f'{a}: {allele_composition[a]}%', style='margin-left: 10px')
                                #  for a in allele_composition.keys()],
                                #p(f'Non-binding: {non_binding_composition}%', style='margin-left: 10px')
                            ],
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
                else:
                    motifs_row.add(
                        div(
                            img(
                                src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==",
                                style=f'width: 100%;'
                                      f'display: block;'
                                      f'margin-left: auto;'
                                      f'margin-right: auto;'
                            ),
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
            motifs.add(
                div(
                    [
                        div(b(f'{sample} sequence motif(s)'),
                            className='card-header'),
                        div(motifs_row, className='card-body')
                    ],
                    className='card'
                )
            )
        return motifs

    def supervised_sequence_logos(self, className=None):

        motifs = div(className=className)
        first_set = {}
        n_motifs = {}
        gibbs_peps = {}
        for sample in self.samples:
            for allele in self.alleles + ['unannotated']:
                if self.results.supervised_gibbs_directories[sample][allele] is not None:
                    report = str(list(self.results.tmp_folder.glob(f'./{allele}_{sample}_*/*_report.html'))[0])
                    with open(report, 'r') as f:
                        lines = ' '.join(f.readlines())
                    n_motifs[f'{allele}_{sample}'] = (re.search('Identified ([0-9]*) sequence motifs', lines)[1])
                    pep_groups_file = str(list(self.results.tmp_folder.glob(
                        f'./{allele}_{sample}_*/res/gibbs.{n_motifs[f"{allele}_{sample}"]}g.ds.out'))[0])
                    with open(pep_groups_file, 'r') as f:
                        pep_lines = f.readlines()[1:]
                    gibbs_peps[f'{allele}_{sample}'] = {x: [] for x in range(int(n_motifs[f"{allele}_{sample}"]))}
                    for line in pep_lines:
                        line = [x for x in line.split(' ') if x != '']
                        group = int(line[1])
                        pep = line[3]
                        gibbs_peps[f'{allele}_{sample}'][group].append(pep)

        max_n_motifs = np.max([int(n) for n in n_motifs.values()])
        image_width = np.floor(95 / (len(self.alleles) + max_n_motifs))\
            if (len(self.alleles) + max_n_motifs) > 3 else np.floor(95 / 4)
        for sample in self.samples:
            motifs_row = div(className='row')
            for allele in self.alleles:
                if self.results.supervised_gibbs_directories[sample][allele]:
                    logo = str(Path(self.results.supervised_gibbs_directories[sample][allele])/'logos'/'gibbs_logos_1of1-001.png')
                    encoded_motif_image = base64.b64encode(open(logo, 'rb').read())
                    motifs_row.add(
                        div(
                            [
                                b(f'{allele}'),
                                img(src='data:image/png;base64,{}'.format(encoded_motif_image.decode()),
                                    style='width: 100%;'
                                          'display: block;'
                                          'margin-left: auto;'
                                          'margin-right: auto;'),
                                p(f'Peptides: {len(gibbs_peps[f"{allele}_{sample}"][0])}\n'),
                            ],
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
                else:  # there were not enough peptides to cluster
                    motifs_row.add(
                        div(
                            [
                                b(f'{allele}'),
                                p('Too few peptides to cluster')
                            ],
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
            # now the unannotated peptides
            if self.results.supervised_gibbs_directories[sample]['unannotated']:
                logos = list((Path(self.results.supervised_gibbs_directories[sample]['unannotated'])/'logos')
                             .glob(f'*of{n_motifs["unannotated_"+sample]}-001.png'))
                logos = [str(x) for x in logos]
                logos.sort()
                group = 1
                for x in range(max_n_motifs):
                    if x < len(logos):
                        logo = logos[x]
                        encoded_motif_image = base64.b64encode(open(logo, 'rb').read())
                        motifs_row.add(
                            div(
                                [
                                    b(f'Unannotated group {group}'),
                                    img(src='data:image/png;base64,{}'.format(encoded_motif_image.decode()),
                                        style='width: 100%;'
                                              'display: block;'
                                              'margin-left: auto;'
                                              'margin-right: auto;'),
                                    p(f'Peptides: {len(gibbs_peps[f"unannotated_{sample}"][x])}\n'),
                                ],
                                style=f'width: {image_width}%;'
                                      f'display: block;'
                                      f'margin-left: auto;'
                                      f'margin-right: auto;'
                                      f'font-size: 10pt'
                            )
                        )
                        group += 1
                    else:
                        motifs_row.add(
                            div(
                                img(
                                    src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==",
                                    style=f'width: 100%;'
                                          f'display: block;'
                                          f'margin-left: auto;'
                                          f'margin-right: auto;'
                                ),
                                style=f'width: {image_width}%;'
                                      f'display: block;'
                                      f'margin-left: auto;'
                                      f'margin-right: auto;'
                                      f'font-size: 10pt'
                            )
                        )
            motifs.add(
                div(
                    [
                        div(b(f'{sample} sequence motif(s)'),
                            className='card-header'),
                        div(motifs_row, className='card-body')
                    ],
                    className='card'
                )
            )
        return motifs

    def supervised_sequence_logos_and_heatmaps(self, className=None):

        motifs = div(className=className)
        first_set = {}
        n_motifs = {}
        gibbs_peps = {}
        for sample in self.samples:
            for allele in self.alleles + ['unannotated']:
                if self.results.supervised_gibbs_directories[sample][allele] is not None:
                    report = str(list(self.results.tmp_folder.glob(f'./{allele}_{sample}_*/*_report.html'))[0])
                    with open(report, 'r') as f:
                        lines = ' '.join(f.readlines())
                    n_motifs[f'{allele}_{sample}'] = (re.search('Identified ([0-9]*) sequence motifs', lines)[1])
                    pep_groups_file = str(list(self.results.tmp_folder.glob(
                        f'./{allele}_{sample}_*/res/gibbs.{n_motifs[f"{allele}_{sample}"]}g.ds.out'))[0])
                    with open(pep_groups_file, 'r') as f:
                        pep_lines = f.readlines()[1:]
                    gibbs_peps[f'{allele}_{sample}'] = {x: [] for x in range(int(n_motifs[f"{allele}_{sample}"]))}
                    for line in pep_lines:
                        line = [x for x in line.split(' ') if x != '']
                        group = int(line[1])
                        pep = line[3]
                        gibbs_peps[f'{allele}_{sample}'][group].append(pep)

        max_n_motifs = np.max([int(n) for n in n_motifs.values()])
        image_width = np.floor(95 / (len(self.alleles) + max_n_motifs + 1))
        for sample in self.samples:
            motifs_row = div(className='row')
            motifs_row.add(div(self.sample_heatmap(sample), style=f'width: {image_width}%;'
                                                                  'display: block;'
                                                                  'margin-left: auto;'
                                                                  'margin-right: auto;'))
            for allele in self.alleles:
                if self.results.supervised_gibbs_directories[sample][allele]:
                    logo = str(Path(self.results.supervised_gibbs_directories[sample][allele])/'logos'/'gibbs_logos_1of1-001.png')
                    encoded_motif_image = base64.b64encode(open(logo, 'rb').read())
                    motifs_row.add(
                        div(
                            [
                                b(f'{allele}'),
                                img(src='data:image/png;base64,{}'.format(encoded_motif_image.decode()),
                                    style='width: 100%;'
                                          'display: block;'
                                          'margin-left: auto;'
                                          'margin-right: auto;'),
                                p(f'Peptides: {len(gibbs_peps[f"{allele}_{sample}"][0])}\n'),
                            ],
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
                else:  # there were not enough peptides to cluster
                    motifs_row.add(
                        div(
                            [
                                b(f'{allele}'),
                                p('Too few peptides to cluster')
                            ],
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
            # now the unannotated peptides
            logos = list((Path(self.results.supervised_gibbs_directories[sample]['unannotated'])/'logos')
                         .glob(f'*of{n_motifs["unannotated_"+sample]}-001.png'))
            logos = [str(x) for x in logos]
            logos.sort()
            group = 1
            for x in range(max_n_motifs):
                if x < len(logos):
                    logo = logos[x]
                    encoded_motif_image = base64.b64encode(open(logo, 'rb').read())
                    motifs_row.add(
                        div(
                            [
                                b(f'Unannotated group {group}'),
                                img(src='data:image/png;base64,{}'.format(encoded_motif_image.decode()),
                                    style='width: 100%;'
                                          'display: block;'
                                          'margin-left: auto;'
                                          'margin-right: auto;'),
                                p(f'Peptides: {len(gibbs_peps[f"unannotated_{sample}"][x])}\n'),
                            ],
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
                    group += 1
                else:
                    motifs_row.add(
                        div(
                            img(
                                src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==",
                                style=f'width: 100%;'
                                      f'display: block;'
                                      f'margin-left: auto;'
                                      f'margin-right: auto;'
                            ),
                            style=f'width: {image_width}%;'
                                  f'display: block;'
                                  f'margin-left: auto;'
                                  f'margin-right: auto;'
                                  f'font-size: 10pt'
                        )
                    )
            motifs.add(
                div(
                    [
                        div(b(f'{sample} sequence motif(s)'),
                            className='card-header'),
                        div(motifs_row, className='card-body')
                    ],
                    className='card'
                )
            )
        return motifs

    def make_report(self):
        doc = document(title='MhcQcPipe Report')
        with doc.head:
            link(rel="stylesheet", href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css",
                 integrity="sha384-9aIt2nRpC12Uk9gS9baDl411NQApFmC26EwAOH8WgZl5MYYxFfc+NcPb1dKGj7Sk",
                 crossorigin="anonymous")
            link(rel="stylesheet", href='/home/labcaron/Projects/MhcQcPipe/MhcQcPipe/assets/report_style.css')
            #script(type='text/javascript', src='https://cdn.plot.ly/plotly-latest.min.js')
            script(src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js")
            script(src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.0/js/bootstrap.min.js")
        with doc:
            with div(id='layout', className='container', style='max-width: 1600px;'
                                                               'min-width: 800px;'
                                                               'margin-top: 20px;'
                                                               'margin-bottom: 20px'):
                with div(className='row'):
                    with div(className='col-12', style='display: flex; height: 60px'):
                        h2('MhcQcPipe Report',
                           style="background-color:#4CAF50; padding:5px; color:white; border-radius: 4px; width: 100%")
                        self.lab_logo
                with div(className='row'):
                    with div(className='col-6' if len(self.samples) > 1 else 'col-12'):
                        p([b('Date: '), f'{str(datetime.now().date())}'])
                        p([b('Submitted by: '), f'{self.submitter_name if self.submitter_name else "Anonymous"}'])
                        with div(style='display: flex'):
                            b('Desciption of experiment:', style='margin-right: 5px; white-space: nowrap')
                            p(self.experiment_description if self.experiment_description else 'None provided')
                        p([b('Alleles: '), ', '.join(self.results.alleles)])

                        b('Samples:')
                        div(
                            [
                                p('\n '.join(
                                    [
                                        f'\t{name}: {description}' if description else f'\t{name}' for name, description in
                                        self.results.descriptions.items()
                                    ]
                                ), style="white-space: pre"
                                )
                            ]
                        )
                        b('Analysis details:')
                        if self.mhc_class == 'I':
                            gibbs_lengths = '\n  '.join([f'{sample}: {self.results.gibbs_cluster_lengths[sample]} mers'
                                                         for sample in self.samples])
                            gibbs_description = f', except unsupervised GibbsCluster which used the following length ' \
                                                f'peptides:\n\t{gibbs_lengths}'
                        else:
                            gibbs_description = ''
                        p(f'Peptides for all steps subset by length to between '
                          f'{self.results.min_length} & {self.results.max_length} mers{gibbs_description}',
                          style="white-space: pre-wrap")
                    if len(self.samples) > 1:
                        self.gen_upset_plot(className='col-6')
                hr()
                with div(className='row'):
                    pep_table = self.gen_peptide_tables(className='col-12')
                    #if len(self.samples) > 1:
                        #hor_rul = hr(className="hidden-hr")
                        #plot_holder = div(className='col-6')
                        #upset_plot = self.gen_upset_plot(className='col-4')
                        #plot_holder.add(upset_plot)
                        #if upset_plot['class'] == 'col-12':
                        #    plot_holder['class'] = 'row'
                        #    hor_rul['class'] = 'not-hidden-hr'
                        #    pep_table['class'] = 'col-12'
                hr()
                with div(className='row'):
                    self.gen_binding_histogram(className='col-6')
                    self.gen_length_histogram(className='col-6')
                hr()
                '''
                if len(self.samples) > 1:
                    with div(className='row'):
                        self.gen_venn_diagram(className='col-12')
                    hr()
                '''

                with div(className='row'):
                    with div(className='col-12'):
                        h3('Binding Heatmaps')
                with div(className='row'):
                    self.gen_heatmaps(className='col-12')
                hr()
                with div(className='row'):
                    with div(className='col-8'):
                        h3('Sequence Logos (clustering from GibbsCluster)')
                        div([
                            div(style='width: 18px; height: 18px; background-color: #21d426; border-radius: 3px'),
                            p('Polar', style="margin-left: 5px; margin-right: 10px"),
                            # div(style='width: 18px; height: 18px; background-color: #d41cbf; border-radius: 3px'),
                            # p('Neutral', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #0517bd; border-radius: 3px'),
                            p('Basic', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #d40a14; border-radius: 3px'),
                            p('Acidic', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #000000; border-radius: 3px'),
                            p('Hydrophobic', style="margin-left: 5px; margin-right: 10px")
                        ], style="display: flex; pad: 5px"),
                with div(className='row'):
                    with div(className='col-12'):
                        with ul(className='nav nav-tabs', id='myTab') as navtab:
                            navtab['role'] = 'tablist'
                            with li(className='nav-item') as navitem:
                                navitem['role'] = 'presentation'
                                with a("Unsupervised GibbsCluster", className="nav-link active") as navlink:
                                    navlink['id'] = 'plain-gibbs-tab'
                                    navlink['data-toggle'] = 'tab'
                                    navlink['role'] = 'tab'
                                    navlink['aria-controls'] = 'plain-gibbs'
                                    navlink['aria-selected'] = 'true'
                                    navlink['href'] = '#plain-gibbs'
                            with li(className='nav-item') as navitem:
                                navitem['role'] = 'presentation'
                                with a("Allele-specific GibbsCluster", className="nav-link") as navlink:
                                    navlink['id'] = 'allele-gibbs-tab'
                                    navlink['data-toggle'] = 'tab'
                                    navlink['role'] = 'tab'
                                    navlink['aria-controls'] = 'allele-gibbs'
                                    navlink['aria-selected'] = 'false'
                                    navlink['href'] = '#allele-gibbs'
                        with div(className='tab-content', id='myTabContent'):
                            logos = self.sequence_logos(className='tab-pane fade show active')
                            logos['id'] = 'plain-gibbs'
                            logos['role'] = 'tabpanel'
                            logos['aria-labelledby'] = 'plain-gibbs-tab'

                            allele_logos = self.supervised_sequence_logos(className='tab-pane fade')
                            allele_logos['id'] = 'allele-gibbs'
                            allele_logos['role'] = 'tabpanel'
                            allele_logos['aria-labelledby'] = 'allele-gibbs-tab'
                '''
                #hr()
                #with div(className='row'):
                    with div(className='col-8'):
                        h3('Sequence Logos (clustering from GibbsCluster)')
                        div([
                            div(style='width: 18px; height: 18px; background-color: #21d426; border-radius: 3px'),
                            p('Polar', style="margin-left: 5px; margin-right: 10px"),
                            #div(style='width: 18px; height: 18px; background-color: #d41cbf; border-radius: 3px'),
                            #p('Neutral', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #0517bd; border-radius: 3px'),
                            p('Basic', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #d40a14; border-radius: 3px'),
                            p('Acidic', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #000000; border-radius: 3px'),
                            p('Hydrophobic', style="margin-left: 5px; margin-right: 10px")
                        ], style="display: flex; pad: 5px"),
                with div(className='row'):
                    with div(className='col-4'):
                        self.gen_heatmaps(className='col-12')

                    with div(className='col-8'):
                        with ul(className='nav nav-tabs', id='myTab') as navtab:
                            navtab['role'] = 'tablist'
                            with li(className='nav-item') as navitem:
                                navitem['role'] = 'presentation'
                                with a("Unsupervised GibbsCluster", className="nav-link active") as navlink:
                                    navlink['id'] = 'plain-gibbs-tab'
                                    navlink['data-toggle'] = 'tab'
                                    navlink['role'] = 'tab'
                                    navlink['aria-controls'] = 'plain-gibbs'
                                    navlink['aria-selected'] = 'true'
                                    navlink['href'] = '#plain-gibbs'
                            with li(className='nav-item') as navitem:
                                navitem['role'] = 'presentation'
                                with a("Allele-specific GibbsCluster", className="nav-link") as navlink:
                                    navlink['id'] = 'allele-gibbs-tab'
                                    navlink['data-toggle'] = 'tab'
                                    navlink['role'] = 'tab'
                                    navlink['aria-controls'] = 'allele-gibbs'
                                    navlink['aria-selected'] = 'false'
                                    navlink['href'] = '#allele-gibbs'
                        with div(className='tab-content', id='myTabContent'):
                            logos = self.sequence_logos(className='tab-pane fade show active')
                            logos['id'] = 'plain-gibbs'
                            logos['role'] = 'tabpanel'
                            logos['aria-labelledby'] = 'plain-gibbs-tab'

                            allele_logos = self.supervised_sequence_logos_and_heatmaps(className='tab-pane fade')
                            allele_logos['id'] = 'allele-gibbs'
                            allele_logos['role'] = 'tabpanel'
                            allele_logos['aria-labelledby'] = 'allele-gibbs-tab'
                '''

                    #self.sequence_logos(className='col-12')
                    #self.supervised_sequence_logos(className='col-12')

        loc = f'{str(self.results.tmp_folder/"report.html")}'
        with open(loc, 'w') as f:
            f.write(doc.render())
        return loc



def venn_diagram(analysis_results: MhcToolHelper) -> go.Figure:
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
