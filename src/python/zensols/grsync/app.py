"""Application entry point.

"""
__author__ = 'Paul Landes'

from typing import List, Dict, Any
from dataclasses import dataclass, field
from abc import ABCMeta
import logging
from pathlib import Path
from zensols.persist import persisted
from zensols.cli import LogConfigurator, ActionCliManager
from . import DistManager, AppConfig

logger = logging.getLogger(__name__)


@dataclass
class DistManagerFactory(object):
    """Creates instances of :class:`.DistManager`.

    """
    path: Path = field()
    """The path to the YAML application configuration file."""

    @property
    @persisted('_config')
    def config(self) -> AppConfig:
        return None if self.path is None else AppConfig(self.path)

    def __call__(self, **kwargs) -> DistManager:
        params = dict(kwargs)
        params['config'] = self.config
        return DistManager(**params)


@dataclass
class Application(object):
    """Application base class.

    """
    CLASS_INSPECTOR = {}
    CLI_META = {'option_excludes': {'dist_mng_factory'},
                'option_overrides': {'repo_pref': {'short_name': 'r'}}}

    dist_mng_factory: DistManagerFactory = field()
    """The main class that freezes/thaws and provides repo information."""

    def __post_init__(self):
        self._params: Dict[str, Any] = {}

    @property
    @persisted('_dist_mng')
    def dist_mng(self) -> DistManager:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'params: {self._params}')
        return self.dist_mng_factory(**self._params)


@dataclass
class InfoApplication(Application):
    """Captures and syncronizes a user home and its Git repositories with other
    hosts.

    """
    CLI_META = ActionCliManager.combine_meta(
        Application,
        {'option_excludes': {'log_config'},
         'mnemonic_overrides': {'list_profiles': 'profiles'}})

    log_config: LogConfigurator = field()
    """The application log configurator."""

    profiles: str = field(default=None)
    """Comma spearated list of profiles in config."""

    def __post_init__(self):
        super().__post_init__()
        if self.profiles is not None:
            self._params['profiles'] = AppConfig.split_profiles(self.profiles)
        self.log_config.level = 'err'
        self.log_config()

    def info(self):
        """Pretty print discovery information."""
        self.dist_mng.discover_info()

    def repoinfo(self, names: str = None):
        """Get information on repositories.

        :param names: the last component of the repo's directory name

        """
        names: List[str] = None if names is None else names.split(',')
        self.dist_mng.print_repo_info(names)

    def repos(self, format: str = '{path}'):
        """Output all repository top level info.

        :param format: format string (ie {name}: {path}, remotes={remotes},
                       dirty={dirty})

        """
        self.dist_mng.print_repos(format)

    def list_profiles(self):
        """Print the profiles """
        config: AppConfig = self.dist_mng_factory.config
        print('\n'.join(config.get_profiles()))


@dataclass
class ModifyApplication(Application, metaclass=ABCMeta):
    """Super class for applications that modify the file system.

    """
    CLI_META = ActionCliManager.combine_meta(
        Application,
        {'option_overrides': {'dist_dir': {'metavar': 'DIRECTORY',
                                           'short_name': 'd'},
                              'dry_run': {'short_name': None},
                              'profiles': {'short_name': 'p'}}})

    dist_dir: Path = field(default=None)
    """The location of build out distribution."""

    profiles: str = field(default=None)
    """Comma spearated list of profiles in config."""

    dry_run: bool = field(default=False)
    """Do not do anything, just act like it."""

    def __post_init__(self):
        super().__post_init__()
        for attr in 'dist_dir profiles dry_run'.split():
            if hasattr(self, attr):
                self._params[attr] = getattr(self, attr)


@dataclass
class TargetApplication(ModifyApplication, metaclass=ABCMeta):
    CLI_META = ActionCliManager.combine_meta(
        ModifyApplication,
        {'option_overrides': {'target_dir': {'metavar': 'DIRECTORY',
                                             'short_name': 't'}}})

    target_dir: Path = field(default=None)
    """The location of build out target dir."""

    def __post_init__(self):
        super().__post_init__()
        if self.target_dir is not None:
            self._params['target_dir'] = self.target_dir


@dataclass
class FreezeApplication(ModifyApplication):
    CLI_META = ModifyApplication.CLI_META

    def freeze(self, wheel_dep: Path = Path('zensols.grsync'),
               repo_pref: str = None):
        """Create a distribution.

        :param whee_dep: used to create the wheel dep files

        :param repo_pref: the repository to make primary on thaw

        """
        self.dist_mng.freeze(wheel_dep)


@dataclass
class ThawApplication(TargetApplication):
    CLI_META = TargetApplication.CLI_META

    def thaw(self):
        """Build out a distribution.

        """
        self.dist_mng.thaw()


@dataclass
class CopyMoveApplication(TargetApplication):
    CLI_META = ActionCliManager.combine_meta(
        TargetApplication,
        {'option_overrides':
         {'move_dir': {'metavar': 'DIRECTORY'},
          'dir_reduce': {'long_name': 'reduce', 'short_name': None}}})

    def copy(self, repo_pref: str = None):
        """Build out a distribution.

        :param repo_pref: the repository to make primary on thaw

        """
        self.dst_mnt.copy()

    def move(self, move_dir: Path = None, dir_reduce: bool = False):
        """Move a distribution to another root (easy to delete).

        :param move_dir: the location of build out move dir

        :param reduce: dir_remove empty directories

        """
        self.dst_mnt.move(move_dir, dir_reduce)
