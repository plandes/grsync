import logging
import sys
from pathlib import Path
from git import Repo
from zensols.persist import persisted
from zensols.grsync import (
    RemoteSpec,
    PathTranslator
)

logger = logging.getLogger(__name__)
MASTER_SECTION = 'branch "master"'


class RepoSpec(object):
    """This class represents a git repository and all the symbolic links from the
    distribution (usually the user's home directory) that link into it.

    """
    DEFAULT_FORMAT = '{name}: {path}, remotes={remotes}, dirty={dirty}'
    SHORT_FORMAT = '{name}: {path} ({remotes})'

    def __init__(self, path: Path, path_translator: PathTranslator,
                 repo: Repo = None):
        """Create with the path to the repo and optionally a git.Repo."""
        self.path = path
        self.path_translator = path_translator
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

    def _is_linked_to(self, link):
        is_linked = str(link.target).startswith(str(self.path))
        if is_linked:
            link.increment_use_count()
        return is_linked

    def add_linked(self, links):
        self.links = tuple(filter(lambda l: self._is_linked_to(l), links))

    def freeze(self):
        return {'name': self.name,
                'path': str(self.path_translator.relative_to(self.path)),
                'links': [l.freeze() for l in self.links],
                'remotes': [r.freeze() for r in self.remotes]}

    def format(self, fmt=None, writer=sys.stdout):
        if fmt is None:
            fmt = self.DEFAULT_FORMAT
        remotes = map(lambda x: x.name, self.remotes)
        remotes = ' '.join(sorted(remotes))
        rs = {'name': self.name,
              'path': self.path_translator.to_relative(self.path),
              'dirty': str(self.repo.is_dirty()).lower(),
              'remotes': remotes}
        return fmt.format(**rs)

    def write(self, writer=sys.stdout):
        path = self.path_translator.to_relative(self.path)
        untracked = self.repo.untracked_files
        diffs = self.repo.index.diff(None)
        writer.write(f'{self.name}:\n')
        writer.write(f'  path: {path}\n')
        writer.write(f'  dirty: {str(self.repo.is_dirty()).lower()}\n')
        writer.write('  remotes:\n')
        for r in self.remotes:
            writer.write(f'    {r.name}: {r.url}\n')
        if len(self.links) > 0:
            writer.write('  links:\n')
            for l in self.links:
                source = self.path_translator.to_relative(l.source)
                target = self.path_translator.to_relative(l.target)
                writer.write(f'    {source} -> {target}\n')
        if len(diffs) > 0:
            writer.write('  diffs:\n')
            for d in diffs:
                writer.write(f'    {d.a_path}\n')
        if len(untracked) > 0:
            writer.write('  untracked:\n')
            for f in untracked:
                writer.write(f'    {f}\n')

    def __str__(self):
        return self.format()

    def __repr__(self):
        return self.__str__()


class FrozenRepo(object):
    def __init__(self, remotes: list, links: list, target_dir: Path,
                 path: Path, repo_pref: str, path_translator: PathTranslator):
        """Initialize.

        :type links: list of LinkEntry (circular dependency with thaw.py for
        now)

        """
        self.remotes = remotes
        self.links = links
        self.target_dir = target_dir
        self.path = path
        self.repo_pref = repo_pref
        self.path_translator = path_translator

    @property
    @persisted('_repo_spec')
    def repo_spec(self):
        return RepoSpec(self.path, self.path_translator)

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
            repo_spec = RepoSpec(self.path, self.path_translator)
        else:
            master, not_masters = self._split_master_remote_defs()
            name = master['name']
            url = master['url']
            logger.info(f'cloning repo: {url} -> {self.path}')
            repo = Repo.clone_from(url, self.path, recursive=True)
            repo.remotes[0].rename(name)
            for rmd in not_masters:
                repo.create_remote(rmd['name'], rmd['url'])
            repo_spec = RepoSpec(self.path, self.path_translator, repo)
        for link in self.links:
            logger.info(f'thawing link {link}')
            if link.source.exists():
                logger.warning(f'refusing to overwrite link: {link.source}')
            else:
                par = link.source.parent
                if not par.exists():
                    logger.info('creating link directory: {par}')
                    par.mkdir(parents=True)
                link.source.symlink_to(link.target)
        repo_spec.links = self.links
        return repo_spec

    def __str__(self):
        return f'{self.path} -> {self.target_dir}: {self.remotes}'

    def __repr__(self):
        return self.__str__()
