# Usage

The program has two phases: *freeze* and *thaw* (see [overview](#overview)).
The command line program is used twice: first on the *freeze* on the source
system and then *thaw* on the target machine.

First the distribution is created as a configuration file along with saved
files in a distribution zip file.  This distribution file is then copied to the
target machine that is to be configured with the user's home directory setup.
The distribution also includes a bootstrap script that creates a Python virtual
environment and then invokes the program to *thaw* the distributing.

1. Install the `grsync` program (`pip install zensols.grsync`).
2. Decide what you want to transfer to the target system (see
[configuration](#configuration.md)).  This file explains each section of the
file with inline comments and should be sufficient to munge your own.
3. Create the distribution, for example: `grsync freeze -c grsync.yml -d ./dist`.
4. Copy the distribution zip file to the host, for example: `scp -r ./dist
~/<somehost>`
5. Log into that host: `slogin <host>`
6. Call the bootstrapper: `cd ./dist && ./bootstrap.sh /usr/bin ./dist python3.7`
This attempts to create the Python virtual environment, install the program
dependencies and *thaw* the distribution.

To do this step manually:
1. Install the `grsync` program (`pip install zensols.grsync`).
2. Thaw the distribution on the target: `grsync thaw -d ./dist`


## Repository Information

As you build your `grsync.yml` [configuration file] (see the
[configuration](#configuration section)), it's helpful to see what repositories
it's finding.  This is you can do this with the `repos` and `repoinfo`, which
show repositories, remotes, and indexed symbol links to or within the
repositories.


## Moving or Deleting Distributions

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


## Command Line Help

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
