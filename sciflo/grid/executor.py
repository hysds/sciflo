import errno
import os
import time
import gc
import logging
import types
import lxml
import threading
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import copy
import multiprocessing
import multiprocessing.pool
import pickle as pickle
from socket import getfqdn
from getpass import getuser

from sciflo.utils import (validateDirectory, linkFile, UrlBaseTracker, isUrl,
                          getXmlEtree, isXml, send_email)
from sciflo.event.pdict import PersistentDict
from .utils import (normalizeScifloArgs, generateScifloId, runLockedFunction,
                    getTb, runFuncWithRetries, updatePdict, linkResult, updateJson,
                    publicizeResultFiles, getAbsPathForResultFiles, statusUpdateJson)
from .postExecution import PostExecutionHandler
from .doc import Sciflo, UnresolvedArgument, WorkUnitConfig, DocumentArgsList
from .funcs import (getWorkUnit, executeWorkUnit, workUnitInfo, CancelledWorkUnit,
                    DEBUG_PROCESSING, LOG_FMT)
from .status import *
from .annotatedDoc import AnnotatedDoc
from .config import GridServiceConfig

SCIFLO_INFO_FIELDS = ['scifloid', 'scifloName', 'call', 'args', 'workDir',
                      'startTime', 'endTime', 'result', 'exceptionMessage',
                      'status', 'pid', 'procIds', 'procIdWuidMap', 'outputDir',
                      'outputUrl', 'jsonFile', 'svgFile', 'executionLog']

STRINGIFY_FIELDS = ['exceptionMessage']

PICKLE_FIELDS = ['result', 'unpublicizedResult']

SCIFLO_PUBLICIZE_FIELDS = ['jsonFile', 'workDir',
                           'outputDir', 'svgFile', 'executionLog']

WORK_UNIT_PUBLICIZE_FIELDS = ['stageFiles', 'workDir', 'executionLog']


def scifloInfo(info=None, **kargs):
    """Wrapper function to return new workUnitInfo dict or modify existing one.
    """

    if info is None:
        info = {}
        for f in SCIFLO_INFO_FIELDS:
            info[f] = kargs.get(f, None)
    else:
        for f in kargs:
            if f in SCIFLO_INFO_FIELDS:
                info[f] = kargs[f]
    return info


class WuReady(object):
    def __init__(self, val): self.val = val


class PostExecResult(object):
    def __init__(self, val): self.val = val


class NoResult(object):
    pass


def waiter(event): event.wait()


class NoDaemonProcess(multiprocessing.Process):
    @property
    def daemon(self):
        return False

    @daemon.setter
    def daemon(self, value):
        pass


class NoDaemonContext(type(multiprocessing.get_context())):
    Process = NoDaemonProcess

# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.


class ScifloPool(multiprocessing.pool.Pool):
    def __init__(self, *args, **kwargs):
        kwargs['context'] = NoDaemonContext()
        super(ScifloPool, self).__init__(*args, **kwargs)


class ScifloExecutorError(Exception):
    pass


class ScifloExecutor(object):
    """Execution engine for sciflo."""

    def __init__(self, sflString, args={}, workers=4, workerTimeout=None,
                 logLevel=logging.DEBUG, workDir=None,
                 cacheName="WorkUnitCache", outputDir=None, scifloid=None,
                 publicize=False, configFile=None, lookupCache=True,
                 configDict={}, writeGraph=True, statusUpdateFunc=None,
                 emailNotify=None, outputUrl=None):
        """Constructor."""

        import multiprocessing as mp

        self.sflString = sflString
        self.args = normalizeScifloArgs(args)
        if isinstance(self.args, dict):
            self.sciflo = Sciflo(self.sflString, globalInputDict=self.args)
        elif isinstance(self.args, (list, tuple)):
            self.sciflo = Sciflo(self.sflString, self.args)
        else:
            raise ScifloExecutorError("Unrecognized type for args: %s" %
                                      type(self.args))
        self.sciflo.resolve()
        self.scifloName = self.sciflo.getName()
        self.wuConfigs = self.sciflo.getWorkUnitConfigs()
        if scifloid is None:
            self.scifloid = generateScifloId()
        else:
            self.scifloid = scifloid
        self.manager = mp.Manager()
        self.procIds = []
        self.applyResultsDict = {}
        self.resultsDict = {}
        self.postExecResultsDict = {}
        self.doneDict = {}
        self.executionError = None
        if workers > 50:
            raise ScifloExecutorError("Cannot specify workers > 50.")
        self.workers = workers
        self.pool = ScifloPool(self.workers)
        self.configDict = configDict
        #self.lock = self.manager.RLock()
        self.lock = threading.RLock()
        self.event = self.manager.Event()
        self.waiterProcess = mp.Process(target=waiter, name="waiter",
                                        args=[self.event])
        self.logLevel = logLevel
        if DEBUG_PROCESSING:
            self.logger = mp.process.getLogger()
        else:
            self.logger = logging.getLogger(self.scifloName)
        self.logger.setLevel(self.logLevel)
        self.pid = os.getpid()
        self.writeGraph = writeGraph
        self.statusUpdateFunc = statusUpdateFunc
        self.emailNotify = emailNotify

        # config file and GridServiceConfig
        self.configFile = configFile
        self.gsc = GridServiceConfig(self.configFile)

        # set worker timeout from config file and override
        self.workerTimeout = workerTimeout
        if self.workerTimeout is None:
            self.workerTimeout = self.gsc.getWorkerTimeout()

        # sciflo work dir
        if workDir is None:
            workDir = self.gsc.getWorkUnitWorkDir()
        self.workDir = os.path.abspath(workDir)
        validateDirectory(self.workDir)

        # sciflo output dir
        self.outputDir = outputDir
        if self.outputDir is None:
            self.outputDir = os.path.join(self.workDir, self.scifloid)
        validateDirectory(self.outputDir)
        self.outputUrl = outputUrl

        # send logging messages to an execution log also (in addition to console)
        self.logFile = os.path.join(self.outputDir, 'sfl_execution.log')
        fh = logging.FileHandler(self.logFile)
        fh.setLevel(self.logLevel)
        fh.setFormatter(logging.Formatter(LOG_FMT))
        self.logger.addHandler(fh)

        # cache related attrs
        self.cacheName = cacheName
        self.lookupCache = lookupCache
        if self.cacheName is None:
            self.pdict = None
        else:
            try:
                self.pdict = PersistentDict(self.cacheName, pickleVals=True)
            except Exception as e:
                self.logger.debug("Got exception trying to get PersistentDict \
for sciflo '%s': %s.  No cache will be used." % (self.scifloName, e),
                                  extra={'id': self.scifloid})
                self.cacheName = None
                self.pdict = None
        self.hexDict = {}

        # annotated doc
        self.annDoc = AnnotatedDoc(self.sciflo, self.outputDir)

        # json file
        self.jsonFile = os.path.join(self.outputDir, 'sciflo.json')

        # svgfile
        self.svgFile = os.path.join(self.outputDir, 'scifloGraph.svg')
        if self.writeGraph:
            self.sciflo.writeGraph(self.svgFile)

        # configFile, publicize, grid service config, base url and url base
        # tracker
        self.publicize = publicize
        self.baseUrl = self.gsc.getBaseUrl()
        if self.baseUrl is None:
            if self.publicize:
                self.baseUrl = self.gsc.getGridBaseUrl()
            else:
                self.baseUrl = "file://%s%s" % (getfqdn(), self.workDir)
        self.ubt = UrlBaseTracker(self.workDir, self.baseUrl)
        if self.publicize:
            self.publicizeUbt = self.ubt
        else:
            self.publicizeUbt = None

        # sciflo procId->wuid map
        self.procIdWuidMap = {}

        # build deferred ids, dict, and results dict
        for w in self.wuConfigs:
            procId = w.getId()

            # check if all args are resolved
            resolved = self.resolveArgs(w)

            # if all args are resolved, get work unit
            if resolved:
                self.hexDict[procId] = w.getHexDigest()
                try:
                    wu = getWorkUnit(w, configFile=self.configFile,
                                     configDict=self.configDict)
                except Exception as e:
                    raise ScifloExecutorError("Encountered error calling \
getWorkUnit(): %s\n%s" % (str(e), getTb()))
                wuid = wu.getWuid()
                appRes = WuReady(wu)
                # update info in work unit json for monitoring
                updateJson(wu.getJsonFile(), wu.getInfo(),
                           stringifyKeys=STRINGIFY_FIELDS, ubt=self.publicizeUbt,
                           publicizeKeys=WORK_UNIT_PUBLICIZE_FIELDS,
                           pickleKeys=PICKLE_FIELDS)
                self.updateStatus('WorkUnit status for "%s": %s' %
                                  (procId, readyStatus), wu.getInfo())
            else:
                wuid = None
                appRes = w
                self.updateStatus('WorkUnit status for "%s": %s' %
                                  (procId, waitingStatus), wu.getInfo())
            self.procIdWuidMap[procId] = wuid
            self.procIds.append(procId)
            self.applyResultsDict[procId] = appRes
            self.resultsDict[procId] = NoResult()
            self.postExecResultsDict[procId] = w.getPostExecutionTypeList()

        self.output = self.sciflo.getFlowOutputConfigs()

        # sciflo info
        self.scifloInfo = scifloInfo(None, scifloid=self.scifloid,
                                     scifloName=self.scifloName,
                                     call=self.sflString,
                                     args=self.args, workDir=self.workDir,
                                     status=sentStatus, pid=self.pid,
                                     procIds=self.procIds,
                                     procIdWuidMap=self.procIdWuidMap,
                                     outputDir=self.outputDir,
                                     jsonFile=self.jsonFile,
                                     svgFile=self.svgFile,
                                     executionLog=self.logFile)

        # update json
        updateJson(self.jsonFile, self.scifloInfo,
                   stringifyKeys=STRINGIFY_FIELDS,
                   ubt=self.publicizeUbt, publicizeKeys=SCIFLO_PUBLICIZE_FIELDS,
                   pickleKeys=PICKLE_FIELDS)

    def updateStatus(self, message, info):
        """Update status via WebSockets."""

        if self.statusUpdateFunc:
            self.statusUpdateFunc(message,
                                  statusUpdateJson(info,
                                                   ['exceptionMessage',
                                                    'result',
                                                    'unpublicizedResult']))

    def updateScifloInfo(self, **kargs):
        """Update sciflo info, pdict, and json file."""

        self.scifloInfo = scifloInfo(self.scifloInfo, **kargs)
        updateJson(self.jsonFile, self.scifloInfo,
                   stringifyKeys=STRINGIFY_FIELDS,
                   ubt=self.publicizeUbt, publicizeKeys=SCIFLO_PUBLICIZE_FIELDS,
                   pickleKeys=PICKLE_FIELDS)

    def resolveArgs(self, wuConfig):
        """Resolve all args of a work unit."""

        argsList = wuConfig.getArgs()
        if isinstance(argsList, DocumentArgsList):
            newArgsList = DocumentArgsList(argsList.docStr)
        else:
            newArgsList = []
        unresolvedArgsCount = 0

        for arg in argsList:
            # resolve document types in arg list if argsList is itself not a
            # document type
            if isinstance(arg, DocumentArgsList) and \
                    not isinstance(argsList, DocumentArgsList):
                newArgsList2 = DocumentArgsList(arg.docStr)
                unresolvedArgsCount2 = 0

                for arg2 in arg:
                    if isinstance(arg2, UnresolvedArgument):
                        newArg2 = self.resolveArg(arg2)

                        # If it is still an UnresolvedArgument instance,
                        # put it back
                        if isinstance(newArg2, NoResult):
                            unresolvedArgsCount2 += 1
                        else:
                            pass
                        newArgsList2.append(newArg2)
                    else:
                        newArgsList2.append(arg2)
                if unresolvedArgsCount2 == 0:
                    arg = self.resolveDocumentInput(wuConfig, newArgsList2)[-1]
                else:
                    arg = newArgsList2
                    unresolvedArgsCount += 1

            # resolve unresolved arg
            if isinstance(arg, UnresolvedArgument):
                newArg = self.resolveArg(arg)

                # If it is still an UnresolvedArgument instance, put it back
                if isinstance(newArg, NoResult):
                    unresolvedArgsCount += 1
                else:
                    pass
                newArgsList.append(newArg)
            else:
                newArgsList.append(arg)

        isResolved = False
        if unresolvedArgsCount == 0:
            if isinstance(newArgsList, DocumentArgsList):
                newArgsList = self.resolveDocumentInput(wuConfig, newArgsList)
            isResolved = True
            wuConfig._args = newArgsList
        return isResolved

    def resolveArg(self, unresArg):
        """Resolve unresolved argument."""

        try:
            # resolving id
            resolvingId = unresArg.getId()

            # get result
            resolvingRes = self.resultsDict[resolvingId]
            if isinstance(resolvingRes, NoResult):
                return resolvingRes

            # get post exec result
            if unresArg.getOutputFromPostExecution():
                resolvingIdx = unresArg.getPostExecutionOutputIndex()
                resolvingRes = \
                    self.postExecResultsDict[resolvingId][resolvingIdx]
            # just use result
            else:
                resolvingIdx = unresArg.getOutputIndex()
                if resolvingIdx is not None:
                    resolvingRes = self.resultsDict[resolvingId][resolvingIdx]

            # file rewrite?
            rewriteFile = unresArg.getRewriteFile()
            if rewriteFile:
                if os.sep in rewriteFile:
                    rewriteFile = os.path.basename(rewriteFile)
                rewriteFile = os.path.join(self.outputDir, rewriteFile)
                if isUrl(resolvingRes) or os.path.exists(str(resolvingRes)):
                    try:
                        localPath = self.ubt.getLocalPath(resolvingRes)
                    except:
                        localPath = None

                    # if local, rewrite in same directory
                    if localPath:
                        rewriteFile = os.path.join(os.path.dirname(localPath),
                                                   rewriteFile)
                        linkFile(localPath, rewriteFile)

                    # else copy to sciflo output dir
                    else:
                        rewriteFile = os.path.join(self.outputDir, rewriteFile)
                        urllib.request.urlretrieve(resolvingRes, rewriteFile)

                    # publicize?
                    if self.publicize:
                        resolvingRes = self.ubt.getUrl(rewriteFile)
                    else:
                        resolvingRes = rewriteFile
                else:
                    open(rewriteFile, 'w').write("%s\n" % str(resolvingRes))
                resolvingRes = rewriteFile
            return resolvingRes
        except Exception as e:
            self.logger.debug("Got error in resolveArg() method for '%s' in \
sciflo '%s': %s\n%s" % (resolvingId, self.scifloName, str(e), getTb()),
                extra={'id': self.scifloid})
            raise

    def resolveDocumentInput(self, wuConfig, docArgList):
        """Resolve process input doc and return new args list."""

        def addCDATAPlaceholders(txt):
            return "CDATA_BEGIN_PLACEHOLDER%sCDATA_END_PLACEHOLDER" % txt

        def replaceCDATAPlaceholders(txt):
            return txt.replace(
                'CDATA_BEGIN_PLACEHOLDER', '<![CDATA[').replace(
                'CDATA_END_PLACEHOLDER', ']]>').replace(
                '<CDATA_TPL>', '<![CDATA[').replace(
                '</CDATA_TPL>', ']]>').replace(
                '&amp;', '&')
        inputsElt, inputsNsDict = getXmlEtree(docArgList.docStr)
        wuType = wuConfig.getType()
        if wuType in ('soap', 'post'):
            argIdx = 1
        else:
            argIdx = 0
        for elt in inputsElt.getiterator():
            if docArgList[argIdx] is not None:
                format = elt.get('format', None)
                eltTxt = str(docArgList[argIdx])
                # interpolate CDATA
                if format == 'CDATA':
                    if isXml(eltTxt):
                        eltChild, eltNs = getXmlEtree(eltTxt)
                        cdataBlockElt = lxml.etree.SubElement(elt, 'CDATA_TPL')
                        cdataBlockElt.append(eltChild)
                        eltTxt = None
                        cdataBlockElt.text = None
                    else:
                        eltTxt = addCDATAPlaceholders(eltTxt)
                else:
                    # interpolate xml element
                    if isXml(eltTxt):
                        # create elt tree and append as child
                        eltChild, eltNs = getXmlEtree(eltTxt)
                        elt.append(eltChild)
                        eltTxt = None
                    # interpolate xml fragment
                    else:
                        tmpXml = '<tmp>%s</tmp>' % eltTxt
                        if isXml(tmpXml):
                            eltChild, eltNs = getXmlEtree(tmpXml)
                            eltChildKids = eltChild.getchildren()
                            if len(eltChildKids) == 0:
                                pass  # no children to add
                            else:
                                for i in eltChild.getchildren():
                                    elt.append(i)
                                eltTxt = None
                        # interpolate string
                        else:
                            pass
                elt.text = eltTxt
                if elt.get('from', None):
                    del elt.attrib['from']
                if format:
                    del elt.attrib['format']
            argIdx += 1
        docList = [replaceCDATAPlaceholders(
            lxml.etree.tostring(i, pretty_print=True, encoding='unicode')) for i in inputsElt]
        doc = '\n'.join(docList)
        if wuType in ('soap', 'post'):
            return [docArgList[0], doc]
        else:
            return [doc]

    def dispatchWorker(self, wu):
        """Dispatch workUnitWorker to execute work unit."""

        procId = wu.getProcId()
        wu.setInfoItem('status', sentStatus)
        updateJson(wu.getJsonFile(), wu.getInfo(),
                   stringifyKeys=STRINGIFY_FIELDS, ubt=self.publicizeUbt,
                   publicizeKeys=WORK_UNIT_PUBLICIZE_FIELDS,
                   pickleKeys=PICKLE_FIELDS)  # for monitoring
        self.updateStatus('WorkUnit status for "%s": %s' %
                          (procId, sentStatus), wu.getInfo())
        self.logger.debug("Dispatched workUnitWorker for '%s' in sciflo '%s'." %
                          (procId, self.scifloName),
                          extra={'id': self.scifloid})

        # link work unit work dir
        workDir = wu.getWorkDir()
        linkDir = os.path.join(self.outputDir, "%05d-%s" %
                               (wu.getInfoItem('procCount'), procId))
        try:
            linkFile(workDir, linkDir)
        except Exception as e:
            self.logger.debug("Got error trying to link work dir '%s' to '%s' \
for '%s' in sciflo '%s': %s\n%s" % (workDir, linkDir, procId, self.scifloName,
                                    str(e), getTb()), extra={'id': self.scifloid})

        # lookup cache?
        if self.lookupCache:
            cacheName = self.cacheName
        else:
            cacheName = None

        # get ApplyResult
        self.applyResultsDict[procId] = \
            executeWorkUnit(wu, self.pool, timeout=self.workerTimeout,
                            callback=self.callback, cacheName=cacheName,
                            cancelFlag=wu.getInfoItem('cancelFlag'))

        # add provenance info for workUnit execution started
        self.annDoc.addProcessStarted(wu.getProcId())

    def spawn(self):
        """Spawn starter work units."""

        import multiprocessing as mp

        # update sciflo info
        self.updateScifloInfo(startTime=time.time(), status=workingStatus)

        # go loop over ids
        for procId in self.procIds:
            # skip if not yet resolved
            if isinstance(self.applyResultsDict[procId],
                          (WorkUnitConfig, mp.pool.ApplyResult)):
                pass
            # execute work unit using pool
            elif isinstance(self.applyResultsDict[procId], WuReady):
                wu = self.applyResultsDict[procId].val
                self.dispatchWorker(wu)
            else:
                raise ScifloExecutorError("Unknown type for applyResultsDict \
item: %s" % type(self.applyResultsDict[procId]))
        self.logger.debug("Finished spawning starter work units for sciflo \
'%s'." % self.scifloName, extra={'id': self.scifloid})

    def execute(self):
        """Execute sciflo."""

        # add provenance info for startup
        self.annDoc.addScifloStarted(os.path.abspath(__file__))

        # spawn starters
        try:
            runLockedFunction(self.lock, self.spawn)
        except Exception as e:
            self.logger.debug("Got error running self.spawn() \
in runLockedFunction() for sciflo '%s': %s\n%s" %
                              (self.scifloName, str(e), getTb()),
                              extra={'id': self.scifloid})
            self.executionError = ('main', ScifloExecutorError(
                "Error spawning starter work units: %s" % str(e)), getTb())
            self.shutdown()
            return

        # block
        self.logger.debug("Waiting for work units to complete for sciflo \
'%s'..." % self.scifloName, extra={'id': self.scifloid})
        self.waiterProcess.start()
        self.waiterProcess.join()
        self.logger.debug("Finished waiting in sciflo '%s'." % self.scifloName,
                          extra={'id': self.scifloid})

        # add provenance info for shutdown
        self.annDoc.addScifloFinished()

        # shutdown
        self.shutdown()

    def shutdown(self):
        """Shutdown execution."""

        try:
            startTime = time.time()

            if self.executionError is not None:
                self.logger.debug("Calling terminate() for sciflo '%s'..." %
                                  self.scifloName, extra={'id': self.scifloid})
                self.pool.terminate()
                self.output = ScifloExecutorError("Error result for '%s': \
%s\n%s" % self.executionError)
                self.annDoc.addGlobalOutput(
                    None, self.output)  # write to global
                if isinstance(self.executionError[1], CancelledWorkUnit):
                    finalStatus = cancelledStatus
                else:
                    finalStatus = exceptionStatus
                self.executionError = list(
                    map(str, self.executionError))  # force str
            else:
                self.logger.debug("Calling close() for sciflo '%s'..." %
                                  self.scifloName, extra={'id': self.scifloid})
                finalStatus = doneStatus
            self.logger.debug("Calling join() for sciflo '%s'..." %
                              self.scifloName, extra={'id': self.scifloid})
            self.pool.close()
            self.pool.join()
            endTime = time.time()
            self.logger.debug("done.  Shutdown took %s seconds for sciflo \
'%s'." % ((endTime - startTime), self.scifloName), extra={'id': self.scifloid})

            # update sciflo info
            self.updateScifloInfo(endTime=time.time(), status=finalStatus,
                                  result=self.output,
                                  exceptionMessage=self.executionError)

            # write inidividual results to result files
            if isinstance(self.output, ScifloExecutorError):
                numOutputs = 1
            else:
                numOutputs = len(self.output)
            if numOutputs == 1:
                resFile = os.path.join(self.outputDir, 'workunit_result-0.txt')
                with open(resFile, 'w') as f:
                    f.write("%s\n" % self.output)
            else:
                for i in range(numOutputs):
                    resFile = os.path.join(self.outputDir,
                                           'workunit_result-%d.txt' % i)
                    with open(resFile, 'w') as f:
                        f.write("%s\n" % self.output[i])
        except OSError as oe:
            # When disk space fills up during the middle of a Sciflo run, catch it
            # here and return a non-0 exit code.
            self.logger.debug("Got OSError in shutdown() for sciflo '%s':%s\n%s" %
                              (self.scifloName, str(oe), getTb()),
                              extra={'id': self.scifloid})
            if oe.errno == errno.ENOSPC:
                os._exit(1)
            else:
                os._exit(0)

        except Exception as e:
            self.logger.debug("Got error in shutdown() for sciflo '%s':%s\n%s" %
                              (self.scifloName, str(e), getTb()),
                              extra={'id': self.scifloid})
            os._exit(0)

    def callback(self, callbackResult):
        """Callback for work unit execution."""
        try:
            runLockedFunction(self.lock, self.handle, callbackResult)
        except Exception as e:
            emessage = "Error running callback in runLockedFunction() for \
sciflo '%s':%s\n%s" % (self.scifloName, str(e), getTb())
            self.logger.debug(emessage, extra={'id': self.scifloid})
            self.executionError = ('callback', ScifloExecutorError(emessage),
                                   getTb())
            try:
                runFuncWithRetries(5, self.event.set)
            except Exception as e:
                emessage = "Got error setting event from callback() exception \
in sciflo '%s': %s\n%s" % (self.scifloName, str(e), getTb())
                self.logger.debug(emessage, extra={'id': self.scifloid})
                raise ScifloExecutorError(emessage)

    def handle(self, callbackResult):
        """Handle callback results."""

        procId, info = callbackResult
        info = workUnitInfo(info, status=calledBackStatus)
        updateJson(info['jsonFile'], info, stringifyKeys=STRINGIFY_FIELDS,
                   ubt=self.publicizeUbt,
                   publicizeKeys=WORK_UNIT_PUBLICIZE_FIELDS,
                   pickleKeys=PICKLE_FIELDS)
        self.updateStatus('WorkUnit status for "%s": %s' %
                          (procId, calledBackStatus), info)
        self.logger.debug("workUnitWorker for '%s' called back in sciflo '%s' \
with status '%s'.  Handling result." %
                          (procId, self.scifloName, info['workerStatus']),
                          extra={'id': self.scifloid})
        self.doneDict[procId] = True

        # continue if no error happened elsewhere
        if self.executionError is None:
            try:
                self._handle(procId, info)
            except Exception as e:
                self.handleError(procId,
                                 workUnitInfo(info, result=e,
                                              exceptionMessage=str(e),
                                              tracebackMessage=getTb()))

    def _handle(self, procId, info):
        """Handle results."""

        # set result in resultDict; publicize if specified
        if self.publicize and info['call'] not in ('sciflo.utils.makeLocal', 'sciflo.utils.makeLocalNoDods'):
            self.resultsDict[procId] = publicizeResultFiles(
                info['result'], self.ubt)
        else:
            self.resultsDict[procId] = info['result']

        # append work unit's execution log to sciflo's execution log
        f = open(info['executionLog'])
        wuLog = f.read()
        f.close()
        self.logger.debug("Execution log for '%s': %s" % (
            procId, wuLog), extra={'id': self.scifloid})

        # add provenance info for workUnit execution started
        self.annDoc.addProcessFinished(procId, info['pidFile'])

        # write inidividual results to result files
        numOutputs = 1
        if not isinstance(info['result'], Exception):
            for i in self.sciflo._flowProcessesProcess:
                if procId == i.get('id'):
                    outputElt = i.xpath('./sf:outputs',
                                        namespaces=self.sciflo._namespacePrefixDict)[0]
                    numOutputs = len(outputElt.getchildren())
        if numOutputs == 1:
            resFile = os.path.join(info['workDir'], 'workunit_result-0.txt')
            f = open(resFile, 'w')
            f.write("%s\n" % info['result'])
            f.close()
        else:
            for i in range(numOutputs):
                resFile = os.path.join(info['workDir'],
                                       'workunit_result-%d.txt' % i)
                f = open(resFile, 'w')
                f.write("%s\n" % info['result'][i])
                f.close()

        # handle errors otherwise handle results
        if isinstance(info['result'], Exception):
            self.handleError(procId, info)
            return
        else:
            self.handleResult(procId, info)

        # update global outputs
        self.updateGlobalOutputs(procId)

        # resolve and spawn waiting work units
        self.resolveAndSpawn()

        # log what's still waiting
        waitingProcs = [i for i in self.procIds
                        if isinstance(self.applyResultsDict[i], WorkUnitConfig)]
        self.logger.debug("'%s' detects %i work units that are waiting to run \
in sciflo '%s': %s" % (procId, len(waitingProcs), self.scifloName,
                       waitingProcs), extra={'id': self.scifloid})

        # check to see if a result has been set for all work units;
        # if so, set done flag
        allResultsSet = True
        noResultsYet = []
        for thisProcId in self.procIds:
            if isinstance(self.resultsDict[thisProcId], NoResult):
                allResultsSet = False
                noResultsYet.append(thisProcId)
                # break
        self.logger.debug("No results yet in sciflo '%s': %s" %
                          (self.scifloName, noResultsYet),
                          extra={'id': self.scifloid})
        if allResultsSet:
            self.event.set()
            return

        # backup detector
        if len(self.doneDict) == len(self.procIds):
            self.logger.debug("Detected that all work units are done in sciflo \
'%s'.  Error in detecting results from resultsDict from '%s' callback." %
                              (self.scifloName, procId), extra={'id': self.scifloid})
            self.event.set()

    def handleResult(self, procId, info):
        """Handle result."""

        # get our own pdict
        if self.cacheName is None:
            pdict = None
        else:
            try:
                pdict = PersistentDict(self.cacheName, pickleVals=True)
            except Exception as e:
                self.logger.debug("Got exception trying to get PersistentDict \
for handleResult() for procId '%s' in sciflo '%s': %s.  No cache will be used."
                                  % (procId, self.scifloName, e), extra={'id': self.scifloid})
                pdict = None

        # get res
        res = info['result']

        # save as originalResult to keep history if result is publicized later
        info['unpublicizedResult'] = copy.deepcopy(info['result'])

        if info['workerStatus'] == cachedStatus:
            logHead = "Cached result"
        else:
            logHead = "Result"
        logRes = str(res)
        if len(logRes) > 80:
            logRes = "%s..." % logRes[0:79]
        self.logger.debug("%s for '%s' in sciflo '%s': %s" %
                          (logHead, procId, self.scifloName, logRes),
                          extra={'id': self.scifloid})

        # run post exec
        info = workUnitInfo(info, status=postExecutionStatus)
        updateJson(info['jsonFile'], info, stringifyKeys=STRINGIFY_FIELDS,
                   ubt=self.publicizeUbt,
                   publicizeKeys=WORK_UNIT_PUBLICIZE_FIELDS,
                   pickleKeys=PICKLE_FIELDS)
        self.updateStatus('WorkUnit status for "%s": %s' %
                          (procId, postExecutionStatus), info)
        postExecList = self.postExecResultsDict[procId]
        for i, (resIdx, funcStr) in enumerate(postExecList):
            postExecHex = hashlib.md5('{}_{}_{}'.format(info['hex'], resIdx,
                                                        funcStr).encode('utf-8')).hexdigest()
            postExecResult = None

            # get from cache
            if self.lookupCache and pdict is not None:
                try:
                    pePklFile = pdict[postExecHex]
                except Exception as e:
                    self.logger.debug("Got error trying to retrieve cached \
post execution for '%s' in sciflo '%s': %s\n%s" % (procId, self.scifloName,
                                                   str(e), getTb()),
                                      extra={'id': self.scifloid})
                    pePklFile = None
                if pePklFile is not None and os.path.exists(pePklFile):
                    pefh = open(pePklFile)
                    postExecResult = PostExecResult(pickle.load(pefh))
                    pefh.close()

            # otherwise just run it
            if postExecResult is None:
                self.logger.debug("Running post execution for '%s' in sciflo \
'%s': %s" % (procId, self.scifloName, (resIdx, funcStr)),
                    extra={'id': self.scifloid})
                try:
                    postExecHandler = PostExecutionHandler(resIdx, funcStr,
                                                           info['workDir'])
                    postExecResult = PostExecResult(
                        postExecHandler.execute(res, info['workDir']))

                    # write post exec result to cache
                    if pdict is not None:
                        try:
                            updatePdict(pdict, postExecHex,
                                        os.path.join(info['workDir'], "%s.pkl" % postExecHex))
                            self.logger.debug("Wrote post execution results \
for '%s' to cache under '%s' in sciflo '%s'." %
                                              (procId, postExecHex,
                                               self.scifloName),
                                              extra={'id': self.scifloid})
                        except Exception as e:
                            self.logger.debug("Got exception trying to write \
post execution results for '%s' to cache under '%s' in sciflo '%s': %s\n%s" %
                                              (procId, postExecHex, self.scifloName,
                                               str(e), getTb()),
                                              extra={'id': self.scifloid})
                except Exception as e:
                    postExecResult = PostExecResult(e)
                    self.logger.debug("Got error running post execution for \
'%s' in sciflo '%s': %s" % (procId, self.scifloName, res),
                        extra={'id': self.scifloid})
            else:
                self.logger.debug("Using cached post execution result for \
'%s' in sciflo '%s': %s" % (procId, self.scifloName, (resIdx, funcStr)),
                    extra={'id': self.scifloid})

            # set it; not if we need to publicize
            if self.publicize:
                self.postExecResultsDict[procId][i] = \
                    publicizeResultFiles(
                        postExecResult.val, self.ubt, dir=info['workDir'])
            else:
                self.postExecResultsDict[procId][i] = \
                    getAbsPathForResultFiles(
                        postExecResult.val, dir=info['workDir'])
            self.logger.debug("Finished post execution for '%s' in sciflo '%s':\
 %s" % (procId, self.scifloName, (resIdx, funcStr)),
                extra={'id': self.scifloid})

        # write result to annotated doc and set to done;
        # note if we need to publicize
        info = workUnitInfo(info, status=doneStatus)
        if self.publicize:
            self.annDoc.addProcessResult(procId,
                                         publicizeResultFiles(res, self.ubt))
            thisInfo = workUnitInfo(copy.deepcopy(info),
                                    result=publicizeResultFiles(info['result'],
                                                                self.ubt))
            updateJson(thisInfo['jsonFile'], thisInfo,
                       stringifyKeys=STRINGIFY_FIELDS, ubt=self.publicizeUbt,
                       publicizeKeys=WORK_UNIT_PUBLICIZE_FIELDS,
                       pickleKeys=PICKLE_FIELDS)
            self.updateStatus('WorkUnit status for "%s": %s' %
                              (procId, thisInfo['workerStatus']), thisInfo)
        else:
            self.annDoc.addProcessResult(procId, res)
            updateJson(info['jsonFile'], info, stringifyKeys=STRINGIFY_FIELDS,
                       ubt=self.publicizeUbt,
                       publicizeKeys=WORK_UNIT_PUBLICIZE_FIELDS,
                       pickleKeys=PICKLE_FIELDS)
            self.updateStatus('WorkUnit status for "%s": %s' %
                              (procId, info['workerStatus']), info)

        # write to cache if defined and not cached
        if pdict is not None and info['workerStatus'] == doneStatus:
            try:
                updatePdict(pdict, self.hexDict[procId], info['jsonFile'])
                self.logger.debug("Wrote info for '%s' to cache under '%s' \
in sciflo '%s'." % (procId, self.hexDict[procId], self.scifloName),
                    extra={'id': self.scifloid})
            except Exception as e:
                self.logger.debug("Got exception trying to write info for \
'%s' to cache under '%s' in sciflo '%s': %s\n%s" % (procId,
                                                    self.hexDict[procId], self.scifloName, str(e), getTb()),
                                  extra={'id': self.scifloid})

    def handleError(self, procId, info):
        """Handle error."""

        try:
            res = info['result']
            tb = info['tracebackMessage']
            self.logger.debug("Error result for '%s' in sciflo '%s': %s\n%s" %
                              (procId, self.scifloName, res, tb),
                              extra={'id': self.scifloid})
            self.logger.debug("Stopping execution in sciflo '%s'." %
                              self.scifloName, extra={'id': self.scifloid})
            self.executionError = (procId, res, tb)

            # write exception to annotated doc
            self.annDoc.addProcessException(procId, tb)

            # set exception status
            if isinstance(res, CancelledWorkUnit):
                status = cancelledStatus
            else:
                status = exceptionStatus
            info = workUnitInfo(info, status=status)
            updateJson(info['jsonFile'], info, stringifyKeys=STRINGIFY_FIELDS,
                       ubt=self.publicizeUbt,
                       publicizeKeys=WORK_UNIT_PUBLICIZE_FIELDS,
                       pickleKeys=PICKLE_FIELDS)
            self.updateStatus('WorkUnit status for "%s": %s' %
                              (procId, status), info)
        except Exception as e:
            self.logger.debug("Got error in handleError() for '%s' in sciflo \
'%s': %s\n%s" % (procId, self.scifloName, str(e), getTb()),
                extra={'id': self.scifloid})

        # set event
        try:
            self.event.set()
        except IOError as e:
            self.logger.debug("Got IOError setting event from handleError() \
for '%s' in sciflo '%s': %s\n%s" % (procId, self.scifloName, str(e), getTb()),
                              extra={'id': self.scifloid})

    def updateGlobalOutputs(self, procId):
        """Update global outputs."""

        for i in range(len(self.output)):
            o = self.output[i]
            if isinstance(o, UnresolvedArgument):
                resolvingId = o.getId()
                if procId == resolvingId:
                    # get resolving result
                    resolvingRes = self.resolveArg(o)

                    # link result
                    if isinstance(resolvingRes, (bytes,
                                                 str)) and os.path.exists(resolvingRes):
                        resolvingRes = linkResult(resolvingRes, self.outputDir)

                    # publicize?
                    if self.publicize:
                        resolvingRes = publicizeResultFiles(resolvingRes,
                                                            self.ubt)

                    # write to annotated doc
                    self.annDoc.addGlobalOutput(i, resolvingRes)

                    #set in output
                    self.output[i] = resolvingRes

    def resolveAndSpawn(self):
        """Resolve and spawn waiting work units."""

        for thisProcId in self.procIds:
            wuConfig = self.applyResultsDict[thisProcId]
            if not isinstance(wuConfig, WorkUnitConfig):
                continue

            # resolve args
            resolved = self.resolveArgs(wuConfig)

            # if resolved execute work unit using pool
            if resolved:
                self.hexDict[thisProcId] = wuConfig.getHexDigest()
                wu = getWorkUnit(wuConfig, configFile=self.configFile,
                                 configDict=self.configDict)
                self.procIdWuidMap[thisProcId] = wu.getWuid()
                self.updateStatus('WorkUnit status for "%s": %s' %
                                  (thisProcId, readyStatus), wu.getInfo())
                self.dispatchWorker(wu)

                # update sciflo info
                self.updateScifloInfo(procIdWuidMap=self.procIdWuidMap)


def _runSciflo(sflStr, args={}, workers=4, timeout=None, workDir=None,
               outputDir=None, scifloid=None, publicize=False,
               configFile=None, lookupCache=True, configDict={},
               writeGraph=True, statusUpdateFunc=None, emailNotify=None,
               outputUrl=None):
    """Run sciflo in a forked process."""

    s = None
    try:
        s = ScifloExecutor(sflStr, args=args, workers=workers,
                           workerTimeout=timeout, workDir=workDir,
                           outputDir=outputDir, scifloid=scifloid,
                           publicize=publicize, configFile=configFile,
                           lookupCache=lookupCache, configDict=configDict,
                           writeGraph=writeGraph, statusUpdateFunc=statusUpdateFunc,
                           emailNotify=emailNotify, outputUrl=outputUrl)
        s.execute()
        result = s.output
    except Exception as e:
        result = e
        print((getTb()))

    notifyByEmail(emailNotify, result, s)
    return result


def runSciflo(sflStr, args={}, workers=4, timeout=None, workDir=None,
              outputDir=None, scifloid=None, publicize=False,
              configFile=None, lookupCache=True, configDict={},
              writeGraph=True, statusUpdateFunc=None, emailNotify=None,
              outputUrl=None):
    """Garbage collect after running _runSciflo."""

    res = _runSciflo(sflStr, args, workers, timeout, workDir, outputDir,
                     scifloid, publicize, configFile, lookupCache,
                     configDict, writeGraph, statusUpdateFunc,
                     emailNotify, outputUrl)
    gc.collect()
    if isinstance(res, Exception):
        raise res
    return res


def notifyByEmail(address, result, executor):
    """Notify by email."""

    if not address in (None, ''):
        try:
            # handle exceptions
            if isinstance(result, Exception):
                if executor is not None:
                    title = 'SciFlo execution FAILED for %s' % executor.scifloid
                    message = 'Navigate to the SciFlo work directory below for more information:\n\n'
                    if isinstance(executor.outputUrl, str):
                        message += '%s\n\n\n' % executor.outputUrl
                    else:
                        message += '%s\n\n\n' % executor.outputDir
                else:
                    title = 'SciFlo execution FAILED'
                    message = ''
                message += 'Error info:\n\n%s' % result
            else:
                title = 'SciFlo execution COMPLETED for %s' % executor.scifloid
                if executor.publicize:
                    message = 'Navigate to the SciFlo work directory URL below for more information:\n\n'
                    if isinstance(executor.outputUrl, str):
                        message += '%s\n\n\n' % executor.outputUrl
                    else:
                        message += '%s\n\n\n' % executor.outputDir
                else:
                    message = 'Navigate to the SciFlo work directory below for more information:\n\n'
                    message += executor.outputDir

            send_email(getuser(), [address], [], title, message)
        except Exception as e:
            print(("Got error trying to notify %s by email: %s" %
                   (address, getTb())))
            pass
