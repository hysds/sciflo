#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        service.py
# Purpose:     Aeronet service functions.
#
# Author:      Zhangfan Xing
#
# Created:     Mon Aug 14 14:42:03 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, sys

from sciflo.utils import ScifloConfigParser
from sciflo.data.recognize import getSystemLevelUserDir
from sciflo.data.aeronet import uuid

def getPubDataDir():
    """Return tuple of (absolute path, url path) to public data directory."""
    
    configFile = os.path.join(getSystemLevelUserDir(), 'myconfig.xml')
    scp = ScifloConfigParser(configFile)
    param = scp.getParameter('htmlBaseHref')
    if param is None: raise RuntimeError("Parameter '%s' is undefined in %s." % \
        ('htmlBaseHref', configFile))
    return (os.path.join(sys.prefix, 'share', 'sciflo', 'data'),
            param.replace('/web/', '/data/'))

# 20071031, xing, the other approach using getPubDataDir is preferred now
## obtain path of workdir from config and create it if non-existent
#from sciflo.utils import ScifloConfigParser
#WORKDIR = ScifloConfigParser().getParameter("workUnitRootWorkDir")
#if WORKDIR != None:
#    if os.path.isdir(WORKDIR):
#        pass
#    elif os.path.isfile(WORKDIR):
#        raise OSError("%s exists as a file not a dir" % WORKDIR)
#    else:
#        os.mkdir(WORKDIR)

PUB_DATA_DIR, PUB_DATA_DIR_URL = getPubDataDir()
PUB_DATA_DIR += "/aeronet"
PUB_DATA_DIR_URL += "/aeronet"
if os.path.isdir(PUB_DATA_DIR):
    pass
elif os.path.isfile(PUB_DATA_DIR):
    raise OSError("%s exists as a file not a dir" % PUB_DATA_DIR)
else:
    os.mkdir(PUB_DATA_DIR)
    # hack to make it world read/writable. what is better way?
    os.chmod(PUB_DATA_DIR,0777)

# tag to make csv file name random
#RANDOM_TAG = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'sciflo'))
# uuid4() provides random uuid
# it gives problem when sciflo runs as daemon: fixed uuid for one instance!
#RANDOM_TAG = str(uuid.uuid4())
# uuid1() provides uuid based on host id and current time (in nanoseconds)
RANDOM_TAG = str(uuid.uuid1())

def writeAsXML(vars, rows):
    """Write data rows for one aeronet site as xml text.
       Should be consistent with mysql query in subset.py
    """
    xmlText = "    <dataSet>\n"
    for y in rows:
        xmlText += "      <data>\n"
        xmlText += "        <time>%s</time>\n" %(y[0])
        xmlText += "        <lon type='xs:float'>%s</lon>\n" %(y[1])
        xmlText += "        <lat type='xs:float'>%s</lat>\n" %(y[2])
        offset = 3
        for i in range(len(vars)):
            xmlText += "        <%s type='xs:float'>%s</%s>\n" %(vars[i],y[offset+i],vars[i])
        xmlText += "      </data>\n"
    xmlText += "    </dataSet>\n"
    return xmlText

def writeToFileAsCSV(vars, rows, path):
    """Write data rows for one aeronet site to a file in csv format.
       Should be consistent with mysql query in subset.py
    """

    f = open(path,'w+b') # file will be truncated
    f.write('time,lon,lat,'+','.join(vars)+'\n')
    for x in rows:
        f.write(','.join(map(str,x)) + "\n")
    f.close()
    # hack to make it world read/writable. what is better way?
    os.chmod(path,0666)
    return path
