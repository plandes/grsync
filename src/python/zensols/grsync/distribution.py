""""Contains the class needed to thaw the distribution.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Dict, Any, Iterable
import logging
from pathlib import Path
import platform
import zipfile
import json
from zensols.persist import persisted, PersistedWork
from zensols.grsync import (
    FrozenRepo,
    FileEntry,
    LinkEntry,
    PathTranslator,
    Discoverer,
)

logger = logging.getLogger(__name__)


class Distribution(object):
    """Represents a frozen distribution.

    """
    def __init__(self, path: Path, defs_file: Path, target_dir: Path,
                 path_translator: PathTranslator):
        """Initialize the distribution instance.

        :param path: points to the distribution file itself

        :param target_dir: points to the directory where we thaw the
                           distribution

        :param path_translator: translates relative paths to the thaw directory

        """
        self.path = path
        self.defs_file = defs_file
        self.target_dir = target_dir
        self.path_translator = path_translator
        self.params = {'os': platform.system().lower()}

    @classmethod
    def from_struct(cls: type, struct: Dict[str, Any],
                    target_dir: Path) -> Distribution:
        """Return a distrbution directly from the data structure created from
        :class:`.Discoverer`.

        :param struct: the data structure given by :meth:`.Discoverer.freeze`
                       using ``flatten=True``

        :param target_dir: where the distribution will be *thawed*

        """
        self = cls(None, None, target_dir, PathTranslator(target_dir))
        self._struct = PersistedWork('_struct', self, initial_value=struct)
        return self

    @classmethod
    def from_discoverer(cls: type, discoverer: Discoverer,
                        target_dir: Path) -> Distribution:
        """Return a distrbution directly from the data structure created from
        :class:`.Discoverer`.

        :param discoverer: a discoverer instance created by the *freeze* state

        :param target_dir: where the distribution will be *thawed*

        """
        fspec = discoverer.freeze(True)
        return cls.from_struct(fspec, target_dir)

    @property
    @persisted('_struct')
    def struct(self) -> Dict[str, Any]:
        """Return the JSON deserialized (meta data) of the distribution.

        """
        with zipfile.ZipFile(str(self.path.resolve())) as zf:
            with zf.open(self.defs_file) as f:
                jstr = f.read().decode('utf-8')
                struct = json.loads(jstr)
        return struct

    @property
    def version(self) -> str:
        """Get the distribution format version, which for now, is just the application
        version.

        """
        if 'app_version' in self.struct:
            return self.struct['app_version']

    @property
    @persisted('_files')
    def files(self) -> Iterable[FileEntry]:
        """Get the files in the distribution.

        """
        return map(lambda fi: FileEntry(self, fi), self.struct['files'])

    @property
    @persisted('_empty_dirs')
    def empty_dirs(self) -> Iterable[FileEntry]:
        """Get empty directories defined in the dist configuration.
        """
        return map(lambda fi: FileEntry(self, fi), self.struct['empty_dirs'])

    @property
    @persisted('_links')
    def links(self) -> Iterable[LinkEntry]:
        """Pattern links and symbolic links not pointing to repositories.

        """
        return map(lambda fi: LinkEntry(self, fi), self.struct['links'])

    @property
    @persisted('_repos')
    def repos(self) -> Iterable[FrozenRepo]:
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
