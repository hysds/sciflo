#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        crawlAll.py
# Purpose:     Crawl and catalog using crawler config in crawler directory.
#
# Author:      Gerald Manipon
#
# Created:     Wed Nov 29 18:42:34 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, sys, glob, tempfile, traceback
from datetime import datetime as DT

from sciflo.catalog import *
from sciflo.utils import *

#check if currently running; if not, lock; otherwise exit immediately
lockFile = os.path.join(tempfile.gettempdir(),
                        'crawler.%s.lck' % getpass.getuser())
if os.path.exists(lockFile):
    lockingPid = open(lockFile, 'r').read()
    if os.path.isdir(os.path.join('/proc', lockingPid)) and lockingPid != '':
        print(("%s: Process %s already running." % \
            (DT.utcfromtimestamp(time.time()).isoformat(), lockingPid)))
        sys.exit(0)
    else:
        print(("%s: Zombie process?  Removed lock with pid %s." % \
            (DT.utcfromtimestamp(time.time()).isoformat(), lockingPid)))
        os.unlink(lockFile)

#create lock file
currentPid = str(os.getpid())
f = open(lockFile, 'w')
f.write(currentPid)
f.close()

#get vars
scp = ScifloConfigParser()
dbPort = scp.getParameter('dbPort')
dbUser = scp.getParameter('dbUser')
dbPassword = scp.getParameter('dbPassword')
if dbUser in [None, 'None', '']:
    schema='mysql://127.0.0.1:%s/urlCatalog' % dbPort
else:
    if dbPassword in [None, 'None', '']:
        schema='mysql://%s@127.0.0.1:%s/urlCatalog' % (dbUser, dbPort)
    else:
        schema='mysql://%s:%s@127.0.0.1:%s/urlCatalog' % (dbUser, dbPassword, dbPort)
crawlerConfigDir = os.path.join(sys.prefix, 'etc', 'crawler')

if len(sys.argv) == 1:
    xmlConfigFiles = glob.glob(os.path.join(crawlerConfigDir, '*.xml'))
else: xmlConfigFiles = sys.argv[1:]

for xmlConfigFile in xmlConfigFiles:
    try:
        print(("Doing", xmlConfigFile))
        libobj=ScifloLibrarian(xmlConfigFile)
        instr=libobj.getInstrument()
        level=libobj.getLevel()
        catalogobj=SqlAlchemyCatalog(schema)
        libobj.setCatalog(catalogobj)
        retval=libobj.crawlAndCatalog(page=True)
        print(("Finished crawlAndCatalog() with: ",retval))
    except:
        traceback.print_exc()
        raise SystemExit(1)

#remove lock file
os.unlink(lockFile)
print(("%s: Script finished.  Removed lock with pid %s." % \
    (DT.utcfromtimestamp(time.time()).isoformat(), currentPid)))
