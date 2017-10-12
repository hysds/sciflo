import os

from sciflo.grid.soapFuncs import (submitSciflo_server, submitSciflo_server_nocache,
cancelSciflo_server)

#get dir
dirName = os.path.abspath(os.path.dirname(__file__))

#get config file here
configFile = os.path.join(dirName,'config.xml')

def submit(*args, **kargs):
    """Submit sciflo."""

    kargs['configFile'] = configFile
    return submitSciflo_server(*args, **kargs)

def submit_nocache(*args, **kargs):
    """Submit sciflo not looking at cache."""

    kargs['configFile'] = configFile
    return submitSciflo_server_nocache(*args, **kargs)

def cancel(*args, **kargs):
    """Cancel sciflo"""

    kargs['configFile'] = configFile
    return cancelSciflo_server(*args, **kargs)
