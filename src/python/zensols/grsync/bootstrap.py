import logging

logger = logging.getLogger(__name__)


class BootstrapGenerator(object):
    """
    Generate the script that creates the distribution on the target machine.

    """

    SCRIPT = """\
#!/bin/sh

if [ $# -eq 0 ] ; then
    echo "usage: $0 <python_dir> [grsync dir] [python<version>]"
    echo "where: python_dir is the bin directory where python is installed"
    echo "       grsync_dir is the distribution directory copied from the source"
    echo "       python<version> is the version of python (i.e. python3.6)"
    exit 1
fi
NATIVE_PYTHON_BIN_DIR=$1

if [ $# -ge 2 ]; then
    echo "setting inst dir: $2"
    GRSYNC_INST_DIR=$2
else
    GRSYNC_INST_DIR=`pwd`
fi

if [ $# -ge 3 ]; then
    echo "setting python ver: $3"
    PYTHON_VER=$3
else
    PYTHON_VER=$NATIVE_PYTHON_BIN_DIR
fi

PYTHON_DIR=${HOME}/opt/lib/python3
PIP=${PYTHON_DIR}/bin/pip
VIRTUAL_ENV=${NATIVE_PYTHON_BIN_DIR}/virtualenv
PYTHON_PAR=`dirname $PYTHON_DIR`
WHEELS_DIR=${GRSYNC_INST_DIR}/%(wheel_dir)s
WHEELS=${WHEELS_DIR}/*.whl

if [ -f ${PIP} ] ; then
    PIP=${PYTHON_DIR}/bin/pip3
fi

echo "GRSYNC_INST_DIR=${GRSYNC_INST_DIR}"
echo "PYTHON_DIR=${PYTHON_DIR}"
echo "PYTHON_VER=${PYTHON_VER}"
echo "PIP=${PIP}"
echo "VIRTUAL_ENV=${VIRTUAL_ENV}"
echo "PYTHON_PAR=${PYTHON_PAR}"
echo "WHEELS_DIR=${WHEELS_DIR}"
echo "WHEELS=${WHEELS}"

if [ ! -e "${VIRTUAL_ENV}" ] ; then
    echo "virtual environment not installed: 'pip3 install virtualenv'"
    exit 1
fi

echo "bootstrapping python env in ${PYTHON_DIR}, wheels: ${WHEELS}"

rm -rf $PYTHON_PAR

cmd="${VIRTUAL_ENV} -p ${PYTHON_VER} `basename ${PYTHON_DIR}`"

echo "invoke $cmd"
mkdir -p $PYTHON_PAR && \
    cd $PYTHON_PAR && \
    $cmd && \
    cd - || exit 1

if [ -d ${WHEELS_DIR} ] ; then
    echo "installing from wheel"
    ${PIP} install ${GRSYNC_INST_DIR}/%(wheel_dir)s/zensols.grsync*
else
    echo "installing from net"
    ${PIP} install zensols.grsync
fi

# ${PIP} install ${WHEELS}

rm ${HOME}/.bash* ${HOME}/.profile*
# echo to thaw the repo: ${PYTHON_DIR}/bin/grsync thaw -d ${GRSYNC_INST_DIR}
${PYTHON_DIR}/bin/grsync thaw -d ${GRSYNC_INST_DIR}
"""
    PARAM_PATH = 'discover.bootstrap'

    def __init__(self, config):
        self.config = config

    def generate(self, path):
        params = self.config.get_options(self.PARAM_PATH)
        script = self.SCRIPT % params
        logger.info('creating bootstrap script at: {}'.format(path))
        with open(path, 'w') as f:
            f.write(script)
