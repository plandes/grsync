import logging
from pathlib import Path
import itertools as it
import re
from zensols.config import YamlConfig

logger = logging.getLogger(__name__)


class AppConfig(YamlConfig):
    """Application specific configuration access and parsing.

    Since much of the application centers around configuration of what to
    persist, this class does more heavy lifting than most configuraetion like
    classes.

    """
    ROOT = 'discover'
    OBJECTS_PATH = f'{ROOT}.objects'
    PROFILES_PATH = f'{ROOT}.profiles'
    EMPTY_DIR_PATH = f'{ROOT}.empty_dirs'
    OBJECTS_PROFILE_PATH = f'{PROFILES_PATH}.{{}}.objects'
    EMPTY_DIR_PROFILE_PATH = f'{PROFILES_PATH}.{{}}.empty_dirs'

    def __init__(self, config_file=None, default_vars=None):
        super(AppConfig, self).__init__(
            config_file, delimiter='^', default_vars=default_vars)

    @property
    def _find_profiles(self):
        opts = self.get_options(self.PROFILES_PATH, expect=False)
        if opts is None:
            opts = ()
        return opts

    @staticmethod
    def _split_profiles(profile_str):
        return re.split(r'\s*,\s*', profile_str)

    @property
    def _default_profiles(self):
        strlist = self.get_option(
            f'{self.ROOT}.default_profiles', expect=False)
        if strlist is not None:
            return self._split_profiles(strlist)

    def get_profiles(self, profile_overide_str):
        if profile_overide_str is None:
            profiles = self._default_profiles
        else:
            profiles = self._split_profiles(profile_overide_str)
        if profiles is None:
            profiles = self._find_profiles
        profiles = list(profiles)
        # protect user error
        if 'default' not in profiles:
            profiles = ['default'] + list(profiles)
        if 'nodefault' in profiles:
            profiles.pop(profiles.index('default'))
            profiles.pop(profiles.index('nodefault'))
        return profiles

    def _iterate_objects(self, profile):
        if profile == 'default':
            path = self.OBJECTS_PATH
        else:
            path = self.OBJECTS_PROFILE_PATH.format(profile)
        opts = self.get_options(path, expect=False)
        if opts is None and profile == 'default':
            opts = ()
        if opts is None:
            logger.warning(
                f'no such profile for objects: {profile} for path {path}' +
                '--maybe entries exist in other profiles')
            opts = ()
        return map(lambda x: x.strip(), opts)

    def get_discoverable_objects(self, profiles):
        return it.chain(*map(self._iterate_objects, profiles))

    def get_empty_dirs(self, profiles):
        paths = []
        for profile in profiles:
            if profile == 'default':
                path = self.EMPTY_DIR_PATH
            else:
                path = self.EMPTY_DIR_PROFILE_PATH.format(profile)
            opts = self.get_options(path)
            if opts is None:
                ## warnings for missing empty directory entries is worth it
                # logger.warning(
                #     f'no such profile for objects: {profile} for path {path}' +
                #     '--maybe entries exist in other profiles')
                pass
            else:
                paths.extend(opts)
        return map(lambda x: Path(x).expanduser().absolute(), paths)

    def _get_path(self, name):
        return Path(self.get_option(name, expect=True)).expanduser().absolute()

    @property
    def dist_dir(self):
        return self._get_path(f'{self.ROOT}.local.dist_dir')

    @dist_dir.setter
    def dist_dir(self, dist_dir):
        if self.default_vars is None:
            self.default_vars = {}
        self.default_vars[f'{self.ROOT}.local.dist_dir'] = dist_dir

    @property
    def wheel_dir_name(self):
        return self._get_path(f'{self.ROOT}.local.wheels_dir')

    @property
    def bootstrap_script_file(self):
        return Path(self.dist_dir, 'bootstrap.sh')
