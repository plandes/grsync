import logging
from pathlib import Path
from git import Repo
from zensols.grsync import PathUtil, RemoteSpec

logger = logging.getLogger(__name__)
MASTER_SECTION = 'branch "master"'


class RepoSpec(object):
    """This class represents a git repository and all the symbolic links from the
    distribution (usually the user's home directory) that link into it.

    """
    def __init__(self, path: Path, repo: Repo = None):
        """Create with the path to the repo and optionally a git.Repo."""
        self.path = path
        self._repo = repo
        self.links = ()

    @property
    def name(self):
        return self.path.name

    @property
    def repo(self):
        if self._repo is None:
            self._repo = Repo(str(self.path.resolve()))
        return self._repo

    @property
    def master_remote(self):
        if not hasattr(self, '_master_remote'):
            config = self.repo.config_reader()
            if config.has_section(MASTER_SECTION) and \
               config.has_option(MASTER_SECTION, 'remote'):
                self._master_remote = config.get(MASTER_SECTION, 'remote')
            else:
                self._master_remote = None
            logger.debug('path: {}, master remote: {}'.
                         format(self.path.resolve(), self._master_remote))
        return self._master_remote

    @property
    def remotes(self):
        remotes = []
        master_remote = self.master_remote
        for remote in self.repo.remotes:
            is_master = remote.name == master_remote
            remotes.append(RemoteSpec(remote, is_master))
        return remotes

    @property
    def relative_path(self):
        return PathUtil.relative_to_home(self.path)

    def _is_linked_to(self, link):
        is_linked = str(link.target).startswith(str(self.path))
        if is_linked:
            link.increment_use_count()
        return is_linked

    def add_linked(self, links):
        self.links = tuple(filter(lambda l: self._is_linked_to(l), links))

    def freeze(self):
        return {'name': self.name,
                'path': str(self.relative_path),
                'links': [l.freeze() for l in self.links],
                'remotes': [r.freeze() for r in self.remotes]}

    def __str__(self):
        remotes = ', '.join(('({})'.format(x) for x in self.remotes))
        return '{}: {}, r={}'.format(self.name, self.relative_path, remotes)

    def __repr__(self):
        return self.__str__()


class FrozenRepo(object):
    def __init__(self, remotes: list, links: list, target_dir: Path,
                 path: Path, repo_pref: str):
        self.remotes = remotes
        self.links = links
        self.target_dir = target_dir
        self.path = path
        self.repo_pref = repo_pref

    def _split_master_remote_defs(self):
        not_masters = []
        master = None
        for rmd in self.remotes:
            if rmd['name'] == self.repo_pref:
                master = rmd
            else:
                not_masters.append(rmd)
        if master is None:
            not_masters.clear()
            for rmd in self.remotes:
                if rmd['is_master']:
                    master = rmd
                else:
                    not_masters.append(rmd)
        if master is None:
            master = not_masters[0]
            not_masters = not_masters[1:]
        return master, not_masters

    def thaw(self):
        """Thaw a RepoSpec object, which does a clone and then creates the (remaining
        if any) remotes.  This also creates the symbol links that link into
        this repo.  Then return the object represented by the new repo.

        """
        if self.path.exists():
            logger.warning('path already exists: {}--skipping repo clone'.
                           format(self.path))
            repo_spec = RepoSpec(self.path)
        else:
            master, not_masters = self._split_master_remote_defs()
            name = master['name']
            url = master['url']
            logger.info(f'cloning repo: {url} -> {self.path}')
            repo = Repo.clone_from(url, self.path, recursive=True)
            repo.remotes[0].rename(name)
            for rmd in not_masters:
                repo.create_remote(rmd['name'], rmd['url'])
            repo_spec = RepoSpec(self.path, repo)
        for link in self.links:
            logger.info(f'thawing link {link}')
            if link.source.exists():
                logger.warning(f'refusing to overwrite link: {link.source}')
            else:
                link.source.symlink_to(link.target)
        repo_spec.links = self.links
        return repo_spec

    def __str__(self):
        return f'{self.path} -> {self.target_dir}: {self.remotes}'

    def __repl__(self):
        return self.__str__()
