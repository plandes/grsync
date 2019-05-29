from zensols.actioncli import OneConfPerActionOptionsCliEnv
from zensols.grsync import (
    AppConfig,
    DistManager,
)


class InfoCli(object):
    def __init__(self, config, fmt=None, repo_names=None, profiles=None):
        self.config = config
        self.fmt = fmt
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


class FreezeThawCli(object):
    def __init__(self, config=None, dist_dir=None, target_dir=None,
                 wheel_dependency='zensols.grsync', profiles=None):
        self.dm = DistManager(config, dist_dir, target_dir, profiles=profiles)
        self.wheel_dependency = wheel_dependency

    def freeze(self):
        self.dm.freeze(self.wheel_dependency)

    def thaw(self):
        self.dm.thaw()


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
                         'format string (i.e. {name}: {path} ({remotes}))'}]
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
                {'name': 'freezethaw',
                 'executor': lambda params: FreezeThawCli(**params),
                 'actions': [{'name': 'freeze',
                              'doc': 'create a distribution',
                              'opts': [dist_dir_op, wheel_dir_op, profile_op]},
                             {'name': 'thaw',
                              'doc': 'build out a distribution',
                              'opts': [dist_dir_op, target_dir_op,
                                       profile_op]}]}],
               'config_option': {'name': 'config',
                                 'expect': False,
                                 'opt': ['-c', '--config', False,
                                         {'dest': 'config', 'metavar': 'FILE',
                                          'help': 'configuration file'}]},
               'whine': 1}
        super(ConfAppCommandLine, self).__init__(
            cnf, config_env_name='grsyncrc', config_type=AppConfig,
            pkg_dist='zensols.grsync')


def main():
    cl = ConfAppCommandLine()
    cl.invoke()
