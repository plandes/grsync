import unittest
from pathlib import Path
from zensols.config import YamlConfig
from zensols.grsync import AppConfig


class TestConfig(unittest.TestCase):
    def test_yaml(self):
        correct = {'discover.bootstrap.inst_dir': '${HOME}/grsync',
                   'discover.bootstrap.python_dir': '${HOME}/opt/lib/python3',
                   'discover.bootstrap.wheel_dir': 'wheels',
                   'discover.empty_dirs': ['~/tmp'],
                   'discover.local.dist_dir': './dist',
                   'discover.local.wheels_dir': 'wheels',
                   'discover.objects.default': ['~/.profile',
                                                '~/.bashrc',
                                                '~/.Xdefaults',
                                                '~/.xsession',
                                                '~/.emacs',
                                                '~/.emacs.d',
                                                '~/code/home-dir',
                                                '~/code/emacs'],
                   'discover.target':
                   [{'link': {'source': '~/.profile_${os}',
                              'target':
                              '~/code/home-dir/dot/os/${os}/profile'}}],
                   'discover.codedir': '~/code',
                   'discover.wheel.create': False}
        config = YamlConfig('test-resources/yaml-test.yml', delimiter='^')
        self.maxDiff = float('inf')
        self.assertEqual(correct, config.options)

    def test_set_dist(self):
        config = AppConfig('test-resources/midsize-test.yml')
        self.assertEqual(Path('./dist').absolute(), config.dist_dir)
        config.dist_dir = Path('./anewdir')
        self.assertEqual(Path('./anewdir').absolute(), config.dist_dir)
