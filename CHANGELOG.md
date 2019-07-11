# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]


## [0.0.13] - 2019-07-10
### Added
- Reduce directory on move option for the CLI.
- Version check on distribution.
- Fix thawing links on non-existent directories (usually repos not yet
  unfrozen).
- Refactored path translation.
- Add restore modification time on files.
- Added command line option for repository preference which sets master on
  thaw.

### Changed
- Protection around file system operations on thaw for robustness.


## [0.0.12] - 2019-06-23
### Changed
- CLI conflicting short option bug.


## [0.0.11] - 2019-06-23
### Added
- Move/delete thawed distributions allows you to remove an installed thawed
  distribution.
- Thaw directory is now configurable and no longer pinned to the user home
  directory.
- More tests, much better docs, refactored classes and containing source files.

### Changed
- Removed hard coded mode on thaw when creating directories.


### [0.0.9] - 2019-05-27
### Added
- Method to exclude the default profile.

### Changed
- Much more documentation.
- Skip empty directories during freeze if non-existent.


### [0.0.8] - 2019-01-17
### Added
- Profiles.

### Changed
- Better symbolic link support.
- Better CLI integration.


## [0.0.7] - 2018-09-14
### Changed
- Bug fixes and more robust bootstrap install.


## [0.0.6] - 2018-09-01
### Added
- Initial version


[Unreleased]: https://github.com/plandes/grsync/compare/v0.0.13...HEAD
[0.0.13]: https://github.com/plandes/grsync/compare/v0.0.12...v0.0.13
[0.0.12]: https://github.com/plandes/grsync/compare/v0.0.11...v0.0.12
[0.0.11]: https://github.com/plandes/grsync/compare/v0.0.10...v0.0.11
[0.0.10]: https://github.com/plandes/grsync/compare/v0.0.10...v0.0.10
[0.0.9]: https://github.com/plandes/grsync/compare/v0.0.8...v0.0.9
[0.0.8]: https://github.com/plandes/grsync/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/plandes/grsync/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/plandes/grsync/compare/v0.0.5...v0.0.6
