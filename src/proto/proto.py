import logging
from pathlib import Path
from zensols.actioncli import ClassImporter
from zensols.grsync import AppConfig

logger = logging.getLogger(__name__)


def create_config():
    f = Path('test-resources/fs-test.yml').expanduser()
    #f = os.getenv('GRSYNCRC')
    return AppConfig(f)


def tmp():
    dm = ClassImporter('zensols.grsync.distmng.DistManager').instance(
        create_config(), dist_dir='target/dist', target_dir='target/mock')
    logging.getLogger('zensols.grsync.dist').setLevel(logging.INFO)
    dm.tmp()


def main():
    logging.basicConfig(level=logging.WARNING)
    run = 1
    {1: tmp,
     }[run]()


main()
