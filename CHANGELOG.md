# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0]

### Changed

- Refactored a lot of things to improve the Windows standalone version. It now only runs the DTU Health Tech tools 
with WSL, rather than everything.

## [0.6.1]

### Fixed

- Removed unused matplotlib imports

## [0.6.0]

### Added

- Added a changelog!
- GibbsCluster will no longer be run when there are fewer than 20 peptides. This will hopefully prevent it from getting
  stuck.

### Changed

- You can now give different alleles to each sample.
- Individual samples can now be deleted after you load them.
- UpSet plots are now generated with [UpsetSetPlotly](https://github.com/kevinkovalchik/upsetplotly). This allows us
to use Plotly for all the figures, and also makes the report more consistent in style.
- Some simple quality metrics have been added: LF Score (length fraction) and BF Score (binding fraction).
  - LF Score = the fraction of peptides with a length of 8-12 mers (for class I) or 9-22 mers (for class II).
  - BF Score = the fraction of peptides which are predicted to be weak or strong binders for at least one allele.
  - These scores have been combined with the "sample overview" table.
  - There is a color gradient applied to the cells containing these scores. Green = "good", red = "bad".