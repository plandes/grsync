from zensols.actioncli import OneConfPerActionOptionsCliEnv
from zensols.grsync import (
    AppConfig,
    DistManager,
)


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
        cnf = {'executors':
               [{'name': 'distribution',
                 'executor': lambda params: DistManager(**params),
                 'actions': [{'name': 'info',
                              'meth': 'discover_info',
                              'doc': 'pretty print discovery information'},
                             {'name': 'freeze',
                              'doc': 'create a distribution',
                              'opts': [dist_dir_op, wheel_dir_op]},
                             {'name': 'thaw',
                              'doc': 'build out a distribution',
                              'opts': [dist_dir_op, target_dir_op]}]}],
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
