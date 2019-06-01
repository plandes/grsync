import logging
import unittest
from pathlib import Path
from git import Repo
import shutil
from zensols.grsync import (
    AppConfig,
    DistManager,
)

logger = logging.getLogger('zensols.grsync.test_freeze')
#logging.basicConfig(level=logging.INFO)
#logger.setLevel(logging.DEBUG)
#logging.getLogger('zensols.grsync.freeze').setLevel(logging.DEBUG)


class TestFreeze(unittest.TestCase):
    def setUp(self):
        logger.info('setting up')
        mpath = Path('target/mock')
        if not mpath.exists():
            vpath = mpath / 'view'
            vpath.mkdir(parents=True)
            rpath = vpath / 'repo_def'
            Repo.clone_from('https://github.com/plandes/zenbuild', rpath)
            shutil.copytree(rpath, vpath / 'repo_src')
            emp_path = mpath / 'dir_a' / 'dir_b'
            Path(emp_path).mkdir(parents=True)
            shutil.copy('README.md', mpath / 'file_a.txt')
            file_a = mpath / 'dir_a' / 'file_a.txt'
            shutil.copy('README.md', file_a)
            Path(mpath).joinpath('opt', 'empty_dir').mkdir(0o755, parents=True)
            s_src = mpath / 'symlink.txt'
            s_src.symlink_to(Path('.').joinpath('dir_a', 'file_a.txt'))
            s_src = mpath / 'symlink_to_repo'
            s_src.symlink_to(Path('.') / 'view' / 'repo_src' / 'README.md')
        self.mpath = mpath

    def create_config(self):
        return AppConfig(Path('test-resources/fs-test.yml').expanduser())

    def test_something(self):
        logging.info('testing freeze')
        dm = DistManager(self.create_config(), target_dir=self.mpath.absolute())
        #dm.discover_info()
        res = dm.discoverer.freeze(flatten=True)
        for n in 'create_date source'.split():
            del res[n]
        c = {'empty_dirs': [{'mode': 16877, 'modestr': 'drwxr-xr-x', 'rel': 'opt/empty_dir'}],
             'files': [{'mode': 33188,
                        'modestr': '-rw-r--r--',
                        'rel': 'dir_a/file_a.txt'}],
             'links': [{'source': 'profile_{os}', 'target': 'newdir/dir_a'}],
             'repo_pref': 'github',
             'repo_specs': ({'links': [],
                             'name': 'repo_def',
                             'path': 'view/repo_def',
                             'remotes': [{'is_master': True,
                                          'name': 'origin',
                                          'url': 'https://github.com/plandes/zenbuild'}]},
                            {'links': [{'source': 'symlink_to_repo',
                                        'target': 'view/repo_src/README.md'}],
                             'name': 'repo_src',
                             'path': 'view/repo_src',
                             'remotes': [{'is_master': True,
                                          'name': 'origin',
                                          'url': 'https://github.com/plandes/zenbuild'}]}),}
        self.assertEqual(sorted(c.items()), sorted(res.items()))
