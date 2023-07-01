from pathlib import Path
from zensols.pybuild import SetupUtil

su = SetupUtil(
    setup_path=Path(__file__).parent.absolute(),
    name="zensols.grsync",
    package_names=['zensols', 'resources'],
    package_data={'': ['*.conf', '*.json', '*.yml']},
    description='Synchronize and manage multiple GitHub repositories',
    user='plandes',
    project='grsync',
    keywords=['tooling', 'configuration'],
).setup()
