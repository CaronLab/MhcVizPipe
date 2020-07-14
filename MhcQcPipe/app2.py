# -*- coding: utf-8 -*-
import base64
import io
import os
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from random import uniform
from datetime import datetime
from pathlib import Path
from MhcQcPipe import report
from MhcQcPipe.Tools.cl_tools import MhcPeptides, MhcToolHelper

import pandas as pd

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
external_stylesheets = [dbc.themes.BOOTSTRAP,
                        'https://codepen.io/chriddyp/pen/bWLwgP.css',
                        f'{ROOT_DIR}/assets/blinker.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

class_i_alleles = []
with open(Path(ROOT_DIR, 'assets', 'class_I_alleles.txt')) as f:
    for allele in f.readlines():
        allele = allele.strip()
        class_i_alleles.append({'label': allele, 'value': allele})

class_ii_alleles = []
with open(Path(ROOT_DIR, 'assets', 'class_II_alleles.txt')) as f:
    for allele in f.readlines():
        allele = allele.strip()
        class_ii_alleles.append({'label': allele, 'value': allele})

gui_layout = html.Div(children=[
    dcc.Store(id='peptides', data={}),

    html.H3(children='Data', style={'text-decoration': 'underline'}),

    dbc.Row(dbc.Col(
        html.P('Use the "LOAD DATA" button to load a peptide search results file or paste a list of peptides '
               'directly in the box below. Note that you must subsequently add the data to the analysis '
               'using the "ADD TO ANALYSIS" button below. If you are analyzing data from more than one '
               'experiment, fill out the sample name and description fields so you can distinguish them '
               'in the report. You may load up to 6 samples.'),
        width=8
    )),

    dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select a File', style={'text-decoration': 'underline', 'color': 'blue'})
            ]),
            style={
                'width': '360px',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=False
        ),

    html.P(id='display-file-name'),

    dcc.Textarea(
        placeholder='Paste a peptide list or use the LOAD DATA button',
        id='peptide-list-area',
        style={
            'margin-left': '10px',
            'width': '360px',
            'height': '120px'
        },
        spellCheck=False
    ),

    dbc.Modal(
        children=[
            dbc.ModalHeader('Select column header'),
            dbc.ModalBody(
                [
                    html.Div(
                        [
                            html.P('The file looks like it has multiple columns. '
                                   'Select the header for the column which contains the peptide list:'),
                            dbc.RadioItems(
                                id='column-header-choices'),
                            dbc.Button('Done', id='done-selecting-column')
                        ]
                    )
                ]
            )],
        id="modal",
        is_open=False,
        centered=True,
        backdrop=False
        ),

    html.P(
        'Sample information:',
        style={
            'margin-top': '10px',
            'font-weight': 'bold'
        }),
    html.P(
        'Provide some information to identify data in the report.',
        style={
            'margin-left': '10px'
        }
    ),

    html.Div(
        [
            dcc.Input(
                id='sample-name',
                placeholder='Sample name',
                style={'height': '50%', 'width': '360px'})
        ],
        style={'display': 'flex', 'margin-left': '10px', 'margin-bottom': '2px'}
    ),

    html.Div(
        [
            dcc.Input(
                id='sample-description',
                placeholder='Sample description (optional)',
                value='',
                style={'height': '50%', 'width': '360px'})
        ],
        style={'display': 'flex', 'margin-left': '10px', 'margin-bottom': '2px'}
    ),

    html.Div(
        [],
        id='info-needed',
        style={'margin-left': '10px'}
    ),


    html.Div(children=[
        html.Button(
            id='add-peptides',
            children='Add to analysis',
            style={'background-color': '#4CAF50', 'color': 'white', 'border': 'none', 'margin-top': '10px'})
    ]),

    html.P('Loaded data:', style={'font-weight': 'bold', 'margin-top': '10px'}),

    html.Div(
        id='loaded-data',
        children=[],
        style={'margin-left': '2em'}
    ),

    html.P('MHC class:', style={'font-weight': 'bold'}),

    dcc.Dropdown(
        id='mhc-class',
        options=[
            {'label': 'Class I', 'value': 'I'},
            {'label': 'Class II', 'value': 'II'},
        ],
        value='I',
        style={'width': '40%', 'margin-left': '1em'}
    ),

    html.P('Alleles (optional, type to search, can select multiple):', style={'font-weight': 'bold'}),

    dcc.Dropdown(
        id='mhc-alleles',
        options=class_i_alleles,
        multi=True,
        style={'width': '40%', 'margin-left': '1em'}
    ),


    html.H3(children='Run analysis', style={'text-decoration': 'underline'}),

    html.Div(
        [
            dcc.Input(id='analysis-description',
                      placeholder='Experiment description (optional)',
                      style={'height': '50%', 'margin-top': '10px', 'width': '360px'})
        ],
        style={'display': 'flex'}
    ),

    html.Div(
        [
            dcc.Input(id='submitter-name',
                      placeholder='Submitter name (optional)',
                      style={'height': '50%', 'margin-top': '10px', 'width': '360px'})
        ],
        style={'display': 'flex'}
    ),

    html.Div(
        id='is-there-a-problem',
        children=[]
    ),

    html.Button(id='run-analysis',
                children='Go!', style={'background-color': '#4CAF50', 'color': 'white',
                                       'border': 'none', 'margin-top': '10px'}),

    html.A(id='link-to-report',
           style={'color': 'blue',
                  'text-decoration': 'underline',
                  'margin-top': '1em',
                  'margin-left': '1em',
                  'font-size': '24pt',
                  'font-weight': 'bold'}
           ),

    dcc.Loading([html.A(id='loading', hidden=True)], fullscreen=True),

    html.Div('', id='report-holder'),

    html.P(children='Advanced algorithm options:', style={'font-weight': 'bold', 'margin-top': '3em'}, hidden=True),

    html.P(children='Parameters for each algorithm are preset to recommended values for the given MHC class. However, '
                    'you can adjust these settings if you are experienced and have special requirements.', hidden=True)

], id='main-contents')

app.layout = html.Div(
    [
        html.H1(children='MhcQcPipe'),

        html.Div(children='''
            A quick and easy QC application for mass spectrometry data of MHC class I and II peptides.
        '''),

        html.Hr(),

        dbc.Tabs(
            [
                dbc.Tab(gui_layout, label='Run analysis')
            ],
            id='tabs',
        )
    ],
    style={'padding': '20px', 'display': 'block'},
)


@app.callback([Output('peptide-list-area', 'value'),
               Output('modal', 'is_open'),
               Output('column-header-choices', 'options'),
               Output('display-file-name', 'children'),
               Output('peptides', 'data'),
               Output('sample-name', 'value'),
               Output('sample-description', 'value'),
               Output('loaded-data', 'children'),
               Output('info-needed', 'children')
               ],
              [Input('upload-data', 'contents'),
               Input('done-selecting-column', 'n_clicks'),
               Input('add-peptides', 'n_clicks')],
              [State('upload-data', 'filename'),
               State('column-header-choices', 'value'),
               State('sample-name', 'value'),
               State('sample-description', 'value'),
               State('peptide-list-area', 'value'),
               State('loaded-data', 'children'),
               State('peptides', 'data')
               ])
def parse_peptide_file(contents, select_n_clicks, add_peps_n_clicks, filename, selected_column, sample_name,
                       sample_description, peptide_list_state, loaded_data, peptide_data):

    ctx = dash.callback_context
    triggered_by = button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_by == 'upload-data':
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        lines = io.StringIO(decoded.decode('utf-8')).readlines()
        try:
            if ',' in lines[0]:
                return ''.join(lines), True, [{'label': x, 'value': x} for x in lines[0].split(',')], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data, []
            elif '\t' in lines[0]:
                return ''.join(lines), True, [{'label': x, 'value': x} for x in lines[0].split('\t')], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data, []
            else:
                return ''.join(lines), False, [], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data, []
        except Exception as e:
            return f'There was an error processing this file:\n\n{e}', False, 'ERROR', [], sample_name, sample_description, loaded_data, []

    elif triggered_by == 'done-selecting-column':
        if not selected_column:
            raise PreventUpdate
        lines = [x.strip() for x in peptide_list_state.split('\n')]
        if ',' in lines[0]:
            headers = lines[0].split(',')
            sep = ','
        else:
            headers = lines[0].split('\t')
            sep = '\t'
        i = headers.index(selected_column)
        peps = [line.split(sep)[i].strip() for line in lines[1:]]
        return '\n'.join(peps), False, [], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data, []

    elif triggered_by == 'add-peptides':
        if peptide_list_state in ['', None]:
            return peptide_list_state, False, [], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data, \
                   [dbc.Alert('You haven\'t entered any peptides.', id=str(uniform(0, 1)),
                              className='blink_me', color='danger', style={'width': '360px'})]
        if sample_name in ['', None]:
            # the sample name or description has not been filled out, so we put up a reminder. The random ID is to force
            # it to blink each time.
            return peptide_list_state, False, [], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data,\
                   [dbc.Alert('Please enter a sample name.', id=str(uniform(0, 1)),
                              className='blink_me', color='danger', style={'width': '360px'})]
        if len(loaded_data) >= 6:
            return peptide_list_state, False, [], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data, \
                   [dbc.Alert('You cannot load more than 6 samples.', id=str(uniform(0, 1)),
                              className='blink_me', color='danger', style={'width': '360px'})]
        peps = [x.strip() for x in peptide_list_state.split('\n')]
        peps = list(set(peps))
        peptide_data[sample_name] = {'description': sample_description, 'peptides': peps}
        if sample_description != '':
            loaded_data += [html.P(f'{sample_name}: {sample_description}', style={'margin': '2px'})]
        else:
            loaded_data += [html.P(f'{sample_name}', style={'margin': '2px'})]
        return '', False, [], '', peptide_data, '', '', loaded_data, []

    else:
        raise PreventUpdate


@app.callback([Output('mhc-alleles', 'options'),
               Output('mhc-alleles', 'value')],
              [Input('mhc-class', 'value')])
def change_mhc_class_alleles(mhc_class):
    if mhc_class == 'I':
        return [class_i_alleles, []]
    elif mhc_class == 'II':
        return [class_ii_alleles, []]
    else:
        raise PreventUpdate


@app.callback([Output('link-to-report', 'children'),
               Output('is-there-a-problem', 'children'),
               Output('loading', 'children'),
               Output('tabs', 'children')],
              [Input('run-analysis', 'n_clicks')],
              [State('peptides', 'data'),
               State('submitter-name', 'value'),
               State('analysis-description', 'value'),
               State('mhc-class', 'value'),
               State('mhc-alleles', 'value'),
               State('tabs', 'children')])
def run_analysis(n_clicks, peptides, submitter_name, description, mhc_class, alleles, tabs):
    if (peptides in [None, {}]) and (n_clicks is not None):
        return '', [dbc.Alert(id=str(uniform(0, 1)), color='danger',
                              children='You need to load some data first.',
                              className='blink_me',
                              style={'width': '360px', 'margin-top': '2px'})], [], 'sorry, this is what happens right now when you haven\'t loaded data... I\'ll work on fixing it... click the reload button in your browser to go back to the interface.'
    else:
        if n_clicks is None:
            raise PreventUpdate

        samples = []
        for sample_name in peptides.keys():
            samples.append(
                MhcPeptides(sample_name=sample_name,
                            sample_description=peptides[sample_name]['description'],
                            peptides=peptides[sample_name]['peptides'])
            )
        cl_tools = MhcToolHelper(
            samples=samples,
            mhc_class=mhc_class,
            alleles=alleles
        )
        cl_tools.make_binding_predictions()
        cl_tools.cluster_with_gibbscluster()
        finished_report = report.generate_report(cl_tools, mhc_class, description, submitter_name).children
        tabs.append(
            dbc.Tab(
                finished_report,
                label=f'Report {str(datetime.now())}'
            )
        )

        return 'link to report', [], '', tabs


'''@app.callback([Output('tabs', 'children')],
              [Input('report-holder', 'children')],
              [State('tabs', 'children')])
def show_report(report_contents, tabs):
    tabs.append(
        dbc.Tab(
            report_contents,
            label=f'Report {str(datetime.now())}'
        )
    )
    return [tabs]'''
'''
@app.callback([Output('main-contents', 'children')],
              [Input('link-to-report', 'n_clicks')],
              [State('main-contents', 'children')])
def go_to_report(n_clicks, contents):
    ctx = dash.callback_context
    triggered_by = button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_by == 'link-to-report':
        return [html.H3('wooooO!!!!!!!!!')]
    else:
        raise PreventUpdate
'''

'''    dcc.Tabs(children=
             [
                 dcc.Tab(label='GibbsCluster 2.0', children=[
                     html.P('GibbsCluster options go here.')
                 ]),
                 dcc.Tab(label='netMHCpan 4.1', children=[
                     html.P('netMHCpan options go here.')
                 ]),
                 dcc.Tab(label='netMHCIIpan 4.0', children=[
                     html.P('netMHCpan options go here.')
                 ])
             ]),'''

#def run_pipeline(peptides, mhc_class, submitter):
    #p


if __name__ == '__main__':
    app.run_server(debug=True, port=8792, host='0.0.0.0')