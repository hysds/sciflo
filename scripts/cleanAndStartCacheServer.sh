#!/bin/bash
cd /tmp
TACFILE=`python -c "import os, pkg_resources; print pkg_resources.resource_filename('sciflo', os.path.join('..', 'tac', 'PersistentDictServer.tac'))"`
CACHEHOME=`$SCIFLO_DIR/bin/getConfigVal.py cacheHome`
rm -rf $CACHEHOME
twistd --logfile=$SCIFLO_DIR/log/workUnitCache.log --pidfile=twistd_$USER.pid -y $TACFILE
