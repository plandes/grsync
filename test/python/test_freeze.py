import logging
import unittest
from pathlib import Path
import shutil
from git import Repo
import shutil
from zensols.grsync import (
    AppConfig,
    DistManager,
)

logger = logging.getLogger('zensols.grsync.test_freeze')
logging.basicConfig(level=logging.INFO)
#logger.setLevel(logging.DEBUG)
#logging.getLogger('zensols.grsync.thaw').setLevel(logging.DEBUG)


class TestFreezeThaw(unittest.TestCase):
    def setUp(self):
        logger.info('setting up')
        self.targ_dir = Path('target')
        freeze_dir = Path(self.targ_dir / 'mock')
        if not freeze_dir.exists():
            vpath = freeze_dir / 'view'
            vpath.mkdir(parents=True)
            rpath = vpath / 'repo_def'
            Repo.clone_from('https://github.com/plandes/zenbuild', rpath)
            shutil.copytree(rpath, vpath / 'repo_src')
            emp_path = freeze_dir / 'dir_a' / 'dir_b'
            Path(emp_path).mkdir(parents=True)
            shutil.copy('README.md', freeze_dir / 'file_a.txt')
            file_a = freeze_dir / 'dir_a' / 'file_a.txt'
            shutil.copy('README.md', file_a)
            Path(freeze_dir).joinpath('opt', 'empty_dir').mkdir(0o755, parents=True)
            s_src = freeze_dir / 'symlink.txt'
            s_src.symlink_to(Path('.').joinpath('dir_a', 'file_a.txt'))
            s_src = freeze_dir / 'symlink_to_repo'
            s_src.symlink_to(Path('.') / 'view' / 'repo_src' / 'README.md')
        self.config = AppConfig(Path('test-resources/fs-test.yml').expanduser())
        self.freeze_dir = freeze_dir
        self.thaw_dir = Path(self.targ_dir / 'thaw')
        self.dist_dir = self.targ_dir / 'dist'
        self.freeze_dm = DistManager(
            self.config, target_dir=self.freeze_dir, dist_dir=self.dist_dir)

    def test_freeze_struct(self):
        logging.info('testing freeze')
        dm = self.freeze_dm
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

    def test_thaw(self):
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.freeze_dm.freeze()
        self.assertTrue(self.dist_dir.exists())
        dm = DistManager(
            self.config, target_dir=self.thaw_dir, dist_dir=self.dist_dir,
            dry_run=False)
        dm.thaw()