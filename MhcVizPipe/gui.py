# -*- coding: utf-8 -*-
import base64
import io
import dash
from dash.dependencies import Input, Output, State
from dash.dash import no_update
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from random import uniform
from datetime import datetime
from pathlib import Path
from MhcVizPipe.ReportTemplates import report
from MhcVizPipe.Tools.cl_tools import MhcPeptides, MhcToolHelper
import flask
from sys import argv
from urllib.parse import quote as urlquote
from MhcVizPipe.defaults import ROOT_DIR, default_config_file, config_file
from MhcVizPipe.defaults import Parameters
import gunicorn.app.base
from time import sleep
from platform import system as platform_sys
from MhcVizPipe.Tools.install_tools import run_all


Parameters = Parameters()

external_stylesheets = [dbc.themes.BOOTSTRAP,
                        #'https://codepen.io/chriddyp/pen/bWLwgP.css',
                        f'{ROOT_DIR}/assets/blinker.css']

server = flask.Flask(__name__)

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, server=server)
app.title = "MhcVizPipe"

class_i_alleles = []
if Parameters.NETMHCPAN_VERSION == '4.0':
    allele_file = Path(ROOT_DIR, 'assets', 'class_I_alleles_4.0.txt')
else:
    allele_file = Path(ROOT_DIR, 'assets', 'class_I_alleles.txt')
with open(allele_file) as f:
    for allele in f.readlines():
        allele = allele.strip()
        class_i_alleles.append({'label': allele, 'value': allele})

class_ii_alleles = []
with open(Path(ROOT_DIR, 'assets', 'class_II_alleles.txt')) as f:
    for allele in f.readlines():
        allele = allele.strip()
        class_ii_alleles.append({'label': allele, 'value': allele})

def lab_logo():
    lab_logo = base64.b64encode(
        open(str(Path(ROOT_DIR) / 'assets/logo_CARONLAB_horizontal.jpg'), 'rb').read()).decode()
    return html.Img(src=f'data:image/jpg;base64,{lab_logo}', className='img-fluid',
                    style={'max-width': '100%', 'max-height': '55px', 'margin-left':  '10px', 'margin-bottom': '8px', 'opacity': '95%'})


if not Parameters.GIBBSCLUSTER or not (Parameters.NETMHCPAN or Parameters.NETMHCIIPAN):
    need_to_run_setup = True
else:
    need_to_run_setup = False

app.layout = html.Div(children=[
    dcc.Store(id='peptides', data={}),
    html.Div('', id='tmp-folder', hidden=True),

    dbc.Row([
        dbc.Col([
            html.Div(
                [
                    html.H1(children=[html.P('M'),
                                      html.H3('hc'),
                                      html.P('V'),
                                      html.H3('iz'),
                                      html.P('P'),
                                      html.H3('ipe')],
                            style={"background-color": "#0c0c0c", "padding": "5px", "color": "white",
                                   "border-radius": "6px", "width": "100%", "display": 'flex'}),
                    lab_logo()
                ],
                style={'height': '75px', 'display': 'flex'}
            ),
            html.P(
                'A quick and user-friendly visualization tool for mass spectrometry data of MHC class I and II peptides.'),
            html.A('Click here for help and resources', id='open-info-modal', style=dict(color='blue')),
            dbc.Button('Settings', className='btn btn-secondary', style={"float": "right"}, id='settings-btn'),
            dbc.Button('First-time setup', id='initial-setup', className='btn btn-secondary',
                       style={"float": "right", 'margin-right': '5px'})
        ])
    ]),

    dbc.Modal(
        [
            dbc.ModalHeader('First-time setup'),
            dbc.ModalBody(
                [
                    html.P('Welcome to MhcVizPipe! It looks like this might be the first time you have '
                           'run the program. If you do not already have existing installations of GibbsCluster and '
                           'NetMHCpan or NetMHCIIpan on your system, please use this utility to help you '
                           'install them and get everything set up. You can access this utility again at any '
                           'time by clicking the "First-Time Setup" button in the upper-right corner of the GUI.'),
                    html.P('If you have not yet done so, you need to download GibbsCluster and NetMHCpan and/or '
                                    'NetMHCIIpan. Downloading the tools requires an academic email address.'),
                    html.H6('Downloading Tools'),
                    html.Ul(
                        [
                            html.Li('On the download pages linked below, you will have the option for different '
                                    'versions and for "Linux" or "Darwin". Choose the version indicated below. '
                                    'If your OS is any Linux distribution (e.g. Ubuntu, Linux Mint, Fedora, '
                                    'Cent OS, etc.) choose "Linux". If you have a Mac, choose "Darwin".'),
                            html.Li('Note that you will have to agree to the EULA prior to downloading.')
                        ]
                    ),
                    html.P('The programs can be downloaded by following the "Downloads" tabs on the following pages:'),
                    html.Div(
                        [
                            html.P(['GibbsCluster2.0: ',
                                    html.A('https://services.healthtech.dtu.dk/service.php?GibbsCluster-2.0',
                                           href='https://services.healthtech.dtu.dk/service.php?GibbsCluster-2.0',
                                           target='_blank',
                                           style={'color': 'blue'})]),
                            html.P(['NetMHCpan (choose version 4.0a or 4.1b): ',
                                    html.A('https://services.healthtech.dtu.dk/service.php?NetMHCpan-4.1',
                                           href='https://services.healthtech.dtu.dk/service.php?NetMHCpan-4.1',
                                           target='_blank',
                                           style={'color': 'blue'})]),
                            html.P(['NetMHCIIpan4.0: ',
                                    html.A('https://services.healthtech.dtu.dk/service.php?NetMHCIIpan-4.0',
                                           href='https://services.healthtech.dtu.dk/service.php?NetMHCIIpan-4.0',
                                           target='_blank',
                                           style={'color': 'blue'})])
                        ],
                        style={'margin-left': '20px'}
                    ),
                    html.P('You do not need both NetMHCpan4.0 and NetMHCpan4.1. MhcVizPipe is compatible with both '
                           'of them, so you can choose one or both. In our lab we are using 4.0.'),
                    html.H6('Installing'),
                    html.Ol(
                        [
                            html.Li('Once you have downloaded everything, make a new folder somewhere (anywhere, '
                                    'it doesn\'t matter where) and place the downloaded files in it to keep track '
                                    'of them. Do not decompress/unzip them.'),
                            html.Li('Click the "Select Files" button and select ALL of the downloaded files '
                                    'in the folder.'),
                            html.Li('Click the "Install" button.')
                        ]
                    ),
                    html.P('During the installation, the compressed archive files you downloaded will be extracted '
                           'into a new folder in you "Home" directory called "mhcvizpipe_tools". Each tool will be '
                           'appropriately configured to run in its new location and any required additional files '
                           'will be automatically downloaded. Finially, the MhcVizPipe settings will be updated to '
                           'use the newly installed tools. This might all take a few minutes depending on the '
                           'speed of your internet connection.'),
                    html.Div(dcc.Upload(
                        dbc.Button('Select Files',
                                   style={'width': '50%', 'font-size': '12pt'},
                                   id='choose-tool-files-btn'),
                        style={'text-align': 'center'},
                        id='choose-tool-files',
                        multiple=True)
                    ),
                    html.Div(
                        [
                            html.B('Loaded files:'),
                            html.Div(id='loaded-tool-files')
                        ],
                        id='loaded-tool-div',
                        hidden=True
                    ),
                    html.Div(id='setup-status', style={'margin-top': '5px'}),
                    html.Div(dbc.Button('Install',
                                        id='install-tools',
                                        style={'width': '50%', 'font-size': '12pt'},
                                        disabled=True),
                             style={'text-align': 'center', 'margin-top': '5px'}),
                    dbc.Button('Cancel', id='setup-cancel', style={'font-size': '10pt'}),
                    dcc.Loading(html.P('', id='installing-stuff', hidden=True), type='circle', fullscreen=True)
                ]
            )
        ],
        id='setup-modal',
        is_open=need_to_run_setup,
        centered=True,
        backdrop='static',
        style={'max-width': '800px'}
    ),

    dbc.Modal(
        [
            dbc.ModalHeader('Setup successful!'),
            dbc.ModalBody(
                'Click anywhere outside this box to continue.'
            )
        ],
        id='setup-successful',
        is_open=False,
        centered=True
    ),

    dbc.Modal(
        [
            dbc.ModalHeader('Settings'),
            dbc.ModalBody(
                [
                    html.P('Edit the contents of the text box below to change MVP settings.'),
                    html.P('NOTE: Do not change the contents of section headers (e.g. [DIRECTORIES]) or anything '
                           'to the left of an equals sign.'),
                    dcc.Textarea(style={'width': '100%', 'height': '480px'}, id='settings-area', spellCheck=False),
                    html.Div(
                        [],
                        id='settings-problem',
                        style={'margin-left': '10px'}
                    ),
                    dbc.Button('Done', color='primary', id='settings-done', style={'margin-right': '5px'}),
                    dbc.Button('Cancel', id='settings-cancel'),
                    dbc.Button('Load defaults', id='settings-defaults', style={'float': 'right'})
                ]
            )
        ],
        id='settings-modal',
        is_open=False,
        centered=True,
        backdrop='static',
        style={'max-width': '800px'}
    ),

    html.Hr(),

    dbc.Row([
        dbc.Col([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select a File', style={'text-decoration': 'underline', 'color': 'blue'})
                ]),
                style={
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center'
                },
                # Allow multiple files to be uploaded
                multiple=True
            ),

            html.P(id='display-file-name'),

            dcc.Textarea(
                placeholder='Paste a peptide list or select a file using the above interface',
                id='peptide-list-area',
                style={
                    'width': '100%',
                    'height': '120px'
                },
                spellCheck=False
            ),

            html.P(
                'Sample information:',
                style={
                    'margin-top': '10px',
                    'font-weight': 'bold'
                }),

            html.Div(
                [
                    dcc.Input(
                        id='sample-name',
                        placeholder='Sample name',
                        style={'height': '50%', 'width': '100%'})
                ],
                style={'display': 'flex', 'margin-left': '10px', 'margin-bottom': '2px'}
            ),

            html.Div(
                [
                    dcc.Input(
                        id='sample-description',
                        placeholder='Sample description (optional)',
                        value='',
                        style={'height': '50%', 'width': '100%'})
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
                    children='Load Data',
                    className='btn btn-secondary',
                    style={'margin-top': '10px', 'width': '50%', 'font-size': '14pt'})
            ], style={'text-align': 'center'}),

            html.P('Loaded data:', style={'font-weight': 'bold', 'margin-top': '10px'}),

            html.Div(
                id='loaded-data',
                children=[],
                style={'margin-left': '2em'}
            ),
        ], width=12)
    ]),

    html.Hr(),


    dbc.Modal(
        children=[
            dbc.ModalHeader('Resources and Help'),
            dbc.ModalBody(
                [
                    html.Div(
                        [
                            html.B('Welcome to MhcVizPipe!'),
                            html.P('Here you will find information on how to run an analysis and the tools used '
                                   'in the pipeline.'),
                            html.P(['MhcVizPipe is developed and maintained by the laboratory of Dr. Etienne Caron. '
                                    'For general inquiries and information please visit ',
                                    html.A('https://github.com/caronlab/MhcVizPipe/wiki',
                                           href='https://github.com/caronlab/MhcVizPipe/wiki',
                                           target='_blank',
                                           style=dict(color='blue')),
                                    ' or contact Etienne (caronchusj@gmail.com) or Kevin (kkovalchik.chusj@gmail.com). '
                                    'For technical issues and support, please open an issue on our GitHub repository: ',
                                    html.A('https://github.com/caronlab/MhcVizPipe/issues',
                                           href='https://github.com/caronlab/MhcVizPipe/issues',
                                           style=dict(color='blue'),
                                           target="_blank"),],
                                   style={'margin-left': '20px'}),
                            html.Hr(style={'margin-top': '0'}),
                            html.B('Running an analysis:'),
                            html.Div([
                                html.P([html.P('1. ', style={'white-space': 'pre'}),
                                        'Load data by pasting a peptide list into the peptide list section, using '
                                       'the "drag and drop" area, or clicking "Select a File".'],
                                       style={'display': 'flex'}),
                                html.P([html.B('    Note: ', style={'white-space': 'pre'}),
                                        'You may load more than one file at a time. If you do so the sample names '
                                        'will be completed using the filenames and all samples will be automatically '
                                        'added to the analysis. You can skip steps 2 and 3 unless you are adding other '
                                        'individual samples.'], style={'display': 'flex'}),
                                html.P([html.P('2. ', style={'white-space': 'pre'}),
                                        'Enter a sample name and (optionally) a description of the sample. '
                                        'If you selected a single file the filename will have been automatically '
                                        'entered into the sample name field, but you are free to change it.'
                                        ], style={'display': 'flex'}),
                                html.P([html.P('3. ', style={'white-space': 'pre'}),
                                        html.P(['Click the ', html.B('"LOAD DATA"'),
                                                ' button and the sample will show up under "Loaded data".'])
                                        ], style={'display': 'flex'}),
                                html.P([html.P('4. ', style={'white-space': 'pre'}),
                                        'Add more samples as needed.'
                                        ], style={'display': 'flex'}),
                                html.P([html.P('5. ', style={'white-space': 'pre'}),
                                        'Using the drop-down "MHC class" menu, select the class of peptides you '
                                        'are analyzing (i.e. class I or class II).'
                                        ], style={'display': 'flex'}),
                                html.P([html.P('6. ', style={'white-space': 'pre'}),
                                        'Add alleles using the "Alleles" search box. Start typing an allele name '
                                        'and available options will appear. Note that the format you enter must match '
                                        'the available list, so pay attention to how the allele names are formatted. '
                                        'You may add any number of alleles.'
                                        ], style={'display': 'flex'}),
                                html.P([html.P('7. ', style={'white-space': 'pre'}),
                                        html.P(['Optionally, use the text boxes above the ', html.B('"GO!" '),
                                                ' button to enter a general description of the experiment and your '
                                                'name (if needed for your own bookkeeping).']),
                                        ], style={'display': 'flex'}),
                                html.P([html.P('8. ', style={'white-space': 'pre'}),
                                        html.P(['Click the ', html.B('"GO!" '), 'button to start your analysis! '
                                                                                'You will see a loading screen '
                                                                                'while things are running, followed '
                                                                                'by a pop-up window with a link '
                                                                                'to the report.'])
                                        ], style={'display': 'flex'}),
                            ], style={'margin-left': '20px'}),
                            html.B('References:'),
                            html.Div([
                                'If you use MhcVizPipe, please cite the following publication:',
                                html.P('Paper info to go here', style={'font-size': '11pt', 'margin-left': '20px'}),
                                'MhcVizPipe makes use of the following tools: NetMHCpan4.0, NetMHCIIpan4.0 and'
                                ' GibbsCluster2.0.',
                                html.P('NetMHCpan citation', style={'font-size': '11pt', 'margin-left': '20px'}),
                                html.P('NetMHCIIpan citation', style={'font-size': '11pt', 'margin-left': '20px'}),
                                html.P('GibbsCluster citation', style={'font-size': '11pt', 'margin-left': '20px'}),
                            ], style={'margin-left': '20px'}),
                            html.Button(
                                id='close-info-modal',
                                children='Done',
                                style={'background-color': '#636efa', 'color': 'white', 'border': 'none'}
                            )
                        ]
                    )
                ]
            )],
        id="resources",
        is_open=False,
        centered=True,
        style={'max-width': '800px'}
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
        backdrop='static'
        ),

    dbc.Row([
        dbc.Col([
            html.P('MHC class:', style={'font-weight': 'bold'}),

            dcc.Dropdown(
                id='mhc-class',
                options=[
                    {'label': 'Class I', 'value': 'I'},
                    {'label': 'Class II', 'value': 'II'},
                ],
                value='I',
                style={'width': '100%', 'margin-left': '5px'}
            ),

            html.P('Alleles (type to search, can select multiple):',
                   style={'font-weight': 'bold', 'margin-top': '10px'}),

            dcc.Dropdown(
                id='mhc-alleles',
                options=class_i_alleles,
                multi=True,
                style={'width': '100%', 'margin-left': '5px'}
            ),

            html.P('General information:', style={'font-weight': 'bold', 'margin-top': '10px'}),

            dcc.Input(id='analysis-description',
                      placeholder='Experiment description (optional)',
                      style={'margin-left': '10px', 'width': '100%', 'display': 'flex'}),

            dcc.Input(id='submitter-name',
                      placeholder='Submitter name (optional)',
                      style={'margin-top': '10px', 'margin-left': '10px', 'width': '100%', 'display': 'flex'})

        ], width=6),

        dbc.Col([
            html.P('Experimental information (optional):', style={'font-weight': 'bold'}),

            dcc.Textarea(
                id='experimental-info',
                style={
                    'margin-left': '10px',
                    'width': '100%',
                    'height': '325px'
                },
                value='Species: \n'
                      '# of cells: \n'
                      'Lysis buffer: \n'
                      'Type of beads: \n'
                      'Antibody: \n'
                      'Incubation time: \n'
                      'MHC-ligand complex elution buffer: \n'
                      'Peptide elution buffer: \n'
                      'Type of MS/MS: \n'
                      'Peptide identification software: \n'
                      'Peptide FDR: \n'
                      '(Enter any further information using the same format)',
                spellCheck=False
            ),
        ], width=6)
    ]),
    html.Div(
        id='is-there-a-problem',
        children=[]
    ),

    html.Hr(),

    html.Div(
        html.Button(id='run-analysis',
                    children='Go!',
                    className='btn btn-secondary',
                    style={'margin-top': '10px', 'width': '50%', 'font-size': '14pt'}),
        style={'text-align': 'center'}
    ),


    dcc.Loading([html.A(id='loading', hidden=True)], fullscreen=True),


    html.P(children='Advanced algorithm options:', style={'font-weight': 'bold', 'margin-top': '3em'}, hidden=True),

    html.P(children='Parameters for each algorithm are preset to recommended values for the given MHC class. However, '
                    'you can adjust these settings if you are experienced and have special requirements.', hidden=True),

    dbc.Modal(
        children=[
            dbc.ModalHeader('Report ready!'),
            dbc.ModalBody(
                [
                    html.Div(
                        [
                            dbc.Row(
                                dbc.Col(
                                    html.P('Your report is ready! Click the following link to open it in a new '
                                           'tab. To download it, right-click and choose "save link as" '
                                           '(or something similar to that). If you wish to run another analysis, '
                                           'click the "Reset" button to reset the form.'),
                                )
                            ),
                            dbc.Row(
                                dbc.Col(
                                    html.A(id='link-to-report',
                                           # href='get_report',
                                           target='_blank',
                                           style={'color': 'blue',
                                                  'text-decoration': 'underline',
                                                  'margin-top': '1em',
                                                  'margin-left': '1em',
                                                  'font-size': '12pt'}
                                           ),
                                )
                            ),
                        ]
                    ),
                ],
            ),
            dbc.ModalFooter(
                html.A(dbc.Button('Reset'), href='/')
            )
        ],
        id="modal2",
        is_open=False,
        centered=True,
        backdrop='static'
        ),

], style={'padding': '20px', 'max-width': '800px'}, id='main-contents')


@app.callback([Output('setup-modal', 'is_open'),
               Output('loaded-tool-div', 'hidden'),
               Output('loaded-tool-files', 'children'),
               Output('setup-status', 'children'),
               Output('install-tools', 'disabled'),
               Output('setup-successful', 'is_open'),
               Output('installing-stuff', 'children')],
              [Input('initial-setup', 'n_clicks'),
               Input('choose-tool-files', 'contents'),
               Input('install-tools', 'n_clicks'),
               Input('setup-cancel', 'n_clicks')],
              [State('choose-tool-files', 'filename')])
def setup_tools(initial_setup_nclicks,
                files_contents,
                install_nclicks,
                setup_cancel_nclicks,
                files_filename):
    ctx = dash.callback_context
    triggered_by = button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_by == 'initial-setup':
        return True, True, [], [], True, False, no_update
    elif triggered_by == 'choose-tool-files':
        loaded = {}
        for file in files_filename:
            if platform_sys() == 'Linux' and 'Darwin' in file:
                return True, True, [], dbc.Alert(f'WARNING: Your operating system is Linux but you have downloaded '
                                                 f'a Mac OS tool: {file}. Please ensure all files match your '
                                                 f'operating system.',
                                                 className='blink_me',
                                                 color='danger'), True, False, no_update
            elif platform_sys() == 'Darwin' and 'Linux' in file:
                return True, True, [], dbc.Alert(f'WARNING: Your operating system is Mac OS but you have downloaded '
                                                 f'a Linux tool: {file}. Please ensure all files match your '
                                                 f'operating system.',
                                                 className='blink_me',
                                                 color='danger'), True, False, no_update
        for file in files_filename:
            if not (file.endswith('.tar.gz') or file.endswith('.tar')):
                return True, True, [], dbc.Alert(f'WARNING: Unrecognized filetype {"".join(Path(file).suffixes)} for '
                                                 f'file: {file}. Please make sure you have not decompressed the '
                                                 f'downloaded archives or selected an incorrect file by mistake.',
                                                 className='blink_me',
                                                 color='danger'), True, False, no_update
            elif 'netmhcpan-4.0' in file.lower():
                loaded['NetMHCpan4.0'] = file
            elif 'netmhcpan-4.1' in file.lower():
                loaded['NetMHCpan4.1'] = file
            elif 'netmhciipan-4.0' in file.lower():
                loaded['NetMHCIIpan4.0'] = file
            elif 'gibbscluster-2.0' in file.lower():
                loaded['GibbsCluster2.0'] = file
            else:
                return True, True, [], dbc.Alert(f'WARNING: Unrecognized file: {file}. Please make sure all the files '
                                                 f'you have selected are from the above list.',
                                                 className='blink_me',
                                                 color='danger'), True, False, no_update
        loaded_files = html.Div(
            [
                html.P(f'{tool}: {filename}') for tool, filename in loaded.items()
            ],
            style={'margin-left': '20px'}
        )

        not_loaded = [x for x in ['NetMHCpan4.0', 'NetMHCpan4.1', 'NetMHCIIpan4.0', 'GibbsCluster2.0']
                      if x not in loaded.keys()]

        if 'NetMHCpan4.0' in list(loaded.keys()) and 'NetMHCpan4.0' in list(loaded.keys()):
            return True, False, loaded_files, dbc.Alert(
                f'WARNING: You have selected both NetMHCpan version 4.0 and 4.1. These are both compatible, but you',
                className='blink_me',
                color='danger'), True, False, no_update

        if 'GibbsCluster2.0' not in list(loaded.keys()) or \
            ('NetMHCpan4.0' not in list(loaded.keys()) and
             'NetMHCpan4.1' not in list(loaded.keys()) and
             'NetMHCIIpan4.0' not in list(loaded.keys())):
            return True, False, loaded_files, dbc.Alert(f'WARNING: Please select all necessary files for installation. You '
                                             f'need GibbsCluster and at least one of the other tools on the above '
                                             f'list.',
                                             className='blink_me',
                                             color='danger'), True, False, no_update
        if not_loaded:
            return True, False, loaded_files, dbc.Alert(f'NOTE: You have not chosen files for {not_loaded}. You may '
                                                        f'proceed, but these tools will not be available as part '
                                                        f'of MhcVizPipe. Click "Install" to continue. Note that '
                                                        f'this might take a while depending on the speed of '
                                                        f'your internet connection.',
                                                        className='blink_me'), False, False, no_update
        else:
            return True, False, loaded_files, dbc.Alert(f'All files recognized. Click "Install" to continue. Note that '
                                                        f'this might take a while depending on the speed of '
                                                        f'your internet connection.',
                                                        className='blink_me'), False, False, no_update
    elif triggered_by == 'install-tools':
        files = list(zip(files_filename, files_contents))
        run_all(files)
        return False, False, [], [], False, True, 'done!'
    elif triggered_by == 'setup-cancel':
        return False, False, [], [], False, False, no_update
    else:
        raise PreventUpdate

@app.callback([Output('settings-modal', 'is_open'),
               Output('settings-area', 'value'),
               Output('settings-problem', 'children'),
               Output('mhc-class', 'value')],
              [Input('settings-defaults', 'n_clicks'),
               Input('settings-done', 'n_clicks'),
               Input('settings-cancel', 'n_clicks'),
               Input('settings-btn', 'n_clicks')],
              [State('settings-area', 'value'),
               State('mhc-class', 'value')])
def update_settings(defaults, done, cancel, open_settings, settings, mhc_class):
    # we pass out the state of mhc-class to force the allele list to get updated. This is necessary if
    # the version of netMHCpan has been changed.
    ctx = dash.callback_context
    triggered_by = button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_by == 'settings-btn':
        with open(config_file, 'r') as f:
            settings = ''.join(f.readlines())
        return True, settings, [], mhc_class

    elif triggered_by == 'settings-done':
        for line in settings.split('\n'):
            if line \
                    and not line.startswith('#') \
                    and not line.startswith('[') \
                    and '=' not in line\
                    or (line.startswith('[') and not line.endswith(']')):
                message = [html.P(f'There is a formatting issue. Please check that the following line contains an '
                                  f'equal sign (i.e. =), or if you want the line to be a comment then ensure it '
                                  f'starts with #. If it is a section header it must start with [ and end with ]:'),
                           html.P(f'{line}')]
                problem = dbc.Alert(id=str(uniform(0, 1)), color='danger',
                                     children=message,
                                     style={'margin-top': '2px', 'width': '100%'}),
                return True, settings, problem, mhc_class

        with open(config_file, 'w') as f:
            f.write(settings)
        return False, '', [], mhc_class

    elif triggered_by == 'settings-defaults':
        with open(default_config_file, 'r') as f:
            settings = ''.join(f.readlines())
        return True, settings, [], mhc_class

    elif triggered_by == 'settings-cancel':
        return False, settings, [], mhc_class

    else:
        raise PreventUpdate


@app.callback([Output('mhc-alleles', 'options'),
               Output('mhc-alleles', 'value')],
              [Input('mhc-class', 'value')])
def change_mhc_class_alleles(mhc_class):
    if mhc_class == 'I':
        class_i_alleles = []
        if Parameters.NETMHCPAN_VERSION == '4.0':
            allele_file = Path(ROOT_DIR, 'assets', 'class_I_alleles_4.0.txt')
        else:
            allele_file = Path(ROOT_DIR, 'assets', 'class_I_alleles.txt')
        with open(allele_file) as f:
            for allele in f.readlines():
                allele = allele.strip()
                class_i_alleles.append({'label': allele, 'value': allele})
        return [class_i_alleles, []]
    elif mhc_class == 'II':
        return [class_ii_alleles, []]
    else:
        raise PreventUpdate

@app.callback([Output('resources', 'is_open')],
              [Input('open-info-modal', 'n_clicks'),
               Input('close-info-modal', 'n_clicks')])
def open_close_info_modal(open_modal, close_modal):
    ctx = dash.callback_context
    triggered_by = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_by == 'open-info-modal':
        return [True]
    elif triggered_by == 'close-info-modal':
        return [False]
    else:
        raise PreventUpdate


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

    if filename:
        filename = [str(f).replace('(', '_').replace(')', '_').replace('{', '_').replace('}', '_')
                        .replace('[', '_').replace(']', '_') for f in filename]

    if sample_name:
        sample_name = sample_name.replace('(', '_').replace(')', '_').replace('{', '_').replace('}', '_')\
            .replace('[', '_').replace(']', '_')

    if triggered_by == 'upload-data':
        if len(filename) == 1:
            filename = filename[0]
            contents = contents[0]
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            lines = io.StringIO(decoded.decode('utf-8')).readlines()
            try:
                if ',' in lines[0]:
                    return ''.join(lines), True, [{'label': x, 'value': x} for x in lines[0].split(',')], f'File: {filename}', peptide_data, filename, sample_description, loaded_data, []
                elif '\t' in lines[0]:
                    return ''.join(lines), True, [{'label': x, 'value': x} for x in lines[0].split('\t')], f'File: {filename}', peptide_data, filename, sample_description, loaded_data, []
                else:
                    return ''.join(lines).replace('"', ''), False, [], f'File: {filename}', peptide_data, filename, sample_description, loaded_data, []
            except Exception as e:
                return peptide_list_state, False, [], f'File: {filename}', peptide_data, filename, sample_description, loaded_data, \
                       [dbc.Alert(f'There was an error processing this file: {e}', id=str(uniform(0, 1)),
                                  className='blink_me', color='danger', style={'width': '720px'})]
        else:
            first_content_type, content_string = contents[0].split(',')
            first_decoded = base64.b64decode(content_string)
            first_lines = io.StringIO(first_decoded.decode('utf-8')).readlines()

            if ',' in first_lines[0]:
                return '', True, [{'label': x, 'value': x} for x in first_lines[0].split(
                    ',')], f'Files: {", ".join(filename)}', peptide_data, '', '', loaded_data, []
            elif '\t' in first_lines[0]:
                return '', True, [{'label': x, 'value': x} for x in first_lines[0].split(
                    '\t')], f'Files: {", ".join(filename)}', peptide_data, '', '', loaded_data, []
            else:
                for file, content in zip(filename, contents):
                    content_type, content_string = content.split(',')
                    decoded = base64.b64decode(content_string)
                    lines = io.StringIO(decoded.decode('utf-8')).readlines()
                    peps = [x.replace('"', '').strip() for x in lines]
                    peptide_data[file] = {'description': file, 'peptides': peps}
                    loaded_data += [html.P(f'{file}', style={'margin': '2px'})]
                return '', False, [], '', peptide_data, '', '', loaded_data, []

    elif triggered_by == 'done-selecting-column':
        if len(filename) == 1:
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
            peps = [line.split(sep)[i].strip().replace('"', '') for line in lines[1:]]
            return '\n'.join(peps), False, [], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data, []
        else:
            if not selected_column:
                raise PreventUpdate
            for file, content in zip(filename, contents):
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                lines = io.StringIO(decoded.decode('utf-8')).readlines()
                if ',' in lines[0]:
                    headers = lines[0].split(',')
                    sep = ','
                else:
                    headers = lines[0].split('\t')
                    sep = '\t'
                i = headers.index(selected_column)
                peps = [line.split(sep)[i].strip().replace('"', '') for line in lines[1:]]
                total_n = len(peps)
                peps = list(set(peps))
                peptide_data[file] = {'description': file, 'peptides': peps, 'total_peps': total_n}
                loaded_data += [html.P(f'{file}', style={'margin': '2px'})]
            return '', False, [], '', peptide_data, '', '', loaded_data, []

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
        if sample_name in list(peptide_data.keys()):
            # the sample name or description has not been filled out, so we put up a reminder. The random ID is to force
            # it to blink each time.
            return peptide_list_state, False, [], f'File: {filename}', peptide_data, sample_name, sample_description, loaded_data,\
                   [dbc.Alert('You cannot enter replicate sample names.', id=str(uniform(0, 1)),
                              className='blink_me', color='danger', style={'width': '360px'})]
        peps = [x.strip() for x in peptide_list_state.split('\n')]
        total_n = len(peps)
        peps = list(set(peps))
        peptide_data[sample_name] = {'description': sample_description, 'peptides': peps, 'total_peps': total_n}
        if sample_description != '':
            loaded_data += [html.P(f'{sample_name}: {sample_description}', style={'margin': '2px'})]
        else:
            loaded_data += [html.P(f'{sample_name}', style={'margin': '2px'})]
        return '', False, [], '', peptide_data, '', '', loaded_data, []

    else:
        raise PreventUpdate


@app.callback([Output('link-to-report', 'children'),
               Output('link-to-report', 'href'),
               Output('is-there-a-problem', 'children'),
               Output('loading', 'children'),
               Output('modal2', 'is_open')],
              [Input('run-analysis', 'n_clicks')],
              [State('peptides', 'data'),
               State('submitter-name', 'value'),
               State('analysis-description', 'value'),
               State('mhc-class', 'value'),
               State('mhc-alleles', 'value'),
               State('experimental-info', 'value')])
def run_analysis(n_clicks, peptides, submitter_name, description, mhc_class, alleles, exp_info):
    if (peptides in [None, {}]) and (n_clicks is not None):
        return (no_update,
                no_update,
                [dbc.Alert(id=str(uniform(0, 1)), color='danger',
                                                children='You need to load some data first.',
                                                style={'width': '360px', 'margin-top': '2px'})],
                no_update,
                False)
    elif (alleles in [None, [], ['']]) and (n_clicks is not None):
        return (no_update,
                no_update,
                [dbc.Alert(id=str(uniform(0, 1)), color='danger',
                                                children='Please select one or more alleles.',
                                                style={'width': '360px', 'margin-top': '2px'})],
                no_update,
                False)

    else:
        if n_clicks is None:
            raise PreventUpdate

        samples = []
        for sample_name in peptides.keys():
            peps = [p.strip() for p in peptides[sample_name]['peptides'] if len(p.strip()) != 0]
            samples.append(
                MhcPeptides(sample_name=sample_name,
                            sample_description=peptides[sample_name]['description'],
                            peptides=peps)
            )
        time = str(datetime.now()).replace(' ', '_')
        analysis_location = str(Path(Parameters.TMP_DIR)/time)
        if mhc_class == 'I':
            min_length = 8
            max_length = 12
        else:
            min_length = 9
            max_length = 22
        cl_tools = MhcToolHelper(
            samples=samples,
            mhc_class=mhc_class,
            alleles=alleles,
            tmp_directory=analysis_location,
            min_length=min_length,
            max_length=max_length
        )
        cl_tools.make_binding_predictions()
        cl_tools.cluster_with_gibbscluster()
        cl_tools.cluster_with_gibbscluster_by_allele()
        analysis = report.mhc_report(cl_tools, mhc_class, description, submitter_name, exp_info)
        _ = analysis.make_report()
        download_href = f'/download/{urlquote(time+"/"+"report.html")}'

        return 'Link to report', download_href, [], '', True

@app.server.route("/download/<path:path>")
def get_report(path):
    return flask.send_from_directory(Parameters.TMP_DIR, path)


def make_app():
    return app

class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    welcome = f'''
     ========================================
     MhcVizPipe v0.1.9

     Welcome to MhcVizPipe! To open the GUI, open the following link
     in your web browser (also found below): http://{Parameters.HOSTNAME}:{Parameters.PORT}

     For a brief introduction to using the GUI, click the link to
     "help and resources" near the top of the GUI. For more information
     and the latest updates please visit our GitHub repository:
     https://github.com/kevinkovalchik/MhcVizPipe.

     ========================================
    '''
    if 'debug' in argv or '-debug' in argv or '--debug' in argv:
        app.run_server(debug=True, port=8971, host=Parameters.HOSTNAME)
    else:
        print(welcome)
        sleep(0.5)
        options = {
            'bind': f'{Parameters.HOSTNAME}:{Parameters.PORT}',
            'timeout': Parameters.TIMEOUT
        }
        StandaloneApplication(app.server, options).run()
