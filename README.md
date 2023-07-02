# GRSync: Persist create build out environments

[![PyPI][pypi-badge]][pypi-link]
[![Python 3.9][python39-badge]][python39-link]
[![Python 3.10][python310-badge]][python310-link]
[![Build Status][build-badge]][build-link]

This program captures your home directory and synchronize it with another host
using Git repo metadata, symbolic links and persisted files.

I wrote this because I couldn't find anything that creates repositories with
the idea of having a portable and easy to recreate your home directory on
another host.  If I've reinvented the wheel, please let me know :)

More specifically: it persists and creates build out environments in a nascent
account.  The program *memorizing* a users home directory and building it out
on another system (see [overview](#overview)).  This is done by:
1. Copying files, directories and git repos configuration.
2. Creating a distribution compressed file.
3. Uncompress on the destination system and create repos.

A future release will also synchronize and manage multiple GitHub repositories.

A [utility script] also provided to do operations on all configured local git
repositories.


## Documentation

See the [full documentation](https://plandes.github.io/grsync/index.html).  The
[API reference](https://plandes.github.io/grsync/api.html) is also available.


## Obtaining

The easist way to install the command line program is via the `pip` installer:
```bash
pip install zensols.grsync
```

Binaries are also available on [pypi].

## Overview

Not only is the aim to create a repproducable development (or like)
environment, it is also to create a *clean* environment.  This means we have
temporary directories we might expect to exist for our process(es), and of
course repositories cloned in their nascent state.  These steps are summarized
below:

1. **Freeze**: This process captures the current host's setup and
configuration (specified in the [configuration file]) and includes:
* Empty directories.
* Git repository meta data.
* Locations of files to copy, top level directories of files to recursively
copy, where symlinks are considered files as well and currently not
followed.  See [caveat](#symbolic-links).

A sub-step of this process is *discover*, which reads the file system as
indicated by the configuration file.  This includes reading git repostiory
metadata, identifying file metadata (i.e. permissions) etc.
1. **Bootstraping**: create an Python virtual environment on the target machine
that can be loaded with this program and depenedencies.  This is not a
necessary step as the program is available as a [pip] install.  However, if
this step can be used to help automate new environments, after which, you
could futher add/install software with tools such as [Puppet].
3. **Thaw**: This includes two steps:
1. **File Extraction**: extracts the files from the distribution zip created
in the *freeze* step.
2. **Repo Cloning**: this step recursively clones all repositories.


## Usage

The program has two phases: *freeze* and *thaw* (see [overview](#overview)).
The command line program is used twice: first on the *freeze* on the source
system and then *thaw* on the target machine.

See [usage](https://plandes.github.io/grsync/doc/usage.html) for more information.


## Configuration

The configuration is used the *freeze* phase to create the distribution file.
This fil contains all git repositories, files, empty directory paths on the
current file system that is stored to be *thawed* on the target system.

See [configuration](doc/configuration.md) for detailed documentation on
configuration [test case yaml file](test-resources/midsize-test.yml) for an
example of a simple configuration file to capture a set of git repositories and
small set of files.  The freeze/thaw/move test case uses [this configuration
file](test-resources/fs-test.yml), which is more comprehensive and up to date.


## Symbolic Links

As mentioned in the [usage](#usage) section, symbolic links pointing to any
file in a repository are *froozen*, which means that integrity at thaw time is
ensured.  However, links **not** pointing to a repository are persisted, but
the files and directories they point to are not.

A future release might have a *follow symbolic links* type functionality that
allows this.  However, for now, you must include both the link and the data it
points to get this integrity.


## Requirements

* At least [Python 3.9]
* A system that supports [PyYAML]


## Planned Future Features

Preserve and restore file and directory timestamps.


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## License

[MIT License](LICENSE.md)

Copyright (c) 2020 - 2023 Paul Landes


<!-- links -->
[pypi]: https://pypi.org/project/zensols.grsync/
[pypi-link]: https://pypi.python.org/pypi/zensols.grsync
[pypi-badge]: https://img.shields.io/pypi/v/zensols.grsync.svg
[python39-badge]: https://img.shields.io/badge/python-3.9-blue.svg
[python39-link]: https://www.python.org/downloads/release/python-390
[python310-badge]: https://img.shields.io/badge/python-3.10-blue.svg
[python310-link]: https://www.python.org/downloads/release/python-3100
[build-badge]: https://github.com/plandes/grsync/workflows/CI/badge.svg
[build-link]: https://github.com/plandes/grsync/actions

[Python 3.9]: https://www.python.org
[PyYAML]: https://pyyaml.org
[test configuration]: test-resources/grsync-test.yml

[maven profiles]: https://maven.apache.org/guides/introduction/introduction-to-profiles.html
[configuration file]: test-resources/midsize-test.yml#L29
[configuration file profile entry]: test-resources/midsize-test.yml#L29
[pip]: https://docs.python.org/3/installing/index.html
[Puppet]: https://en.wikipedia.org/wiki/Puppet_(software)
[utility script]: https://plandes.github.io/grsync/doc/usage.html#utility-git-script
