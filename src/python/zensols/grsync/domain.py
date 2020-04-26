import logging
from git import Remote
from pathlib import Path
from zensols.persist import persisted

logger = logging.getLogger(__name__)


class PathTranslator(object):
    """
    Utility class around helping with paths.

    """
    def __init__(self, target_path):
        self.target_path = target_path

    def relative_to(self, path):
        """Return a path that's relative to the user's home directory."""
        return path.relative_to(self.target_path.resolve())

    def to_relative(self, path):
        return str(Path(self.target_path, path).absolute())

    def expand(self, path):
        """Return the user's home directory as a ``pathlib.Path`` object."""
        return Path.joinpath(self.target_path, path)


class SymbolicLink(object):
    """This classs represents a file system symbolic link.  The class also freezes
    created symbol links.

    """
    def __init__(self, source: Path, path_translator: PathTranslator):
        """Create.

        :param source: The pathlib.Path that points to the symbolic link on the
        local file system.

        """
        self.source = source
        self.path_translator = path_translator
        self.use_count = 0

    @property
    def target(self):
        """The target (where it point to)."""
        return self.source.resolve()

    @property
    def source_relative(self):
        """The relative location source (to the user's home)."""
        if not hasattr(self, '_src'):
            self._src = self.path_translator.relative_to(self.source)
        return self._src

    @property
    def target_relative(self):
        """The relative location (where it points to) relative to the user's home.

        """
        if not hasattr(self, '_dst'):
            self._dst = self.path_translator.relative_to(self.target)
        return self._dst

    def increment_use_count(self):
        """Indicate this symblic link is used (linked) to another target."""
        self.use_count += 1

    def freeze(self):
        """Create and return an object graph as a dict of the link."""
        return {'source': str(self.source_relative),
                'target': str(self.target_relative)}

    def __str__(self):
        return '{} -> {}'.format(self.source, self.target)

    def __repr__(self):
        return self.__str__()


class FileEntry(object):
    """Represents a file based entry in the frozen version of the distribution zip.

    """
    def __init__(self, dist, finfo: dict):
        self.dist = dist
        self.finfo = finfo

    def _str_to_path(self, pathstr: str):
        return Path(pathstr)

    def _target_relative(self, path):
        return self.dist.path_translator.expand(path)

    @property
    @persisted('_rel')
    def relative(self):
        "Return the relative path of the file."""
        return Path(self._str_to_path(self.finfo['rel']))

    @property
    @persisted('_path')
    def path(self):
        "Return the absolute path of the file."""
        return self._target_relative(self.relative)

    @property
    @persisted('_mode')
    def mode(self):
        "Return the numeric mode of the file"
        return self.finfo['mode']

    @property
    @persisted('_modestr')
    def modestr(self):
        "Return a human readable string of the mode of the file."
        return self.finfo['modestr']

    @property
    @persisted('_modify_time')
    def modify_time(self):
        "Return the numeric modify time of the file"
        return self.finfo['modify_time']

    def __str__(self):
        return f'{self.relative} -> {self.path}: {self.mode} ({self.modestr})'

    def __repr__(self):
        return self.__str__()


class LinkEntry(FileEntry):
    """Represents a symbolic link in the frozen version of the distribution zip.

    """
    def __init__(self, dist, finfo: dict, target_dir=None):
        super(LinkEntry, self).__init__(dist, finfo)
        self.target_dir = target_dir

    def _str_to_path(self, pathstr: str):
        return Path(pathstr.format(**self.dist.params))

    def _target_relative(self, path):
        if self.target_dir is not None:
            return Path(self.target_dir, path)
        else:
            return super(LinkEntry, self)._target_relative(path)

    @property
    @persisted('_rel')
    def relative(self):
        return Path(self._str_to_path(self.finfo['source']))

    @property
    def source(self):
        return self.path

    @property
    def target(self):
        rel_path = Path(self._str_to_path(self.finfo['target']))
        rel_path = self._target_relative(rel_path)
        return rel_path

    def __str__(self):
        return f'{self.source} -> {self.target}'


class RemoteSpec(object):
    """This class represents a remote for a git repo.
    """
    def __init__(self, remote: Remote, is_master=None):
        """Initialize

        :param remote: The a remote object from the git repo
        :param is_master: Whether or not the remote is the primary (upstream)
        remote

        """
        self.remote = remote
        with remote.config_reader as cr:
            self.url = cr.get('url')
        self.is_master = is_master

    @property
    def name(self):
        "Return the remote's name."
        return self.remote.name

    def rename(self, name, url=None):
        """Rename the remote in the git repository itself (along with the class
        instance).

        """
        remote = self.remote
        remote.rename(name)
        with remote.config_writer as cw:
            if url is not None:
                cw.set('url', url)
            self.repo.git.config('branch.master.pushremote', name)

    def freeze(self):
        """Freeze/create an object graph representation of the remote as a dict.

        """
        return {'name': self.name,
                'url': self.url,
                'is_master': self.is_master}

    def __str__(self):
        return '{}: {}'.format(self.name, self.url)

    def __repr__(self):
        return self.__str__()
