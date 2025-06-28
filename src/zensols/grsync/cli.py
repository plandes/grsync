"""Command line entry point to the application.

"""
__author__ = 'Paul Landes'

from typing import List, Any, Dict, Type
import sys
from zensols.cli import ActionResult, CliHarness
from zensols.cli import ApplicationFactory as CliApplicationFactory
from . import DistManager, InfoApplication


class ApplicationFactory(CliApplicationFactory):
    def __init__(self, *args, **kwargs):
        kwargs['package_resource'] = 'zensols.grsync'
        super().__init__(*args, **kwargs)

    @classmethod
    def get_dist_manager(cls: Type) -> DistManager:
        """Return the distribution manager."""
        harness: CliHarness = ApplicationFactory.create_harness()
        app: InfoApplication = harness.get_instance('repos')
        return app.dist_mng


def main(args: List[str] = sys.argv, **kwargs: Dict[str, Any]) -> ActionResult:
    harness: CliHarness = ApplicationFactory.create_harness(relocate=False)
    harness.invoke(args, **kwargs)
