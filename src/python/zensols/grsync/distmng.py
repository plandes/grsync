import logging
from pathlib import Path
from zensols.config import YamlConfig
from zensols.persist import persisted
from zensols.grsync import (
    Discoverer,
    Distribution,
    FreezeManager,
    ThawManager,
    PathTranslator,
    DistributionMover,
)

logger = logging.getLogger(__name__)


class DistManager(object):
    """The main entry point that supports saving user home directory information
    (freezing) so that the data can later be restored (thawed).  It does this
    by finding git repositories and saving the remotes.  It also finds symbolic
    links, files and empty directories specified in the configuration.

    """
    def __init__(self, config: YamlConfig, dist_dir: Path = None,
                 target_dir: Path = None, profiles: list = None,
                 repo_preference: str = None, dry_run: bool = False):
        """Initialize.

        :param config: the app config
        :param dist_dir: the location of the frozen distribution
        :param target_dir: the location of the distrbution to freeze or where
                           to exapand (default to the user home)
        :param profiles: the (maven like) profiles that define what to freeze
        :param repo_preference: the repository to make master on thaw (default
                                to configuration file)

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
        self.repo_preference = repo_preference
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
        self._app_version = None

    @property
    def app_version(self):
        return self._app_version

    @app_version.setter
    def app_version(self, app_version):
        self._app_version = app_version

    @property
    @persisted('_discoverer')
    def discoverer(self):
        return Discoverer(
            self.config, self.profiles, self.path_translator,
            self.repo_preference)

    @property
    def distribution(self):
        return Distribution(
            self.dist_file, self.defs_file, self.target_dir,
            self.path_translator)

    def discover_info(self):
        """Proviate information about what's found in the user home directory.  This is
        later used to freeze the data.

        """
        from pprint import pprint
        pprint(self.discoverer.freeze(flatten=True))

    def print_repos(self, fmt=None):
        for repo_spec in self.discoverer.discover(False)['repo_specs']:
            print(repo_spec.format(fmt=fmt))

    def print_repo_info(self, names=None):
        struct = self.discoverer.discover(flatten=True)
        specs = {x.name: x for x in struct['repo_specs']}
        if names is None:
            names = sorted(specs.keys())
        for name in names:
            if name not in specs:
                raise ValueError(f'no such repository: {name}')
            specs[name].write()

    def freeze(self, wheel_dependency=None):
        """Freeze the current configuration and file set to the distribution zip.

        """
        fmng = FreezeManager(
            self.config, self.dist_file, self.defs_file, self.discoverer,
            self.app_version)
        fmng.freeze(wheel_dependency)

    def thaw(self):
        """Expand the distribution zip on to the file system.

        """
        tmng = ThawManager(
            self.distribution, self.defs_file,
            self.path_translator, self.app_version, self.dry_run)
        tmng.thaw()

    def move(self, destination_path, dir_reduce=True):
        """Move a thawed file set to ``destination_path``.  If ``dir_reduce`` is
        ``True`` then recursively remove directories.

        """
        if destination_path is not None:
            destination_path = Path(destination_path).expanduser().absolute()
        mv = DistributionMover(
            self.distribution, self.target_dir,
            destination_path, dry_run=self.dry_run)
        mv.move()
        if dir_reduce:
            mv.dir_reduce()

    def tmp(self):
        destination_path = Path('target/thaw').absolute()
        mv = DistributionMover(
            self.distribution, self.target_dir,
            destination_path, dry_run=self.dry_run)
        mv.dir_reduce()
