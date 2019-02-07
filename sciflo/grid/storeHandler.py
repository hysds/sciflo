#-----------------------------------------------------------------------------
# Name:        storeHandler.py
# Purpose:     WorkUnitStoreHandler class.
#
# Author:      Gerald Manipon
#
# Created:     Tue Jun 28 07:25:35 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import re
import types
import time
from inspect import isclass

from .status import *
from sciflo.db import *
from sciflo.utils import getListFromUnknownObject, validateDirectory

#work unit store name
workUnitStoreName = 'workUnits'

#work unit store fields
workUnitStoreFieldsList = ['wuid','digest','owner','status','type',
                           'call','args','stageFiles','workDir',
                           'entryTime','startTime','endTime',
                           'result','exceptionMessage','postExecutionResults',
                           'cancelFlag','executePid','managerPid','tracebackMessage',
                           'executionLog']

#return fields that should be resolved from the cached(previously run) work unit
cachedFields = ['type','call','args','stageFiles','result','exceptionMessage',
                'postExecutionResults','tracebackMessage','executionLog']

#work unit manager store fields
workUnitManagerStoreFieldsList = ['wuid','digest','executePid','managerPid','entryTime']

class WorkUnitStoreHandlerError(Exception):
    """Exception class for WorkUnitStoreHandler class."""
    pass

class WorkUnitStoreHandler(object):
    """WorkUnitStoreHandler base class.  Work unit metadata stored in the WorkUnitStore
    include: id, hex digest, owner, status, type, call, args, work directory, entry time,
    start time, end time, result, exception message, post execution results, cancelFlag,
    executePid,managerPid."""

    def __init__(self, storeConfig):
        """Constructor."""

        #make sure storeConfig is StoreConfig
        if not isinstance(storeConfig, StoreConfig):
            raise WorkUnitStoreHandlerError("Must specify a StoreConfig object.")

        #set attributes
        self._storeConfig = storeConfig
        self._storeClass = self._storeConfig.getStoreClass()
        self._storeName = self._storeConfig.getStoreName()
        self._storeFieldsList = self._storeConfig.getStoreFieldsList()
        self._storeArgs = self._storeConfig.getStoreArgs()
        self._storeKargs = self._storeConfig.getStoreKargs()

        #create manager store
        args = [self._storeName,  workUnitManagerStoreFieldsList]
        args.extend(self._storeArgs)
        self._managerStore = self._storeClass(*args)
        self._store = None
        self._cachedStore = None
        
    def setStore(self, wuid, cachedStore=False):
        #create store
        if wuid is None: return None
        args = [self._storeName,  self._storeFieldsList]
        dbHome = os.path.join(self._storeArgs[0], 'wuidStores', wuid)
        validateDirectory(dbHome, noExceptionRaise=True)
        args.append(dbHome)
        args.extend(self._storeArgs[1:])
        if cachedStore: self._cachedStore = self._storeClass(*args)
        else: self._store = self._storeClass(*args)
        return True

    def queryUnique(self, queryField, queryValue, returnField=None, dataStore=False, cachedStore=False):
        """Return the field values of a field matching.  If no return fields are specified,
        it just returns the value of field.  If a single return field is specified, the
        result is a single value.  If a list of return fields is specified, result is a
        list corresponding to that list.  This is where the actual implementation
        of the query is defined.
        """
        if dataStore:
            if cachedStore:
                return self._cachedStore.queryUnique(queryField, queryValue, returnField)
            else:
                return self._store.queryUnique(queryField, queryValue, returnField)
        else:
            return self._managerStore.queryUnique(queryField, queryValue, returnField)

    def addWorkUnit(self, wuid, digest=None, owner=None, status=None,
                    type=None, call=None, args=[], stageFiles=[], workDir=None,
                    entryTime=None, startTime=None, endTime=None, result=None,
                    exceptionMessage=None, postExecutionResults=[], cancelFlag=0,
                    executePid=0,managerPid=0, tracebackMessage=None, executionLog=''):
        """Add a new entry into the work unit store."""

        #check that wuid is not here already
        if self.isWorkUnitIdHere(wuid):
            raise WorkUnitStoreHandlerError("Work unit id %s is already in the store." % wuid)

        #add
        self._managerStore.add(wuid, digest, executePid, managerPid, entryTime)
        self.setStore(wuid)
        self._store.add(wuid, digest, owner, status, type, call, args, stageFiles, workDir,
                  entryTime, startTime, endTime, result, exceptionMessage,
                  postExecutionResults,cancelFlag,executePid,managerPid, tracebackMessage,
                  executionLog)

    def removeWorkUnit(self, wuid):
        """Remove an entry(record) from the work unit store."""

        #check that wuid is not here already
        if not self.isWorkUnitIdHere(wuid):
            raise WorkUnitStoreHandlerError("Work unit id %s is not already in the store." % wuid)

        #remove
        self._managerStore.remove(wuid)
        self.setStore(wuid)
        self._store.remove(wuid)

    def getValueByWorkUnitId(self, wuid, field):
        """Return the value of a field in the store by work unit id.
        Resolve any cached entries to their values.
        """

        #if work unit is here, check if it was cached by checking digest for a sciflo work unit id
        if self.isWorkUnitIdHere(wuid):
            #set store
            self.setStore(wuid)

            #get digest and status
            digest, status = (None, None)
            qTryRes = None
            for qTry in range(2):
                qTryRes = self.queryUnique('wuid', wuid, ['digest', 'status'], dataStore=True)
                if qTryRes is not None: 
                    digest, status = qTryRes
                    break
                time.sleep(1)
            if qTryRes is None:
                raise WorkUnitStoreHandlerError("Couldn't get digest/status for wuid %s" % wuid)
                

            #print "digest,status:",digest,status
            #if it is a sciflowuid, it is cached
            fields = getListFromUnknownObject(field)
            if digest is not None and re.search(r'^sciflowuid-', digest) and status == cachedStatus:
                self.setStore(digest, cachedStore=True)
                if len(fields) == 1:
                    if fields[0] in cachedFields: return self.queryUnique('wuid', digest, fields[0],
                                                                          dataStore=True,
                                                                          cachedStore=True)
                    else: return self.queryUnique('wuid', wuid, fields[0], dataStore=True)
                else:
                    cFields = []
                    dFields = []
                    for f in fields:
                        if f in cachedFields: cFields.append(f)
                        else: dFields.append(f)
                    cResults = getListFromUnknownObject(self.queryUnique('wuid', digest, cFields,
                                                                         dataStore=True,
                                                                         cachedStore=True))
                    dResults = getListFromUnknownObject(self.queryUnique('wuid', wuid, dFields,
                                                                         dataStore=True))
                    results = []
                    for f in fields:
                        if f in cFields: results.append(cResults[cFields.index(f)])
                        elif f in dFields: results.append(dResults[dFields.index(f)])
                        else: raise WorkUnitStoreHandlerError("Cannot find field %s in results." % f)
                        
                    return results

            #otherwise return the value from this work unit
            else:
                if len(fields) == 1: return self.queryUnique('wuid', wuid, fields[0],
                                                             dataStore=True)
                else: return self.queryUnique('wuid', wuid, fields, dataStore=True)

        #if not here return None
        else: return None

    def isWorkUnitIdHere(self,wuid):
        """Return 1 if wuid is in store.  Otherwise, None."""
        return self.queryUnique('wuid',wuid)

    def getWorkUnitIdByDigest(self, digest):
        """Return work unit id of the hex digest passed.  Otherwise returns None."""

        wuid = self.queryUnique('digest',digest,'wuid')
        self.setStore(wuid)
        return wuid

    def _getRecentWorkUnitIdFromPid(self,pidField,pid):
        """Return the most recent work unit id from a pid field and pid."""

        #query for wuid and starttimes
        results = self._managerStore.query(pidField,pid,['wuid','entryTime'])

        #recent wuid
        recentWuid = None

        #recent time diffr
        recentDiff = None

        #time now
        timeNow = time.time()

        #loop over and find most recent
        for wuid, entryTime in results:

            #if entry time is none, skip
            if entryTime is None: continue

            #time now
            timeDiff = timeNow-entryTime
            if recentWuid:
                if timeDiff < recentDiff: recentDiff=timeDiff
            else:
                recentWuid = wuid
                recentDiff = timeDiff

        return recentWuid

    def _modifyByWorkUnitId(self, wuid, modifyFields, modifyValues):
        """Modify a work unit record by its id.  A work unit can only be modified if
        its status is not in the finishedStatusList list.
        """

        #get status
        status = self.getStatus(wuid)

        #if status is in finished status list, raise error
        if status in finishedStatusList:
            raise WorkUnitStoreHandlerError("Cannot modify work unit %s.  Status is %s." % \
            (wuid, status))

        #make data dict
        dataDict = {}
        managerDataDict = {}
        index = 0
        for field in modifyFields:
            dataDict[field] = modifyValues[index]
            if field in workUnitManagerStoreFieldsList: managerDataDict[field] = modifyValues[index]
            index += 1

        #update
        self._store.update(wuid,dataDict)
        self._managerStore.update(wuid,managerDataDict)

    def getWorkUnitIdByExecutePid(self, pid):
        """Return the most recent work unit id of the pid passed.  Otherwise returns None."""
        return self._getRecentWorkUnitIdFromPid('executePid',pid)

    def getWorkUnitIdByManagerPid(self, pid):
        """Return the most recent work unit id of the manager pid passed.  Otherwise returns None."""
        return self._getRecentWorkUnitIdFromPid('managerPid',pid)

    def getAllByWorkUnitId(self, wuid):
        """Return a list of all fields belonging to the wuid.  Return [digest,owner,status,type,
        call,args,stageFiles,workDir,entryTime,startTime,endTime,result,exceptionMessage,
        postExecutionResults, cancelFlag, executePid, managerPid].
        """
        return self.getValueByWorkUnitId(wuid,workUnitStoreFieldsList)

    def getDigest(self,wuid):
        """Return the digest of a wuid."""
        return self.getValueByWorkUnitId(wuid,'digest')

    def setDigest(self, wuid, digest):
        """Set the digest for a wuid."""
        self._modifyByWorkUnitId(wuid,['digest'],[digest])

    def getOwner(self, wuid):
        """Return the owner of a wuid."""
        return self.getValueByWorkUnitId(wuid,'owner')

    def setOwner(self, wuid, owner):
        """Set the ownder of a wuid."""
        self._modifyByWorkUnitId(wuid,['owner'],[owner])

    def getStatus(self, wuid):
        """Return the status of a wuid."""
        return self.getValueByWorkUnitId(wuid,'status')

    def setStatus(self, wuid, status):
        """Set the status of a wuid."""
        self._modifyByWorkUnitId(wuid,['status'],[status])

    def getType(self, wuid):
        """Return the type of a wuid."""
        return self.getValueByWorkUnitId(wuid,'type')

    def setType(self, wuid, type):
        """Set the type of a wuid."""
        self._modifyByWorkUnitId(wuid,['type'],[type])

    def getCall(self, wuid):
        """Return the call of a wuid."""
        return self.getValueByWorkUnitId(wuid,'call')

    def setCall(self, wuid, call):
        """Set the call of a wuid."""
        self._modifyByWorkUnitId(wuid,['call'],[call])

    def getArgs(self, wuid):
        """Return the args of a wuid."""
        return self.getValueByWorkUnitId(wuid,'args')

    def setArgs(self, wuid, args):
        """Set the args of a wuid."""
        self._modifyByWorkUnitId(wuid,['args'],[args])

    def getStageFiles(self, wuid):
        """Return the stage files of a wuid."""
        return self.getValueByWorkUnitId(wuid,'stageFiles')

    def setStageFiles(self, wuid, stageFiles):
        """Set the stage files of a wuid."""
        self._modifyByWorkUnitId(wuid,['stageFiles'],[stageFiles])

    def getWorkDir(self, wuid):
        """Return the work directory of a wuid."""
        return self.getValueByWorkUnitId(wuid,'workDir')

    def setWorkDir(self, wuid, workDir):
        """Set the work directory of a wuid."""
        self._modifyByWorkUnitId(wuid,['workDir'],[workDir])

    def getEntryTime(self, wuid):
        """Return the entry time of a wuid."""
        return self.getValueByWorkUnitId(wuid,'entryTime')

    def setEntryTime(self, wuid, entryTime):
        """Set entry time of the wuid."""
        self._modifyByWorkUnitId(wuid,['entryTime'],[entryTime])

    def getStartTime(self, wuid):
        """Return the start time of the wuid."""
        return self.getValueByWorkUnitId(wuid,'startTime')

    def setStartTime(self, wuid, startTime):
        """Set the start time of the wuid."""
        self._modifyByWorkUnitId(wuid,['startTime'],[startTime])

    def getEndTime(self, wuid):
        """Return the end time of the wuid."""
        return self.getValueByWorkUnitId(wuid,'endTime')

    def setEndTime(self, wuid, endTime):
        """Set the end time of the wuid."""
        self._modifyByWorkUnitId(wuid,['endTime'],[endTime])

    def getResult(self, wuid):
        """Return the result of the wuid."""
        return self.getValueByWorkUnitId(wuid,'result')

    def setResult(self, wuid, result):
        """Set the result of the wuid."""
        self._modifyByWorkUnitId(wuid,['result'],[result])

    def getExceptionMessage(self, wuid):
        """Return the exception message of the wuid."""
        return self.getValueByWorkUnitId(wuid,'exceptionMessage')

    def setExceptionMessage(self, wuid, exceptionMessage):
        """Set the exception message of the wuid."""
        self._modifyByWorkUnitId(wuid,['exceptionMessage'],[exceptionMessage])

    def getPostExecutionResults(self, wuid):
        """Return the post execution results of the wuid."""
        return self.getValueByWorkUnitId(wuid,'postExecutionResults')

    def setPostExecutionResults(self, wuid, postExecutionResults):
        """Set the post execution results of the wuid."""
        self._modifyByWorkUnitId(wuid,['postExecutionResults'],[postExecutionResults])

    def getCancelFlag(self, wuid):
        """Return the cancel flag of the wuid."""
        return self.getValueByWorkUnitId(wuid,'cancelFlag')

    def setCancelFlag(self, wuid, cancelFlag):
        """Set the cancel flag of the wuid."""
        self._modifyByWorkUnitId(wuid,['cancelFlag'],[cancelFlag])

    def getExecutePid(self, wuid):
        """Return the execution pid of the wuid."""
        return self.getValueByWorkUnitId(wuid,'executePid')

    def setExecutePid(self, wuid, executePid):
        """Set the execute pid of the wuid."""
        self._modifyByWorkUnitId(wuid,['executePid'],[executePid])

    def getManagerPid(self, wuid):
        """Return the manager pid of the wuid."""
        return self.getValueByWorkUnitId(wuid,'managerPid')

    def setManagerPid(self, wuid, managerPid):
        """Set the manager pid of the wuid."""
        self._modifyByWorkUnitId(wuid,['managerPid'],[managerPid])

    def getTracebackMessage(self, wuid):
        """Return the traceback message of the wuid."""
        return self.getValueByWorkUnitId(wuid,'tracebackMessage')

    def setTracebackMessage(self, wuid, tracebackMessage):
        """Set the traceback message of the wuid."""
        self._modifyByWorkUnitId(wuid,['tracebackMessage'],[tracebackMessage])

    def getExecutionLog(self, wuid):
        """Return the execution loge of the wuid."""
        return self.getValueByWorkUnitId(wuid,'executionLog')

    def setExecutionLog(self, wuid, executionLog):
        """Set the execution log of the wuid."""
        self._modifyByWorkUnitId(wuid,['executionLog'],[executionLog])
        
    def getValueByDigest(self, digest, field):
        """Return the value of a field in the store by work unit id.
        Resolve any cached entries to their values.
        """
        
        #get wu config id
        wuIdList = self._managerStore.query('digest', digest, 'wuid')
        
        #loop over and accumulate results
        retList = []
        for wuIds in wuIdList:
            if len(wuIds) != 1:
                raise WorkUnitStoreHandlerError("Cannot handle number of wuIds found: %s" % wuIds)
            retList.append(self.getValueByWorkUnitId(wuIds[0], field))
        return retList

#schedule store fields
#These args are what gets passed to addAndExecuteWorkUnit():
#(owner,type,call,args,stageFiles=None,postExecutionTypeList=None,
#                          timeout=86400,callbackConfig=None,configFile=None)
scheduleStoreFieldsList = ['wuConfigId','scifloid','index','procId','executeNodeProtocol',
                           'executeNodeAddr','executeNodePort','executeNodeNamespace',
                           'wuid','digest','status','owner','type','call','args','stageFiles',
                           'postExecutionTypeList','timeout','entryTime','finishedTime',
                           'result','exceptionMessage','postExecutionResults',
                           'cancelFlag','resolvedFlag','tracebackMessage','implicitFlag',
                           'executionLog','workDir']

#schedule manager store fields
scheduleManagerStoreFieldsList = ['wuConfigId','scifloid','wuid','digest']

class ScheduleStoreHandlerError(Exception):
    """Exception class for ScheduleStoreHandler class."""
    pass

class ScheduleStoreHandler(object):
    """ScheduleStoreHandler base class."""

    def __init__(self, storeConfig):
        """Constructor."""

        #make sure storeConfig is StoreConfig
        if not isinstance(storeConfig, StoreConfig):
            raise ScheduleStoreHandlerError("Must specify a StoreConfig object.")

        #set attributes
        self._storeConfig = storeConfig
        self._storeClass = self._storeConfig.getStoreClass()
        self._storeName = self._storeConfig.getStoreName()
        self._storeFieldsList = self._storeConfig.getStoreFieldsList()
        self._storeArgs = self._storeConfig.getStoreArgs()
        self._storeKargs = self._storeConfig.getStoreKargs()

        #create manager store
        args = [self._storeName,  scheduleManagerStoreFieldsList]
        args.extend(self._storeArgs)
        self._managerStore = self._storeClass(*args)
        self._store = None
        self._cachedStore = None
    
    def setStore(self, wuConfigId, cachedStore=False):
        #create store
        if wuConfigId is None: return None
        args = [self._storeName,  self._storeFieldsList]
        dbHome = os.path.join(self._storeArgs[0], 'wuConfigIdStores', wuConfigId)
        validateDirectory(dbHome, noExceptionRaise=True)
        args.append(dbHome)
        args.extend(self._storeArgs[1:])
        if cachedStore: self._cachedStore = self._storeClass(*args)
        else: self._store = self._storeClass(*args)
        return True

    def queryUnique(self, queryField, queryValue, returnField=None, dataStore=False, cachedStore=False):
        """Return the field values of a field matching.  If no return fields are specified,
        it just returns the value of field.  If a single return field is specified, the
        result is a single value.  If a list of return fields is specified, result is a
        list corresponding to that list.  This is where the actual implementation
        of the query is defined.
        """
        if dataStore:
            if cachedStore:
                return self._cachedStore.queryUnique(queryField, queryValue, returnField)
            else:
                return self._store.queryUnique(queryField, queryValue, returnField)
        else:
            return self._managerStore.queryUnique(queryField, queryValue, returnField)

    def addWorkUnitConfig(self, wuConfigId, scifloId, wuIndex, procId, executeNodeProtocol,
                    executeNodeAddr, executeNodePort,executeNodeNamespace,
                    wuId, wuConfigDigest, status, owner, wuType, wuCall, wuArgs,
                    stageFiles, postExecutionTypeList, timeout, entryTime, finishedTime,
                    result, exceptionMessage, postExecutionResults, cancelFlag, resolvedFlag,
                    tracebackMessage, implicitFlag, executionLog, workDir):
        """Add a new entry into the work unit schedule store."""

        #check that wuConfigId is not here already
        if self.isWorkUnitConfigIdHere(wuConfigId):
            raise ScheduleStoreHandlerError("Work unit config id %s is already in the store." % wuConfigId)

        #add
        self._managerStore.add(wuConfigId, scifloId, wuId, wuConfigDigest)
        self.setStore(wuConfigId)
        self._store.add(wuConfigId, scifloId, wuIndex, procId, executeNodeProtocol,
                    executeNodeAddr, executeNodePort,executeNodeNamespace,
                    wuId, wuConfigDigest, status, owner, wuType, wuCall, wuArgs,
                    stageFiles, postExecutionTypeList, timeout, entryTime, finishedTime,
                    result, exceptionMessage, postExecutionResults, cancelFlag, resolvedFlag,
                    tracebackMessage, implicitFlag, executionLog, workDir)

    def removeWorkUnitConfig(self, wuConfigId):
        """Remove an entry(record) from the work unit schedule store."""

        #check that wuConfigId is not here already
        if not self.isWorkUnitConfigIdHere(wuConfigId):
            raise ScheduleStoreHandlerError("Work unit config id %s is not already in the store." % wuConfigId)

        #remove
        self._managerStore.remove(wuConfigId)
        self.setStore(wuConfigId)
        self._store.remove(wuConfigId)

    def getValueByWorkUnitConfigId(self, wuConfigId, field):
        """Return the value of a field in the store by work unit config id.
        Resolve any cached entries to their values.
        """
        
        #if work unit config is here, check if it was cached by checking digest
        if self.isWorkUnitConfigIdHere(wuConfigId):
            #set store
            self.setStore(wuConfigId)

            #get digest and status
            digest, status = self.queryUnique('wuConfigId', wuConfigId, ['digest', 'status'], dataStore=True)

            #print "digest,status:",digest,status
            #if it is a sciflowuid, it is cached
            fields = getListFromUnknownObject(field)
            if digest is not None and re.search(r'^workunitconfigid-', digest) and status == cachedStatus:
                self.setStore(digest, cachedStore=True)
                if len(fields) == 1:
                    if fields[0] in cachedFields: return self.queryUnique('wuConfigId', digest, fields[0],
                                                                          dataStore=True,
                                                                          cachedStore=True)
                    else: return self.queryUnique('wuConfigId', wuConfigId, fields[0], dataStore=True)
                else:
                    cFields = []
                    dFields = []
                    for f in fields:
                        if f in cachedFields: cFields.append(f)
                        else: dFields.append(f)
                    cResults = getListFromUnknownObject(self.queryUnique('wuConfigId', digest, cFields,
                                                                         dataStore=True,
                                                                         cachedStore=True))
                    dResults = getListFromUnknownObject(self.queryUnique('wuConfigId', wuConfigId, dFields,
                                                                         dataStore=True))
                    results = []
                    for f in fields:
                        if f in cFields: results.append(cResults[cFields.index(f)])
                        elif f in dFields: results.append(dResults[dFields.index(f)])
                        else: raise ScheduleStoreHandlerError("Cannot find field %s in results." % f)
                        
                    return results

            #otherwise return the value from this work unit
            else:
                if len(fields) == 1: return self.queryUnique('wuConfigId', wuConfigId, fields[0],
                                                             dataStore=True)
                else: return self.queryUnique('wuConfigId', wuConfigId, fields, dataStore=True)

        #if not here return None
        else: return None
        
    def getValueByWorkUnitId(self, wuid, field):
        """Return the value of a field in the store by work unit config id.
        Resolve any cached entries to their values.
        """
        
        #get wu config id
        wuConfigId = self.queryUnique('wuid',wuid,'wuConfigId')
        
        return self.getValueByWorkUnitConfigId(wuConfigId, field)
    
    def getValueByDigest(self, digest, field):
        """Return the value of a field in the store by work unit config id.
        Resolve any cached entries to their values.
        """
        
        #get wu config id
        wuConfigIdList = self._managerStore.query('digest', digest, 'wuConfigId')
        
        #loop over and accumulate results
        retList = []
        for wuConfigIds in wuConfigIdList:
            if len(wuConfigIds) != 1:
                raise ScheduleStoreHandlerError("Cannot handle number of wuConfigIds found: %s" % wuConfigIds)
            retList.append(self.getValueByWorkUnitConfigId(wuConfigIds[0], field))
        return retList
    
    def isWorkUnitConfigIdHere(self,wuConfigId):
        """Return 1 if wuConfigId is in store.  Otherwise, None."""
        return self.queryUnique('wuConfigId',wuConfigId)

    def _modifyByWorkUnitConfigId(self, wuConfigId, modifyFields, modifyValues):
        """Modify a work unit config record by its id.
        """
        
        #make data dict
        dataDict = {}
        managerDataDict = {}
        index = 0
        for field in modifyFields:
            dataDict[field] = modifyValues[index]
            if field in scheduleManagerStoreFieldsList: managerDataDict[field] = modifyValues[index]
            index += 1

        #update
        self.setStore(wuConfigId)
        self._store.update(wuConfigId,dataDict)
        self._managerStore.update(wuConfigId,managerDataDict)

    def _modifyByWorkUnitId(self, wuid, modifyFields, modifyValues):
        """Modify a work unit config record by its work unit id.
        """

        #get wu config id
        wuConfigId = self.queryUnique('wuid',wuid,'wuConfigId')

        return self._modifyByWorkUnitConfigId(wuConfigId, modifyFields, modifyValues)

    def getStatus(self, wuConfigId):
        """Return the status of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'status')
    
    def getStatusByWuid(self, wuid):
        """Return the status of a wuid."""
        return self.getValueByWorkUnitId(wuid,'status')

    def setStatus(self, wuConfigId, status):
        """Set the status of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['status'],[status])

    def setStatusByWuid(self, wuid, status):
        """Set the status of a wuid."""
        self._modifyByWorkUnitId(wuid,['status'],[status])

    def getExecuteNodeInfo(self, wuConfigId):
        """Return the list of execute node information: protocol, host address,
        port, namespace.
        """

        #get values
        protocol = self.getValueByWorkUnitConfigId(wuConfigId, 'executeNodeProtocol')
        addr = self.getValueByWorkUnitConfigId(wuConfigId, 'executeNodeAddr')
        port = self.getValueByWorkUnitConfigId(wuConfigId, 'executeNodePort')
        ns = self.getValueByWorkUnitConfigId(wuConfigId, 'executeNodeNamespace')

        #return
        return (protocol, addr, port, ns)

    def getArgs(self, wuConfigId):
        """Return the args of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'args')

    def setArgs(self, wuConfigId, args):
        """Set the args of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['args'],[args])

    def getWorkUnitConfigIdByScifloAndProcIds(self, scifloId, procId):
        """Return the workUnitConfigId by scifloid and procid."""

        #get wu config id
        wuConfigIdList = self._managerStore.query('scifloid', scifloId, 'wuConfigId')
        
        #loop over and find matching procId
        for wuConfigIds in wuConfigIdList:
            if len(wuConfigIds) != 1:
                raise ScheduleStoreHandlerError("Cannot handle number of wuConfigIds found: %s" % wuConfigIds)
            thisProcId = self.getValueByWorkUnitConfigId(wuConfigIds[0], ['procId'])
            if procId == thisProcId: return wuConfigIds[0]
            
        raise ScheduleStoreHandlerError("Cannot find procId %s in scifloid %s." % (procId, scifloId))

    def getScifloidInfo(self, scifloId, fields):
        """Return sorted list of dicts containing field info.  Sorted by
        process number in sciflo.
        """

        #fields
        fields = getListFromUnknownObject(fields)

        #append procNum automatically if not in there already
        fields.insert(0,'index')

        #get wuConfigIds
        wuConfigIdList = self._managerStore.query('scifloid', scifloId, 'wuConfigId')
        
        #loop over and build result list
        retList = []
        for wuConfigIds in wuConfigIdList:
            if len(wuConfigIds) != 1:
                raise ScheduleStoreHandlerError("Cannot handle number of wuConfigIds found: %s" % wuConfigIds)
            retList.append(self.getValueByWorkUnitConfigId(wuConfigIds[0], fields))

        #sort
        retList.sort()

        #loop over create dict and set order
        newList = []
        for ret in retList:
            retDict = {}
            for i in range(1,len(fields)):
                fname = fields[i]
                val = ret[i]
                retDict[fname] = val
            newList.append(retDict)

        #return
        return newList

    def getPostExecutionResults(self, wuConfigId):
        """Return the postExecutionResults of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'postExecutionResults')

    def setPostExecutionResults(self, wuConfigId, postExecutionResults):
        """Set the postExecutionResults of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['postExecutionResults'],[postExecutionResults])

    def getResult(self, wuConfigId):
        """Return the result of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'result')

    def setResult(self, wuConfigId, result):
        """Set the result of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['result'],[result])

    def getResolvedFlag(self, wuConfigId):
        """Return the resolved flag of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'resolvedFlag')

    def setResolvedFlag(self, wuConfigId, resolvedFlag):
        """Set the resolved flag of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['resolvedFlag'],[resolvedFlag])

    def getExceptionMessage(self, wuConfigId):
        """Return the exception message of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'exceptionMessage')

    def setExceptionMessage(self, wuConfigId, exceptionMessage):
        """Set the exception message of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['exceptionMessage'],[exceptionMessage])

    def getOwner(self, wuConfigId):
        """Return the owner of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'owner')

    def getType(self, wuConfigId):
        """Return the type of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'type')

    def getCall(self, wuConfigId):
        """Return the call of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'call')

    def getStageFiles(self, wuConfigId):
        """Return the stage files of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'stageFiles')

    def getPostExecutionTypeList(self, wuConfigId):
        """Return the list of post execution types of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'postExecutionTypeList')

    def getTimeout(self, wuConfigId):
        """Return the timeout of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'timeout')

    def getTracebackMessage(self, wuConfigId):
        """Return the traceback message of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'tracebackMessage')

    def setTracebackMessage(self, wuConfigId, tracebackMessage):
        """Set the traceback message of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['tracebackMessage'],[tracebackMessage])

    def getProcId(self, wuConfigId):
        """Return the process id of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'procId')

    def getWuid(self, wuConfigId):
        """Return the wuid of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'wuid')

    def setWuid(self, wuConfigId, wuid):
        """Set the wuid of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['wuid'],[wuid])

    def getImplicitFlag(self, wuConfigId):
        """Return the implicit flag of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'implicitFlag')

    def setImplicitFlag(self, wuConfigId, implicitFlag):
        """Set the implicit flag of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['implicitFlag'],[implicitFlag])

    def getExecutionLog(self, wuConfigId):
        """Return the execution log of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'executionLog')

    def setExecutionLog(self, wuConfigId, executionLog):
        """Set the execution log of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['executionLog'],[executionLog])

    def getIndex(self, wuConfigId):
        """Return the index of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'index')

    def getWorkUnitConfigIdByDigest(self, digest):
        """Return work unit config id of the hex digest passed.  Otherwise returns None."""

        wuid = self.queryUnique('digest', digest, 'wuConfigId')
        self.setStore(wuid)
        return wuid
    
    def getDigest(self, wuConfigId):
        """Return the digest of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'digest')

    def setDigest(self, wuConfigId, digest):
        """Set the digest of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['digest'],[digest])

    def getWorkDir(self, wuConfigId):
        """Return the workDir of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'workDir')

    def setWorkDir(self, wuConfigId, workDir):
        """Set the workDir of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['workDir'],[workDir])

    def getEntryTime(self, wuConfigId):
        """Return the entryTime of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'entryTime')

    def setEntryTime(self, wuConfigId, entryTime):
        """Set the entryTime of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['entryTime'],[entryTime])

    def getFinishedTime(self, wuConfigId):
        """Return the finishedTime of a wuConfigId."""
        return self.getValueByWorkUnitConfigId(wuConfigId,'finishedTime')

    def setFinishedTime(self, wuConfigId, finishedTime):
        """Set the finishedTime of a wuConfigId."""
        self._modifyByWorkUnitConfigId(wuConfigId,['finishedTime'],[finishedTime])