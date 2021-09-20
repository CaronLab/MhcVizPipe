# -*- coding: utf-8 -*-
from datetime import datetime
from MhcVizPipe.Tools.cl_tools import MhcToolHelper
import plotly.graph_objects as go
import numpy as np
from MhcVizPipe.Tools import plotly_venn
import base64
import pandas as pd
from upsetplotly import UpSetPlotly
from pathlib import Path
from dominate.util import raw
from dominate.tags import *
from dominate import document
import PlotlyLogo.logo as pl
from MhcVizPipe.parameters import ROOT_DIR
import concurrent.futures
from MhcVizPipe.parameters import Parameters
from MhcVizPipe import __version__
from html import unescape


def wrap_plotly_fig(fig: go.Figure, width: str = '100%', height: str = '100%'):
    if 'px' in width:
        fig = fig.to_html(include_plotlyjs=False, full_html=False, default_height=height, default_width=width)
        return div(raw(fig), style=f'width: {width}')
    else:
        fig = fig.to_html(include_plotlyjs=False, full_html=False, default_height=height, default_width='100%')
        return div(raw(fig), style=f'width: {width}')


def make_logo(cores_file: str):
    return pl.logo_from_alignment(cores_file, plot=False, return_fig=True)


def ploty_fig_to_image(fig: go.Figure, width: int = 360, height: int = 360):
    fig_data = fig.to_image(format='svg', width=width, height=height).decode()
    return img(src=f'data:image/svg+xml;base64,{fig_data}',
               className='img-fluid',
               style=f'width: 100%; height: auto')


def get_plotlyjs():
    fig = go.Figure()
    fig = fig.to_html(include_plotlyjs=True, full_html=False)
    plotlyjs = fig[fig.index("<script"):fig.rindex("<div id=")] + "</div></script>"
    return raw(plotlyjs)


class mhc_report:
    def __init__(self,
                 analysis_results: MhcToolHelper,
                 mhc_class: str,
                 cpus: int,
                 experiment_description: str = None,
                 submitter_name: str = None,
                 experimental_info=None
                 ):
        self.results = analysis_results
        self.mhc_class = mhc_class
        self.experiment_description = experiment_description
        self.submitter_name = submitter_name
        self.sample_alleles = analysis_results.sample_alleles
        self.preds = analysis_results.binding_predictions.drop_duplicates()
        self.samples = list(self.preds['Sample'].unique())
        self.experimental_info = experimental_info
        self.cpus = cpus
        self.parameters = Parameters()

        peptide_numbers = {}
        for sample in self.results.samples:
            peptide_numbers[sample] = {}
            peptide_numbers[sample]['original_total'] = len(set(self.results.original_peptides[sample]))
            peptide_numbers[sample]['within_length'] = len(set(self.results.sample_peptides[sample]))
            for allele in self.sample_alleles[sample]:
                peptide_numbers[sample][allele] = {}
                for strength in ['Strong', 'Weak', 'Non-binder']:
                    peptide_numbers[sample][allele][strength] = len(
                        self.preds.loc[(self.preds['Sample'] == sample) &
                                       (self.preds['Allele'] == allele) &
                                       (self.preds['Binder'] == strength), 'Peptide'].unique()
                    )
        self.peptide_numbers = peptide_numbers

        pep_binding_dict = {}
        for sample in self.results.samples:
            counts_df = self.preds.loc[self.preds['Sample'] == sample, :]
            counts_df = counts_df.pivot(index='Peptide', columns='Allele', values='Binder')
            pep_binding_dict[sample] = counts_df.copy(deep=True)
        self.pep_binding_dict = pep_binding_dict
        self.fig_dir = self.results.tmp_folder / 'figures'
        if not self.fig_dir.exists():
            self.fig_dir.mkdir()
        (self.fig_dir / 'heatmaps_w_common_y_axis').mkdir()
        self.metrics = {}
        self.calculate_metrics()

    def calculate_metrics(self, write_file: bool = True):
        # get counts of binders and non-binders
        def get_highest_binding(predictions):
            if 'Strong' in predictions.values:
                return 'Strong'
            elif 'Weak' in predictions.values:
                return 'Weak'
            else:
                return 'Non-binding'

        # mix two colors, input must be tuples representing RGB colors
        # adapted from here: https://stackoverflow.com/questions/25668828/how-to-create-colour-gradient-in-python
        def color_fader(c1, c2, mix=0):  # fade (linear interpolate) from color c1 (at mix=0) to c2 (mix=1)
            c1 = np.asarray(c1)
            c2 = np.asarray(c2)
            mixed = (1 - mix) * c1 + mix * c2
            return f'rgb{tuple(mixed)}'

        good_color = (100, 246, 52)
        bad_color = (255, 35, 75)

        def score_color(score):
            return color_fader(bad_color, good_color, score)

        min_len = self.results.min_length
        max_len = self.results.max_length
        self.metrics['acceptable_length_key'] = f'n_peptides_{min_len}-{max_len}_mers'

        for sample in self.results.samples:
            all_peps = list(set(self.results.original_peptides[sample]))  # all peptides
            n_all_peps = len(all_peps)  # number of peptides in original list
            lengths = np.vectorize(len)(all_peps)  # lengths of those peptides
            n_with_acceptable_length = np.sum(
                (lengths >= self.results.min_length) & (lengths <= self.results.max_length))

            counts_df = self.preds.loc[self.preds['Sample'] == sample, :]
            counts_df = counts_df.pivot(index='Peptide', columns='Allele', values='Binder')
            bindings = counts_df.apply(get_highest_binding, axis=1).values
            binders, counts = np.unique(bindings, return_counts=True)
            binder_counts = {binder: count for binder, count in zip(list(binders), (list(counts)))}
            n_binders = n_with_acceptable_length - binder_counts['Non-binding']
            lf_score = round(n_with_acceptable_length / n_all_peps, 2)
            bf_score = round(n_binders / n_with_acceptable_length, 2)
            lf_color = score_color(lf_score)
            bf_color = score_color(bf_score)

            self.metrics[sample] = {}
            self.metrics[sample]['n_peptides'] = n_all_peps
            self.metrics[sample][self.metrics['acceptable_length_key']] = n_with_acceptable_length
            self.metrics[sample]['lf_score'] = lf_score
            self.metrics[sample]['bf_score'] = bf_score
            self.metrics[sample]['lf_color'] = lf_color
            self.metrics[sample]['bf_color'] = bf_color

        if write_file:
            with open(str(self.results.tmp_folder / 'sample_metrics.txt'), 'w') as f:
                f.write(f'sample\tn_peptides\tn_peptides_{min_len}-{max_len}_mers\tlength_score\tbinding_score\n')
                for sample in self.results.samples:
                    f.write(f'{sample}\t')
                    f.write(f"{self.metrics[sample]['n_peptides']}\t")
                    f.write(f"{self.metrics[sample][f'n_peptides_{min_len}-{max_len}_mers']}\t")
                    f.write(f"{self.metrics[sample]['lf_score']}\t")
                    f.write(f"{self.metrics[sample]['bf_score']}\n")

    def lab_logo(self):
        lab_logo = base64.b64encode(
            open(str(Path(ROOT_DIR) / 'assets/logo_CARONLAB_horizontal.jpg'), 'rb').read()).decode()
        return img(src=f'data:image/jpg;base64,{lab_logo}', className='img-fluid',
                   style="max-width:100%; max-height:100%; margin-left: 10px;"
                         "margin-bottom: 8px")  # can add opacity: 50% to style if desired

    def exp_info(self, className=None):
        info_div = div(className=className, style='margin: 0')
        if isinstance(self.experimental_info, str):
            info = self.experimental_info.split('\n')
        else:
            info = self.experimental_info

        if info:
            for i in info:
                if ':' not in i:
                    continue
                idx = i.index(':')
                field = i[:idx + 1].strip()
                desc = i[idx + 1:].strip()
                if not desc:
                    continue
                info_div.add(
                    p(
                        [
                            b(field + ' '),
                            desc
                        ]
                    )
                )
        return info_div

    def quick_quality_table(self, className=None):
        t = table(className=f'table table-hover table-bordered',
                  style="text-align: center",
                  id='quality-table')
        t.add(
            thead(
                tr(
                    [
                        th('Sample', style="padding: 5px"),
                        th(f'Total peptides', style="padding: 5px"),
                        th(f'Peptides between {self.results.min_length}-{self.results.max_length} mers', style="padding: 5px"),
                        th('LF Score', style="padding: 5px"),
                        th('BF Score', style="padding: 5px"),
                    ]
                )
            )
        )
        tablebody = tbody()
        for sample in self.results.samples:
            tablerow = tr()
            tablerow.add(td(sample, style='word-break: break-word'))
            tablerow.add(td(self.metrics[sample]['n_peptides']))
            tablerow.add(td(self.metrics[sample][self.metrics['acceptable_length_key']]))
            tablerow.add(td(f'{self.metrics[sample]["lf_score"]}',
                            style=f'background-color: {self.metrics[sample]["lf_color"]}'))
            tablerow.add(td(f'{self.metrics[sample]["bf_score"]}',
                            style=f'background-color: {self.metrics[sample]["bf_color"]}'))
            tablebody.add(tablerow)

        t.add(tablebody)
        return div(t, className=f'table-responsive {className}' if className else 'table-responsive')

    def gen_peptide_tables(self, className=None, return_card=False):

        t = table(className=f'table table-hover table-bordered',
                  style="text-align: center",
                  id='peptidetable')
        t.add(
            thead(
                tr(
                    [
                        th('Sample', style="padding: 5px"),
                        th('Total peptides', style="padding: 5px"),
                        th('Allele', style="padding: 5px"),
                        th('Strong binders', style="padding: 5px"),
                        th('Weak binders', style="padding: 5px"),
                        th('Non-binders', style="padding: 5px")
                    ]
                )
            )
        )

        for sample in self.results.samples:
            tablebody = tbody()
            for allele in self.sample_alleles[sample]:
                tablerow = tr()
                if allele == self.sample_alleles[sample][0]:
                    tablerow.add(td(p(sample, style='word-break: break-word'),
                                    rowspan=len(self.sample_alleles[sample]),
                                    style="vertical-align : middle;text-align:center;"
                                    )
                                 )
                    tablerow.add(td(self.peptide_numbers[sample]['within_length'],
                                    rowspan=len(self.sample_alleles[sample])))
                tablerow.add(td(allele, style="word-break: break-word"))
                tablerow.add(
                    [
                        td(f"{self.peptide_numbers[sample][allele][strength]} "
                           f"({round(self.peptide_numbers[sample][allele][strength] * 100 / self.peptide_numbers[sample]['within_length'], 1)}%)")
                        for strength in ['Strong', 'Weak', 'Non-binder']
                    ]
                )
                tablebody.add(tablerow)
            t.add(tablebody)
        if return_card:
            card = div(className='card', style='height: 100%')
            card.add(
                [
                    div([b('Peptide Counts')], className='card-header'),
                    div(div(t, className='table-responsive'), className='card-body')
                ]
            )
            return div(card, className=className)
        else:
            return div(t, className=f'table-responsive {className}' if className else 'table-responsive')

    def gen_binding_histogram(self, className=None):
        def get_highest_binding(predictions):
            if 'Strong' in predictions.values:
                return 'Strong'
            elif 'Weak' in predictions.values:
                return 'Weak'
            else:
                return 'Non-binding'

        n_peps_fig = go.Figure()
        for sample in self.results.samples:
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
                                 hovermode='x',
                                 legend=dict(orientation="h",
                                             yanchor="bottom",
                                             y=1.02,
                                             xanchor="right",
                                             x=1,
                                             bgcolor="rgba(255, 255, 255, 0.8)"),
                                 font_color='#212529'
                                 )
        n_peps_fig.layout.title.xanchor = 'center'
        n_peps_fig.update_yaxes(title_text='Number of peptides')
        n_peps_fig.update_xaxes(title_text='Binding strength')
        n_peps_fig.update_xaxes(titlefont={'size': 16}, tickfont={'size': 14})
        n_peps_fig.update_yaxes(titlefont={'size': 16}, tickfont={'size': 14})
        n_peps_fig.write_image(str(self.fig_dir / 'binding_histogram.pdf'), engine="kaleido")
        card = div(div(b('Binding Affinities'), className='card-header'), className='card')
        card.add(div(raw(n_peps_fig.to_html(full_html=False, include_plotlyjs=False)), className='card-body'))

        return div(card, className=className)

    def gen_length_histogram(self, className=None):
        len_dist = go.Figure()
        for sample in self.results.samples:
            peps = list(set(self.results.original_peptides[sample]))
            peps = [pep for pep in peps if len(pep) <= 30]
            lengths, counts = np.unique(np.vectorize(len)(peps), return_counts=True)
            len_dist.add_trace(go.Bar(name=sample, x=lengths, y=counts))
        len_dist.update_layout(margin=dict(l=20, r=20, t=20, b=20),
                               hovermode='x',
                               legend=dict(orientation="h",
                                           yanchor="bottom",
                                           y=1.02,
                                           xanchor="right",
                                           x=1,
                                           bgcolor="rgba(255, 255, 255, 0.8)"),
                               font_color='#212529'
                               )
        len_dist.layout.title.xanchor = 'center'
        len_dist.update_yaxes(title_text='Number of peptides')
        len_dist.update_xaxes(title_text='Peptide length')
        len_dist.update_xaxes(titlefont={'size': 16}, tickfont={'size': 14})
        len_dist.update_yaxes(titlefont={'size': 16}, tickfont={'size': 14})
        len_dist.layout.xaxis.dtick = 1
        len_dist.update_xaxes(fixedrange=True)
        len_dist.write_image(str(self.fig_dir / 'length_distribution.pdf'), engine="kaleido")
        card = div(p([b('Peptide Length Distribution '), '(maximum of 30 mers)'], className='card-header'),
                   className='card')
        card.add(div(raw(len_dist.to_html(full_html=False, include_plotlyjs=False)), className='card-body'))
        return div(card, className=className)

    def sample_heatmap(self, sample: str):
        #ymax = np.max([self.peptide_numbers[sample]['total'] for sample in self.samples])
        pivot = self.preds.loc[self.preds['Sample'] == sample, :].pivot(index='Peptide', columns='Allele',
                                                                        values='Rank').astype(float)
        if self.mhc_class == 'I':
            pivot[pivot > 2.5] = 2.5
            colorscale = [[0, '#ef553b'], [2.0 / 2.5, '#636efa'], [2.1 / 2.5, '#fdffc2'], [1, '#fdffc2']]
        else:
            pivot[pivot > 12] = 12
            colorscale = [[0, '#ef553b'], [10 / 12, '#636efa'], [10.5 / 12, '#fdffc2'], [1, '#fdffc2']]
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
            colorbar=colorbar,
            #xgap=1
        ))
        fig.update_layout(font_color='#212529'
                          )
        fig.layout.plot_bgcolor = '#ffffff'
        fig.layout.margin = dict(l=20, r=20, t=20, b=20)
        fig.update_yaxes(title_text='Peptides')
        fig.update_xaxes(title_text='Allele')
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        fig.write_image(str(self.fig_dir / f'{sample}_heatmap.pdf'), engine="kaleido")

        return fig

    def gen_heatmaps(self, className=None):
        ymax = np.max([self.peptide_numbers[sample]['within_length'] for sample in self.results.samples])
        ymax += 0.01 * ymax
        heatmaps = div(className=f'row', style='margin: 10px;'
                                               'border-color: #dee2e6;'
                                               'border-width: 1px;'
                                               'border-style: solid')
        for sample in self.results.samples:
            pivot = self.preds.loc[self.preds['Sample'] == sample, :].pivot(index='Peptide', columns='Allele',
                                                                  values='Rank').astype(float)
            if self.mhc_class == 'I':
                pivot[pivot > 2.5] = 2.5
                colorscale = [[0, '#ef553b'], [2.0 / 2.5, '#636efa'], [2.1 / 2.5, '#fdffc2'], [1, '#fdffc2']]
            else:
                pivot[pivot > 12] = 12
                colorscale = [[0, '#ef553b'], [10 / 12, '#636efa'], [10.5 / 12, '#fdffc2'], [1, '#fdffc2']]
            data = pivot.sort_values(list(pivot.columns), ascending=True)
            n_peps = len(data)

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
                colorbar=colorbar,
                #xgap=2
            ))
            fig.add_shape(type='line',
                          x0=0,
                          y0=n_peps,
                          x1=1,
                          y1=n_peps,
                          line=dict(color='black', width=2, dash='dash'),
                          xref='paper',
                          yref='y')
            fig.update_layout(font_color='#212529',
                              title={
                                  'text': sample,
                                  'x': 0.5,
                                  'xanchor': 'center'}
                              )
            fig.layout.margin = dict(l=0, r=0, t=40, b=0)
            fig.update_yaxes(range=[0, ymax],
                             title_text='Peptides')
            fig.update_xaxes(title_text='Allele')
            fig.update_xaxes(titlefont={'size': 16}, tickfont={'size': 14})
            fig.update_yaxes(titlefont={'size': 16}, tickfont={'size': 14})
            fig.update_xaxes(fixedrange=True)
            fig.update_yaxes(fixedrange=True)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=False)

            heatmaps.add(
                div(raw(fig.to_html(full_html=False, include_plotlyjs=False)), className='col-4',
                    style="margin-right: auto")
            )

            fig.write_image(str(self.fig_dir / 'heatmaps_w_common_y_axis' / f'{sample}_heatmap.pdf'), engine="kaleido")

        #card = div(className='card')
        #card.add(div(b('Binding Specificity Heatmaps'), className='card-header'))
        #card.add(div(heatmaps, className='container'))

        #return div(card, className=className)
        return heatmaps

    def gen_upset_plot(self, className=None):
        # total_peps = len([pep for s in self.results.samples for pep in s.peptides])
        total_peps = np.sum([len(self.results.sample_peptides[s]) for s in self.results.samples])
        data = [set(self.results.sample_peptides[s]) for s in self.results.samples]
        sample_names = [str(s) for s in self.results.samples]
        lengths = {p: len(p) for p in self.results.all_original_peptides}

        usp = UpSetPlotly(samples=data, sample_names=sample_names)
        usp.add_secondary_plot(data=lengths, label='Peptide<br>length', plot_type='box')

        usp_plot = usp.plot(order_by=None,
                            intersection_limit='by_sample 0.01',
                            show_fig=False,
                            return_fig=True,
                            color='#686868')
        usp_plot.layout.margin = dict(l=0, r=0, t=40, b=0)
        usp_plot.update_layout(font_color='#212529')
        usp_plot.update_xaxes(titlefont={'size': 16}, tickfont={'size': 14})
        usp_plot.update_yaxes(titlefont={'size': 16}, tickfont={'size': 14})

        upset_fig = f'{self.fig_dir / "upsetplot.pdf"}'
        usp_plot.write_image(upset_fig, engine='kaleido')
        n = len(self.results.samples)
        if n <= 5:
            height = '450px'
        else:
            height = f'{500 + (n - 5) * 25}px'
        card = div(className='card', style=f"height: 100%")
        card.add(div([b('UpSet Plot '), '(only displaying intersections containing >= 1% of at least one sample)'],
                     className='card-header'))

        plot_body = div(wrap_plotly_fig(usp_plot, height=height), className='card-body')
        card.add(plot_body)
        if not className:
            if usp.n_plotted_intersections >= 6:
                className = 'col-12'
            else:
                className = 'col-6'
        return div(card, className=className)

    def sequence_logos(self, className=None):
        motifs = div(className=className)
        gibbs_peps = {}
        logo_dir = self.fig_dir / 'unsupervised_logos'
        logo_dir.mkdir()

        # get the peptides in each group
        for sample in self.results.samples:
            if self.results.gibbs_files[sample]['unsupervised'] is not None:
                pep_groups_file = self.results.gibbs_files[sample]['unsupervised']['pep_groups_file']
                if not Path(pep_groups_file).exists():
                    raise FileNotFoundError(f'The GibbsCluster output file {pep_groups_file} does not exist.')
                with open(pep_groups_file, 'r') as f:
                    pep_lines = f.readlines()[1:]
                n_motifs = self.results.gibbs_files[sample]['unsupervised']['n_groups']
                gibbs_peps[sample] = {str(x): [] for x in range(1, int(n_motifs)+1)}  # <---- there is a problem here because gibbcluster can find weird groups (like 2of2 but no 1of2) so we need to account for this somehow

                for line in pep_lines:
                    line = [x for x in line.split(' ') if x != '']
                    group = str(int(line[1]) + 1)
                    pep = line[3]
                    gibbs_peps[sample][group].append(pep)  # will contain the peptides belonging to each group

        sample_logos = {}
        # make logos asynchronously
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.cpus) as executor:
            for sample in self.results.samples:
                if self.results.gibbs_files[sample]['unsupervised'] is not None:
                    cores = self.results.gibbs_files[sample]['unsupervised']['cores']
                    if not isinstance(cores, list):
                        cores = [cores]
                    sample_logos[sample] = [executor.submit(make_logo, core) for core in cores]

        for sample in self.results.samples:
            if sample in sample_logos.keys():
                sample_logos[sample] = [x.result() for x in sample_logos[sample]]

        for sample in self.results.samples:
            motifs_row = div(className='row')
            total_n_peptides = 0
            n_outliers = 0
            if self.results.gibbs_files[sample]['unsupervised'] is not None:
                cores = self.results.gibbs_files[sample]['unsupervised']['cores']

                logos = sample_logos[sample]

                pep_groups = []
                for x in range(len(cores)):
                    pep_groups.append(cores[x].name.replace('gibbs.', '')[0])
                p_df: pd.DataFrame = self.pep_binding_dict[sample]
                width = 160 + 50*len(self.sample_alleles[sample])
                motifs_row.add(wrap_plotly_fig(self.sample_heatmap(sample), width=f'{width}px', height='360px'))
                logos_for_row = div(className="row")
                motifs_row.add(div(logos_for_row, className="col"))
                for i in range(len(logos)):
                    logos[i][0].write_image(str(logo_dir / f'{sample}_{i}.pdf'), engine="kaleido")
                    g_peps = set(gibbs_peps[sample][pep_groups[i]])  # the set of peptides found in the group
                    strong_binders = {allele: round(len(g_peps & set(p_df[p_df[allele] == "Strong"].index)) * 100 /
                                                    len(g_peps)) for allele in self.sample_alleles[sample]}
                    top_binder = np.max(list(strong_binders.values()))

                    composition = []
                    for key in list(strong_binders.keys()):
                        text = f'{key}: {strong_binders[key]}%, '
                        if key == list(strong_binders.keys())[-1]:
                            text = text[:-2]
                        style_str = "display: inline-block; white-space: pre; margin: 0"
                        if (strong_binders[key] == top_binder) & (strong_binders[key] != 0):
                            composition.append(b(text, style=style_str))
                        else:
                            composition.append(p(text, style=style_str))

                    logos_for_row.add(
                        div(
                            [
                                wrap_plotly_fig(logos[i][0], height="300px", width="100%"),
                                p(f'Peptides in group: {len(g_peps)}\n',
                                  style='text-align: center; white-space: pre; margin: 0'),
                                div([*composition], style="width: 100%; text-align: center")
                            ],
                            className='col',
                            style=f'max-width: 400px;'
                                  f'min-width: 260px'
                                  f'height: 100%;'
                                  f'display: block;'
                                  f'margin-right: auto;'
                                  f'font-size: 11pt'
                        ),
                    )
                total_n_peptides = len(p_df)
                n_outliers = self.results.gibbs_files[sample]['unsupervised']['n_outliers']
            else:
                motifs_row.add(
                    div(
                        [
                            p('Too few peptides to reliably cluster')
                        ],
                        className='col',
                        style=f'max-width: 400px;'
                              f'min-width: 260px'
                              f'display: block;'
                              f'margin-right: auto;'
                              f'font-size: 11pt;'
                              f'text-align: center'
                    )
                )
            motifs.add(
                div(
                    [
                        div(p([b(f'{sample}  '), f'(peptides clustered: {total_n_peptides}, outliers: {n_outliers})']),
                            className='card-header'),
                        div(motifs_row, className='card-body')
                    ],
                    className='card'
                )
            )
        return motifs

    def supervised_sequence_logos(self, className=None):
        logo_dir = self.fig_dir / 'allele_specific_logos'
        logo_dir.mkdir()
        motifs = div(className=className)
        gibbs_peps = {}

        for sample in self.results.samples:
            for allele in self.sample_alleles[sample] + ['unannotated']:
                if self.results.gibbs_files[sample][allele] is not None:
                    pep_groups_file = self.results.gibbs_files[sample][allele]['pep_groups_file']
                    with open(pep_groups_file, 'r') as f:
                        pep_lines = f.readlines()[1:]
                    n_motifs = self.results.gibbs_files[sample][allele]['n_groups']
                    gibbs_peps[f'{allele}_{sample}'] = {str(x): [] for x in range(1, int(n_motifs)+1)}
                    for line in pep_lines:
                        line = [x for x in line.split(' ') if x != '']
                        group = str(int(line[1]) + 1)
                        pep = line[3]
                        gibbs_peps[f'{allele}_{sample}'][group].append(pep)

        sample_logos = {}
        # make logos asynchronously
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.cpus) as executor:
            for sample in self.results.samples:
                sample_logos[sample] = {}
                for allele in self.sample_alleles[sample] + ['unannotated']:
                    if self.results.gibbs_files[sample][allele] is not None:
                        cores = self.results.gibbs_files[sample][allele]['cores']
                        if not isinstance(cores, list):
                            cores = [cores]
                        sample_logos[sample][allele] = [executor.submit(make_logo, core) for core in cores]

        for sample in self.results.samples:
            for allele in self.sample_alleles[sample] + ['unannotated']:
                if self.results.gibbs_files[sample][allele] is not None:
                    sample_logos[sample][allele] = [x.result() for x in sample_logos[sample][allele]]

        for sample in self.results.samples:
            motifs_row = div(className='row')
            for allele in self.sample_alleles[sample]:
                if self.results.gibbs_files[sample][allele] is not None:
                    sample_logos[sample][allele][0][0].write_image(str(logo_dir / f'{sample}_{allele}.pdf'), engine="kaleido")
                    motifs_row.add(
                        div(
                            [
                                b(f'{allele}'),
                                wrap_plotly_fig(sample_logos[sample][allele][0][0], height="300px", width="100%"),
                                p(f'Peptides: {len(gibbs_peps[f"{allele}_{sample}"]["1"])}\n'),
                            ],
                            className='col',
                            style=f'max-width: 400px;'
                                  f'min-width: 260px'
                                  f'display: block;'
                                  f'margin-right: auto;'
                                  f'font-size: 11pt;'
                                  f'text-align: center'
                        )
                    )
                else:  # there were not enough peptides to cluster
                    motifs_row.add(
                        div(
                            [
                                b(f'{allele}'),
                                p('Too few peptides to reliably cluster')
                            ],
                            className='col',
                            style=f'max-width: 400px;'
                                  f'min-width: 260px'
                                  f'display: block;'
                                  f'margin-right: auto;'
                                  f'font-size: 11pt;'
                                  f'text-align: center'
                        )
                    )
            # now the unannotated peptides
            if self.results.gibbs_files[sample]['unannotated'] is not None:
                logos = self.results.gibbs_files[sample]['unannotated']['cores']
                pep_groups = []
                for logo in logos:
                    pep_groups.append(logo.name.replace('gibbs.', '')[0])
                for x in range(len(logos)):
                    sample_logos[sample]['unannotated'][x][0].write_image(str(logo_dir / f'{sample}_unannotated_{x}.pdf'), engine="kaleido")
                    motifs_row.add(
                        div(
                            [
                                b(f'Non-binders group {pep_groups[x]}'),
                                wrap_plotly_fig(sample_logos[sample]['unannotated'][x][0], height="300px", width="100%"),
                                p(f'Peptides: {len(gibbs_peps[f"unannotated_{sample}"][pep_groups[x]])}\n'),
                            ],
                            className='col',
                            style=f'max-width: 400px;'
                                  f'min-width: 260px'
                                  f'display: block;'
                                  f'margin-right: auto;'
                                  f'font-size: 11pt;'
                                  f'text-align: center'
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
        doc = document(title='MhcVizPipe Report')
        with doc.head:
            link(rel="stylesheet", href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css",
                 integrity="sha384-9aIt2nRpC12Uk9gS9baDl411NQApFmC26EwAOH8WgZl5MYYxFfc+NcPb1dKGj7Sk",
                 crossorigin="anonymous")
            style(open(str(Path(ROOT_DIR)/'assets/report_style.css'), 'r').read())
            script(src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js")
            script(src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.0/js/bootstrap.min.js")
            body(onload="plots = document.getElementsByClassName('plotly-graph-div');"
                        "l = plots.length;"
                        "for (i=0; i < l; i++) {Plotly.relayout(plots[i], {autosize: true});}")
            script("$(document).ready(function(){$('.nav-tabs a').click(function(){$(this).tab('show');});"
                   "$('.nav-tabs a').on('shown.bs.tab',"
                   "function(){"
                   "plots = document.getElementsByClassName('plotly-graph-div');"
                        "l = plots.length;"
                        "for (i=0; i < l; i++) {Plotly.update(plots[i]);}"
                   "});});")
        with doc:
            get_plotlyjs()
            with div(id='layout', className='container', style='max-width: 1600px;'
                                                               'min-width: 1000px;'
                                                               'margin-top: 20px;'
                                                               'margin-bottom: 20px'):
                with div(className='row'):
                    with div(className='col-12', style='display: flex; height: 60px'):
                        div([h1('M'), h3('hc'), h1('V'), h3('iz'), h1('P'), h3(f'ipe'),
                             h5(f' (v{__version__})', style="white-space: pre"),
                             h3(' - Analysis report', style="white-space: pre")],
                            style="background-color: #0c0c0c; padding: 5px; color: white;"
                                  "border-radius: 6px; width: 100%; display: flex"),
                        self.lab_logo()
                hr()
                with div(className='row'):
                    with div(className='col-6', style='margin: 0'):
                        p([b('Date: '), f'{str(datetime.now().date())}'])
                        p([b('Submitted by: '), f'{self.submitter_name if self.submitter_name else "Anonymous"}'])
                        p([b('Analysis type: '), f'Class {self.mhc_class}'])
                        with div(style='display: flex'):
                            b('Description of experiment:', style='margin-right: 5px; white-space: nowrap')
                            p(self.experiment_description if self.experiment_description else 'None provided')

                        b('Samples:')
                        div(
                            [
                                p('\n'.join(
                                    [
                                        f'\t{s["sample-name"]}: {s["sample-description"]}\n'
                                        f'\t\tAlleles: {s["sample-alleles"]}'
                                        for s in self.results.sample_info
                                    ]
                                ), style="white-space: pre"
                                )
                            ]
                        )
                    self.exp_info(className='col-6')
                hr()
                h3("Sample Overview")
                p(f"{unescape('&bull;')}LF Score: "
                  f"fraction of peptides between {self.results.min_length} and {self.results.max_length} mers.\n"
                  f"{unescape('&bull;')}BF Score: fraction of peptides between {self.results.min_length} and "
                  f"{self.results.max_length} mers which are predicted to be strong or weak binders.\n"
                  , style="white-space: pre")
                n = len(self.results.samples)
                if n <= 5:
                    height = '500px'
                else:
                    height = f'{500 + (n - 5) * 25}px'
                with div(className='row', style='overflow: auto'):
                    self.quick_quality_table(className='col')
                    if len(self.samples) > 1:
                        u = self.gen_upset_plot()
                        #u['style'] = f'margin-bottom: 1em'
                    self.gen_length_histogram(className='col-12')
                hr()
                h3("Annotation Results")
                pan = 'NetMHCpan' if self.mhc_class == 'I' else 'NetMHCIIpan'
                sb = '0.5' if self.mhc_class == 'I' else '2.0'
                wb = '2.0' if self.mhc_class == 'I' else '10.0'
                p(f'{pan} eluted ligand predictions made for all peptides between {self.results.min_length} & '
                  f'{self.results.max_length} mers, inclusive.\n'
                  f' - Percent rank cutoffs for strong and weak binders: {sb} and {wb}.\n'
                  f' - Percentages are calculated across rows (i.e. percentage of total peptides for a respective sample).',
                  style='white-space: pre')
                with div(className='row'):
                    if len(self.results.samples) <= 6:
                        self.gen_peptide_tables(className='col-6')
                        self.gen_binding_histogram(className='col-6')
                    else:
                        self.gen_peptide_tables(className='col-12')
                        self.gen_binding_histogram(className='col-12')
                hr()
                with div(className='row'):
                    with div(className='col-12'):
                        h3('Binding Heatmaps')
                        p(f'{pan} eluted ligand predictions made for all peptides between {self.results.min_length} & '
                          f'{self.results.max_length} mers, inclusive.\n'
                          f'Approximate color legend (detailed mapping shown next to heatmaps):',
                          style='white-space: pre')
                        div([
                            div(style='width: 18px; height: 18px; background-color: #ef553b; border-radius: 3px'),
                            p(f'Predicted strong binders (%rank <= {sb})', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #636efa; border-radius: 3px'),
                            p(f'Predicted weak binders ({sb} < %rank <= {wb})', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #fdffc2; border-radius: 3px;'
                                      'border-style: solid; border-color: #e5ecf6; border-width: 1px'),
                            p('Predicted non-binders', style="margin-left: 5px; margin-right: 10px"),
                            #div(hr(style="border-top: dashed 2px black"), style='width: 18px; height: 18px; diplay: flex; justify-content: center; align-items:center; text-align: center'),
                            p([b('- -  ', style='white-space: pre'), '# of peptides in sample'], style="margin-left: 5px; margin-right: 10px")
                        ], style="display: flex; pad: 5px; margin-left: 20px"),
                self.gen_heatmaps()
                #with div(className='row'):
                #    self.gen_heatmaps(className='col-12')
                hr()
                with div(className='row'):
                    with div(className='col-8'):
                        h3('Sequence Motifs')
                        p(f'Clustering performed with all peptides between {self.results.min_length} & '
                          f'{self.results.max_length} mers, inclusive.')
                        p(f' - Percentages represent the percentage of peptides in a given group predicted to strongly '
                          'bind the indicated allele.')
                        div([
                            div(style='width: 18px; height: 18px; background-color: #21d426; border-radius: 3px'),
                            p('Polar', style="margin-left: 5px; margin-right: 10px"),
                            div(style='width: 18px; height: 18px; background-color: #d41cbf; border-radius: 3px'),
                            p('Neutral', style="margin-left: 5px; margin-right: 10px"),
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

        loc = f'{str(self.results.tmp_folder/"report.html")}'
        with open(loc, 'w') as f:
            f.write(doc.render().replace("&lt;", "<"))
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
