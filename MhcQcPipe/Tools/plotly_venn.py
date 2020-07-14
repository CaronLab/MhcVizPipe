# coding: utf-8
from itertools import chain
from collections import Iterable
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import colors
import math
import numpy as np
import plotly.graph_objects as go

default_colors = [
    # r, g, b, a
    'rgba(92, 192, 98, 0.5)',
    'rgba(90, 155, 212, 0.5)',
    'rgba(246, 236, 86, 0.6)',
    'rgba(241, 90, 96, 0.4)',
    'rgba(255, 117, 0, 0.3)',
    'rgba(82, 82, 190, 0.2)',
]

def ellipse_arc(x_center=0, y_center=0, a=1, b=1, rotation=0, N=100, closed=False):
    start_angle = 0
    end_angle = 2 * np.pi
    t = np.linspace(start_angle, end_angle, N)
    x = a*np.cos(t)*np.cos(rotation) - b*np.sin(t)*np.sin(rotation) + x_center
    y = a*np.cos(t)*np.sin(rotation) + b*np.sin(t)*np.cos(rotation) + y_center
    path = f'M {x[0]}, {y[0]}'
    for k in range(1, len(t)):
        path += f'L{x[k]}, {y[k]}'
    if closed:
        path += ' Z'
    return path


def draw_ellipse(fig: go.Figure, x, y, w, h, a, fillcolor):
    e = ellipse_arc(x_center=x,
                    y_center=y,
                    a=w/2,
                    b=h/2,
                    rotation=a,
                    closed=True)
    shapes = fig.layout.shapes
    shapes += tuple([
        dict(
            type='path',
            path=e,
            fillcolor=fillcolor,
            line={'color': fillcolor}
        )
    ])
    fig.update_layout(shapes=shapes)


def draw_triangle(fig: go.Figure, x1, y1, x2, y2, x3, y3, fillcolor):
    xy = [
        (x1, y1),
        (x2, y2),
        (x3, y3),
    ]
    fig.add_trace(go.Scatter(x=[x1, x2, x3], y=[y1, y2, y3], fill='toself', fillcolor=fillcolor))


def draw_text(fig: go.Figure, x, y, text, color='rgba(0,0,0,1)', fontsize=14, ha="center", va="middle"):
    fig.add_annotation(
        x=x,
        y=y,
        text=text,
        font={'size': fontsize, 'color': color},
        xanchor=ha,
        yanchor=va,
        showarrow=False

    )


def get_labels(data, fill=["number"]):
    """
    get a dict of labels for groups in data

    @type data: list[Iterable]
    @rtype: dict[str, str]

    input
      data: data to get label for
      fill: ["number"|"logic"|"percent"]

    return
      labels: a dict of labels for different sets

    example:
    In [12]: get_labels([range(10), range(5,15), range(3,8)], fill=["number"])
    Out[12]:
    {'001': '0',
     '010': '5',
     '011': '0',
     '100': '3',
     '101': '2',
     '110': '2',
     '111': '3'}
    """

    N = len(data)

    sets_data = [set(data[i]) for i in range(N)]  # sets for separate groups
    s_all = set(chain(*data))                     # union of all sets

    # bin(3) --> '0b11', so bin(3).split('0b')[-1] will remove "0b"
    set_collections = {}
    for n in range(1, 2**N):
        key = bin(n).split('0b')[-1].zfill(N)
        value = s_all
        sets_for_intersection = [sets_data[i] for i in range(N) if  key[i] == '1']
        sets_for_difference = [sets_data[i] for i in range(N) if  key[i] == '0']
        for s in sets_for_intersection:
            value = value & s
        for s in sets_for_difference:
            value = value - s
        set_collections[key] = value

    labels = {k: "" for k in set_collections}
    if "logic" in fill:
        for k in set_collections:
            labels[k] = k + ": "
    if "number" in fill:
        for k in set_collections:
            labels[k] += str(len(set_collections[k]))
    if "percent" in fill:
        data_size = len(s_all)
        for k in set_collections:
            labels[k] += "(%.1f%%)" % (100.0 * len(set_collections[k]) / data_size)

    return labels


def figure_layout(figsize=None, x_range=(0, 1), y_range=(0, 1)):
    fig = go.Figure()
    if figsize:
        fig.layout.width = figsize[0]
        fig.layout.height = figsize[1]
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            range=x_range,
            visible=False
        ),
        yaxis=dict(
            visible=False,
            scaleanchor="x",
            scaleratio=1,
            range=y_range
        ),
        margin=dict(
            l=20,
            r=20,
            b=20,
            t=20
        )
    )
    return fig


def venn2(labels, names=['A', 'B'], **options):
    """
    plots a 2-set Venn diagram

    @type labels: dict[str, str]
    @type names: list[str]
    @rtype: (Figure, AxesSubplot)

    input
      labels: a label dict where keys are identified via binary codes ('01', '10', '11'),
              hence a valid set could look like: {'01': 'text 1', '10': 'text 2', '11': 'text 3'}.
              unmentioned codes are considered as ''.
      names:  group names
      more:   colors, figsize, dpi, fontsize

    return
      plotly graph_objects Figure object
    """

    colors = options.get('colors', default_colors[:2])
    figsize = options.get('figsize', (900, 700))
    fontsize = options.get('fontsize', 16)

    fig = figure_layout(x_range=[0, 1], y_range=[0, 0.6])

    # body
    draw_ellipse(fig, 0.375, 0.3, 0.5, 0.5, 0.0, colors[0])
    draw_ellipse(fig, 0.625, 0.3, 0.5, 0.5, 0.0, colors[1])
    draw_text(fig, 0.74, 0.30, labels.get('01', ''), fontsize=fontsize)
    draw_text(fig, 0.26, 0.30, labels.get('10', ''), fontsize=fontsize)
    draw_text(fig, 0.50, 0.30, labels.get('11', ''), fontsize=fontsize)

    # legend
    draw_text(fig, 0.20, 0.56, names[0], fontsize=fontsize, ha="right", va="bottom")
    draw_text(fig, 0.80, 0.56, names[1], fontsize=fontsize, ha="left", va="bottom")
    #leg = ax.legend(names, loc='center left', bbox_to_anchor=(1.0, 0.5), fancybox=True)
    #leg.get_frame().set_alpha(0.5)
    return fig

def venn3(labels, names=['A', 'B', 'C'], **options):
    """
    plots a 3-set Venn diagram

    @type labels: dict[str, str]
    @type names: list[str]
    @rtype: (Figure, AxesSubplot)

    input
      labels: a label dict where keys are identified via binary codes ('001', '010', '100', ...),
              hence a valid set could look like: {'001': 'text 1', '010': 'text 2', '100': 'text 3', ...}.
              unmentioned codes are considered as ''.
      names:  group names
      more:   colors, figsize, dpi, fontsize

    return
      pyplot Figure and AxesSubplot object
    """
    colors = options.get('colors', default_colors[:3])
    figsize = options.get('figsize', (700, 700))
    fontsize = options.get('fontsize', 16)

    fig = figure_layout(x_range=[0, 1], y_range=[0, 0.9])

    # body
    draw_ellipse(fig, 0.333, 0.633, 0.5, 0.5, 0.0, colors[0])
    draw_ellipse(fig, 0.666, 0.633, 0.5, 0.5, 0.0, colors[1])
    draw_ellipse(fig, 0.500, 0.310, 0.5, 0.5, 0.0, colors[2])
    draw_text(fig, 0.50, 0.27, labels.get('001', ''), fontsize=fontsize)
    draw_text(fig, 0.73, 0.65, labels.get('010', ''), fontsize=fontsize)
    draw_text(fig, 0.61, 0.46, labels.get('011', ''), fontsize=fontsize)
    draw_text(fig, 0.27, 0.65, labels.get('100', ''), fontsize=fontsize)
    draw_text(fig, 0.39, 0.46, labels.get('101', ''), fontsize=fontsize)
    draw_text(fig, 0.50, 0.65, labels.get('110', ''), fontsize=fontsize)
    draw_text(fig, 0.50, 0.51, labels.get('111', ''), fontsize=fontsize)

    # legend
    draw_text(fig, 0.15, 0.87, names[0], fontsize=fontsize, ha="right", va="bottom")
    draw_text(fig, 0.85, 0.87, names[1], fontsize=fontsize, ha="left", va="bottom")
    draw_text(fig, 0.50, 0.02, names[2], fontsize=fontsize, va="top")
    #leg = ax.legend(names, loc='center left', bbox_to_anchor=(1.0, 0.5), fancybox=True)
    #leg.get_frame().set_alpha(0.5)
    return fig


def venn4(labels, names=['A', 'B', 'C', 'D'], **options):
    """
    plots a 4-set Venn diagram

    @type labels: dict[str, str]
    @type names: list[str]
    @rtype: (Figure, AxesSubplot)

    input
      labels: a label dict where keys are identified via binary codes ('0001', '0010', '0100', ...),
              hence a valid set could look like: {'0001': 'text 1', '0010': 'text 2', '0100': 'text 3', ...}.
              unmentioned codes are considered as ''.
      names:  group names
      more:   colors, figsize, dpi, fontsize

    return
      pyplot Figure and AxesSubplot object
    """
    colors = options.get('colors', default_colors[:4])
    figsize = options.get('figsize', (12, 12))
    fontsize = options.get('fontsize', 16)

    fig = figure_layout(x_range=[0, 1], y_range=[0, 0.8])

    # body
    draw_ellipse(fig, 0.350, 0.400, 0.72, 0.45, 140.0*np.pi/180, colors[0])
    draw_ellipse(fig, 0.450, 0.500, 0.72, 0.45, 140.0*np.pi/180, colors[1])
    draw_ellipse(fig, 0.544, 0.500, 0.72, 0.45, 40.0*np.pi/180, colors[2])
    draw_ellipse(fig, 0.644, 0.400, 0.72, 0.45, 40.0*np.pi/180, colors[3])
    draw_text(fig, 0.85, 0.42, labels.get('0001', ''), fontsize=fontsize)
    draw_text(fig, 0.68, 0.72, labels.get('0010', ''), fontsize=fontsize)
    draw_text(fig, 0.77, 0.59, labels.get('0011', ''), fontsize=fontsize)
    draw_text(fig, 0.32, 0.72, labels.get('0100', ''), fontsize=fontsize)
    draw_text(fig, 0.71, 0.30, labels.get('0101', ''), fontsize=fontsize)
    draw_text(fig, 0.50, 0.66, labels.get('0110', ''), fontsize=fontsize)
    draw_text(fig, 0.65, 0.50, labels.get('0111', ''), fontsize=fontsize)
    draw_text(fig, 0.14, 0.42, labels.get('1000', ''), fontsize=fontsize)
    draw_text(fig, 0.50, 0.17, labels.get('1001', ''), fontsize=fontsize)
    draw_text(fig, 0.29, 0.30, labels.get('1010', ''), fontsize=fontsize)
    draw_text(fig, 0.39, 0.24, labels.get('1011', ''), fontsize=fontsize)
    draw_text(fig, 0.23, 0.59, labels.get('1100', ''), fontsize=fontsize)
    draw_text(fig, 0.61, 0.24, labels.get('1101', ''), fontsize=fontsize)
    draw_text(fig, 0.35, 0.50, labels.get('1110', ''), fontsize=fontsize)
    draw_text(fig, 0.50, 0.38, labels.get('1111', ''), fontsize=fontsize)

    # legend
    draw_text(fig, 0.13, 0.18, names[0], fontsize=fontsize, ha="right")
    draw_text(fig, 0.18, 0.83, names[1], fontsize=fontsize, ha="right", va="bottom")
    draw_text(fig, 0.82, 0.83, names[2], fontsize=fontsize, ha="left", va="bottom")
    draw_text(fig, 0.87, 0.18, names[3], fontsize=fontsize, ha="left", va="top")
    #leg = ax.legend(names, loc='center left', bbox_to_anchor=(1.0, 0.5), fancybox=True)
    #leg.get_frame().set_alpha(0.5)
    return fig


def venn5(labels, names=['A', 'B', 'C', 'D', 'E'], **options):
    """
    plots a 5-set Venn diagram

    @type labels: dict[str, str]
    @type names: list[str]
    @rtype: (Figure, AxesSubplot)

    input
      labels: a label dict where keys are identified via binary codes ('00001', '00010', '00100', ...),
              hence a valid set could look like: {'00001': 'text 1', '00010': 'text 2', '00100': 'text 3', ...}.
              unmentioned codes are considered as ''.
      names:  group names
      more:   colors, figsize, dpi, fontsize

    return
      pyplot Figure and AxesSubplot object
    """
    colors = options.get('colors', [default_colors[i] for i in range(5)])
    figsize = options.get('figsize', (900, 900))
    fontsize = options.get('fontsize', 16)

    fig = figure_layout(x_range=[0, 1], y_range=[0, 1])

    # body
    draw_ellipse(fig, 0.428, 0.449, 0.87, 0.50, 155.0 * np.pi / 180, colors[0])
    draw_ellipse(fig, 0.469, 0.543, 0.87, 0.50, 82.0 * np.pi / 180, colors[1])
    draw_ellipse(fig, 0.558, 0.523, 0.87, 0.50, 10.0 * np.pi / 180, colors[2])
    draw_ellipse(fig, 0.578, 0.432, 0.87, 0.50, 118.0 * np.pi / 180, colors[3])
    draw_ellipse(fig, 0.489, 0.383, 0.87, 0.50, 46.0 * np.pi / 180, colors[4])
    draw_text(fig, 0.27, 0.11, labels.get('00001', ''), fontsize=fontsize)
    draw_text(fig, 0.72, 0.11, labels.get('00010', ''), fontsize=fontsize)
    draw_text(fig, 0.55, 0.13, labels.get('00011', ''), fontsize=fontsize)
    draw_text(fig, 0.91, 0.58, labels.get('00100', ''), fontsize=fontsize)
    draw_text(fig, 0.78, 0.64, labels.get('00101', ''), fontsize=fontsize)
    draw_text(fig, 0.84, 0.41, labels.get('00110', ''), fontsize=fontsize)
    draw_text(fig, 0.76, 0.55, labels.get('00111', ''), fontsize=fontsize)
    draw_text(fig, 0.51, 0.90, labels.get('01000', ''), fontsize=fontsize)
    draw_text(fig, 0.39, 0.15, labels.get('01001', ''), fontsize=fontsize)
    draw_text(fig, 0.42, 0.78, labels.get('01010', ''), fontsize=fontsize)
    draw_text(fig, 0.50, 0.15, labels.get('01011', ''), fontsize=fontsize)
    draw_text(fig, 0.67, 0.76, labels.get('01100', ''), fontsize=fontsize)
    draw_text(fig, 0.70, 0.71, labels.get('01101', ''), fontsize=fontsize)
    draw_text(fig, 0.51, 0.74, labels.get('01110', ''), fontsize=fontsize)
    draw_text(fig, 0.64, 0.67, labels.get('01111', ''), fontsize=fontsize)
    draw_text(fig, 0.10, 0.61, labels.get('10000', ''), fontsize=fontsize)
    draw_text(fig, 0.20, 0.31, labels.get('10001', ''), fontsize=fontsize)
    draw_text(fig, 0.76, 0.25, labels.get('10010', ''), fontsize=fontsize)
    draw_text(fig, 0.65, 0.23, labels.get('10011', ''), fontsize=fontsize)
    draw_text(fig, 0.18, 0.50, labels.get('10100', ''), fontsize=fontsize)
    draw_text(fig, 0.21, 0.37, labels.get('10101', ''), fontsize=fontsize)
    draw_text(fig, 0.81, 0.37, labels.get('10110', ''), fontsize=fontsize)
    draw_text(fig, 0.74, 0.40, labels.get('10111', ''), fontsize=fontsize)
    draw_text(fig, 0.27, 0.70, labels.get('11000', ''), fontsize=fontsize)
    draw_text(fig, 0.34, 0.25, labels.get('11001', ''), fontsize=fontsize)
    draw_text(fig, 0.33, 0.72, labels.get('11010', ''), fontsize=fontsize)
    draw_text(fig, 0.51, 0.22, labels.get('11011', ''), fontsize=fontsize)
    draw_text(fig, 0.25, 0.58, labels.get('11100', ''), fontsize=fontsize)
    draw_text(fig, 0.28, 0.39, labels.get('11101', ''), fontsize=fontsize)
    draw_text(fig, 0.36, 0.66, labels.get('11110', ''), fontsize=fontsize)
    draw_text(fig, 0.51, 0.47, labels.get('11111', ''), fontsize=fontsize)

    # legend
    draw_text(fig, 0.02, 0.72, names[0], fontsize=fontsize, ha="right")
    draw_text(fig, 0.72, 0.94, names[1], fontsize=fontsize, va="bottom")
    draw_text(fig, 0.97, 0.74, names[2], fontsize=fontsize, ha="left")
    draw_text(fig, 0.88, 0.05, names[3], fontsize=fontsize, ha="left")
    draw_text(fig, 0.12, 0.05, names[4], fontsize=fontsize, ha="right")
    # leg = ax.legend(names, loc='center left', bbox_to_anchor=(1.0, 0.5), fancybox=True)
    # leg.get_frame().set_alpha(0.5)

    return fig


def venn6(labels, names=['A', 'B', 'C', 'D', 'E', 'F'], **options):
    """
    plots a 6-set Venn diagram

    @type labels: dict[str, str]
    @type names: list[str]
    @rtype: (Figure, AxesSubplot)

    input
      labels: a label dict where keys are identified via binary codes ('000001', '000010', '000100', ...),
              hence a valid set could look like: {'000001': 'text 1', '000010': 'text 2', '000100': 'text 3', ...}.
              unmentioned codes are considered as ''.
      names:  group names
      more:   colors, figsize, dpi, fontsize

    return
      pyplot Figure and AxesSubplot object
    """
    colors = options.get('colors', default_colors[:6])
    figsize = options.get('figsize', (900, 900))
    fontsize = options.get('fontsize', 14)

    # fig = figure_layout(figsize, x_range=[0.173, 0.788], y_range=[0.230, 0.845])
    fig = figure_layout(x_range=[0.25, 0.75], y_range=[0.3, 0.75])

    # body
    # See https://web.archive.org/web/20040819232503/http://www.hpl.hp.com/techreports/2000/HPL-2000-73.pdf
    draw_triangle(fig, 0.637, 0.921, 0.649, 0.274, 0.188, 0.667, colors[0])
    draw_triangle(fig, 0.981, 0.769, 0.335, 0.191, 0.393, 0.671, colors[1])
    draw_triangle(fig, 0.941, 0.397, 0.292, 0.475, 0.456, 0.747, colors[2])
    draw_triangle(fig, 0.662, 0.119, 0.316, 0.548, 0.662, 0.700, colors[3])
    draw_triangle(fig, 0.309, 0.081, 0.374, 0.718, 0.681, 0.488, colors[4])
    draw_triangle(fig, 0.016, 0.626, 0.726, 0.687, 0.522, 0.327, colors[5])
    draw_text(fig, 0.27, 0.562, labels.get('000001', ''), fontsize=fontsize)
    draw_text(fig, 0.430, 0.249, labels.get('000010', ''), fontsize=fontsize)
    draw_text(fig, 0.356, 0.444, labels.get('000011', ''), fontsize=fontsize)
    draw_text(fig, 0.609, 0.255, labels.get('000100', ''), fontsize=fontsize)
    draw_text(fig, 0.323, 0.546, labels.get('000101', ''), fontsize=fontsize)
    draw_text(fig, 0.513, 0.316, labels.get('000110', ''), fontsize=fontsize)
    draw_text(fig, 0.523, 0.348, labels.get('000111', ''), fontsize=fontsize)
    draw_text(fig, 0.747, 0.458, labels.get('001000', ''), fontsize=fontsize)
    draw_text(fig, 0.325, 0.492, labels.get('001001', ''), fontsize=fontsize)
    draw_text(fig, 0.670, 0.481, labels.get('001010', ''), fontsize=fontsize)
    draw_text(fig, 0.359, 0.478, labels.get('001011', ''), fontsize=fontsize)
    draw_text(fig, 0.653, 0.444, labels.get('001100', ''), fontsize=fontsize)
    draw_text(fig, 0.344, 0.526, labels.get('001101', ''), fontsize=fontsize)
    draw_text(fig, 0.653, 0.466, labels.get('001110', ''), fontsize=fontsize)
    draw_text(fig, 0.363, 0.503, labels.get('001111', ''), fontsize=fontsize)
    draw_text(fig, 0.750, 0.616, labels.get('010000', ''), fontsize=fontsize)
    draw_text(fig, 0.682, 0.654, labels.get('010001', ''), fontsize=fontsize)
    draw_text(fig, 0.402, 0.310, labels.get('010010', ''), fontsize=fontsize)
    draw_text(fig, 0.392, 0.421, labels.get('010011', ''), fontsize=fontsize)
    draw_text(fig, 0.653, 0.691, labels.get('010100', ''), fontsize=fontsize)
    draw_text(fig, 0.651, 0.644, labels.get('010101', ''), fontsize=fontsize)
    draw_text(fig, 0.490, 0.340, labels.get('010110', ''), fontsize=fontsize)
    draw_text(fig, 0.468, 0.399, labels.get('010111', ''), fontsize=fontsize)
    draw_text(fig, 0.692, 0.545, labels.get('011000', ''), fontsize=fontsize)
    draw_text(fig, 0.666, 0.592, labels.get('011001', ''), fontsize=fontsize)
    draw_text(fig, 0.665, 0.496, labels.get('011010', ''), fontsize=fontsize)
    draw_text(fig, 0.374, 0.470, labels.get('011011', ''), fontsize=fontsize)
    draw_text(fig, 0.653, 0.537, labels.get('011100', ''), fontsize=fontsize)
    draw_text(fig, 0.652, 0.579, labels.get('011101', ''), fontsize=fontsize)
    draw_text(fig, 0.653, 0.488, labels.get('011110', ''), fontsize=fontsize)
    draw_text(fig, 0.389, 0.486, labels.get('011111', ''), fontsize=fontsize)
    draw_text(fig, 0.553, 0.75, labels.get('100000', ''), fontsize=fontsize)
    draw_text(fig, 0.313, 0.604, labels.get('100001', ''), fontsize=fontsize)
    draw_text(fig, 0.388, 0.694, labels.get('100010', ''), fontsize=fontsize)
    draw_text(fig, 0.375, 0.633, labels.get('100011', ''), fontsize=fontsize)
    draw_text(fig, 0.605, 0.359, labels.get('100100', ''), fontsize=fontsize)
    draw_text(fig, 0.334, 0.555, labels.get('100101', ''), fontsize=fontsize)
    draw_text(fig, 0.582, 0.397, labels.get('100110', ''), fontsize=fontsize)
    draw_text(fig, 0.542, 0.372, labels.get('100111', ''), fontsize=fontsize)
    draw_text(fig, 0.468, 0.708, labels.get('101000', ''), fontsize=fontsize)
    draw_text(fig, 0.355, 0.572, labels.get('101001', ''), fontsize=fontsize)
    draw_text(fig, 0.420, 0.679, labels.get('101010', ''), fontsize=fontsize)
    draw_text(fig, 0.375, 0.597, labels.get('101011', ''), fontsize=fontsize)
    draw_text(fig, 0.641, 0.436, labels.get('101100', ''), fontsize=fontsize)
    draw_text(fig, 0.348, 0.538, labels.get('101101', ''), fontsize=fontsize)
    draw_text(fig, 0.635, 0.453, labels.get('101110', ''), fontsize=fontsize)
    draw_text(fig, 0.370, 0.548, labels.get('101111', ''), fontsize=fontsize)
    draw_text(fig, 0.594, 0.689, labels.get('110000', ''), fontsize=fontsize)
    draw_text(fig, 0.579, 0.670, labels.get('110001', ''), fontsize=fontsize)
    draw_text(fig, 0.398, 0.670, labels.get('110010', ''), fontsize=fontsize)
    draw_text(fig, 0.395, 0.653, labels.get('110011', ''), fontsize=fontsize)
    draw_text(fig, 0.633, 0.682, labels.get('110100', ''), fontsize=fontsize)
    draw_text(fig, 0.616, 0.656, labels.get('110101', ''), fontsize=fontsize)
    draw_text(fig, 0.587, 0.427, labels.get('110110', ''), fontsize=fontsize)
    draw_text(fig, 0.526, 0.415, labels.get('110111', ''), fontsize=fontsize)
    draw_text(fig, 0.495, 0.677, labels.get('111000', ''), fontsize=fontsize)
    draw_text(fig, 0.505, 0.648, labels.get('111001', ''), fontsize=fontsize)
    draw_text(fig, 0.428, 0.663, labels.get('111010', ''), fontsize=fontsize)
    draw_text(fig, 0.430, 0.631, labels.get('111011', ''), fontsize=fontsize)
    draw_text(fig, 0.639, 0.524, labels.get('111100', ''), fontsize=fontsize)
    draw_text(fig, 0.591, 0.604, labels.get('111101', ''), fontsize=fontsize)
    draw_text(fig, 0.622, 0.477, labels.get('111110', ''), fontsize=fontsize)
    draw_text(fig, 0.501, 0.523, labels.get('111111', ''), fontsize=fontsize)

    # legend
    # draw_text(fig, 0.3, 0.77, names[0], fontsize=fontsize)
    # draw_text(fig, 0.69, 0.751, names[1], fontsize=fontsize)
    # draw_text(fig, 0.71, 0.41, names[2], fontsize=fontsize)
    # draw_text(fig, 0.700, 0.247, names[3], fontsize=fontsize)
    # draw_text(fig, 0.291, 0.255, names[4], fontsize=fontsize)
    # draw_text(fig, 0.203, 0.484, names[5], fontsize=fontsize)
    # leg = ax.legend(names, loc='center left', bbox_to_anchor=(1.0, 0.5), fancybox=True)
    # leg.get_frame().set_alpha(0.5)

    return fig

