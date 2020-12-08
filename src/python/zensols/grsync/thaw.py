import logging
import traceback
import os
import zipfile
import shutil
from git.exc import GitCommandError
from pathlib import Path
from zensols.grsync import (
    PathTranslator,
    Distribution,
)

logger = logging.getLogger(__name__)


class ThawManager(object):
    def __init__(self, dist: Distribution, defs_file: Path,
                 path_translator: PathTranslator, app_version, dry_run=bool):
        self.dist = dist
        self.defs_file = defs_file
        self.path_translator = path_translator
        self.app_version = app_version
        self.dry_run = dry_run

    def assert_version(self):
        logger.info(f'app version: {self.app_version} =? {self.dist.version}')
        if self.app_version is None:
            raise ValueError('could not determine the application version')
        if self.dist.version is None:
            raise ValueError('distribution has incompatable version')
        if self.app_version != self.dist.version:
            raise ValueError('distribution has incompatable version: ' +
                             self.dist.version)

    def _thaw_empty_dirs(self):
        """Create empty directories on the file system.

        """
        for entry in self.dist.empty_dirs:
            path = entry.path
            if path.exists():
                logger.warning(f'path already exists: {path}')
            else:
                logger.info(f'creating path {path}')
                if not self.dry_run:
                    # we store the mode of the directory, but we don't want
                    # that to apply to all children dirs that might not exist
                    # yet
                    if entry.mode is None:
                        # use the default mode for missing directories during
                        # the freeze phase
                        path.mkdir(parents=True, exist_ok=True)
                    else:
                        path.mkdir(mode=entry.mode, parents=True, exist_ok=True)

    def _thaw_files(self, zf):
        """Thaw files in the distribution by extracting from the zip file ``zf``.  File
        definitions are found in ``struct``.

        """
        for entry in self.dist.files:
            path = entry.path
            parent = path.parent
            if not parent.exists():
                logger.info(f'creating parent directory: {parent}')
                if not self.dry_run:
                    parent.mkdir(parents=True)
            logger.debug(f'thawing file: {path}')
            if path.exists():
                logger.warning(f'path already exists: {path}')
            else:
                logger.info(f'{path}: mode={entry.modestr}, ' +
                            f'time={entry.modify_time}')
                if not self.dry_run:
                    with zf.open(str(entry.relative)) as fin:
                        with open(str(path), 'wb') as fout:
                            shutil.copyfileobj(fin, fout)
                logger.debug(f'setting mode of {path} to {entry.mode} ' +
                             f'({entry.modestr}, {entry.modify_time})')
                if not self.dry_run:
                    path.chmod(entry.mode)
                    if entry.modify_time is not None:
                        os.utime(path, (entry.modify_time, entry.modify_time))

    def _thaw_repos(self):
        """Thaw repositories in the config, which does a clone and then creates the
        (remaining if any) remotes.

        """
        for repo in self.dist.repos:
            repo_path = repo.path
            parent = repo_path.parent
            logger.info(f'thawing repo: {repo}')
            if not parent.exists():
                logger.info(f'creating parent directory: {parent}')
                if not self.dry_run:
                    parent.mkdir(parents=True, exist_ok=True)
            try:
                if not self.dry_run:
                    try:
                        thawed = repo.thaw()
                        logger.debug(f'thawed: {thawed}')
                    except Exception as e:
                        # robust
                        traceback.print_exc()
                        logger.error(f'could not thaw {repo}: {e}')
            except GitCommandError as err:
                logger.warning(f'couldn\'t create repo {repo_path}--skippping: {err}')

    def _thaw_pattern_links(self):
        """Method to call other thaw methods based on type.

        """
        for link in self.dist.links:
            if link.source.exists():
                logger.warning(f'link source already exists: {link.source}')
            elif not link.target.exists():
                logger.warning(
                    f'link target does not exist: {link}--skipping')
            else:
                logger.info(f'linking: {link}')
                if not self.dry_run:
                    par = link.source.parent
                    if not par.exists():
                        logger.info(f'creating link directory: {par}')
                        par.mkdir(parents=True)
                    link.source.symlink_to(link.target)

    def thaw(self):
        """Thaw the distribution, which includes creating git repositories, extracting
        (frozen) files, creating symbolic links, and creating empty directories
        that were captured/configured during the freezing phase.

        """
        logger.info(f'expanding distribution in {self.dist.path}')
        self.assert_version()
        with zipfile.ZipFile(str(self.dist.path.resolve())) as zf:
            self._thaw_empty_dirs()
            self._thaw_files(zf)
            self._thaw_repos()
            self._thaw_pattern_links()
