from pathlib import Path
from zensols.actioncli import YamlConfig


class AppConfig(YamlConfig):
    """Application specific configuration access and parsing..

    """
    def __init__(self, config_file=None, default_vars=None):
        super(AppConfig, self).__init__(
            config_file, delimiter='^', default_vars=default_vars)

    @property
    def discoverable_objects(self):
        return map(lambda x: x.strip(),
                   self.get_options('discover.objects', expect=True))

    @property
    def empty_dirs(self):
        return map(lambda x: Path(x).expanduser(),
                   self.get_options('discover.empty_dirs', expect=True))

    @property
    def dist_dir(self):
        return Path(self.get_option('discover.local.dist_dir', expect=True))

    @dist_dir.setter
    def dist_dir(self, dist_dir):
        if self.default_vars is None:
            self.default_vars = {}
        self.default_vars['discover.local.dist_dir'] = dist_dir

    @property
    def wheel_dir_name(self):
        return self.get_option('discover.local.wheels_dir', expect=True)

    @property
    def bootstrap_script_file(self):
        return Path(self.dist_dir, 'bootstrap.sh')
