import logging
import os
import unittest
from pathlib import Path
import shutil
from git import Repo
from zensols.grsync import (
    AppConfig,
    DistManager,
)

logger = logging.getLogger(__name__)

if 1:
    logging.basicConfig(level=logging.ERROR)
else:
    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger('zensols.grsync.thaw').setLevel(logging.DEBUG)


def rec_sort(x):
    if isinstance(x, list) or isinstance(x, tuple):
        x = sorted(list(map(rec_sort, x)))
    elif isinstance(x, dict):
        for k, v in x.items():
            x[k] = rec_sort(v)
        x = sorted(x.items())
    return x


class TestFreezeThaw(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 10 ** 8
        logger.info('setting up')

        self.targ_dir = Path('target')
        if self.targ_dir.exists():
            shutil.rmtree(str(self.targ_dir.absolute()))
            self.targ_dir.mkdir(parents=True)

        self.repo_path = Path('.').absolute()
        self.move_path = Path(self.targ_dir / 'move')
        freeze_dir = Path(self.targ_dir / 'mock')
        if not freeze_dir.exists():
            vpath = freeze_dir / 'view'
            vpath.mkdir(0o755, parents=True)
            rpath = vpath / 'repo_def'
            Repo.clone_from(str(self.repo_path), rpath)
            shutil.copytree(rpath, vpath / 'repo_src')
            emp_path = freeze_dir / 'dir_a' / 'dir_b'
            Path(emp_path).mkdir(0o755, parents=True)
            shutil.copy('README.md', emp_path / 'file_b.txt')
            os.chmod(str(emp_path / 'file_b.txt'), 0o664)
            shutil.copy('README.md', freeze_dir / 'file_a.txt')
            os.chmod(str(freeze_dir / 'file_a.txt'), 0o664)
            shutil.copy('README.md', freeze_dir / 'dir_a' / 'file_a.txt')
            os.chmod(str(freeze_dir / 'dir_a' / 'file_a.txt'), 0o664)
            shutil.copy('README.md', freeze_dir / 'file_0.txt')
            os.chmod(str(freeze_dir / 'file_0.txt'), 0o664)
            Path(freeze_dir).joinpath('opt', 'empty_dir').mkdir(0o755, parents=True)
            s_src = freeze_dir / 'symlink.txt'
            s_src.symlink_to(Path('.').joinpath('dir_a', 'file_a.txt'))
            s_src = freeze_dir / 'symlink_to_repo'
            s_src.symlink_to(Path('.') / 'view' / 'repo_src' / 'README.md')
            s_src = freeze_dir / 'profile_darwin'
            s_src.symlink_to(Path('.') / 'newdir' / 'dir_a')
            emp_path = freeze_dir / 'dir_s' / 'dir_y'
            Path(emp_path).mkdir(0o755, parents=True)
            s_src = freeze_dir / 'no_dst_symlink_to_a_dir'
            s_src.symlink_to(Path('.') / 'dir_s' / 'dir_y')
            emp_path = freeze_dir / 'dir_x'
            Path(emp_path).mkdir(0o755, parents=True)
            shutil.copy('README.md', freeze_dir / 'dir_x' / 'no_dst_file.txt')
            os.chmod(str(freeze_dir / 'dir_x' / 'no_dst_file.txt'), 0o664)
            s_src = freeze_dir / 'no_dst_symlink_to_a_file.txt'
            s_src.symlink_to(Path('.') / 'dir_x' / 'no_dst_file.txt')
            emp_path = freeze_dir / 'dir_w_symlinks'
            Path(emp_path).mkdir(0o755, parents=True)
            s_src = freeze_dir / 'dir_w_symlinks' / 'nd_symlink_to_a_file.txt'
            s_src.symlink_to(Path('.') / 'dir_w_symlinks' / 'no_dst_file.txt')
        self.config = AppConfig(Path('test-resources/fs-test.yml').expanduser())
        self.freeze_dir = freeze_dir
        self.thaw_dir = Path(self.targ_dir / 'thaw')
        self.dist_dir = self.targ_dir / 'dist'
        self.freeze_dm = DistManager(
            self.config, target_dir=self.freeze_dir, dist_dir=self.dist_dir)
        self.freeze_dm.app_version = 'test_run'
        self.thaw_dm = DistManager(
            self.config, target_dir=self.thaw_dir, dist_dir=self.dist_dir,
            dry_run=False)
        self.thaw_dm.app_version = 'test_run'

    def test_freeze(self):
        logging.info('testing freeze')
        dm = self.freeze_dm
        # dm.discover_info()
        res = dm.discoverer.freeze(flatten=True)
        repo_path = str(self.repo_path)
        for n in 'create_date source'.split():
            del res[n]
        for rs in res['repo_specs']:
            for r in rs['remotes']:
                r['is_master'] = True
        for lab in 'empty_dirs files'.split():
            for d in res[lab]:
                del d['create_time']
                del d['modify_time']
        c = {'empty_dirs': [{'mode': 16877, 'modestr': 'drwxr-xr-x', 'rel': 'opt/empty_dir'}],
             'files': [{'mode': 33204,
                        'modestr': '-rw-rw-r--',
                        'rel': 'file_0.txt'},
                       {'mode': 33204,
                        'modestr': '-rw-rw-r--',
                        'rel': 'dir_a/dir_b/file_b.txt'},
                       {'mode': 33204,
                        'modestr': '-rw-rw-r--',
                        'rel': 'dir_a/file_a.txt'}],
             'links': [{'source': 'profile_{os}', 'target': 'dir_a/dir_b/file_b.txt'},
                       {'source': 'symlink.txt', 'target': 'dir_a/file_a.txt'},
                       {'source': 'no_dst_symlink_to_a_dir', 'target': 'dir_s/dir_y'},
                       {'source': 'no_dst_symlink_to_a_file.txt', 'target': 'dir_x/no_dst_file.txt'},
                       {'source': 'dir_w_symlinks/nd_symlink_to_a_file.txt',
                        'target': 'dir_w_symlinks/dir_w_symlinks/no_dst_file.txt'}],
             'repo_pref': 'github',
             'repo_specs': ({'links': [],
                             'name': 'repo_def',
                             'path': 'view/repo_def',
                             'remotes': [{'is_master': True,
                                          'name': 'origin',
                                          'url': repo_path}]},
                            {'links': [{'source': 'symlink_to_repo',
                                        'target': 'view/repo_src/README.md'}],
                             'name': 'repo_src',
                             'path': 'view/repo_src',
                             'remotes': [{'is_master': True,
                                          'name': 'origin',
                                          'url': repo_path}]}),}
        self.assertEqual(rec_sort(c), rec_sort(res))

    def _check_dist(self, root, test_link_resolves):
        def fd(path):
            p = Path(root, *path.split('/')).absolute()
            logger.debug(f'create: {p}')
            return p

        sl = fd('symlink_to_repo')
        self.assertTrue(sl.is_symlink())
        if test_link_resolves:
            self.assertTrue(fd('view/repo/README.md'), sl.resolve())
        sl = fd('symlink.txt')
        self.assertTrue(sl.is_symlink())
        if test_link_resolves:
            self.assertEqual(fd('dir_a/file_a.txt'), sl.resolve())
        self.assertTrue(fd('opt/empty_dir').is_dir())
        self.assertTrue(fd('dir_a/file_a.txt').is_file())
        self.assertTrue(fd('dir_a/file_a.txt').is_file())
        self.assertTrue(fd('dir_a/dir_b').is_dir())
        self.assertTrue(fd('file_0.txt').is_file())
        self.assertTrue(fd('dir_a/file_a.txt').is_file())
        self.assertTrue(fd('dir_a/dir_b/file_b.txt').is_file())
        self.assertTrue(fd('view/repo_def/zenbuild').is_dir())
        self.assertTrue(fd('view/repo_def/.git').is_dir())
        self.assertTrue(fd('view/repo_src/zenbuild').is_dir())
        self.assertTrue(fd('view/repo_src/.git').is_dir())

    def test_thaw(self):
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.freeze_dm.freeze()
        self.assertTrue(self.dist_dir.exists())
        dm = self.thaw_dm
        dm.thaw()
        self._check_dist(self.thaw_dir, True)

    def test_move(self):
        if not self.freeze_dm.dist_file.exists():
            self.freeze_dm.freeze()
        if not self.thaw_dm.target_dir.exists():
            self.thaw_dm.thaw()
        if self.move_path.exists():
            shutil.rmtree(self.move_path)
        dm = self.thaw_dm
        # dm.dry_run = True
        dm.move(self.move_path)
        self._check_dist(self.move_path, False)
