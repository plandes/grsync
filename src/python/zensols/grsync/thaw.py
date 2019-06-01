import logging
import json
import zipfile
import shutil
from git.exc import GitCommandError
from pathlib import Path
import platform
from zensols.actioncli import persisted
from zensols.grsync import (
    FrozenRepo,
    FileEntry, LinkEntry,
)

logger = logging.getLogger(__name__)


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


class ThawManager(object):
    def __init__(self, dist_file: Path, target_dir: Path, defs_file: Path,
                 dry_run=bool):
        self.dist_file = dist_file
        self.target_dir = target_dir
        self.defs_file = defs_file
        self.dry_run = dry_run

    def _thaw_empty_dirs(self, dist: Distribution):
        """Create empty directories on the file system.

        """
        for entry in dist.empty_dirs:
            path = entry.path
            if path.exists():
                logger.warning(f'path already exists: {path}')
            else:
                logger.info(f'creating path {path}')
                if not self.dry_run:
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
                logger.info('{path} ({entry.modestr})')
                if not self.dry_run:
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
            logger.info(f'thawing repo: {repo}')
            if not parent.exists():
                logger.info(f'creating parent directory: {parent}')
                if not self.dry_run:
                    parent.mkdir(parents=True, exist_ok=True)
            try:
                if not self.dry_run:
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
                if not self.dry_run:
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
