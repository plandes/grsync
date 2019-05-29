import logging
import itertools as it
import json
import zipfile
import shutil
import platform
from git.exc import GitCommandError
import pprint
from pathlib import Path
from zensols.actioncli import YamlConfig, persisted
from zensols.grsync import (
    Discoverer,
    FrozenRepo,
    BootstrapGenerator,
)

logger = logging.getLogger(__name__)


class FileEntry(object):
    def __init__(self, dist, finfo: dict):
        self.dist = dist
        self.finfo = finfo

    def _str_to_path(self, pathstr: str):
        return Path(pathstr)

    def _target_relative(self, path):
        return self.dist._target_relative(path)

    @property
    @persisted('_rel')
    def relative(self):
        return Path(self._str_to_path(self.finfo['rel']))

    @property
    @persisted('_path')
    def path(self):
        return self._target_relative(self.relative)

    @property
    @persisted('_mode')
    def mode(self):
        return self.finfo['mode']

    @property
    @persisted('_modestr')
    def modestr(self):
        return self.finfo['modestr']

    def __str__(self):
        return f'{self.relative} -> {self.path}: {self.mode} ({self.modestr})'

    def __repr__(self):
        return self.__str__()


class LinkEntry(FileEntry):
    def __init__(self, dist, finfo: dict, target_dir=None):
        super(LinkEntry, self).__init__(dist, finfo)
        self.target_dir = target_dir

    def _str_to_path(self, pathstr: str):
        return Path(pathstr.format(**self.dist.params))

    def _target_relative(self, path):
        if self.target_dir is not None:
            return Path(self.target_dir, path)
        else:
            return super(LinkEntry, self)._target_relative(path)

    @property
    @persisted('_rel')
    def relative(self):
        return Path(self._str_to_path(self.finfo['source']))

    @property
    def source(self):
        return self.path

    @property
    def target(self):
        rel_path = Path(self._str_to_path(self.finfo['target']))
        rel_path = self._target_relative(rel_path)
        return rel_path

    def __str__(self):
        return f'{self.source} -> {self.target}'


class Distribution(object):
    def __init__(self, struct: list, target_dir: Path):
        self.struct = struct
        self.target_dir = target_dir
        self.params = {'os': platform.system().lower()}

    def _target_relative(self, path):
        """Return a path that is relative to where we're thawing the distribution,
        which is usually the user's home directory.

        """
        return Path.joinpath(self.target_dir, path)

    @property
    @persisted('_files')
    def files(self) -> list:
        return map(lambda fi: FileEntry(self, fi), self.struct['files'])

    @property
    @persisted('_empty_dirs')
    def empty_dirs(self) -> list:
        return map(lambda fi: FileEntry(self, fi), self.struct['empty_dirs'])

    @property
    @persisted('_links')
    def links(self) -> list:
        return map(lambda fi: LinkEntry(self, fi), self.struct['links'])

    @property
    @persisted('_repos')
    def repos(self) -> list:
        repos = []
        repo_pref = self.struct['repo_pref']
        for rdef in self.struct['repo_specs']:
            links = tuple(map(lambda fi: LinkEntry(self, fi),
                              rdef['links']))
            repo = FrozenRepo(rdef['remotes'], links, self.target_dir,
                              self._target_relative(rdef['path']), repo_pref)
            repos.append(repo)
        return repos


class FreezeManager(object):
    def __init__(self, config, dist_file, defs_file, discoverer):
        self.config = config
        self.dist_file = dist_file
        self.defs_file = defs_file
        self.discoverer = discoverer

    def _create_wheels(self, wheel_dependency):
        """Create wheel dependencies on this software so the host doesn't need Internet
        connectivity.  Currently the YAML dependency breaks this since only
        binary per host wheels are available for download and the wrong was is
        given of spanning platforms (i.e. OSX to Linux).

        """
        wheel_dir_name = self.config.wheel_dir_name
        wheel_dir = Path(self.dist_dir, wheel_dir_name)
        logger.info(f'creating wheels from dependency {wheel_dependency} in {wheel_dir}')
        if not wheel_dir.exists():
            wheel_dir.mkdir(parents=True, exist_ok=True)
        from pip._internal import main
        pip_cmd = f'wheel --wheel-dir={wheel_dir} --no-cache-dir {wheel_dependency}'
        logger.debug('pip cmd: {}'.format(pip_cmd))
        main(pip_cmd.split())

    def _freeze_dist(self):
        """Freeze the distribution (see the class documentation).

        """
        dist_dir = self.dist_file.parent
        if not dist_dir.exists():
            dist_dir.mkdir(parents=True, exist_ok=True)
        data = self.discoverer.freeze()
        with zipfile.ZipFile(self.dist_file, mode='w') as zf:
            for finfo in data['files']:
                fabs = finfo['abs']
                frel = str(Path(finfo['rel']))
                logger.debug(f'adding file: {fabs}')
                zf.write(fabs, arcname=frel)
                del finfo['abs']
                finfo['rel'] = frel
            logger.info(f'writing distribution defs to {self.defs_file}')
            zf.writestr(self.defs_file, json.dumps(data, indent=2))
        logger.info(f'created frozen distribution in {self.dist_file}')

    def freeze(self, wheel_dependency=None):
        """Freeze the distribution by saving creating a script to thaw along with all
        artifacts (i.e. repo definitions) in a zip file.

        """
        self._freeze_dist()
        script_file = self.config.bootstrap_script_file
        bg = BootstrapGenerator(self.config)
        bg.generate(script_file)
        script_file.chmod(0o755)
        # wheel creation last since pip clobers/reconfigures logging
        create_wheel = self.config.get_option('discover.wheel.create')
        if create_wheel and wheel_dependency is not None:
            self._create_wheels(wheel_dependency)


class ThawManager(object):
    def __init__(self, dist_file: Path, target_dir: Path, defs_file: Path):
        self.dist_file = dist_file
        self.target_dir = target_dir
        self.defs_file = defs_file

    def _thaw_empty_dirs(self, dist: Distribution):
        """Create empty directories on the file system.

        """
        for entry in dist.empty_dirs:
            path = entry.path
            if path.exists():
                logger.warning(f'path already exists: {path}')
            else:
                logger.info(f'creating path {path}')
                # we store the mode of the directory, but we don't want that to
                # apply to all children dirs that might not exist yet
                path.mkdir(mode=entry.mode, parents=True, exist_ok=True)

    def _thaw_files(self, dist: Distribution, zf):
        """Thaw files in the distribution by extracting from the zip file ``zf``.  File
        definitions are found in ``struct``.

        """
        for entry in dist.files:
            path = entry.path
            parent = path.parent
            if not parent.exists():
                logger.info(f'creating parent directory: {parent}')
                parent.mkdir(parents=True)
            logger.debug(f'thawing file: {path}')
            if path.exists():
                logger.warning(f'path already exists: {path}')
            else:
                with zf.open(str(entry.relative)) as fin:
                    with open(str(path), 'wb') as fout:
                        shutil.copyfileobj(fin, fout)
                logger.debug(f'setting mode of {path} to {entry.mode} ' +
                             f'({entry.modestr})')
                path.chmod(entry.mode)

    def _thaw_repos(self, dist: Distribution):
        """Thaw repositories in the config, which does a clone and then creates the
        (remaining if any) remotes.

        """
        for repo in dist.repos:
            repo_path = repo.path
            parent = repo_path.parent
            logger.debug(f'thawing repo: {repo}')
            if not parent.exists():
                logger.info(f'creating parent directory: {parent}')
                parent.mkdir(parents=True, exist_ok=True)
            try:
                thawed = repo.thaw()
                logger.debug(f'thawed: {thawed}')
            except GitCommandError as err:
                logger.warning(f'couldn\'t create repo {repo_path}--skippping: {err}')

    def _thaw_pattern_links(self, dist):
        """Method to call other thaw methods based on type.

        """
        for link in dist.links:
            if link.source.exists():
                logger.warning(f'link source already exists: {link.source}')
            elif not link.target.exists():
                logger.warning(
                    f'link target does not exist: {link}--skipping')
            else:
                logger.info(f'linking: {link}')
                link.source.symlink_to(link.target)

    def thaw(self):
        """Thaw the distribution, which includes creating git repositories, extracting
        (frozen) files, creating symbolic links, and creating empty directories
        that were captured/configured during the freezing phase.

        """
        dist_file = self.dist_file
        logger.info(f'expanding distribution in {dist_file}')
        with zipfile.ZipFile(str(dist_file.resolve())) as zf:
            with zf.open(self.defs_file) as f:
                jstr = f.read().decode('utf-8')
                struct = json.loads(jstr)
            dist = Distribution(struct, self.target_dir)
            self._thaw_files(dist, zf)
            self._thaw_repos(dist)
            self._thaw_empty_dirs(dist)
            self._thaw_pattern_links(dist)


class DistManager(object):
    """The main entry point that supports saving user home directory information
    (freezing) so that the data can later be restored (thawed).  It does this
    by finding git repositories and saving the remotes.  It also finds symbolic
    links, files and empty directories specified in the configuration.

    """
    def __init__(self, config: YamlConfig, dist_dir: Path = None,
                 target_dir: Path = None, profiles: list = None):
        self.config = config
        # config will be missing on thaw
        if config is None:
            if dist_dir is None:
                raise ValueError('missing dist file option')
            self.dist_dir = Path(dist_dir)
        else:
            if dist_dir is not None:
                self.config.dist_dir = dist_dir
            self.dist_dir = self.config.dist_dir
        if target_dir is not None:
            self.target_dir = Path(target_dir)
        else:
            self.target_dir = Path.home()
        self.config_dir = 'conf'
        self.defs_file = '{}/dist.json'.format(self.config_dir)
        self.profiles = profiles

    def freeze(self, wheel_dependency=None):
        fmng = FreezeManager(
            self.config, self.dist_file, self.defs_file, self.discoverer)
        fmng.freeze(wheel_dependency)

    @property
    @persisted('_dist_file')
    def dist_file(self):
        """Return the main distribution compressed file that will have the
        configuration needed to thaw, all saved files and symbolic links.

        """
        return Path(self.dist_dir, 'dist.zip')

    @property
    @persisted('_discoverer')
    def discoverer(self):
        return Discoverer(self.config, self.profiles)

    def discover_info(self):
        """Proviate information about what's found in the user home directory.  This is
        later used to freeze the data.

        """
        disc = self.discoverer()
        struct = disc.freeze()
        pprint.PrettyPrinter().pprint(struct)

    def _to_home_relative(self, path):
        return str(Path(Path.home(), path).absolute())

    def print_repos(self, fmt='{name}'):
        disc = self.discoverer
        struct = disc.freeze()
        for repo_spec in struct['repo_specs']:
            remotes = map(lambda x: x['name'], repo_spec['remotes'])
            remotes = ' '.join(sorted(remotes))
            rs = {'name': repo_spec['name'],
                  'path': self._to_home_relative(repo_spec['path']),
                  'remotes': remotes}
            print(fmt.format(**rs))

    def print_repo_info(self, names=None):
        disc = self.discoverer
        struct = disc.freeze()
        specs = {x['name']: x for x in struct['repo_specs']}
        if names is None:
            names = sorted(specs.keys())
        else:
            names = names.split()
        for name in names:
            if name not in specs:
                raise ValueError(f'no such repository: {name}')
            s = specs[name]
            path = str(Path(Path.home(), s['path']).absolute())
            print(f"{s['name']}:\n  path: {path}\n  remotes:")
            for r in s['remotes']:
                print(f"    {r['name']}: {r['url']}")
            print('  links:')
            for l in s['links']:
                source = self._to_home_relative(l['source'])
                target = self._to_home_relative(l['target'])
                print(f"    {source} -> {target}")

    def thaw(self):
        tmng = ThawManager(self.dist_file, self.target_dir, self.defs_file)
        tmng.thaw()

    def tmp(self):
        #self.freeze()
        dist_file = self.dist_file
        logger.info(f'moving installed distribution in {dist_file}')
        with zipfile.ZipFile(str(dist_file.resolve())) as zf:
            with zf.open(self.defs_file) as f:
                jstr = f.read().decode('utf-8')
                struct = json.loads(jstr)
        dist = Distribution(struct, self.target_dir)
        objs = (dist.repos, dist.files, dist.empty_dirs, dist.links)
        paths = it.chain(map(lambda x: x.path, it.chain(*objs)),
                         map(lambda l: l.path,
                             it.chain(*map(lambda r: r.links, dist.repos))))
        for path in paths:
            print(path)
