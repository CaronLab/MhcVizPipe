from setuptools import setup, find_packages

setup(
    name='MhcVizPipe',
    version='',
    packages=find_packages(),
    url='https://github.com/kevinkovalchik/MhcVizPipe',
    license='MIT',
    author='Kevin Kovalchik',
    author_email='',
    description='A reporting pipeline for visualization of immunopeptidomics MS data.',
    python_requires='>=3.7',
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
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
