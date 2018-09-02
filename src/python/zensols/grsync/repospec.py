import logging
from pathlib import Path
from git import Repo
from zensols.grsync import PathUtil, RemoteSpec

logger = logging.getLogger('zensols.grsync.rspec')
MASTER_SECTION = 'branch "master"'


class RepoSpec(object):
    """This class represents a git repository and all the symbolic links from the
    distribution (usually the user's home directory) that link into it.

    """
    def __init__(self, path: Path, repo: Repo=None):
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

    @classmethod
    def _split_master_remote_defs(clz, rdef):
        not_masters = []
        master = None
        for rmd in rdef['remotes']:
            if rmd['is_master']:
                master = rmd
            else:
                not_masters.append(rmd)
        if master is None:
            master = not_masters[0]
            not_masters = not_masters[1:]
        return master, not_masters

    @classmethod
    def thaw(clz, rdef, target_dir, repo_path):
        """Thaw a RepoSpec object, which does a clone and then creates the (remaining
        if any) remotes.  This also creates the symbol links that link into
        this repo.  Then return the object represented by the new repo.

        """
        if repo_path.exists():
            logger.warning('path already exists: {}--skipping repo clone'.
                           format(repo_path))
            repo_spec = RepoSpec(repo_path)
        else:
            master, not_masters = clz._split_master_remote_defs(rdef)
            name = master['name']
            url = master['url']
            logger.info('cloning repo: {} -> {}'.format(url, repo_path))
            repo = Repo.clone_from(url, repo_path, recursive=True)
            repo.remotes[0].rename(name)
            for rmd in not_masters:
                repo.create_remote(rmd['name'], rmd['url'])
            repo_spec = RepoSpec(repo_path, repo)
        for link in rdef['links']:
            src = Path(target_dir, link['source'])
            targ = Path(target_dir, link['target'])
            link['source'] = src
            link['target'] = targ
            logger.info('thawing link {} -> {}'.format(src, targ))
            if src.exists():
                logger.warning('refusing to overwrite link: {}'.format(src))
            else:
                src.symlink_to(targ)
        repo_spec.links = rdef['links']
        return repo_spec

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
        return str(link.target).startswith(str(self.path))

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
