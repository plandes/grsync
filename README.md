# Persist and create build out environments in a nascent account

[![Travis CI Build Status][travis-badge]][travis-link]
[![PyPI][pypi-badge]][pypi-link]

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


<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
## Table of Contents

- [Obtaining](#obtaining)
- [Overview](#overview)
- [Usage](#usage)
    - [Repository Information](#repository-information)
    - [Moving or Deleting Distributions](#moving-or-deleting-distributions)
    - [Command Line Help](#command-line-help)
- [Configuration](#configuration)
    - [Variable Substitution](#variable-substitution)
    - [Links](#links)
    - [Profiles](#profiles)
        - [Excluding Top Level Objects](#excluding-top-level-objects)
    - [Example Configuration](#example-configuration)
- [Symbolic Links](#symbolic-links)
- [Requirements](#requirements)
- [Planned Future Features](#planned-future-features)
- [Changelog](#changelog)
- [License](#license)

<!-- markdown-toc end -->


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

First the distribution is created as a configuration file along with saved
files in a distribution zip file.  This distribution file is then copied to the
target machine that is to be configured with the user's home directory setup.
The distribution also includes a bootstrap script that creates a Python virtual
environment and then invokes the program to *thaw* the distributing.

1. [Install](#obtaining) the `grsync` program.
2. Decide what you want to transfer to the target system (see
   [configuration](#configuration)).  This file explains each section of the
   file with inline comments and should be sufficient to munge your own.
3. Create the distribution, for example: `grsync freeze -c grsync.yml -d ./dist`.
4. Copy the distribution zip file to the host, for example: `scp -r ./dist
   ~/<somehost>`
5. Log into that host: `slogin <host>`
6. Call the bootstrapper: `cd ./dist && ./bootstrap.sh /usr/bin ./dist python3.6`
   This attempts to create the Python virtual environment, install the program
   dependencies and *thaw* the distribution.

   To do this step manually:
   1. [Install](#obtaining) the `grsync` program.
   2. Thaw the distribution on the target: `grsync thaw -d ./dist`


### Repository Information

As you build your `grsync.yml` [configuration file] (see the
[configuration](#configuration section)), it's helpful to see what repositories
it's finding.  This is you can do this with the `repos` and `repoinfo`, which
show repositories, remotes, and indexed symbol links to or within the
repositories.


### Moving or Deleting Distributions

A common usecase is migrate a distribution several times to a target host after
the original host has changed.  However, the thaw process does not clobber file
system objects that already exist, which implies that for each file set change
and thaw the target host's files won't update.

Only files specified in the [configuration file] are moved to a directory with
the same directory structure by moving files.  If a directory is specified, the
directory itself is moved.  If a file is specified for which there is no
directory in the target, the directory is created.

After everything is moved, a process called *directory reduction* occurs by
which empty directories are removed.  This is an optional step given to the
`move` action.

Because the action works with a distribution file (ideally the original) you
must specify where to find the `dist.zip`.  In situations where you've already
deleted the original distribution zip, you'll have to create a new distribution
by freezing what you have.  For this reason it is recommended that you always
include the original `grsync.yml` [configuration file] (see the
[configuration](#configuration section)) in your distribution so it *migrates*
along with each of your freeze/thaw iterations.


### Command Line Help

This information is given by the command line `grsync -h`, but repeated here
for convenience:
```sql
Usage: usage: grsync <list|freeze|info|repoinfo|repos|thaw> [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -w NUMBER, --whine=NUMBER
						add verbosity to logging
  -c FILE, --config=FILE
						configuration file
Actions:
  freeze    Create a distribution
  -d, --distdir <string>                    the location of build out distribution
  --wheeldep <string>       zensols.grsync  used to create the wheel dep files
  -p, --profiles <string>                   comma spearated list of objects to freeze

  info      Pretty print discovery information

  repoinfo  Get information on repositories
  -n, --name <string>                       comma spearated list of repo names
  -p, --profiles <string>                   comma spearated list of objects to freeze

  repos     Output all repository top level info
  -f, --format <string>     {path}          format string (i.e. {name}: {path} ({remotes}))
  -p, --profiles <string>                   comma spearated list of objects to freeze

  thaw      Build out a distribution
  -d, --distdir <string>                    the location of build out distribution
  -t, --targetdir <string>                  the location of build out target dir
  -p, --profiles <string>                   comma spearated list of objects to freeze
```


## Configuration

The configuration is used the *freeze* phase to create the distribution file.
This fil contains all git repositories, files, empty directory paths on the
current file system that is stored to be *thawed* on the target system.

The structure of the configuration file is not validated, and generally
speaking, can be leveraged for variable substitution (see [variable
substitution](#variable-substitution).  An overview of the structure follows:

* **discover**: root
  * **objects**: a list of files, directories and repository directories.
  * **empty_dirs**: A list of directories.
  * **target**: contains information used during the *thaw* process on the
	target host.
	* **config**: the path to create this configuration file, which is optional
	  and should not be given if already declared in as an **object** file
	  entry.
	* **links**: a list of file path pattern symbolic links to create during
	  the **thaw** (see [links](#links)).
	  * **link**: a specific link entry.
		* **source**: the source path at *thaw* time of the symbolic link.
		* **target**: the target path at *thaw* time of the symbolic link.
	* **default_profiles**: a comma-separated list of profile names (including
	  `nodefault`) to be used when the command line option (`-p`) is not given.
	  See [profiles](#profiles).
	* **profiles**: contains all profile definitions for this configuration
	  file.
		* **`<any valid YAML string>`**: this profile name
		  * **objects**: same as top level but pertains only to this profile.
		  * **empty_dirs**: same as top level but pertains only to this profile.
	* **repo**: contains information used when thawing repositories.
	  * **remote_pref**: the remote (and respective URL) to make the primary
		'master' default repository when thawing the repository.  This is
		helpful when there are more than one remotes.
  * **wheel**: instructs the program on what/how wheels are created during the
	*freeze* process.
	* **create**: if `true` create wheels.
  * **local**: specifies how to create the distribution during the *freeze*
	process.
	  * **dist_dir**: the default directory to create the distribution (used
		when not specified on the command line with `-d`).
	  * **wheels_dir**: the directory of where to create the wheels when wheel
		creation is turned on.
  * **bootstrap**: indicates target information used to create the bootstrap
	script/process.
	* **inst_dir**: install directory of the boot strap files on the target on
	  *thaw*.
	* **python_dir**: where the virutal environment python directory is
	  created.
	* **wheel_dir**: location of the wheels directory (if created during
	  *freeze*) to be installed during bootstrap.


### Variable Substitution

The configuration file can be leveraged for variable substitution using a
`^{name}` syntax where `name` is any dot (.) separated path.  The
`discovery.codedir` variable in the [configuration file] is an example of a
variable with substituions in the `objects` entry.  The exception to variable
names in the configuration file are those given to define repositories, files,
etc.


### Links

Configuration link entries tell the program what symolic links to create.
This is useful when you have a repository that keeps track of your
confgiuration information on a per OS or host basis.  For example, your
`~/.profile` might include different `PATH` set up on MacOS vs. Linux.

[Variable substitution](#variable-substitution) is allowed in both the source
and target paths.


### Profiles

Profiles allow you to generate a *frozen* distribution of a subset of declared
repositories and files.  The idea is similar [maven-profiles] with each having
a top level name in the configuration that mirrors the same structure as under
the `discover` level in the [configuration file] with entry `profiles`.

Profiles are always given in a comma-separated list to allow more than one
profile to be added to the list of objects to *freeze*.

The order in which the program decides what profiles to use is (only one of)
the following:
1. Command line with option `-p`.
2. Configuration file.
3. All profiles.


#### Excluding Top Level Objects

The top level objects (i.e. `objects` and `empty_dirs`) are always added to the
distribution with one exception: by excluding the *default* profile.  The
*default* profile is a special profile that includes all default objects to the
distribution.  If you don't want these top level elements, you can specify a
special `nodefault` keyword.


### Example Configuration

See the [test case yaml file](test-resources/midsize-test.yml) for an example
of a simple configuration file to capture a set of git repositories and small
set of files.  The freeze/thaw/move test case uses [this configuration
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

* At least [Python 3.6]
* A system that supports [PyYAML]


## Planned Future Features

Preserve and restore file and directory timestamps.


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## License

Copyright (c) 2018-2019 Paul Landes

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


<!-- links -->
[travis-link]: https://travis-ci.org/plandes/grsync
[travis-badge]: https://travis-ci.org/plandes/grsync.svg?branch=master
[pypi]: https://pypi.org/project/zensols.grsync/
[pypi-link]: https://pypi.python.org/pypi/zensols.grsync
[pypi-badge]: https://img.shields.io/pypi/v/zensols.grsync.svg

[Python 3.6]: https://www.python.org
[PyYAML]: https://pyyaml.org
[test configuration]: test-resources/grsync-test.yml

[maven profiles]: https://maven.apache.org/guides/introduction/introduction-to-profiles.html
[configuration file]: test-resources/midsize-test.yml#L29
[configuration file profile entry]: test-resources/midsize-test.yml#L29
[pip]: https://docs.python.org/3/installing/index.html
[Puppet]: https://en.wikipedia.org/wiki/Puppet_(software)
