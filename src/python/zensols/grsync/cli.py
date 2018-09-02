import os
from zensols.actioncli import OneConfPerActionOptionsCli
from zensols.grsync import AppConfig
from zensols.grsync import DistManager

CONF_ENV_VAR = 'GRSYNCRC'


# recommended app command line
class ConfAppCommandLine(OneConfPerActionOptionsCli):
    """Command line entry point.

    """
    def __init__(self):
        if CONF_ENV_VAR in os.environ:
            default_config_file = os.environ[CONF_ENV_VAR]
        else:
            default_config_file = '%s/.grsyncrc' % os.environ['HOME']
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
                         'help': 'the wheel dependency (you probably don\'t want to set this)'}]
        cnf = {'executors':
               [{'name': 'distribution',
                 'executor': lambda params: DistManager(**params),
                 'actions': [{'name': 'info',
                              'meth': 'discover_info',
                              'doc': 'pretty print discovery information',
                              'opts': []},
                             {'name': 'freeze',
                              'doc': 'create a distribution',
                              'opts': [dist_dir_op, wheel_dir_op]},
                             {'name': 'thaw',
                              'doc': 'build out a distribution',
                              'opts': [dist_dir_op, target_dir_op]}]}],
               'config_option': {'name': 'config',
                                 'opt': ['-c', '--config', False,
                                         {'dest': 'config', 'metavar': 'FILE',
                                          'default': default_config_file,
                                          'help': 'configuration file'}]},
               'whine': 1}
        super(ConfAppCommandLine, self).__init__(
            cnf, pkg_dist='zensols.grsync')

    def _create_config(self, config_file, default_vars):
        defs = {}
        defs.update(default_vars)
        defs.update(os.environ)
        return AppConfig(config_file=config_file, default_vars=defs)


def main():
    cl = ConfAppCommandLine()
    cl.invoke()
