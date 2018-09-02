import logging
from git import Remote
from pathlib import Path

logger = logging.getLogger('zensols.grsync.dom')


class PathUtil(Path):
    """Utility class around helping with paths."""

    @classmethod
    def relative_to_home(clz, path):
        """Return a path that's relative to the user's home directory."""
        return path.relative_to(Path.home().resolve())

    @classmethod
    def expand_home(clz, path):
        """Return the user's home directory as a ``pathlib.Path`` object."""
        return Path.joinpath(Path.home(), path)


class SymbolicLink(object):
    """This classs represents a file system symbolic link.  The class also freezes
    created symbol links.

    """
    def __init__(self, source):
        """Create.

        :param source: The pathlib.Path that points to the symbolic link on the
        local file system.

        """
        self.source = source

    @property
    def target(self):
        """The target (where it point to)."""
        return self.source.resolve()

    @property
    def source_relative(self):
        """The relative location source (to the user's home)."""
        if not hasattr(self, '_src'):
            self._src = PathUtil.relative_to_home(self.source)
        return self._src

    @property
    def target_relative(self):
        """The relative location (where it points to) relative to the user's home.

        """
        if not hasattr(self, '_dst'):
            self._dst = PathUtil.relative_to_home(self.target)
        return self._dst

    def freeze(self):
        """Create and return an object graph as a dict of the link."""
        return {'source': str(self.source_relative),
                'target': str(self.target_relative)}

    def __str__(self):
        return '{} -> {}'.format(self.source, self.target)

    def __repr__(self):
        return self.__str__()


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
