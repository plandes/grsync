# Configuration

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


## Variable Substitution

The configuration file can be leveraged for variable substitution using a
`^{name}` syntax where `name` is any dot (.) separated path.  The
`discovery.codedir` variable in the [configuration file] is an example of a
variable with substituions in the `objects` entry.  The exception to variable
names in the configuration file are those given to define repositories, files,
etc.


## Links

Configuration link entries tell the program what symolic links to create.
This is useful when you have a repository that keeps track of your
confgiuration information on a per OS or host basis.  For example, your
`~/.profile` might include different `PATH` set up on MacOS vs. Linux.

[Variable substitution](#variable-substitution) is allowed in both the source
and target paths.


## Profiles

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


### Excluding Top Level Objects

The top level objects (i.e. `objects` and `empty_dirs`) are always added to the
distribution with one exception: by excluding the *default* profile.  The
*default* profile is a special profile that includes all default objects to the
distribution.  If you don't want these top level elements, you can specify a
special `nodefault` keyword.


## Example Configuration

See the [test case yaml file](test-resources/midsize-test.yml) for an example
of a simple configuration file to capture a set of git repositories and small
set of files.  The freeze/thaw/move test case uses [this configuration
file](test-resources/fs-test.yml), which is more comprehensive and up to date
and follows.

```yaml
## this file is only available on a freeze, not thaw

discover:
  test_dir: ./target/mock
  # a variable binding used for interpolation later on
  view: ^{discover.test_dir}/view
  # indicate whether or not to create wheels from dependencies
  # specify directories to unthaw on the atarget
  empty_dirs:
    - ^{discover.test_dir}/opt/empty_dir
  # specify repositories, symbol links and files that will (recursively) be
  # added to the target un unthaw
  objects:
    - ^{discover.view}/repo_def
    - ^{discover.test_dir}/dir_a
    - ^{discover.test_dir}/symlink_to_repo
    - ^{discover.test_dir}/symlink.txt
    - ^{discover.test_dir}/no_dst_symlink_to_a_dir
    - ^{discover.test_dir}/no_dst_symlink_to_a_file.txt
    - ^{discover.test_dir}/dir_w_symlinks/*
    - ^{discover.test_dir}/file_0.txt
  # profiles configuration, defined on the next line if none given on the
  # command line (or empty for using only the default)
  default_profiles: source
  profiles:
    # source and open source repositories
    source:
      objects:
        - ^{discover.view}/repo_src
  # default remote when thawing repositories
  repo:
    remote_pref: github
  target:
    links:
      - link:
          source: ^{discover.test_dir}/profile_{os}
          target: ^{discover.test_dir}/dir_a/dir_b/file_b.txt
  # indicate to create all wheel dependencies (useful for target machine
  # offline--see docs)
  wheel:
    create: false
  # used to freeze the distribution zip file
  local:
    # the default location if the -d flag is not given on the command line
    dist_dir: ./dist
    # the directory to add the dependency wheels (if discover.wheel.create is
    # true)
    wheels_dir: wheels
  # used to create the bootstrap script--you probably want to leave this alone
  bootstrap:
    inst_dir: ${HOME}/grsync
    python_dir: ${HOME}/opt/lib/python3
    wheel_dir: ^{discover.local.wheels_dir}
```
