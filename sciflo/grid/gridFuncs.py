#-----------------------------------------------------------------------------
# Name:        gridFuncs.py
# Purpose:     Various helper/wrapper grid functions.
#
# Author:      Gerald Manipon
#
# Created:     Wed Jul 26 14:32:23 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
from .utils import *
from .manager import (addAndExecuteWorkUnit, cancelWorkUnit, queryWorkUnit,
workUnitCallback, nonforkingAddAndExecuteWorkUnit)
import sys

def addWorkUnit(addMethod, owner, type, call, args, stageFiles=None, postExecutionTypeList=None,
                timeout=86400, callbackConfig=None, configFile=None, publicizeWorkFlag=True,
                localExecutionMode=False, debugMode=False, verbose=False, noLookCache=False):
    """Help function for local use.  Pickles the args (argumentList) and call
    the addAndExecuteWorkUnit() soap/local method passed in."""

    #pickle argsList
    pickledArgs = pickleArgsList(args)

    #pickle postExecutionTypeList
    pickledPostExecList = pickleThis(postExecutionTypeList)
    #call soap service to insert work unit and return wuid
    return addMethod(owner, type, call, pickledArgs, stageFiles, pickledPostExecList, timeout,
                     callbackConfig, configFile, publicizeWorkFlag, localExecutionMode, debugMode,
                     verbose, noLookCache)

def getGridSoapMethods(protocol, addr, port, ns, configFile=None):
    """Create the appropriate soap proxy and return the addAndExecuteWorkUnit,
    cancelWorkUnit, and queryWorkUnit methods."""

    #create proxy
    #if protocol == 'gsi':
    #    proxy=getGSISOAPProxy("https://%s:%s" % (addr, port), ns)

    if protocol == 'ssl': proxy = SOAPProxy("https://%s:%s" % (addr, port), ns)
    elif protocol == 'http': proxy = SOAPProxy("http://%s:%s" % (addr, port), ns)
    else: raise RuntimeError("Failed to recognize protocol type: %s" % protocol)

    #get add, cancel and query workunit methodnames from configuration file
    parserObj = ScifloConfigParser(configFile)
    addStr = parserObj.getMandatoryParameterViaXPath(
        './/{%s}addWorkUnitMethod/{%s}exposedName' % (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
    queryStr = parserObj.getMandatoryParameterViaXPath(
        './/{%s}queryWorkUnitMethod/{%s}exposedName' % (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
    cancelStr = parserObj.getMandatoryParameterViaXPath(
        './/{%s}cancelWorkUnitMethod/{%s}exposedName' % (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))

    #add work unit method
    addWorkUnitMethod = eval("proxy.%s" % addStr)

    #cancel work unit method
    cancelWorkUnitMethod = eval("proxy.%s" % cancelStr)

    #wrapped query work unit method
    queryWorkUnitMethod = eval("proxy.%s" % queryStr)

    def queryMethod(*args, **kargs):
        pickleStr = queryWorkUnitMethod(*args, **kargs)
        return unpickleThis(pickleStr)

    #return
    return (addWorkUnitMethod, cancelWorkUnitMethod, queryMethod)

def getGridSoapMethodsFromConfig(configFile=None):
    """Create the appropriate soap proxy and return the addAndExecuteWorkUnit,
    cancelWorkUnit, and queryWorkUnit methods."""

    #get protocol, port, and namespace from configuration file
    parserObj = ScifloConfigParser(configFile)
    protocol = parserObj.getMandatoryParameter('gridProtocol')
    port = parserObj.getMandatoryParameter('gridPort')
    ns = parserObj.getMandatoryParameter('gridNamespace')

    #get addr
    addr = getfqdn()

    #return
    return getGridSoapMethods(protocol, addr, port, ns, configFile)

def getGridLocalMethods(configFile, debug=False):
    """Return pointers to the addAndExecuteWorkUnit, cancelWorkUnit, and queryWorkUnit
    grid methods for this node."""

    #add work unit method
    if debug: addWorkUnitMethod = GridFunction(nonforkingAddAndExecuteWorkUnit,configFile)
    else: addWorkUnitMethod = GridFunction(addAndExecuteWorkUnit,configFile)

    #cancel work unit method
    cancelWorkUnitMethod = GridFunction(cancelWorkUnit,configFile)

    #wrapped query work unit method
    queryWorkUnitMethod = GridFunction(queryWorkUnit,configFile)

    def queryMethod(*args, **kargs):
        pickleStr = queryWorkUnitMethod(*args, **kargs)
        return unpickleThis(pickleStr)

    #return
    return (addWorkUnitMethod, cancelWorkUnitMethod, queryMethod)

class GridFunction(object):
    """Base class for grid functions."""

    def __init__(self, func, configFile=None):
        """Constructor."""

        self._configFile = configFile
        self._func = func
        
    def __call__(self, *args, **kargs):
        return self._func(*args, **kargs)

class WorkUnitCallback(GridFunction):
    def __init__(self, configFile=None):
        super(WorkUnitCallback,self).__init__(workUnitCallback, configFile)
