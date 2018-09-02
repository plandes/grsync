from pathlib import Path
from zensols.pybuild import SetupUtil

SetupUtil(
    setup_path=Path(__file__).parent.absolute(),
    name="zensols.grsync",
    package_names=['zensols', 'zensols.grsync'],
    description='Synchronize and manage multiple GitHub repositories',
    user='plandes',
    project='grsync',
    keywords=['tooling', 'configuration'],
).setup()
