# Persist and create build out environments in a nascent account

[![Travis CI Build Status][travis-badge]][travis-link]

This program captures your home directory and synchronize it with another host
using Git repo metadata, symbolic links and persisted files.

I wrote this because I couldn't find anything that creates repositories with
the idea of having a portable and easy to recreate your home directory on
another host.  If I've reinvented the wheel, please let me know :)

More specifically: it persists and creates build out environments in a nascent
account.  The program *memorizing* a users home directory and building it out
on another system.  This is done by:
1. Copying files, directories and git repos configuration.
2. Creating a distribution compressed file.
3. Uncompress on the destination system and create repos.

A future release will also synchronize and manage multiple GitHub repositories.


<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
## Table of Contents

- [Obtaining](#obtaining)
- [Usage](#usage)
- [Requirements](#requirements)
- [Changelog](#changelog)
- [License](#license)

<!-- markdown-toc end -->


## Obtaining

The easist way to install the command line program is via the `pip` installer:
```bash
pip install zensols.grsync
```

Binaries are also available on [pypi].


## Usage

The program has two phases: freeze and thaw.  Git repositories (URLs and
configuration, not files), symbolic links and files are first *froozen* into a
distribution zip.

This distribution file is then copied to the target machine that is to be
configured with the user's home directory setup.  The distribution also
includes a bootstrap script that creates a Python virtual environment and then
invokes the program to *thaw* the distributing.

1. [Install](#obtaining) the `grsync` program.
2. Decide what you want to transfer to the target system (see [test
   configuration] file).  This file explains each section of the file with
   inline comments and should be sufficient to munge your own.
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


## Requirements

* At least [Python 3.6]
* A system that supports [PyYAML]


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## License

Copyright (c) 2018 Paul Landes

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

[Python 3.6]: https://www.python.org
[PyYAML]: https://pyyaml.org
[test configuration]: test-resources/grsync-test.yml
