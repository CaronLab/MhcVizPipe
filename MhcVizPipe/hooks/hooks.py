from PyInstaller.utils.hooks import collect_all


def hook(hook_api):
    packages = [
        'plotly',
        'dominate',
        'dash',
        'dash_renderer',
        'dash_core_components',
        'dash_html_components',
        'dash_bootstrap_components',
        'PlotlyLogo',
        'MhcVizPipe',
        'waitress',
        'flask',
        'flask_compress',
        'seaborn',
        'six',
        'appdirs'
    ]
    for package in packages:
        datas, binaries, hiddenimports = collect_all(package)
        hook_api.add_datas(datas)
        hook_api.add_binaries(binaries)
        hook_api.add_imports(*hiddenimports)
