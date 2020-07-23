import plotly.graph_objects as go
from dominate.util import raw
from dominate.tags import *
from dominate import document


def plot(width: str = '100%', height: str = '100%'):
    fig = go.Figure()
    fig.add_trace(go.Bar(y=[1, 2, 3, 2]))
    fig.layout.margin = {'t': 0, 'b': 0, 'r': 10, 'l': 10}
    fig = fig.to_html(include_plotlyjs='cdn', full_html=False, default_height=height, default_width='100%')
    return div(raw(fig), style=f'width: {width}')

def a_plot():
    fig = go.Figure()
    fig.add_trace(go.Bar(y=[1, 2, 3, 2]))
    fig.layout.margin = {'t': 0, 'b': 0, 'r': 10, 'l': 10}
    return fig

def wrap_plotly_fig(fig: go.Figure, width: str = '100%', height: str = '100%'):
    fig = fig.to_html(include_plotlyjs='cdn', full_html=False, default_height=height, default_width='100%')
    return div(raw(fig), style=f'width: {width}')


doc = document(title='MhcQcPipe Report')
with doc.head:
    link(rel="stylesheet", href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css",
         integrity="sha384-9aIt2nRpC12Uk9gS9baDl411NQApFmC26EwAOH8WgZl5MYYxFfc+NcPb1dKGj7Sk",
         crossorigin="anonymous")
    link(rel="stylesheet", href='/home/labcaron/Projects/MhcQcPipe/MhcQcPipe/assets/report_style.css')
    # script(type='text/javascript', src='https://cdn.plot.ly/plotly-latest.min.js')
    script(src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js")
    script(src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.0/js/bootstrap.min.js")

with doc:
    with div(className='container'):
        with div(className='row'):
            with div(style="width: 100%"):
                plot()
        with div(className='row'):
            with div(className='card', style="width: 100%"):
                div('test', className='card-header')
                with div(className='card-body'):
                    with div(className='row'):
                        wrap_plotly_fig(a_plot(), width='200px', height='200px')
                        wrap_plotly_fig(a_plot(), width='200px', height='500px')
                    with div(className='row'):
                        wrap_plotly_fig(a_plot(), width='50%', height='360px')

with open('./out.html', 'w') as f:
    f.write(doc.render())
