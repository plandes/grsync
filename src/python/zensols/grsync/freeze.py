import os
import stat
import socket
import logging
import json
import zipfile
from pathlib import Path
from datetime import datetime
from zensols.persist import persisted
from zensols.grsync import (
    RepoSpec,
    SymbolicLink,
    BootstrapGenerator,
    PathTranslator,
    AppConfig,
)

logger = logging.getLogger(__name__)


class Discoverer(object):
    CONF_TARG_KEY = 'discover.target.config'
    TARG_LINKS = 'discover.target.links'
    REPO_PREF = 'discover.repo.remote_pref'

    """Discover git repositories, links, files and directories to save to
    reconstitute a user home directory later.

    """
    def __init__(self, config: AppConfig, profiles: list,
                 path_translator: PathTranslator, repo_preference: str):
        self.config = config
        self.profiles_override = profiles
        self.path_translator = path_translator
        self._repo_preference = repo_preference

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

    def _discover_repo_specs(self, paths, links):
        """Return a list of RepoSpec objects.

        :param paths: a list of paths each of which start a new RepoSpec
        :param links: a list of symlinks to check if they point to the
        repository, and if so, add them to the RepoSpec

        """
        repo_specs = []
        logger.debug(f'repo spec paths: {paths}')
        for path in paths:
            logger.debug(f'found repo at path {path}')
            repo_spec = RepoSpec(path, self.path_translator)
            repo_spec.add_linked(links)
            if len(repo_spec.remotes) == 0:
                logger.warning(f'repo {repo_spec} has no remotes--skipping...')
            else:
                repo_specs.append(repo_spec)
        return repo_specs

    @property
    @persisted('_profiles')
    def profiles(self):
        if self.config is None:
            raise ValueError('no configuration given; use the --help option')
        return self.config.get_profiles(self.profiles_override)

    def get_discoverable_objects(self):
        """Find git repos, files, sym links and directories to reconstitute
        later.

        """
        paths = []
        logger.info(f'finding objects to perist for {self.config}')
        for fname in self.config.get_discoverable_objects(self.profiles):
            path = Path(fname).expanduser().absolute()
            logger.debug(f'file pattern {fname} -> {path}')
            bname = path.name
            dname = path.parent.expanduser()
            files = list(dname.glob(bname))
            logger.debug(f'expanding {path} -> {dname} / {bname}: {files}')
            paths.extend(files)
        return paths

    def _create_file(self, src, dst=None, no_path_obj=False, robust=False):
        """Return a file object, which has the relative (rel) to home dir path,
        absolute path (abs) used later to zip the file, and mode (mode and
        modestr) information.

        """
        dst = src if dst is None else dst
        if src.exists():
            mode = src.stat().st_mode
            modestr = stat.filemode(mode)
            modify_time = os.path.getmtime(src)
            create_time = os.path.getctime(src)
        elif not robust:
            raise OSError(f'no such file: {src}')
        else:
            logger.warning(f'missing file: {src}--robustly skipping')
            mode, modestr, create_time, modify_time = None, None, None, None
        # the mode string is used as documentation and currently there is no
        # way to convert from a mode string to an octal mode, which would be
        # nice to allow modification of the dist.json file.
        fobj = {'modestr': modestr,
                'mode': mode,
                'create_time': create_time,
                'modify_time': modify_time}
        if no_path_obj:
            fobj['rel'] = str(self.path_translator.relative_to(dst))
        else:
            fobj['abs'] = src
            fobj['rel'] = self.path_translator.relative_to(dst)
        return fobj

    def discover(self, flatten):
        """Main worker method to capture all the user home information (git repos,
        files, sym links and empty directories per the configuration file).

        :param flatten: if ``True`` then return a data structure appropriate
                        for pretty printing; this will omit data needed to
                        create the distrubtion so it shouldn't be used for the
                        freeze task

        """
        files = []
        dirs = []
        empty_dirs = []
        pattern_links = []
        path_trans = self.path_translator

        # find all things to persist (repos, symlinks, files, etc)
        dobjs = self.get_discoverable_objects()
        # all directories are either repositories or base directories to
        # persist files in the distribution file
        dirs_or_gits = tuple(
            filter(lambda x: x.is_dir() and not x.is_symlink(), dobjs))
        # find the directories that have git repos in them (recursively)
        git_paths = self._get_repo_paths(dirs_or_gits)
        # create symbolic link objects from those objects that are links
        links = tuple(map(lambda l: SymbolicLink(l, self.path_translator),
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

        # find files that don't belong to git repos
        for path in filter(lambda x: x not in repo_paths, dirs_or_gits):
            logger.debug('dir {}'.format(path))
            dirs.append({'abs': path, 'rel': path_trans.relative_to(path)})
            gather(path)

        # configurated empty directories are added only if they exist so we can
        # recreate with the correct mode
        for ed in self.config.get_empty_dirs(self.profiles):
            logger.debug('empty dir: {}'.format(str(ed)))
            empty_dirs.append(self._create_file(
                ed, no_path_obj=True, robust=True))

        # pattern symlinks are special links that can change name based on
        # variables like the platform name so each link points to a
        # configuration file for that platform.
        dec_links = self.config.get_option(self.TARG_LINKS)
        if dec_links is not None:
            for link in map(lambda x: x['link'],
                            filter(lambda x: 'link' in x, dec_links)):
                src = Path(link['source']).expanduser().absolute()
                targ = Path(link['target']).expanduser().absolute()
                pattern_links.append(
                    {'source': str(path_trans.relative_to(src)),
                     'target': str(path_trans.relative_to(targ))})

        # create data structures for symbolic link integrity
        files_by_name = {f['abs']: f for f in files}
        for f in files:
            if f['abs'].is_file():
                dname = f['abs'].parent
                files_by_name[dname] = dname
            if flatten:
                del f['abs']
                f['rel'] = str(f['rel'])

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
                    logger.warning(f'hanging link with no target: {link}--' +
                                   'proceeding anyway')

        return {'repo_specs': repo_specs,
                'empty_dirs': empty_dirs,
                'files': files,
                'links': pattern_links}

    @property
    def repo_preference(self):
        """Return the preference for which repo to make primary on thaw
        """
        return self._repo_preference or self.config.get_option(self.REPO_PREF)

    def freeze(self, flatten=False):
        """Main entry point method that creates an object graph of all the data that
        needs to be saved (freeze) in the user home directory to reconstitute
        later (thaw).

        :param flatten: if ``True`` then return a data structure appropriate
                        for pretty printing; this will omit data needed to
                        create the distrubtion so it shouldn't be used for the
                        freeze task

        """
        disc = self.discover(flatten)
        repo_specs = tuple(x.freeze() for x in disc['repo_specs'])
        files = disc['files']
        logger.info('freezing with git repository preference: ' +
                    self.repo_preference)
        disc.update({'repo_specs': repo_specs,
                     'repo_pref': self.repo_preference,
                     'files': files,
                     'source': socket.gethostname(),
                     'create_date': datetime.now().isoformat(
                         timespec='minutes')})
        return disc


class FreezeManager(object):
    def __init__(self, config, dist_file, defs_file, discoverer, app_version):
        self.config = config
        self.dist_file = dist_file
        self.defs_file = defs_file
        self.discoverer = discoverer
        self.app_version = app_version

    def _create_wheels(self, wheel_dependency):
        """Create wheel dependencies on this software so the host doesn't need Internet
        connectivity.  Currently the YAML dependency breaks this since only
        binary per host wheels are available for download and the wrong was is
        given of spanning platforms (i.e. OSX to Linux).

        """
        wheel_dir_name = self.config.wheel_dir_name
        wheel_dir = Path(self.dist_dir, wheel_dir_name)
        logger.info(f'creating wheels from dependency {wheel_dependency} in {wheel_dir}')
        if not wheel_dir.exists():
            wheel_dir.mkdir(parents=True, exist_ok=True)
        from pip._internal import main
        pip_cmd = f'wheel --wheel-dir={wheel_dir} --no-cache-dir {wheel_dependency}'
        logger.debug('pip cmd: {}'.format(pip_cmd))
        main(pip_cmd.split())

    def _freeze_dist(self):
        """Freeze the distribution (see the class documentation).

        """
        dist_dir = self.dist_file.parent
        if not dist_dir.exists():
            dist_dir.mkdir(parents=True, exist_ok=True)
        data = self.discoverer.freeze()
        data['app_version'] = self.app_version
        with zipfile.ZipFile(self.dist_file, mode='w') as zf:
            for finfo in data['files']:
                fabs = finfo['abs']
                frel = str(Path(finfo['rel']))
                logger.debug(f'adding file: {fabs}')
                zf.write(fabs, arcname=frel)
                del finfo['abs']
                finfo['rel'] = frel
            logger.info(f'writing distribution defs to {self.defs_file}')
            zf.writestr(self.defs_file, json.dumps(data, indent=2))
        logger.info(f'created frozen distribution in {self.dist_file}')

    def freeze(self, wheel_dependency=None):
        """Freeze the distribution by saving creating a script to thaw along with all
        artifacts (i.e. repo definitions) in a zip file.

        """
        self._freeze_dist()
        script_file = self.config.bootstrap_script_file
        bg = BootstrapGenerator(self.config)
        bg.generate(script_file)
        script_file.chmod(0o755)
        # wheel creation last since pip clobers/reconfigures logging
        create_wheel = self.config.get_option('discover.wheel.create')
        if create_wheel and wheel_dependency is not None:
            self._create_wheels(wheel_dependency)
