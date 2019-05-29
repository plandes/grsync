import logging
import os
from zensols.actioncli import ClassImporter
from zensols.grsync import AppConfig

logger = logging.getLogger(__name__)


def create_config():
    return AppConfig(os.getenv('GRSYNCRC'))


def tmp():
    dm = ClassImporter('zensols.grsync.dist.DistManager').instance(create_config())
    dm.tmp()


def main():
    logging.basicConfig(level=logging.WARNING)
    run = 1
    {1: tmp,
     }[run]()


main()
