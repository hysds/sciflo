#!/bin/bash
source $HOME/sciflo/bin/activate
cd /tmp
TACFILE=`python -c "import os, pkg_resources; print pkg_resources.resource_filename('sciflo', os.path.join('..', 'tac', 'PersistentDictServer.tac'))"`
python /usr/bin/twistd --logfile=$SCIFLO_DIR/log/workUnitCache.log --pidfile=twistd_$USER.pid -y $TACFILE
