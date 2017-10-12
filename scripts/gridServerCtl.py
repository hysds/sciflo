#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        gridServerCtl.py
# Purpose:     Control script for SciFlo grid server.
#
# Author:      Gerald Manipon
#
# Created:     Thu Feb 16 10:05:54 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys
import getopt
import shutil
import time
import calendar
import datetime
import signal

import sciflo

#lock directory
lockDir = '/tmp'

def usage():
    """Print usage info."""

    print """%s [-c|--configFile <config file>] [-k|--key <server key file>] \
[-C|--cert <server cert file>] [--clean] [--kill] [-d|--debug] [-l|--log] \
[-t|--type <threading|forking|twisted>] [-h|--help]""" % sys.argv[0]

def getRunningServerPid(port):
    """Get pid of any server currently running.  If none, return 0.
    """

    #lock file
    lockFile = os.path.join(lockDir,'sciflo-%s.lock' % port)

    #do checks for existence of process [only valid for linux]
    if os.path.exists(lockFile):
        lockingPid = open(lockFile,'r').read()
        if os.path.isdir(os.path.join('/proc',lockingPid)): return int(lockingPid)
        else:
            print "Zombie process?  Remove lock at %s to fix." % lockFile
            sys.exit(2)
    else: return 0

def instantiateHandlersAndGetRootWorkDir(configFile, cleanFlag):
    """Instantiate schedule and work unit handlers and perform any
    cleanup.  Return root work dir.
    """

    #set schedule store config
    workUnitScheduleConfig = sciflo.grid.config.getScheduleConfigFromConfiguration(configFile)

    #get schedule dir
    (dbHome, dbName) = workUnitScheduleConfig.getStoreArgs()
    #print dbHome,dbName

    #clean schedule
    if cleanFlag and os.path.isdir(dbHome): shutil.rmtree(dbHome)

    #set schedule handler
    scheduleHandler = sciflo.grid.storeHandler.ScheduleStoreHandler(workUnitScheduleConfig)

    #get StoreConfig
    storeConfig = sciflo.grid.config.getStoreConfigFromConfiguration(configFile)

    #get bsddb home dir and db file name
    (wuDbHome, wuDbName) = storeConfig.getStoreArgs()
    #print "In unittest, wuDbHome and wuDbName:",wuDbHome,wuDbName

    #clean work unit store
    if cleanFlag and os.path.isdir(wuDbHome): shutil.rmtree(wuDbHome)

    #store handler instance
    storeHandler = sciflo.grid.storeHandler.WorkUnitStoreHandler(storeConfig)

    #root work unit work dir
    rootWorkDir = sciflo.grid.config.getRootWorkDirFromConfiguration(configFile)

    #clean work unit work dir
    if cleanFlag and os.path.isdir(rootWorkDir): shutil.rmtree(rootWorkDir)

    return rootWorkDir

def start(configFile, serverCertFile=None, serverKeyFile=None, cleanFlag=False,
          debugFlag=False, logFlag=False, threading=True):

    #get grid service configuration
    gscObj = sciflo.grid.config.GridServiceConfig(configFile)
    gridSoapPort = gscObj.getPort()
    gridProtocol = gscObj.getProtocol()
    gridWsdl = gscObj.getWsdl()
    gridNamespace = gscObj.getNamespace()
    gridCallbackMethod = gscObj.getCallbackMethod()
    gridProxyUrl = gscObj.getGridProxyUrl()
    #print gridSoapPort,gridProtocol,gridWsdl,gridNamespace,gridCallbackMethod

    #set debug
    debug = 0
    if debugFlag: debug = 1

    #set log
    log = 0
    if logFlag: log = 1

    #check for lockfile for server running on this port
    alreadyRunningPid = getRunningServerPid(gridSoapPort)

    #check if already running
    if alreadyRunningPid:
        print "Server already running with pid %s." % alreadyRunningPid
        sys.exit(0)

    #instantiate handlers
    rootWorkDir = instantiateHandlersAndGetRootWorkDir(configFile,cleanFlag)

    #set lockFile
    lockFile = os.path.join(lockDir,'sciflo-%s.lock' % gridSoapPort)

    #fork
    pid = os.fork()
    if not pid:

        #set pgid
        os.setpgid(0,0)

        #create lock file
        currentPid = str(os.getpid())
        f = open(lockFile,'w')
        f.write(currentPid)
        f.close()

        while [1]:
            try:

                #secure
                if gridProtocol == 'gsi':
                    server = sciflo.webservices.soap.SoapServer(('0.0.0.0', gridSoapPort), useGSI=1,
                        returnFaultInfo=1, rootDir=rootWorkDir, debug=debug, log=log,
                        proxyUrl=gridProxyUrl, threading=threading)
                elif gridProtocol == 'ssl':
                    server = sciflo.webservices.soap.SoapServer(('0.0.0.0', gridSoapPort), serverCertFile,
                        serverKeyFile, returnFaultInfo=1, rootDir=rootWorkDir, debug=debug,
                        log=log, proxyUrl=gridProxyUrl, threading=threading)
                else:
                    server = sciflo.webservices.soap.SoapServer(('0.0.0.0', gridSoapPort),
                        returnFaultInfo=1, rootDir=rootWorkDir, debug=debug, log=log,
                        proxyUrl=gridProxyUrl, threading=threading)
                break
            except Exception, e:
                print e
                print "Retrying soap server."
                time.sleep(1)

        retval = server.registerEndpoint(sciflo.utils.xmlUtils.transformXml(configFile,
            sciflo.utils.xmlUtils.GRID_ENDPOINT_CONFIG_XSL))
        server.serveForever()
        os._exit(0)
    print "Server process %s started on port %s." % (pid,gridSoapPort)

def stop(configFile):

    #get grid service configuration
    gscObj = sciflo.grid.config.GridServiceConfig(configFile)
    gridSoapPort = gscObj.getPort()

    #check for lockfile for server running on this port
    alreadyRunningPid = getRunningServerPid(gridSoapPort)

    #check if already running
    if alreadyRunningPid: pass
    else:
        print "No server running."
        sys.exit(0)

    #get pid
    lockFile = os.path.join(lockDir,'sciflo-%s.lock' % gridSoapPort)
    f = open(lockFile)
    pidStr = f.read()
    f.close()
    pid = int(pidStr)

    #make sure it's running
    if os.path.isdir(os.path.join('/proc',pidStr)): pass
    else:
        print "Zombie process?  Remove orphaned lock at %s to fix." % lockFile
        sys.exit(2)

    #kill
    try: os.kill(pid,signal.SIGTERM)
    except: print "Got exception trying to kill pid or unlink lock."

    #remove lock
    try:
        os.unlink(lockFile)
        print "Server process %s at port %s stopped." % (pidStr,gridSoapPort)
    except: print "Got exception trying to unlink lock file."


def main():

    #get opts
    try:
        opts,args = getopt.getopt(sys.argv[1:],"c:k:C:dlt:h",
                                  ["configFile=","key=","cert=","clean",
                                   "kill","debug","log","type=","help"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    #set defaults
    configFile = sciflo.utils.getUserScifloConfig()
    scp = sciflo.utils.ScifloConfigParser(configFile)
    serverKeyFile = scp.getParameter('hostKey')
    serverCertFile = scp.getParameter('hostCert')
    cleanFlag = False
    killFlag = False
    debugFlag = False
    logFlag = False
    threading = True

    #flags to prevent multiple specifications of options
    typeSet = False
    configFileSet = False
    serverKeyFileSet = False
    serverCertFileSet = False

    #process opts
    for o,a in opts:

        #check if help
        if o in ("-h","--help"):
            usage()
            sys.exit()

        #set config file
        if o in ("-c","--configFile"):
            if configFileSet:
                print """Multiple -c|--configFile specifications found.\
  Only specify one config file."""
                usage()
                sys.exit(2)
            else:
                configFile = os.path.abspath(a)
                configFileSet = True

        #set server key file
        if o in ("-k","--key"):
            if serverKeyFileSet:
                print """Multiple -k|--key specifications found.\
  Only specify one server key file."""
                usage()
                sys.exit(2)
            else:
                serverKeyFile = a
                serverKeyFileSet = True

        #set server cert file
        if o in ("-C","--cert"):
            if serverCertFileSet:
                print """Multiple -C|--cert specifications found.\
  Only specify one server cert file."""
                usage()
                sys.exit(2)
            else:
                serverCertFile = a
                serverCertFileSet = True
        
        #check type
        if o in ("-t","--type"):
            if typeSet:
                print "Multiple -t|--type specifications found.  Only specify one type."
                usage()
                sys.exit(2)
            else:
                if a not in ('threading', 'forking', 'twisted'):
                    print "Invalid server type: %s." % a
                    usage()
                    sys.exit(2)
                if a == 'threading': threading = True
                elif a == 'forking': threading = False
                else: threading = None
                typeSet = 1

        #check if clean
        if o in ("--clean"): cleanFlag = True

        #check if kill
        if o in ("--kill"): killFlag = True

        #check if debug
        if o in ("-d","--debug"): debugFlag = True

        #check if log
        if o in ("-l","--log"): logFlag = True


    #pass to appropriate function
    if killFlag: stop(configFile)
    else: start(configFile, serverCertFile, serverKeyFile, cleanFlag,
                debugFlag, logFlag, threading)

    #print configFile, serverKeyFile, serverCertFile

if __name__ == '__main__': main()
