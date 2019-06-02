import logging
import itertools as it
import re
import json
import zipfile
import shutil
from pathlib import Path
from zensols.actioncli import YamlConfig, persisted
from zensols.grsync import (
    Discoverer,
    Distribution,
    FreezeManager,
    ThawManager,
    RepoSpec,
    FileEntry,
    FrozenRepo,
    PathTranslator,
)

logger = logging.getLogger(__name__)


class DistributionMover(object):
    def __init__(self, dist: Distribution, target_dir=None,
                 destination_dir: Path = None,
                 force_repo=False, force_dirs=False, dry_run=False):
        self.dist = dist
        self.target_dir = target_dir
        if destination_dir is None:
            destination_dir = Path('old_dist')
        if destination_dir.exists():
            m = re.match(r'^(.+)_(\d+)$', str(destination_dir))
            if m:
                n = int(m.group(2)) + 1
                destination_dir = Path(f'{m.group(1)}_{n}')
        self.destination_dir = destination_dir
        self.force_repo = force_repo
        self.force_dirs = force_dirs
        self.dry_run = dry_run

    def _get_moves(self):
        dist = self.dist
        objs = (dist.links, dist.repos, dist.files, dist.empty_dirs)
        paths = it.chain(map(lambda x: (x.path, x), it.chain(*objs)),
                         map(lambda l: (l.path, l),
                             it.chain(*map(lambda r: r.links, dist.repos))))
        paths = sorted(paths, key=lambda x: len(x[0].parts), reverse=True)
        logger.info(f'moving installed distribution to {self.destination_dir}')
        for src, obj in paths:
            if not src.exists() and not src.is_symlink():
                logger.warning(f'no longer exists: {src}')
            else:
                if isinstance(obj, FrozenRepo):
                    if obj.repo_spec.repo.is_dirty():
                        name = obj.repo_spec.format(RepoSpec.SHORT_FORMAT)
                        if self.force_repo:
                            logger.warning(f'repo is dirty: {name}; moving anyway')
                        else:
                            logger.warning(f'repo is dirty: {name}--skipping')
                            continue
                elif isinstance(obj, FileEntry) and src.is_dir() and not src.is_symlink():
                    fcnt = sum(map(lambda x: 1, src.iterdir()))
                    if fcnt > 0:
                        if self.force_dirs:
                            logger.warning(f'directory not empty: {src}; ' +
                                           'moving anyway')
                        else:
                            logger.warning(f'directory not empty: {src}--skipping')
                            continue
                dst = self.destination_dir / src.relative_to(self.target_dir)
                yield (src, dst.absolute())

    def move(self):
        for src, dst in self._get_moves():
            logger.info(f'{src} => {dst}')
            if not self.dry_run:
                if src.exists() or src.is_symlink():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                else:
                    logger.warning(f'no longer exists: {src}')


class DistManager(object):
    """The main entry point that supports saving user home directory information
    (freezing) so that the data can later be restored (thawed).  It does this
    by finding git repositories and saving the remotes.  It also finds symbolic
    links, files and empty directories specified in the configuration.

    """
    def __init__(self, config: YamlConfig, dist_dir: Path = None,
                 target_dir: Path = None, profiles: list = None,
                 dry_run: bool = False):
        """Initialize.

        :param config: the app config
        :param dist_dir: the location of the frozen distribution
        :param target_dir: the location of the distrbution to freeze or where
                           to exapand (default to the user home)
        :param profiles: the (maven like) profiles that define what to freeze

        """
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
            self.target_dir = Path(target_dir).expanduser().absolute()
        else:
            self.target_dir = Path.home().absolute()
        self.profiles = profiles
        self.dry_run = dry_run
        # configuration directory in the zip distribution
        self.config_dir = 'conf'
        # definitions file contains all the metadata (files, links etc)
        self.defs_file = '{}/dist.json'.format(self.config_dir)
        # the main distribution compressed file that will have the
        # configuration needed to thaw, all saved files and symbolic links.
        self.dist_file = Path(self.dist_dir, 'dist.zip')
        # resovle path to and from the target directory
        self.path_translator = PathTranslator(self.target_dir)

    @property
    @persisted('_discoverer')
    def discoverer(self):
        return Discoverer(self.config, self.profiles, self.path_translator)

    @property
    def distribution(self):
        with zipfile.ZipFile(str(self.dist_file.resolve())) as zf:
            with zf.open(self.defs_file) as f:
                jstr = f.read().decode('utf-8')
                struct = json.loads(jstr)
        return Distribution(
            self.dist_file, struct, self.target_dir, self.path_translator)

    def discover_info(self):
        """Proviate information about what's found in the user home directory.  This is
        later used to freeze the data.

        """
        from pprint import pprint
        pprint(self.discoverer.freeze(flatten=True))

    def print_repos(self, fmt=None):
        for repo_spec in self.discoverer.discover()['repo_specs']:
            print(repo_spec.format(fmt=fmt))

    def print_repo_info(self, names=None):
        struct = self.discoverer.discover()
        specs = {x.name: x for x in struct['repo_specs']}
        if names is None:
            names = sorted(specs.keys())
        for name in names:
            if name not in specs:
                raise ValueError(f'no such repository: {name}')
            specs[name].write()

    def freeze(self, wheel_dependency=None):
        fmng = FreezeManager(
            self.config, self.dist_file, self.defs_file, self.discoverer)
        fmng.freeze(wheel_dependency)

    def thaw(self):
        tmng = ThawManager(
            self.distribution, self.defs_file,
            self.path_translator, self.dry_run)
        tmng.thaw()

    def move(self, destination_path):
        mv = DistributionMover(
            self.distribution, self.target_dir,
            destination_path, dry_run=self.dry_run)
        mv.move()
