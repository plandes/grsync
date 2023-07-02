#!/usr/bin/env python

"""A command line tool that provides information about the git repository
configuration of the user's GRSync configuration.  This script iterates through
all of your configured repositories and performs an action on it, such as using
GNU make to clean, getting status, pulling etc.

"""
__author__ = 'Paul Landes'

from typing import Iterable, Callable, Tuple, Dict
from dataclasses import dataclass, field
import sys
import logging
from pathlib import Path
import plac
import git
from zensols.cli import CliHarness
from zensols.grsync import (
    RepoSpec, Discoverer, DistManager, ApplicationFactory, InfoApplication
)
from zensols.util import Executor

logger = logging.getLogger('repoutil')


@dataclass
class RepoUtil(object):
    """A utility class to provide information about the git repository
    configuration.

    """
    log_dir: bool = field(default=True)
    dry_run: bool = field(default=False)

    @property
    def dist_manager(self) -> DistManager:
        """The distribution manager from the Zensols Info application."""
        harness: CliHarness = ApplicationFactory.create_harness()
        app: InfoApplication = harness.get_instance('repos')
        return app.dist_mng

    @property
    def repo_specs(self) -> Iterable[RepoSpec]:
        """The information on each git repository found by the GRSync
        configuraiton.

        """
        dist_manager: DistManager = self.dist_manager
        disc: Discoverer = dist_manager.discoverer
        return disc.discover(False)['repo_specs']

    @property
    def repo_paths(self) -> Iterable[Path]:
        """The paths of the configured git repositories."""
        return map(lambda x: x.path, self.repo_specs)

    def _execute(self, cmd: str, exist_path_fn: Callable = None):
        ex = Executor(logger, dry_run=self.dry_run, check_exit_value=None)
        for p in self.repo_paths:
            check_dir = p if exist_path_fn is None else exist_path_fn(p)
            if not check_dir.exists():
                logger.warning(f'{p} disappeared--skipping')
            else:
                logger.debug(f'run {cmd}: {p}')
                if self.log_dir:
                    logger.info(f'\n----<{p}>----')
                ex.run(cmd.format(**{'path': p}))

    def dirty(self):
        """Print dirty repos, which are those that need committing."""
        rs: RepoSpec
        for rs in filter(lambda rs: rs.repo.is_dirty(), self.repo_specs):
            print(rs.path)

    def uncommitted(self, remote: str = 'origin', branch: str = 'master'):
        """Print repos that have commits that haven't been pushed yet."""
        def has_commits(rs: RepoSpec) -> bool:
            commits: Tuple[git.Commit] = ()
            try:
                spec: str = f'{remote}/{branch}..{branch}'
                # only the given remote and branch is supported for now
                commits = tuple(rs.repo.iter_commits(spec))
            except git.GitCommandError:
                pass
            return len(commits) > 0

        rs: RepoSpec
        for rs in filter(has_commits, self.repo_specs):
            print(rs.path)

    def clean(self):
        """Do a make clean on all repo paths."""
        def exist_path_fn(path):
            return path / 'makefile'

        self._execute('make -C {path} clean', exist_path_fn)

    def status(self):
        """Do a git status on each path."""
        self._execute('( cd {path} ; git status )')

    def pull(self):
        """Pull from the default up stream repo."""
        self._execute('cd {path} ; git pull --recurse-submodules')

    def list(self):
        """Print a list of actions for this script"""
        print('\n'.join('dirty uncommitted clean status pull list'.split()))


@plac.annotations(
    action=('Action: (<dirty|uncommitted [-b,-r]]|clean|status|pull|fix|list>)',
            'positional', None, str),
    dryrun=('don\'t do anything, just act like it', 'flag', 'd'),
    remote=('repo remote', 'option', 'r'),
    branch=('repo branch', 'option', 'b'))
def main(action: str, dryrun: bool = False,
         remote: str = 'origin', branch: str = 'master'):
    logging.basicConfig(level=logging.WARNING, format='%(message)s')
    logger.setLevel(level=logging.INFO)
    ru = RepoUtil(dry_run=dryrun)
    params: Dict[str, str] = {}
    if action == 'uncommitted':
        params.update({'remote': remote, 'branch': branch})
    try:
        getattr(ru, action)(**params)
    except AttributeError as e:
        print(f'no such action: {action}: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    plac.call(main)
