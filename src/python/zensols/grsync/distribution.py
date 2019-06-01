import logging
from pathlib import Path
import platform
from zensols.actioncli import persisted
from zensols.grsync import (
    FrozenRepo,
    FileEntry,
    LinkEntry,
    PathTranslator,
)

logger = logging.getLogger(__name__)


class Distribution(object):
    def __init__(self, path: Path, struct: list, target_dir: Path,
                 path_translator: PathTranslator):
        self.path = path
        self.struct = struct
        self.target_dir = target_dir
        self.path_translator = path_translator
        self.params = {'os': platform.system().lower()}

    def _target_relative(self, path):
        """Return a path that is relative to where we're thawing the distribution,
        which is usually the user's home directory.

        """
        return Path.joinpath(self.target_dir, path)

    @property
    @persisted('_files')
    def files(self) -> list:
        return map(lambda fi: FileEntry(self, fi), self.struct['files'])

    @property
    @persisted('_empty_dirs')
    def empty_dirs(self) -> list:
        return map(lambda fi: FileEntry(self, fi), self.struct['empty_dirs'])

    @property
    @persisted('_links')
    def links(self) -> list:
        return map(lambda fi: LinkEntry(self, fi), self.struct['links'])

    @property
    @persisted('_repos')
    def repos(self) -> list:
        repos = []
        repo_pref = self.struct['repo_pref']
        for rdef in self.struct['repo_specs']:
            links = tuple(map(lambda fi: LinkEntry(self, fi),
                              rdef['links']))
            repo = FrozenRepo(rdef['remotes'], links, self.target_dir,
                              self._target_relative(rdef['path']), repo_pref,
                              self.path_translator)
            repos.append(repo)
        return repos
