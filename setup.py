from setuptools import setup, find_packages
from MhcVizPipe import __version__

setup(
    name='MhcVizPipe',
    version=__version__,
    packages=find_packages(),
    url='https://github.com/CaronLab/MhcVizPipe',
    license='MIT',
    author='Kevin Kovalchik',
    author_email='',
    description='A reporting pipeline for visualization of immunopeptidomics MS data.',
    python_requires='>=3.7',
    include_package_data=True,
    install_requires=[
        'dash>=1.12.0',
        'plotly',
        'dash-bootstrap-components',
        'pandas',
        'numpy',
        'dominate',
        'upsetplot',
        'seaborn',
        'plotly-logo',
        'waitress',
        'kaleido',
        'johnnydep',
        'structlog'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
