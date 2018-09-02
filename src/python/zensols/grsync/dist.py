import os
import logging
import json
import zipfile
import shutil
import platform
from git.exc import GitCommandError
import pprint
from pathlib import Path
from zensols.actioncli import YamlConfig
from zensols.grsync import Discoverer, RepoSpec, BootstrapGenerator

logger = logging.getLogger('zensols.grsync.dist')


class DistManager(object):
    """The main entry point that supports saving user home directory information
    (freezing) so that the data can later be restored (thawed).  It does this
    by finding git repositories and saving the remotes.  It also finds symbolic
    links, files and empty directories specified in the configuration.

    """
    def __init__(self, config: YamlConfig=None, dist_dir: Path=None,
                 target_dir=None, only_repo_names=None,
                 wheel_dependency='zensols.grsync'):
        self.config = config
        # config will be missing on thaw
        if config is None:
            if dist_dir is None:
                raise ValueError('missing dist file option')
            self.dist_dir = Path(dist_dir)
        else:
            if dist_dir is not None:
                self.config.dist_dir = dist_dir
            self.dist_dir = self.config.dist_dir
        if target_dir is not None:
            self.target_dir = Path(target_dir)
        else:
            self.target_dir = Path.home()
        self.only_repo_names = only_repo_names
        self.wheel_dependency = wheel_dependency
        self.file_install_path = 'to_install'
        self.config_dir = 'conf'
        self.defs_file = '{}/dist.json'.format(self.config_dir)
        self.dir_create_mode = 0o755
        self.exec_file_create_mode = 0o755

    @property
    def dist_file(self):
        """Return the main distribution compressed file that will have the
        configuration needed to thaw, all saved files and symbolic links.

        """
        return Path(self.dist_dir, 'dist.zip')

    def _create_wheels(self):
        """Create wheel dependencies on this software so the host doesn't need Internet
        connectivity.  Currently the YAML dependency breaks this since only
        binary per host wheels are available for download and the wrong was is
        given of spanning platforms (i.e. OSX to Linux).

        """
        wheel_dir_name = self.config.wheel_dir_name
        wheel_dir = Path(self.dist_dir, wheel_dir_name)
        logger.info('creating wheels from dependency {} in {}'.format(
            self.wheel_dependency, wheel_dir))
        if not wheel_dir.exists():
            wheel_dir.mkdir(
                self.dir_create_mode, parents=True, exist_ok=True)
        from pip._internal import main
        pip_cmd = 'wheel --wheel-dir={} --no-cache-dir {}'.format(
            wheel_dir, self.wheel_dependency)
        logger.debug('pip cmd: {}'.format(pip_cmd))
        main(pip_cmd.split())

    def _freeze_dist(self):
        """Freeze the distribution (see the class documentation).

        """
        dist_file = self.dist_file
        if not self.dist_dir.exists():
            self.dist_dir.mkdir(
                self.dir_create_mode, parents=True, exist_ok=True)
        logger.info('freezing distribution in {}'.format(dist_file))
        disc = Discoverer(self.config)
        data = disc.freeze()
        with zipfile.ZipFile(dist_file, mode='w') as zf:
            for finfo in data['files']:
                fabs = finfo['abs']
                frel = str(Path(self.file_install_path, finfo['rel']))
                logger.debug('adding file: {}'.format(fabs))
                zf.write(fabs, arcname=frel)
                del finfo['abs']
                finfo['rel'] = frel
            logger.info('writing distribution defs to {}'.
                        format(self.defs_file))
            zf.writestr(self.defs_file, json.dumps(data, indent=2))

    def discover_info(self):
        """Proviate information about what's found in the user home directory.  This is
        later used to freeze the data.

        """
        disc = Discoverer(self.config)
        data = disc.freeze()
        pprint.PrettyPrinter().pprint(data)

    def freeze(self):
        """Freeze the distribution by saving creating a script to thaw along with all
        artifacts (i.e. repo definitions) in a zip file.

        """
        self._freeze_dist()
        script_file = self.config.bootstrap_script_file
        bg = BootstrapGenerator(self.config)
        bg.generate(script_file)
        script_file.chmod(self.exec_file_create_mode)
        # wheel creation last since pip clobers/reconfigures logging
        create_wheel = self.config.get_option('discover.wheel.create')
        if create_wheel:
            self._create_wheels()

    def _target_relative(self, path):
        """Return a path that is relative to where we're thawing the distribution,
        which is usually the user's home directory.

        """
        return Path.joinpath(self.target_dir, path)

    def _thaw_remote_specs(self, rdef):
        """Thaw a RepoSpec object, which does a clone and then creates the (remaining
        if any) remotes.

        """
        repo_path = self._target_relative(rdef['path'])
        parent = repo_path.parent
        if not parent.exists():
            logger.info('creating parent directory: {}'.format(parent))
            parent.mkdir(self.dir_create_mode, parents=True, exist_ok=True)
        try:
            return RepoSpec.thaw(rdef, self.target_dir, repo_path)
        except GitCommandError as err:
            logger.warning('couldn\'t create repo {}--skippping: {}'.
                           format(repo_path, err))

    def _thaw_repos(self, struct):
        """Thaw all repo specs defined in ``struct``."""
        rdefs = []
        for rdef in struct['repo_specs']:
            name = rdef['name']
            if self.only_repo_names is None or name in self.only_repo_names:
                rdefs.append(rdef)
        for rdef in rdefs:
            self._thaw_remote_specs(rdef)

    def _thaw_files(self, struct, zf):
        """Thaw files in the distribution by extracting from the zip file ``zf``.  File
        definitions are found in ``struct``.

        """
        for finfo in struct['files']:
            mode = finfo['mode']
            rel = Path(finfo['rel'])
            path = self._target_relative(Path(os.path.join(*rel.parts[1:])))
            parent = path.parent
            if not parent.exists():
                logger.info('creating parent directory: {}'.format(parent))
                parent.mkdir(mode=self.dir_create_mode,
                             parents=True, exist_ok=True)
            logger.debug('thawing file: {}'.format(path))
            if path.exists():
                logger.warning('path already exists: {}--skipping file'.
                               format(path))
            else:
                with zf.open(str(rel)) as fin:
                    with open(str(path), 'wb') as fout:
                        shutil.copyfileobj(fin, fout)
                logger.debug('setting mode of {} to {} ({})'.
                             format(path, mode, finfo['modestr']))
                path.chmod(mode)

    def _thaw_empty_dirs(self, struct):
        """Create empty directories on the file system.
        """

        for finfo in struct['empty_dirs']:
            rel = Path(finfo['rel'])
            path = self._target_relative(rel)
            if path.exists():
                logger.warning('path already exists: {}--skipping directory'.
                               format(path))
            else:
                logger.info('creating path {}'.format(path))
                # we store the mode of the directory, but we don't want that to
                # apply to all children dirs that might not exist yet
                path.mkdir(mode=self.dir_create_mode,
                           parents=True, exist_ok=True)

    def _thaw_pattern_links(self, struct):
        """Method to call other thaw methods based on type.

        """
        params = {'os': platform.system().lower()}
        for link in struct['pattern_links']:
            src = link['source'].format(**params)
            src = self._target_relative(src)
            targ = link['target'].format(**params)
            targ = self._target_relative(targ)
            logger.info('link: {} -> {}'.format(src, targ))
            if src.exists():
                logger.warning(
                    'link source already exists: {}--skipping'.format(src))
            elif not targ.exists():
                logger.warning(
                    'link target does not exist: {}--skipping'.format(targ))
            else:
                src.symlink_to(targ)

    def thaw(self):
        """Thaw the distribution, which includes creating git repositories, extracting
        (frozen) files, creating symbolic links, and creating empty directories
        that were captured/configured during the freezing phase.

        """
        dist_file = self.dist_file
        logger.info('expanding distribution in {}'.format(dist_file))
        with zipfile.ZipFile(str(dist_file.resolve())) as zf:
            with zf.open(self.defs_file) as f:
                jstr = f.read().decode('utf-8')
                struct = json.loads(jstr)
            self._thaw_files(struct, zf)
            self._thaw_repos(struct)
            self._thaw_empty_dirs(struct)
            self._thaw_pattern_links(struct)
