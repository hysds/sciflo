#-----------------------------------------------------------------------------
# Name:        manager.py
# Purpose:     WorkUnitManager class.
#
# Author:      Gerald Manipon
#
# Created:     Mon Jun 27 12:55:42 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys
import traceback
import shutil
import types
import signal
from socket import getfqdn
import cPickle as pickle

import sciflo
from sciflo.utils import *
from status import *
from utils import *
from workUnit import *
from storeHandler import *
from config import *
from callback import *
from postExecution import PostExecutionHandler

def publicizeResultFiles(result, urlBaseTrackerObj):
    """Recursively loop through result and check for filenames.  If detected,
    replace with url to that file.  Return the converted result."""

    #if string, try to get url
    if isinstance(result, types.StringType) or isinstance(result, types.UnicodeType):
        try:
            if os.path.exists(result):
                newResult = urlBaseTrackerObj.getUrl(result)
                return newResult
            else: return result
        except: return result
    elif isinstance(result, types.ListType) or isinstance(result, types.TupleType):
        newResult = []
        for r1 in result: newResult.append(publicizeResultFiles(r1, urlBaseTrackerObj))
        if isinstance(result, types.TupleType): return tuple(newResult)
        else: return newResult
    else: return result

def getAbsPathForResultFiles(result):
    """Recursively loop through result and check for filenames.  If detected,
    replace with abs path to that file.  Return the converted result."""

    #if string, try to get url
    if isinstance(result, types.StringType) or isinstance(result, types.UnicodeType):
        try:
            if os.path.exists(result):
                newResult = os.path.abspath(result)
                return newResult
            else: return result
        except: return result
    elif isinstance(result,(types.TupleType,types.ListType)):
        newResult = []
        for r1 in result: newResult.append(getAbsPathForResultFiles(r1))
        if isinstance(result, types.TupleType): return tuple(newResult)
        else: return newResult
    else: return result

class WorkUnitExecutionHandlerError(Exception):
    """Exception class for WorkUnitExecutionHandler class."""
    pass

class WorkUnitExecutionHandler(object):
    """WorkUnitExecutionHandler base class."""


    def __init__(self, workUnitOwner, workUnitType, workUnitCall, workUnitArgs, wuStoreConfig,
                 workRootDir, stageFiles=None, postExecutionHandlers=None, scheduleStoreConfig=None,
                 publicBaseUrl=None, verbose=False, noLookCache=False, wuid=None, procId=None):
        """Constructor."""

        #set attribs
        self._wuOwner = workUnitOwner
        self._wuType = workUnitType
        self._wuCall = workUnitCall
        self._wuArgs = workUnitArgs
        self._wuStoreConfig = wuStoreConfig
        self._wuStoreHandler = None
        self._wuRootDir = workRootDir
        self._wuStatus = None
        self._stageFiles = getListFromUnknownObject(stageFiles)
        self._postExecutionHandlers = getListFromUnknownObject(postExecutionHandlers)
        self._scheduleStoreConfig = scheduleStoreConfig
        self._scheduleHandler = None
        self._workUnit = None
        self._result = None
        self._exceptionMessage = None
        self._tracebackMessage = None
        self._executionLog = None
        self._entryTime = time.time()
        self._startTime = None
        self._endTime = None
        self._postExecutionResults = None
        self._cachedWuId = None
        self._alreadyExecuted = False
        self._executePid = 0
        self._publicBaseUrl = publicBaseUrl
        self._verbose = verbose
        self._noLookCache = noLookCache
        self._procId = procId

        #if this is a sciflo type, make sure a scheduleHandler object was passed
        if self._wuType == 'sciflo':
            if isinstance(self._wuArgs[0],types.DictType) and \
            ('configFile' in self._wuArgs[0].keys() or \
             'localExecutionMode' in self._wuArgs[0].keys() or \
             'debugMode' in self._wuArgs[0].keys()):
                configFile = self._wuArgs[0].get('configFile',None)
                localExecutionMode = self._wuArgs[0].get('localExecutionMode',False)
                debugMode = self._wuArgs[0].get('debugMode',False)
                self._wuArgs = self._wuArgs[1:]
            else:
                configFile = None; localExecutionMode = False; debugMode = False

        #get unique sciflo workunit id (unique across all workunits, even if they are the exactly the same
        if wuid is None: self._wuid = generateWorkUnitId()
        else: self._wuid = wuid

        #set workUnitWorkDir
        if validateDirectory(workRootDir):
            self._workDir = os.path.join(workRootDir,self._wuid)
        else:
            raise WorkUnitExecutionHandlerError, "Couldn't create work unit work directory in root work dir: %s." \
            % workRootDir

        #if publicize, get url for work dir
        if self._publicBaseUrl:
            #create urlbase tracker obj
            self._urlBaseTrackerObj = UrlBaseTracker(self._wuRootDir, self._publicBaseUrl)

            #get url
            self._workUrl = self._urlBaseTrackerObj.getUrl(self._workDir)
        else:
            self._urlBaseTrackerObj = None
            self._workUrl = None

        #get postExecutionHandler ids
        postExecIds = []
        for postExecHdl in self._postExecutionHandlers:
            if postExecHdl is None: postExecIds.append(None)
            else: postExecIds.append(postExecHdl.getIdString())

        #get hex digest for workunit (used for caching)(wuOwner allows privatization of work units)
        self._wuHexDigest = generateWorkUnitHexDigest(self._wuOwner, self._wuType, self._wuCall,
                                                self._wuArgs, self._stageFiles, postExecIds)

        #check if the hex digest is already in the store (cached)
        self._cacheWuId = None

        #if publicizing, use url instead actual dir path
        thisWorkDir = self._workDir
        if self._workUrl: thisWorkDir = self._workUrl

        #get appropriate WorkUnit subclass based on type
        from workUnitTypeMapping import WorkUnitTypeMapping
        wuClass = WorkUnitTypeMapping.get(self._wuType,None)

        #if wuClass is None raise error
        if wuClass is None:
            raise WorkUnitExecutionHandlerError, "Unimplemented WorkUnit subclass for type %s." % self._wuType

        #create work unit; if it is a sciflo work unit, generate scifloid from
        #wuid and pass it and the scheduleHandler in
        if self._wuType == 'sciflo':
            self._workUnit = wuClass(self._wuOwner, self._wuCall, self._wuArgs, self._workDir, self._scheduleHandler,
                                   self._wuid.replace('sciflowuid','scifloid'), configFile=configFile,
                                   localExecutionMode=localExecutionMode, debugMode=debugMode,
                                   verbose=self._verbose, noLookCache=self._noLookCache)
        else:
            self._workUnit = wuClass(self._wuCall,self._wuArgs,self._workDir,
                                     verbose = self._verbose)

        #save stderr/stdout
        self.origStdout, self.origStderr = sys.stdout, sys.stderr

    def getResultDict(self):
        return {'status': self._wuStatus,
                'workDir': self._workDir,
                'result': self._result,
                'postExecutionResults': self._postExecutionResults,
                'exceptionMessage': self._exceptionMessage,
                'tracebackMessage': self._tracebackMessage,
                'executionLog': self._executionLog
                }
    
    def getWorkUnitDigest(self):
        """Return work unit digest."""
        return self._wuHexDigest

    def getWorkUnitOwner(self):
        """Return work unit owner."""
        return self._wuOwner

    def getWorkUnitStatus(self):
        """Return work unit status."""
        return self._wuStatus

    def getWorkUnitType(self):
        """Return work unit type."""
        return self._wuType

    def getWorkUnitCall(self):
        """Return work unit call."""
        return self._wuCall

    def getWorkUnitArgs(self):
        """Return work unit args."""
        return self._wuArgs

    def getWorkUnitStoreHandler(self):
        """Return the work unit store handler."""
        return self._wuStoreHandler

    def getWorkUnitRootDir(self):
        """Return the work unit work root directory."""
        return self._wuRootDir

    def getStageFiles(self):
        """Return the work unit stage files."""
        return self._stageFiles

    def getPostExecutionHandlers(self):
        """Return the work unit post execution handlers."""
        return self._postExecutionHandlers

    def getScheduleHandler(self):
        """Return the work unit schedule handler."""
        return self._scheduleHandler

    def getWorkUnitId(self):
        """Return the work unit id."""
        return self._wuid

    def getWorkDir(self):
        """Return the work unit work directory."""
        return self._workDir

    def getResult(self):
        """Return the result."""
        return self._result

    def getExceptionMessage(self):
        """Return the exception message.  Actual exceptions, if any, are stored in the
        self._result attribute (call getResult())."""
        return self._exceptionMessage
    
    def getTracebackMessage(self):
        return self._tracebackMessage
    
    def getExecutionLog(self):
        return self._executionLog

    def getEntryTime(self):
        """Return the entry time."""
        return self._entryTime

    def getStartTime(self):
        """Return the start time of the execution."""
        return self._startTime

    def getEndTime(self):
        """Return the end time of the execution."""
        return self._endTime

    def getPostExecutionResults(self):
        """Return the list of post execution results."""
        return self._postExecutionResults

    def getExecutePid(self):
        """Return the execute pid."""
        return self._executePid

    def isCached(self):
        """Return the wuid of the cached work unit.  Otherwise None."""
        return self._cachedWuId

    def _restoreStdIO(self):
        """Restore original stderr/stdout."""
        sys.stdout, sys.stderr = self.origStdout, self.origStderr
        return True

    def executeWorkUnit(self, timeout=86400):
        """Run the work unit's stage() and run() methods.  If this work unit
        was found in cache, return 2.  Upon success, return 1.  Return 0 if
        it failed during staging, or post execution.  If already
        executed, return 3."""

        #if executed already, return
        if self._alreadyExecuted: return True
        else: self._alreadyExecuted = True

        #chdir to workdir
        os.chdir(self._workDir)

        #get pid and set in store
        self._executePid = os.getpid()

        #get StdIOFaker object and set stdout/stderr to it
        sys.stdout = sys.stderr = StdIOFaker(self.origStderr)

        #copy stage files/dirs to work dir; set status to staging
        self._wuStatus = stagingStatus
        try: copyToDir(self._stageFiles, self._workDir, unpackBundles = True)
        except Exception, e:

            #get traceback info
            etype = sys.exc_info()[0]
            evalue = sys.exc_info()[1]
            etb = traceback.format_exc()

            #create error message
            emessage = "Exception Type: %s\n" % str(etype)
            emessage += "Exception Value: %s\n" % str(evalue)
            emessage += etb
            self._result = e

            print "Encountered exception during staging: %s" % emessage

            #set status to exception and write error
            self._wuHexDigest = None
            self._exceptionMessage = str(e)
            self._tracebackMessage = emessage
            self._executionLog = sys.stderr.getvalue()
            self._wuStatus = exceptionStatus
            self._result = e

            #restore stdio and return
            self._restoreStdIO()
            return 0

        #set status to working
        self._wuStatus = workingStatus

        #set starttime
        self._startTime = time.time()

        #run work unit
        (self._result, self._tracebackMessage) = \
            sciflo.grid.funcs.workUnitWorker(self._wuid, self._procId,
                                             self._workUnit, timeout)

        #check if work unit status is finished(cancelled)
        if self.getWorkUnitStatus() in finishedStatusList:
            self._restoreStdIO()
            return 0

        #if we are publicizing work dir, we need to publicize local file outputs
        #in the result also.  Otherwise get root directory path to them
        if self._publicBaseUrl:
            self._result = publicizeResultFiles(self._result, self._urlBaseTrackerObj)
        else:
            self._result = getAbsPathForResultFiles(self._result)

        #set endtime
        self._endTime = time.time()

        #test if result is pickleable
        try: testStr = pickle.dumps(self._result,-1)
        except Exception, e: self._result = WorkUnitExecutionHandlerError("Unpickleable result: %s" % self._result)

        #if result is not exception
        if isinstance(self._result, Exception):

            #set status to exception and write error
            self._wuHexDigest = None
            self._exceptionMessage = str(self._result)
            self._executionLog = sys.stderr.getvalue()
            self._wuStatus = exceptionStatus
            self._restoreStdIO()
            return 1

        #do any post execution
        if self._postExecutionHandlers:
            self._wuStatus = postExecutionStatus
            try:
                #run post execution handlers and get post execution results
                self._postExecutionResults = self.runPostExecutionHandlers()
            except Exception, e:
                #get traceback info
                etype = sys.exc_info()[0]
                evalue = sys.exc_info()[1]
                etb = traceback.format_exc()

                #create error message
                emessage = "Exception Type: %s\n" % str(etype)
                emessage += "Exception Value: %s\n" % str(evalue)
                emessage += etb
                self._result = e

                print "Encountered exception during post execution: %s" % emessage

                #set status to exception and write error
                self._wuHexDigest = None
                self._exceptionMessage = str(self._result)
                self._tracebackMessage = emessage
                self._executionLog = sys.stderr.getvalue()
                self._wuStatus = exceptionStatus

                #restore stdio and return
                self._restoreStdIO()
                return 0

        #set execution log and final status
        self._executionLog = sys.stderr.getvalue()
        self._wuStatus = doneStatus

        #restore stdio and return
        self._restoreStdIO()
        return 1

    def runPostExecutionHandlers(self):
        """Run the list of postExecutionHandlers and collect the post execution results.
        Return a list of post execution results."""

        #results list
        resultsList = []

        #loop over post execution handlers and run execute() method
        for postExecutionHandler in self._postExecutionHandlers:

            #get post result
            postResult = postExecutionHandler.execute(self._result, self._workDir)

            #is result a local file and are we publicizing?  If so publicize.
            if self._publicBaseUrl:
                postResult = publicizeResultFiles(postResult, self._urlBaseTrackerObj)

            #append to post result list
            resultsList.append(postResult)

        return resultsList

class WorkUnitManagerError(Exception):
    """Exception class for WorkUnitManager class."""
    pass

class WorkUnitKilled(Exception):
    """Exception class for WorkUnits that are killed."""
    pass

class WorkUnitDied(Exception):
    """Exception class for WorkUnits that die unexpectedly."""
    pass

class WorkUnitManager(object):
    """Class that manages the WorkUnitExecutionHandler object."""

    def __init__(self, owner, type, call, args, storeConfig, workRootDir, stageFiles=None,
                 postExecutionConfigList=None, scheduleConfig=None, callbackConfig=None,
                 publicBaseUrl=None, verbose=False, timeout=86400, noLookCache=False,
                 wuid=None):
        """Constructor."""

        #set data member
        self._wuOwner = owner
        self._wuType = type
        self._wuCall = call
        self._wuArgs = args
        self._storeConfig = storeConfig
        self._rootDir = workRootDir
        self._scheduleConfig = scheduleConfig
        self._stageFiles = stageFiles
        self._postExecutionConfigList = postExecutionConfigList
        self._callbackConfig = callbackConfig
        self._publicBaseUrl = publicBaseUrl
        self._verbose = verbose
        self._allData = None
        self._managerPid = os.getpid()
        self._executePid = 0
        self._timeout = timeout
        self._noLookCache = noLookCache
        self._storeClosed = False
        
        #create store handler
        self._storeHandler = WorkUnitStoreHandler(self._storeConfig)

        #create schedule handler if set
        if self._scheduleConfig:
            self._scheduleHandler = ScheduleStoreHandler(self._scheduleConfig)
        else:
            self._scheduleHandler = None

        #create post execution handlers
        if self._postExecutionConfigList:
            self._postExecutionHandlers = []
            for outputIdx,conversionFuncStr in self._postExecutionConfigList:
                self._postExecutionHandlers.append(PostExecutionHandler(outputIdx,conversionFuncStr))
        else:
            self._postExecutionHandlers = None

        #create callback
        if self._callbackConfig: self._callback = getCallback(self._callbackConfig)
        else: self._callback = None

        #executor
        executorArgs = [self._wuOwner,self._wuType,self._wuCall,self._wuArgs,
                        self._storeConfig,self._rootDir, self._stageFiles,
                        self._postExecutionHandlers,
                        self._scheduleConfig,self._publicBaseUrl,
                        self._verbose, self._noLookCache, wuid]
        self._executor = apply(WorkUnitExecutionHandler,executorArgs)

        #get work unit id
        self._wuid = self._executor.getWorkUnitId()

        #set manager pid
        self._storeHandler.setManagerPid(self._wuid,self._managerPid)
    
    def getWorkUnitId(self):
        """Return the work unit id for this thread."""
        return self._wuid

    def getExecutePid(self):
        """Return the execute pid for this thread."""

        #resolve execute pid
        if self._executePid: return self._executePid

        #Loop until workunitexecutor is created or failed
        #creation of a work unit should not take very long.
        #Instantiation just sets attributes.
        retries = 10
        tryNum = 1
        while tryNum <= retries:
            if self._wuid:
                self._executePid = self._storeHandler.getExecutePid(self._wuid)
                return self._executePid
            time.sleep(1)
            tryNum += 1

        #raise error
        raise WorkUnitManagerError, "Could not get execute pid."

    def run(self):
        res = sciflo.grid.funcs.workUnitExecutionHandlerWorker(self._executor, self._timeout)
        if isinstance(res, types.TupleType) and isinstance(res[0], Exception):
            self.killSelf(res[0])
        
        #get status
        status = self._storeHandler.getStatus(self._wuid)
        #print >>sys.stderr, "status for wuid %s: %s %s" % (self._wuid,status,self._callback)

        #if status if one of the finished, join and return
        if status in finishedStatusList:
            if self._callback: self._callback(self._wuid, status)
            
        #close manager
        self.closeStore()

    def killSelf(self, exceptionObj=WorkUnitKilled("Work unit was killed.")):
        """Kill this work unit manager process.  Pass in an exception type to set in the store."""
        
        #exception message
        emessage = str(exceptionObj)

        #get execute pid
        executePid = self.getExecutePid()

        #kill execute pid (exeuction of WorkUnitExecution object)
        try:
            os.kill(executePid,signal.SIGTERM)
            os.waitpid(executePid, 0)
        except: pass

        #set status, result, and exception message; clear digest
        self._storeHandler.setDigest(self._wuid,None)
        self._storeHandler.setResult(self._wuid,exceptionObj)
        self._storeHandler.setExceptionMessage(self._wuid,emessage)
        #print "Emessage: %s" % emessage
        if isinstance(exceptionObj, WorkUnitDied):
            self._storeHandler.setStatus(self._wuid,exceptionStatus)
        else:
            self._storeHandler.setStatus(self._wuid,cancelledStatus)

        #do callback
        if self._callback: self._callback(self._wuid, cancelledStatus)
        
        #close store
        self.closeStore()
        
    def closeStore(self):
        if not self._storeClosed:
            #self._storeHandler._managerStore.close()
            self._storeClosed = True

def forkManager(owner, type, call, args, storeConfig, workRootDir, stageFiles=None,
                postExecutionConfigList=None, scheduleConfig=None, timeout=86400,
                callbackConfig=None, publicBaseUrl=None, verbose=False, noLookCache=False):
    """Fork a WorkUnitManager and return the work unit id of the work unit.
    After forking, this function calls the join() method of the WorkUnitManager thread.
    """

    #fork
    pid = os.fork()

    #child
    if not pid:

        #set child as the session leader
        os.setpgid(0,0)

        #create WorkUnitManager thread, run, and join
        d = WorkUnitManager(owner, type, call, args, storeConfig, workRootDir,
                               stageFiles, postExecutionConfigList, scheduleConfig,
                               callbackConfig, publicBaseUrl, verbose, timeout=timeout,
                               noLookCache=noLookCache)
        d.run()
        os._exit(0)
    else:
        #create store handler
        storeHandler = WorkUnitStoreHandler(storeConfig)

        #wuid
        wuid = None

        #get wuid of the manager
        while not wuid:
            wuid = storeHandler.getWorkUnitIdByManagerPid(pid)
            time.sleep(.1)

        #return wuid
        return wuid

def workUnitExecute(managerFunc, owner, type, call, args, stageFiles=None, postExecutionTypePickle=None,
                    timeout=86400, callbackConfig=None, configFile=None, publicizeWorkFlag=True,
                    localExecutionMode=False, debugMode=False, verbose=False, noLookCache=False,
                    wuid=None, procId=None):
    """Register a work unit to be run and call a manager to handle its execution.
    """

    #unpickle args
    argsList = unpickleArgsList(args)

    #unpickle postExecutionTypeList
    postExecutionTypeList = unpickleThis(postExecutionTypePickle)

    #get StoreConfig
    workUnitStoreConfig = getStoreConfigFromConfiguration(configFile)

    #get root dir
    workUnitRootWorkDir = getRootWorkDirFromConfiguration(configFile)

    #get schedule config
    if type == 'sciflo':
        workUnitScheduleConfig = getScheduleConfigFromConfiguration(configFile)
        argsList.insert(0,{'configFile': configFile, 'localExecutionMode': localExecutionMode,
                           'debugMode': debugMode, 'noLookCache': noLookCache})
    else: workUnitScheduleConfig = None

    #create url base tracker if we want to publicize
    baseUrl = None
    if publicizeWorkFlag:
        #get configuration info
        gscObj = GridServiceConfig(configFile)
        baseUrl = gscObj.getBaseUrl()
        if baseUrl is None:
            fqdn = getfqdn()
            gridProtocol = gscObj.getProtocol()
            gridPort = gscObj.getPort()
            baseUrl = getBaseUrl(gridProtocol, fqdn, gridPort)
    return managerFunc(owner, type, call, argsList, workUnitStoreConfig, workUnitRootWorkDir,
                       stageFiles, postExecutionTypeList, workUnitScheduleConfig, timeout,
                       callbackConfig, baseUrl, verbose, noLookCache, wuid, procId)

def overwriteGridFuncArgs(*args, **kargs):
    if args[8] is not None and kargs.has_key('configFile'):
        if args[8] == kargs.get('configFile','') or \
        open(args[8]).read() == open(kargs['configFile']).read():
            args = list(args)
            args[8] = kargs['configFile']
            del kargs['configFile']
        else:
            raise RuntimeError, "Multiple configFiles specified: %s and %s." % \
                (args[8],kargs['configFile'])
    elif args[8] is None and kargs.has_key('configFile'):
        args = list(args)
        args[8] = kargs['configFile']
        del kargs['configFile']
    else: pass
    return (args,kargs)

def addAndExecuteWorkUnit(*args, **kargs):
    """Register a work unit to be run and fork a manager to handle its execution.
    """
    args,kargs = overwriteGridFuncArgs(*args, **kargs)
    return workUnitExecute(forkManager,*args, **kargs)

def cancelWorkUnit(wuid, configFile = None, remove = False):
    """Cancel the execution of a work unit."""

    #remove flag
    if remove:
        #if work unit id
        if wuid.startswith('workunitconfigid-'):
            workUnitScheduleConfig = getScheduleConfigFromConfiguration(configFile)
            scheduleHandler = ScheduleStoreHandler(workUnitScheduleConfig)
            ret = scheduleHandler.removeWorkUnitConfig(wuid)
        else:
            storeConfig = getStoreConfigFromConfiguration(configFile)
            storeHandler = WorkUnitStoreHandler(storeConfig)
            try: ret = storeHandler.removeWorkUnit(wuid)
            except WorkUnitStoreHandlerError, e:
                if re.search(r'is not already in the store', str(e)): pass
                else: raise
        return True
    else:
        storeConfig = getStoreConfigFromConfiguration(configFile)
        storeHandler = WorkUnitStoreHandler(storeConfig)
        storeHandler.setCancelFlag(wuid, 1)

def queryWorkUnit(wuid,field,configFile = None):
    """Query a work unit's field.  If a scifloid is passed, query schedule
    table."""

    #if work unit id
    if wuid.startswith('scifloid-'):

        #set schedule store config
        workUnitScheduleConfig = getScheduleConfigFromConfiguration(configFile)

        #set schedule handler
        scheduleHandler = ScheduleStoreHandler(workUnitScheduleConfig)

        #get schedule info of all work units under this scifloid
        ret = scheduleHandler.getScifloidInfo(wuid, field)

    else:

        #get StoreConfig
        storeConfig = getStoreConfigFromConfiguration(configFile)

        #create store handler
        storeHandler = WorkUnitStoreHandler(storeConfig)
        
        '''
        #check status if running;  if not, try to set exception
        executePid = storeHandler.getExecutePid(wuid)
        if executePid is None or storeHandler.getStatus(wuid) in finishedStatusList: pass
        else:
            if not pidIsRunning(executePid):
                try:
                    e = WorkUnitDied("""Work unit's execution pid could not be found in process table.
An external entity killed it (restarting of grid server) or a segmentation fault may have occurred.""")
                    storeHandler.setDigest(wuid, None)
                    storeHandler.setResult(wuid, e)
                    storeHandler.setExceptionMessage(wuid, str(e))
                    storeHandler.setStatus(wuid, exceptionStatus)
                except: pass
        '''

        #query
        ret = storeHandler.getValueByWorkUnitId(wuid,field)

    #pickle query and return
    pickleStr = pickleThis(ret)
    return pickleStr

def workUnitCallback(wuid, status, configFile=None):
    """Callback function to notify that work unit has completed."""

    #set schedule store config
    workUnitScheduleConfig = getScheduleConfigFromConfiguration(configFile)

    #get schedule dir
    (dbHome, dbName) = workUnitScheduleConfig.getStoreArgs()

    #set schedule handler
    scheduleHandler = ScheduleStoreHandler(workUnitScheduleConfig)

    #try 5 times to work around a race condition between the scifloManager
    #and the workUnitManager.
    tryNum = 1
    while tryNum <= 5:
        try:
            #get current status
            curStatus = scheduleHandler.getStatusByWuid(wuid)
            if status == retryStatus and isinstance(curStatus, types.StringTypes):
                if curStatus.startswith('retry_'):
                    retryNum = int(re.search(r'^retry_(\d+)$', curStatus).group(1))
                    if retryNum <= 5:
                        scheduleHandler.setStatusByWuid(wuid, retryStatus + '_%d' % (retryNum + 1))
                        return
                else:
                    scheduleHandler.setStatusByWuid(wuid, retryStatus + '_1')
                    return
            
            #set status
            scheduleHandler.setStatusByWuid(wuid, calledBackStatus)
            return
        except Exception, e: pass
        tryNum += 1

        #sleep
        time.sleep(.1)

    #raise error
    etb = traceback.format_exc()
    raise RuntimeError, "Failed 5 times to callback: %s" % etb

def nonforkingManager(owner, type, call, args, storeConfig, workRootDir, stageFiles=None,
                      postExecutionConfigList=None, scheduleConfig=None, timeout=86400,
                      callbackConfig=None, publicBaseUrl=None, verbose=False, noLookCache=False,
                      wuid=None, procId=None):
    """Run a WorkUnitManager and return the work unit id of the work unit after execution.
    """
    
    #create store handler
    #storeHandler = WorkUnitStoreHandler(storeConfig)

    #create schedule handler if set
    #if scheduleConfig: scheduleHandler = ScheduleStoreHandler(scheduleConfig)
    #else: scheduleHandler = None

    #create post execution handlers
    if postExecutionConfigList:
        postExecutionHandlers = []
        for outputIdx,conversionFuncStr in postExecutionConfigList:
            postExecutionHandlers.append(PostExecutionHandler(outputIdx,conversionFuncStr))
    else: postExecutionHandlers = None

    #executor
    executor = WorkUnitExecutionHandler(owner, type, call, args, storeConfig, workRootDir,
                                        stageFiles,postExecutionHandlers, scheduleConfig,
                                        publicBaseUrl, verbose, noLookCache, wuid, procId)
    #execute and return wuid
    executor.executeWorkUnit(timeout=timeout)
    return (executor.getWorkUnitId(), executor.getResultDict())

def nonforkingAddAndExecuteWorkUnit(*args, **kargs):
    """Register a work unit to be run and  handle its execution.
    """
    args,kargs = overwriteGridFuncArgs(*args, **kargs)
    return workUnitExecute(nonforkingManager,*args, **kargs)
