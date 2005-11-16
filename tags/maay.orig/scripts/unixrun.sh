#!/bin/sh

set -x

#
# launch maay on unix systems
#

if [ -z "$MAAYHOME" ]; then
        echo "requires \$MAAYHOME to point to the maay source root" >& 2
        exit 1
fi

cd "$MAAYHOME"
mkdir -p testenv
python setup.py install_data -d testenv

cd testenv
PYTHONPATH="../src"
export PYTHONPATH
python "$MAAYHOME/scripts/linuxinstall.py" install_db
python "$MAAYHOME/src/maay/maaymain.py"
