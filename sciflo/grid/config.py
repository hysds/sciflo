#-----------------------------------------------------------------------------
# Name:        config.py
# Purpose:     Grid configuration.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jul 21 11:03:23 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
from socket import getfqdn

from sciflo.utils import ScifloConfigParser, validateDirectory, SCIFLO_NAMESPACE
from sciflo.db import StoreConfig, StoreTypeMapping
from storeHandler import workUnitStoreFieldsList, scheduleStoreFieldsList

def getStoreConfigFromConfiguration(file=None):
    """Return the StoreConfig object as defined by the parameters in the
    sciflo configuration xml file.
    """

    #get config parser
    configParser = ScifloConfigParser(file)

    #get work unit store type
    workUnitStoreType = configParser.getMandatoryParameter('workUnitStoreType')

    #print "workUnitStoreType:",workUnitStoreType

    #get params based on store type
    if workUnitStoreType in StoreTypeMapping:

        #get home and, if bsddb, validate that it is a directory
        workUnitStoreHome = configParser.getMandatoryParameter('workUnitStoreHome')
        if workUnitStoreType == 'bsddb' and not validateDirectory(workUnitStoreHome):
            raise RuntimeError, "Couldn't access/create bsddb home %s." % workUnitStoreHome

        #get filename for bsddb and validate
        workUnitStoreDb = configParser.getMandatoryParameter('workUnitStoreDb')

        #get name
        workUnitStoreName = configParser.getMandatoryParameter('workUnitStoreName')

        #store config for work unit store
        workUnitStoreConfig = StoreConfig(workUnitStoreType, workUnitStoreName, workUnitStoreFieldsList,
                                          workUnitStoreHome, workUnitStoreDb)

        return workUnitStoreConfig
    else:
        raise RuntimeError, "Unknown workUnitStoreType %s in configuration." % workUnitStoreType

def getRootWorkDirFromConfiguration(file=None):
    """Return the dir path for workUnit's work directory."""

    #get config parser
    configParser = ScifloConfigParser(file)

    #root directory for work dirs
    workUnitRootWorkDir = configParser.getMandatoryParameter('workUnitRootWorkDir')

    #print "##########################################validating:", workUnitRootWorkDir

    #validate
    if not validateDirectory(workUnitRootWorkDir):
        raise RuntimeError, "Couldn't access/create workUnitRootWorkDir %s." % workUnitRootWorkDir

    return workUnitRootWorkDir

def getScheduleConfigFromConfiguration(file=None):
    """Return the ScheduleConfig object as defined by the sciflo configuration
    xml file.
    """

    #get config parser
    configParser = ScifloConfigParser(file)

    #get schedule store type
    scheduleStoreType = configParser.getMandatoryParameter('scheduleStoreType')

    #print "scheduleStoreType:",scheduleStoreType

    #get params based on store type
    if scheduleStoreType in StoreTypeMapping:

        #get home and, if bsddb, validate that it is a directory
        scheduleStoreHome = configParser.getMandatoryParameter('scheduleStoreHome')
        if scheduleStoreType == 'bsddb' and not validateDirectory(scheduleStoreHome):
            raise RuntimeError, "Couldn't access/create bsddb home %s." % scheduleStoreHome

        #get filename for bsddb and validate
        scheduleStoreDb = configParser.getMandatoryParameter('scheduleStoreDb')

        #get name
        scheduleStoreName = configParser.getMandatoryParameter('scheduleStoreName')

        #store config for workunit schedule store
        scheduleStoreConfig = StoreConfig(scheduleStoreType, scheduleStoreName, scheduleStoreFieldsList,
                                          scheduleStoreHome, scheduleStoreDb)

        return scheduleStoreConfig
    else:
        raise RuntimeError, "Unknown scheduleStoreType %s in configuration." % scheduleStoreType

class GridServiceConfig(object):
    """Class representing the soap grid service configuration for this node.
    """

    def __init__(self, file=None):
        "Constructor."

        #get grid service soap config
        parserObj = ScifloConfigParser(file)
        self._gridProtocol = parserObj.getMandatoryParameter('gridProtocol')
        self._gridPort = int(parserObj.getMandatoryParameter('gridPort'))
        self._gridNamespace = parserObj.getMandatoryParameter('gridNamespace')
        self._gridProxyUrl = parserObj.getParameter('gridProxyUrl')
        self._baseUrl = parserObj.getParameter('baseUrl')
        self._workerTimeout = parserObj.getParameter('workUnitTimeout')
        if self._workerTimeout is None: self._workerTimeout = 86400
        else: self._workerTimeout = int(self._workerTimeout)
        self._addWorkUnitMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}addWorkUnitMethod/{%s}exposedName' % \
            (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._queryWorkUnitMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}queryWorkUnitMethod/{%s}exposedName' % \
            (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._cancelWorkUnitMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}cancelWorkUnitMethod/{%s}exposedName' % \
            (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._callbackMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}callbackMethod/{%s}exposedName' % (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._addWorkUnitPythonMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}addWorkUnitMethod/{%s}pythonFunction' % \
            (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._queryWorkUnitPythonMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}queryWorkUnitMethod/{%s}pythonFunction' % \
            (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._cancelWorkUnitPythonMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}cancelWorkUnitMethod/{%s}pythonFunction' % \
            (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._callbackPythonMethod = parserObj.getMandatoryParameterViaXPath(
            './/{%s}callbackMethod/{%s}pythonFunction' % (SCIFLO_NAMESPACE,SCIFLO_NAMESPACE))
        self._workUnitWorkDir = parserObj.getMandatoryParameter('workUnitRootWorkDir')

        #build wsdl
        if self._gridProtocol == 'gsi' or self._gridProtocol == 'ssl': prot='https'
        else: prot='http'
        
        #grid base url
        self._gridBaseUrl = "%s://%s:%s" % (prot, getfqdn(), self._gridPort)

        #callback wsdl
        self._gridWsdl = "%s/wsdl?%s" % (self._gridBaseUrl, self._gridNamespace)

    def getWorkUnitWorkDir(self):
        """Return the work unit work directory."""
        return self._workUnitWorkDir

    def getProtocol(self):
        """Return grid protocol: gsi, ssl, or http."""
        return self._gridProtocol

    def getPort(self):
        """Return grid port."""
        return self._gridPort

    def getNamespace(self):
        """Return grid namespace."""
        return self._gridNamespace

    def getAddWorkUnitMethod(self):
        """Return add work unit method."""
        return self._addWorkUnitMethod

    def getQueryWorkUnitMethod(self):
        """Return query work unit method."""
        return self._queryWorkUnitMethod

    def getCancelWorkUnitMethod(self):
        """Return cancel work unit method."""
        return self._cancelWorkUnitMethod

    def getCallbackMethod(self):
        """Return callback work unit method."""
        return self._callbackMethod

    def getAddWorkUnitPythonMethod(self):
        """Return add work unit python method."""
        return self._addWorkUnitPythonMethod

    def getQueryWorkUnitPythonMethod(self):
        """Return query work unit python method."""
        return self._queryWorkUnitPythonMethod

    def getCancelWorkUnitPythonMethod(self):
        """Return cancel work unit python method."""
        return self._cancelWorkUnitPythonMethod

    def getCallbackPythonMethod(self):
        """Return callback work unit python method."""
        return self._callbackPythonMethod

    def getWsdl(self):
        """Return grid service wsdl url."""
        return self._gridWsdl

    def getBaseUrl(self):
        """Return base url."""
        return self._baseUrl

    def getGridProxyUrl(self):
        """Return grid proxy url."""
        return self._gridProxyUrl
    
    def getGridBaseUrl(self):
        """Return grid base url."""
        return self._gridBaseUrl
    
    def getWorkerTimeout(self):
        """Return worker timeout."""
        return self._workerTimeout
