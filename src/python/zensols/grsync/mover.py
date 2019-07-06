import logging
import itertools as it
import shutil
from pathlib import Path
from zensols.grsync import (
    Distribution,
    RepoSpec,
    FileEntry,
    FrozenRepo,
)

logger = logging.getLogger(__name__)


class DistributionMover(object):
    """This class moves thawed files that are defined in a distribution zip.  If
    the file is not defined in the distribution then it doesn't move it.

    In situations where you've already deleted the distribution zip, you'll
    have to create a new distribution by freezing what you have.  For this
    reason it is recommended that you always include the original `grsync.yml`
    configuration file in your distribution so it *migrates* along with each of
    your freeze/thaw iterations.

    """
    def __init__(self, dist: Distribution, target_dir=None,
                 destination_dir: Path = None,
                 force_repo=False, force_dirs=False, dry_run=False):
        """Initialize.

        :param dist: the distrbution that represent the distribution zip
        :param target_dir: the directory with the thawed files
        :param destination_dir: where the thawed files/repos will be moved
        :param force_repo: if ``True`` move repositories even if they're dirty
        :param force_dirs: if ``True`` move directories even if they're not empty
        :param dry_run: don't actually do anything, but log like we are
        """
        self.dist = dist
        self.target_dir = target_dir
        if destination_dir is None:
            destination_dir = Path('old_dist').absolute()
        self.destination_dir = destination_dir
        self.force_repo = force_repo
        self.force_dirs = force_dirs
        self.dry_run = dry_run

    def _get_paths(self):
        dist = self.dist
        objs = (dist.links, dist.repos, dist.files, dist.empty_dirs)
        paths = it.chain(map(lambda x: (x.path, x), it.chain(*objs)),
                         map(lambda l: (l.path, l),
                             it.chain(*map(lambda r: r.links, dist.repos))))
        return sorted(paths, key=lambda x: len(x[0].parts), reverse=True)

    def _dir_empty(self, path):
        return sum(map(lambda x: 1, path.iterdir())) == 0

    def _get_moves(self):
        for src, obj in self._get_paths():
            if not src.exists() and not src.is_symlink():
                logger.warning(f'no longer exists: {src}')
            else:
                if isinstance(obj, FrozenRepo):
                    try:
                        grepo = obj.repo_spec.repo
                    except Exception as e:
                        # git.exc.InvalidGitRepositoryError
                        logger.error(f'invalid repository: {obj}--skipping')
                        continue
                    if grepo.is_dirty():
                        name = obj.repo_spec.format(RepoSpec.SHORT_FORMAT)
                        if self.force_repo:
                            logger.warning(f'repo is dirty: {name}; moving anyway')
                        else:
                            logger.warning(f'repo is dirty: {name}--skipping')
                            continue
                elif isinstance(obj, FileEntry) and src.is_dir() and not src.is_symlink():
                    if not self._dir_empty(src):
                        if self.force_dirs:
                            logger.warning(f'directory not empty: {src}; ' +
                                           'moving anyway')
                        else:
                            logger.warning(f'directory not empty: {src}--skipping')
                            continue
                dst = self.destination_dir / src.relative_to(self.target_dir)
                yield (src, dst.absolute())

    def move(self):
        "Move the files over."
        logger.info(f'moving installed distribution to {self.destination_dir}')
        for src, dst in self._get_moves():
            logger.info(f'move {src} -> {dst}')
            if not self.dry_run:
                if src.exists() or src.is_symlink():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                else:
                    logger.warning(f'no longer exists: {src}')

    def dir_reduce(self, parent=None):
        "Remove empty directories recursively starting at ``parent``."
        try:
            if parent is None:
                parent = self.target_dir
            for child in parent.iterdir():
                logger.debug(f'descending: {child}')
                if child.is_dir() and not child.is_symlink():
                    self.dir_reduce(child)
            if parent != self.target_dir and parent.is_dir():
                if self._dir_empty(parent):
                    logger.info(f'deleting empty directory: {parent}')
                    if not self.dry_run:
                        parent.rmdir()
                else:
                    logger.info(f'skipping non-empty directory delete: {parent}')
        except Exception as e:
            # be robust
            logger.error(f"couldn't delete {parent}: {e}")
