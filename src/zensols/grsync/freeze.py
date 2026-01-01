"""Includes classes that read the configuration and traverse the file system to
find matching objects to use to freeze the distribution.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Dict, Iterable, Any
import os
import stat
import socket
import logging
import itertools as it
import re
import json
import zipfile
from pathlib import Path
from datetime import datetime
from zensols.persist import persisted
from zensols.grsync import (
    RepoSpec,
    SymbolicLink,
    BootstrapGenerator,
    PathTranslator,
    AppConfig,
)

logger = logging.getLogger(__name__)


class Discoverer(object):
    """Discover git repositories, links, files and directories to save to
    reconstitute a user home directory later.

    """
    CONF_TARG_KEY = 'discover.target.config'
    TARG_LINKS = 'discover.target.links'
    REPO_PREF = 'discover.repo.remote_pref'
    SKIP_OBJECTS = 'discover.skip'
    SKIP_REPOS = 'discover.repo.skip'

    def __init__(self, config: AppConfig, profiles: list,
                 path_translator: PathTranslator, repo_preference: str):
        self.config = config
        self.profiles_override = profiles
        self.path_translator = path_translator
        self._repo_preference = repo_preference

    def _get_repo_paths(self, paths) -> Iterable[Path]:
        """Recusively find git repository root directories."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('repo root search paths {}'.format(paths))
        for path in paths:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('searching git paths in {}'.format(path.resolve()))
            for root, dirs, files in os.walk(path.resolve()):
                rootpath = Path(root)
                if rootpath.name == '.git':
                    yield rootpath.parent

    def _discover_repo_specs(self, paths: Iterable[Path],
                             links: Tuple[SymbolicLink, ...]) -> \
            Iterable[RepoSpec]:
        """Return a list of RepoSpec objects.

        :param paths: a list of paths each of which start a new RepoSpec

        :param links: a list of symlinks to check if they point to the
                      repository, and if so, add them to the RepoSpec

        """
        if self.config.has_option(self.SKIP_REPOS):
            regex: str
            for regex in self.config.get_option(self.SKIP_REPOS):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"filter paths on regex: '{regex}'")
                pat: re.Pattern = re.compile(regex)
                paths = map(lambda t: t[0],
                            filter(lambda t: t[1].match(str(t[0])) is None,
                                   zip(paths, it.repeat(pat))))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'repo spec paths: {paths}')
        path: Path
        for path in paths:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'found repo at path {path}')
            repo_spec = RepoSpec(path, self.path_translator)
            repo_spec.add_linked(links)
            if len(repo_spec.remotes) == 0:
                logger.warning(f'repo {repo_spec} has no remotes--skipping...')
            else:
                yield repo_spec

    @property
    @persisted('_profiles')
    def profiles(self):
        if self.config is None:
            raise ValueError('no configuration given; use the --help option')
        return self.config.get_profiles(self.profiles_override)

    def get_discoverable_objects(self) -> List[Path]:
        """Find git repos, files, sym links and directories to reconstitute
        later.

        """
        fls: Iterable[str] = self.config.get_discoverable_objects(self.profiles)
        paths = []
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'finding persist objects in {self.config.config_file}')
        if self.config.has_option(self.SKIP_OBJECTS):
            regex: str
            for regex in self.config.get_option(self.SKIP_OBJECTS):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"filter paths on regex: '{regex}'")
                pat: re.Pattern = re.compile(regex)
                fls = tuple(filter(lambda p: pat.match(str(p)) is None, fls))
        for fname in fls:
            path = Path(fname).expanduser().absolute()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'file pattern {fname} -> {path}')
            bname = path.name
            dname = path.parent.expanduser()
            files = list(dname.glob(bname))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'expanding {path} -> {dname} / {bname}: {files}')
            paths.extend(files)
        return paths

    def _create_file(self, src, dst=None, no_path_obj=False, robust=False):
        """Return a file object, which has the relative (rel) to home dir path,
        absolute path (abs) used later to zip the file, and mode (mode and
        modestr) information.

        """
        dst = src if dst is None else dst
        if src.exists():
            mode = src.stat().st_mode
            modestr = stat.filemode(mode)
            modify_time = os.path.getmtime(src)
            create_time = os.path.getctime(src)
        elif not robust:
            raise OSError(f'no such file: {src}')
        else:
            logger.warning(f'missing file: {src}--robustly skipping')
            mode, modestr, create_time, modify_time = None, None, None, None
        # the mode string is used as documentation and currently there is no
        # way to convert from a mode string to an octal mode, which would be
        # nice to allow modification of the dist.json file.
        fobj = {'modestr': modestr,
                'mode': mode,
                'create_time': create_time,
                'modify_time': modify_time}
        if no_path_obj:
            fobj['rel'] = str(self.path_translator.relative_to(dst))
        else:
            fobj['abs'] = src
            fobj['rel'] = self.path_translator.relative_to(dst)
        return fobj

    def _get_dirs_links_specs(self, files: List[Path]):
        # find all things to persist (repos, symlinks, files, etc)
        dobjs: List[Path] = self.get_discoverable_objects()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'dobjs {len(dobjs)}')
        # all directories are either repositories or base directories to
        # persist files in the distribution file
        dirs_or_gits: Tuple[Path, ...] = tuple(
            filter(lambda x: x.is_dir() and not x.is_symlink(), dobjs))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'dirs_or_gits {len(dirs_or_gits)}')
        # find the directories that have git repos in them (recursively)
        git_paths: Iterable[Path] = self._get_repo_paths(dirs_or_gits)
        # create symbolic link objects from those objects that are links
        links = tuple(map(lambda lk: SymbolicLink(lk, self.path_translator),
                          filter(lambda x: x.is_symlink(), dobjs)))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'links {len(links)}')
        if files is not None:
            # normal files are kept track of so we can compress them later
            for f in filter(lambda x: x.is_file() and not x.is_symlink(), dobjs):
                files.append(self._create_file(f))
        # create RepoSpec objects that capture information about the git repo
        repo_specs = self._discover_repo_specs(git_paths, links)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'repo_specs: {repo_specs}')
        return (dirs_or_gits, links, repo_specs)

    def get_repo_specs(self) -> Iterable[RepoSpec]:
        """Return an iterable of :class:`.RepoSpec` instances."""
        dirs_or_gits, links, repo_specs = self._get_dirs_links_specs(None)
        return repo_specs

    def discover(self, flatten: bool) -> Dict[str, Any]:
        """Main worker method to capture all the user home information (git
        repos, files, sym links and empty directories per the configuration
        file).

        :param flatten: if ``True`` then return a data structure appropriate
                        for pretty printing; this will omit data needed to
                        create the distrubtion so it shouldn't be used for the
                        freeze task

        """
        files: List[Path] = []
        dirs = []
        empty_dirs = []
        pattern_links = []
        path_trans = self.path_translator
        dirs_or_gits, links, repo_specs = self._get_dirs_links_specs(files)
        repo_specs: Tuple[RepoSpec, ...] = tuple(repo_specs)
        # these are the Path objects to where the repo lives on the local fs
        repo_paths = set(map(lambda x: x.path, tuple(repo_specs)))
        # add the configuration used to freeze so the target can freeze again
        if self.config.has_option(self.CONF_TARG_KEY):
            config_targ = self.config.get_option(self.CONF_TARG_KEY)
            src = Path(self.config.config_file)
            dst = Path(config_targ).expanduser()
            files.append(self._create_file(dst, dst))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'files: {files}')

        # recusively find files that don't belong to git repos
        def gather(par):
            for c in par.iterdir():
                if c.is_dir() and c not in repo_paths:
                    gather(c)
                elif c.is_file():
                    files.append(self._create_file(c))

        # find files that don't belong to git repos
        for path in filter(lambda x: x not in repo_paths, dirs_or_gits):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('dir {}'.format(path))
            dirs.append({'abs': path, 'rel': path_trans.relative_to(path)})
            gather(path)

        # configurated empty directories are added only if they exist so we can
        # recreate with the correct mode
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'using profiles: {", ".join(self.profiles)}')
        for ed in self.config.get_empty_dirs(self.profiles):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('empty dir: {}'.format(str(ed)))
            empty_dirs.append(self._create_file(
                ed, no_path_obj=True, robust=True))

        # pattern symlinks are special links that can change name based on
        # variables like the platform name so each link points to a
        # configuration file for that platform.
        if self.config.has_option(self.TARG_LINKS):
            dec_links = self.config.get_option(self.TARG_LINKS)
            for link in map(lambda x: x['link'],
                            filter(lambda x: 'link' in x, dec_links)):
                src = Path(link['source']).expanduser().absolute()
                targ = Path(link['target']).expanduser().absolute()
                pattern_links.append(
                    {'source': str(path_trans.relative_to(src)),
                     'target': str(path_trans.relative_to(targ))})

        # create data structures for symbolic link integrity
        files_by_name = {f['abs']: f for f in files}
        for f in files:
            if f['abs'].is_file():
                dname = f['abs'].parent
                files_by_name[dname] = dname
            if flatten:
                del f['abs']
                f['rel'] = str(f['rel'])

        # unused links pointing to repositories won't get created, so those not
        # used by repos are added explicitly to pattern links
        for link in links:
            if link.use_count == 0:
                try:
                    pattern_links.append(
                        {'source': str(link.source_relative),
                         'target': str(link.target_relative)})
                except ValueError as e:
                    logger.error(f'couldn\'t create link: {link}')
                    raise e
                if link.target in files_by_name:
                    dst = files_by_name[link.target]
                    # follow links enhancement picks up here
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'source {link.source} -> {dst}')
                else:
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(f'hanging link with no target: {link}')

        return {'repo_specs': repo_specs,
                'empty_dirs': empty_dirs,
                'files': files,
                'links': pattern_links}

    @property
    def repo_preference(self):
        """Return the preference for which repo to make primary on thaw

        """
        return self._repo_preference or \
            (self.config.has_option(self.REPO_PREF) and
             self.config.get_option(self.REPO_PREF))

    def freeze(self, flatten: bool = False):
        """Main entry point method that creates an object graph of all the data
        that needs to be saved (freeze) in the user home directory to
        reconstitute later (thaw).

        :param flatten: if ``True`` then return a data structure appropriate
                        for pretty printing; this will omit data needed to
                        create the distrubtion so it shouldn't be used for the
                        freeze task

        """
        disc = self.discover(flatten)
        repo_specs = tuple(x.freeze() for x in disc['repo_specs'])
        files = disc['files']
        if logger.isEnabledFor(logging.INFO):
            logger.info('freeezing with git repository ' +
                        f'preference: {self.repo_preference}')
        disc.update({'repo_specs': repo_specs,
                     'repo_pref': self.repo_preference,
                     'files': files,
                     'source': socket.gethostname(),
                     'create_date': datetime.now().isoformat(
                         timespec='minutes')})
        return disc


class FreezeManager(object):
    """Invoked by a client to create *frozen* distribution .

    """
    CREATE_WHEEL = 'discover.wheel.create'

    def __init__(self, config, dist_file, defs_file, discoverer, app_version,
                 dry_run: bool):
        self.config = config
        self.dist_file = dist_file
        self.defs_file = defs_file
        self.discoverer = discoverer
        self.app_version = app_version
        self.dry_run = dry_run

    def _create_wheels(self, wheel_dependency):
        """Create wheel dependencies on this software so the host doesn't need
        Internet connectivity.  Currently the YAML dependency breaks this since
        only binary per host wheels are available for download and the wrong was
        is given of spanning platforms (i.e. OSX to Linux).

        """
        wheel_dir_name = self.config.wheel_dir_name
        wheel_dir = Path(self.dist_dir, wheel_dir_name)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'creating wheels from dependency {wheel_dependency} ' +
                        f'in {wheel_dir}')
        if not wheel_dir.exists():
            wheel_dir.mkdir(parents=True, exist_ok=True)
        from pip._internal import main
        pip_cmd = (f'wheel --wheel-dir={wheel_dir} '
                   f'--no-cache-dir {wheel_dependency}')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('pip cmd: {}'.format(pip_cmd))
        main(pip_cmd.split())

    def _freeze_dist(self):
        """Freeze the distribution (see the class documentation).

        """
        dist_dir = self.dist_file.parent
        if not self.dry_run and not dist_dir.exists():
            dist_dir.mkdir(parents=True, exist_ok=True)
        data = self.discoverer.freeze()
        data['app_version'] = self.app_version
        if not self.dry_run:
            with zipfile.ZipFile(self.dist_file, mode='w') as zf:
                for finfo in data['files']:
                    fabs = finfo['abs']
                    frel = str(Path(finfo['rel']))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'adding file: {fabs}')
                    zf.write(fabs, arcname=frel)
                    del finfo['abs']
                    finfo['rel'] = frel
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f'writing distribution defs to {self.defs_file}')
                zf.writestr(self.defs_file, json.dumps(data, indent=2))
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'created frozen distribution in {self.dist_file}')

    def freeze(self, wheel_dependency=None):
        """Freeze the distribution by saving creating a script to thaw along
        with all artifacts (i.e. repo definitions) in a zip file.

        """
        self._freeze_dist()
        script_file = self.config.bootstrap_script_file
        if not self.dry_run:
            bg = BootstrapGenerator(self.config)
            bg.generate(script_file)
            script_file.chmod(0o755)
        # wheel creation last since pip clobers/reconfigures logging
        if self.config.has_option(self.CREATE_WHEEL):
            create_wheel = self.config.get_option(self.CREATE_WHEEL)
            if create_wheel and wheel_dependency is not None:
                self._create_wheels(wheel_dependency)
