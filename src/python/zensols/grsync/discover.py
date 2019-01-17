import os
import stat
import socket
import logging
from pathlib import Path
from datetime import datetime
from zensols.grsync import RepoSpec, SymbolicLink

logger = logging.getLogger(__name__)


class Discoverer(object):
    CONF_TARG_KEY = 'discover.target.config'
    TARG_LINKS = 'discover.target.links'
    REPO_PREF = 'discover.repo.remote_pref'

    """Discover git repositories, links, files and directories to save to
    reconstitute a user home directory later.

    """
    def __init__(self, config):
        self.config = config

    def _get_repo_paths(self, paths):
        """Recusively find git repository root directories."""
        git_paths = []
        logger.debug('repo root search paths {}'.format(paths))
        for path in paths:
            logger.debug('searching git paths in {}'.format(path.resolve()))
            for root, dirs, files in os.walk(path.resolve()):
                rootpath = Path(root)
                if rootpath.name == '.git':
                    git_paths.append(rootpath.parent)
        return git_paths

    def _relative_to_home(self, path):
        """Return a path that's relative to the user home."""
        return path.relative_to(Path.home().resolve())

    def _discover_repo_specs(self, paths, links):
        """Return a list of RepoSpec objects.

        :param paths: a list of paths each of which start a new RepoSpec
        :param links: a list of symlinks to check if they point to the
        repository, and if so, add them to the RepoSpec

        """
        repo_specs = []
        logger.debug('repo spec paths: {}'.format(paths))
        for path in paths:
            logger.debug('found repo at path {}'.format(path))
            repo_spec = RepoSpec(path)
            repo_spec.add_linked(links)
            if len(repo_spec.remotes) == 0:
                logger.warning('repo at {} has no remotes--skipping...'.
                               format(repo_spec))
            else:
                repo_specs.append(repo_spec)
        return repo_specs

    def get_discoverable_objects(self):
        """Find git repos, files, sym links and directories to reconstitute
        later.

        """
        paths = []
        logger.info('finding objects to capture...')
        for fname in self.config.discoverable_objects:
            logger.debug('file pattern {}'.format(fname))
            path = Path(fname)
            bname = path.name
            dname = path.parent.expanduser()
            files = list(dname.glob(bname))
            logger.debug('expanding {} -> {} / {}: {}'.
                         format(path, dname, bname, files))
            paths.extend(files)
        return paths

    def _create_file(self, src, dst=None, no_path_obj=False):
        """Return a file object, which has the relative (rel) to home dir path,
        absolute path (abs) used later to zip the file, and mode (mode and
        modestr) information.

        """
        dst = src if dst is None else dst
        mode = src.stat().st_mode
        # the mode string is used as documentation and currently there is no
        # way to convert from a mode string to an octal mode, which would be
        # nice to allow modification of the dist.json file.
        fobj = {'modestr': stat.filemode(mode),
                'mode': mode}
        if no_path_obj:
            fobj['rel'] = str(self._relative_to_home(dst))
        else:
            fobj['abs'] = src
            fobj['rel'] = self._relative_to_home(dst)
        return fobj

    def discover(self):
        """Main worker method to capture all the user home information (git repos,
        files, sym links and empty directories per the configuration file).

        """
        files = []
        dirs = []
        empty_dirs = []
        pattern_links = []

        # find all things to persist (repos, symlinks, files, etc)
        dobjs = self.get_discoverable_objects()
        # all directories are either repositories or base directories to
        # persist files in the distribution file
        dirs_or_gits = tuple(
            filter(lambda x: x.is_dir() and not x.is_symlink(), dobjs))
        # find the directories that have git repos in them (recursively)
        git_paths = self._get_repo_paths(dirs_or_gits)
        # create symbolic link objects from those objects that are links
        links = tuple(map(lambda l: SymbolicLink(l),
                          filter(lambda x: x.is_symlink(), dobjs)))
        #logger.debug(f'links: {links}')
        # normal files are kept track of so we can compress them later
        for f in filter(lambda x: x.is_file() and not x.is_symlink(), dobjs):
            files.append(self._create_file(f))
        # create RepoSpec objects that capture information about the git repo
        repo_specs = self._discover_repo_specs(git_paths, links)
        # these are the Path objects to where the repo lives on the local fs
        repo_paths = set(map(lambda x: x.path, repo_specs))
        # add the configuration used to freeze so the target can freeze again
        config_targ = self.config.get_option(self.CONF_TARG_KEY)
        if config_targ is not None:
            src = Path(self.config.config_file)
            dst = Path(config_targ).expanduser()
            files.append(self._create_file(dst, dst))
        logger.debug(f'files: {files}')

        # recusively find files that don't belong to git repos
        def gather(par):
            for c in par.iterdir():
                if c.is_dir() and c not in repo_paths:
                    gather(c)
                elif c.is_file():
                    files.append(self._create_file(c))

        #logger.debug(f'files: {files}')

        # find files that don't belong to git repos
        for path in filter(lambda x: x not in repo_paths, dirs_or_gits):
            logger.debug('dir {}'.format(path))
            dirs.append({'abs': path, 'rel': self._relative_to_home(path)})
            gather(path)

        # configurated empty directories are added only if they exist so we can
        # recreate with the correct mode
        for ed in self.config.empty_dirs:
            logger.debug('empty dir: {}'.format(str(ed)))
            empty_dirs.append(self._create_file(ed, no_path_obj=True))

        # pattern symlinks are special links that can change name based on
        # variables like the platform name so each link points to a
        # configuration file for that platform.
        dec_links = self.config.get_option(self.TARG_LINKS)
        if dec_links is not None:
            for link in map(lambda x: x['link'],
                            filter(lambda x: 'link' in x, dec_links)):
                src = Path(link['source']).expanduser()
                targ = Path(link['target']).expanduser()
                pattern_links.append(
                    {'source': str(self._relative_to_home(src)),
                     'target': str(self._relative_to_home(targ))})

        # create data structures for symbolic link integrity
        files_by_name = {f['abs']: f for f in files}
        for f in files:
            if f['abs'].is_file():
                dname = f['abs'].parent
                files_by_name[dname] = dname

        # unused links pointing to repositories won't get created, so those not
        # used by repos are added explicitly to pattern links
        for link in links:
            if link.use_count == 0:
                try:
                    pattern_links.append(
                        {'source': str(link.source_relative),
                         'target': str(link.target_relative)})
                except ValueError as e:
                    logger.error(f'couldn\'t create link: {link}')
                    raise e
                if link.target in files_by_name:
                    dst = files_by_name[link.target]
                    # follow links enhancement picks up here
                    logger.debug(f'source {link.source} -> {dst}')
                else:
                    logger.warning(f'found link with no persisted target: {link}')

        return {'repo_specs': repo_specs,
                'empty_dirs': empty_dirs,
                'files': files,
                'links': pattern_links}

    def freeze(self):
        """Main entry point method that creates an object graph of all the data that
        needs to be saved (freeze) in the user home directory to reconstitute
        later (thaw).

        """
        disc = self.discover()
        repo_specs = tuple(x.freeze() for x in disc['repo_specs'])
        files = disc['files']
        disc.update({'repo_specs': repo_specs,
                     'repo_pref': self.config.get_option(self.REPO_PREF),
                     'files': files,
                     'source': socket.gethostname(),
                     'create_date': datetime.now().isoformat(
                         timespec='minutes')})
        return disc
