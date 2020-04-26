import logging
from pathlib import Path
import platform
import zipfile
import json
from zensols.persist import persisted
from zensols.grsync import (
    FrozenRepo,
    FileEntry,
    LinkEntry,
    PathTranslator,
)

logger = logging.getLogger(__name__)


class Distribution(object):
    """Represents a frozen distribution.

    """
    def __init__(self, path: Path, defs_file: Path, target_dir: Path,
                 path_translator: PathTranslator):
        """Initialize the distribution instance.

        :param path: points to the distribution file itself
        :param target_dir: points to the directory where we thaw the distribution
        :param path_translator: translates relative paths to the thaw directory
        """
        self.path = path
        self.defs_file = defs_file
        self.target_dir = target_dir
        self.path_translator = path_translator
        self.params = {'os': platform.system().lower()}

    @property
    @persisted('_struct')
    def struct(self):
        """Return the JSON deserialized (meta data) of the distribution.

        """
        with zipfile.ZipFile(str(self.path.resolve())) as zf:
            with zf.open(self.defs_file) as f:
                jstr = f.read().decode('utf-8')
                struct = json.loads(jstr)
        return struct

    @property
    def version(self):
        """Get the distribution format version, which for now, is just the application
        version.

        """
        if 'app_version' in self.struct:
            return self.struct['app_version']

    @property
    @persisted('_files')
    def files(self) -> list:
        """Get the files in the distribution.

        """
        return map(lambda fi: FileEntry(self, fi), self.struct['files'])

    @property
    @persisted('_empty_dirs')
    def empty_dirs(self) -> list:
        """Get empty directories defined in the dist configuration.
        """
        return map(lambda fi: FileEntry(self, fi), self.struct['empty_dirs'])

    @property
    @persisted('_links')
    def links(self) -> list:
        """Pattern links and symbolic links not pointing to repositories.

        """
        return map(lambda fi: LinkEntry(self, fi), self.struct['links'])

    @property
    @persisted('_repos')
    def repos(self) -> list:
        """Repository specifications.

        """
        repos = []
        repo_pref = self.struct['repo_pref']
        for rdef in self.struct['repo_specs']:
            links = tuple(map(lambda fi: LinkEntry(self, fi),
                              rdef['links']))
            repo = FrozenRepo(rdef['remotes'], links, self.target_dir,
                              self.path_translator.expand(rdef['path']),
                              repo_pref, self.path_translator)
            repos.append(repo)
        return repos
