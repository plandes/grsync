import logging
from zensols.actioncli import OneConfPerActionOptionsCliEnv
from zensols.grsync import (
    AppConfig,
    DistManager,
    RepoSpec,
)


class InfoCli(object):
    def __init__(self, config, fmt=None, repo_names=None, profiles=None):
        self.config = config
        self.fmt = fmt
        if repo_names is not None:
            self.repo_names = repo_names.split(',')
        else:
            self.repo_names = repo_names
        self.profiles = profiles

    def info(self):
        dm = DistManager(self.config, profiles=self.profiles)
        dm.discover_info()

    def repos(self):
        dm = DistManager(self.config, profiles=self.profiles)
        dm.print_repos(self.fmt)

    def repo_info(self):
        dm = DistManager(self.config, profiles=self.profiles)
        dm.print_repo_info(self.repo_names)


class DistManagerCli(object):
    def __init__(self, config=None, dist_dir=None, target_dir=None,
                 move_dir=None, wheel_dependency='zensols.grsync', profiles=None):
        self.move_dir = move_dir
        self.dm = DistManager(config, dist_dir, target_dir, profiles=profiles)
        self.wheel_dependency = wheel_dependency

    def freeze(self):
        self.dm.freeze(self.wheel_dependency)

    def thaw(self):
        self.dm.thaw()

    def move(self):
        self.dm.move(self.move_dir)


class ConfAppCommandLine(OneConfPerActionOptionsCliEnv):
    """Command line entry point.

    """
    def __init__(self):
        dist_dir_op = ['-d', '--distdir', False,
                       {'dest': 'dist_dir',
                        'metavar': 'DIRECTORY',
                        'help': 'the location of build out distribution'}]
        target_dir_op = ['-t', '--targetdir', False,
                         {'dest': 'target_dir', 'metavar': 'DIRECTORY',
                          'help': 'the location of build out target dir'}]
        move_dir_op = ['-m', '--movedir', False,
                       {'dest': 'move_dir', 'metavar': 'DIRECTORY',
                        'help': 'the location of build out move dir'}]
        wheel_dir_op = [None, '--wheeldep', False,
                        {'dest': 'wheel_dependency',
                         'default': 'zensols.grsync',
                         'metavar': 'STRING',
                         'help': 'used to create the wheel dep files'}]
        rp_format_op = ['-f', '--format', False,
                        {'dest': 'fmt',
                         'default': '{path}',
                         'metavar': 'STRING',
                         'help':
                         f'format string (i.e. {RepoSpec.DEFAULT_FORMAT})'}]
        repo_name_op = ['-n', '--name', False,
                        {'dest': 'repo_names',
                         'metavar': 'STRING',
                         'help': 'comma spearated list of repo names'}]
        profile_op = ['-p', '--profiles', False,
                      {'metavar': 'STRING',
                       'help': 'comma spearated list of profiles in config'}]
        cnf = {'executors':
               [{'name': 'info',
                 'executor': lambda params: InfoCli(**params),
                 'actions': [{'name': 'info',
                              'doc': 'pretty print discovery information'},
                             {'name': 'repos',
                              'doc': 'output all repository top level info',
                              'opts': [rp_format_op, profile_op]},
                             {'name': 'repoinfo',
                              'meth': 'repo_info',
                              'doc': 'get information on repositories',
                              'opts': [repo_name_op, profile_op]}]},
                {'name': 'dist',
                 'executor': lambda params: DistManagerCli(**params),
                 'actions': [{'name': 'freeze',
                              'doc': 'create a distribution',
                              'opts': [dist_dir_op, wheel_dir_op, profile_op]},
                             {'name': 'thaw',
                              'doc': 'build out a distribution',
                              'opts': [dist_dir_op, target_dir_op,
                                       profile_op]},
                             {'name': 'move',
                              'doc': 'move a distribution to another root (easy to delete)',
                              'opts': [dist_dir_op, target_dir_op,
                                       move_dir_op, profile_op]}]}],
               'config_option': {'name': 'config',
                                 'expect': False,
                                 'opt': ['-c', '--config', False,
                                         {'dest': 'config', 'metavar': 'FILE',
                                          'help': 'configuration file'}]},
               'whine': 1}
        super(ConfAppCommandLine, self).__init__(
            cnf, config_env_name='grsyncrc', config_type=AppConfig,
            pkg_dist='zensols.grsync')

    def _config_logging(self, level):
        root = logging.getLogger()
        map(root.removeHandler, root.handlers[:])
        if level == 0:
            levelno = logging.ERROR
        elif level == 1:
            levelno = logging.WARNING
        elif level == 2:
            levelno = logging.INFO
        elif level == 3:
            levelno = logging.DEBUG
        if level <= 2:
            fmt = '%(message)s'
        else:
            fmt = '%(levelname)s:%(asctime)-15s %(name)s: %(message)s'
        logging.basicConfig(format=fmt, level=levelno)


def main():
    cl = ConfAppCommandLine()
    cl.invoke()
