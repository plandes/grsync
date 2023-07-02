#!/usr/bin/env python

"""An example that lists all dirty (containing un-tracked or modified files)
repositories.

"""
__author__ = 'Paul Landes'

from typing import Iterable
from zensols.cli import CliHarness
from zensols.grsync import (
    RepoSpec, Discoverer, DistManager, ApplicationFactory, InfoApplication
)


def main():
    harness: CliHarness = ApplicationFactory.create_harness()
    app: InfoApplication = harness.get_instance('repos')
    dist_manager: DistManager = app.dist_mng
    disc: Discoverer = dist_manager.discoverer
    repo_specs: Iterable[RepoSpec] = disc.discover(False)['repo_specs']
    for spec in filter(lambda rs: rs.repo.is_dirty(), repo_specs):
        print(spec.path)


if __name__ == '__main__':
    main()
