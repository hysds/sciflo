import os
import sys
import traceback
import pwd
import logging
import time
import json
import pickle as pickle
from random import Random
from queue import Empty
from SOAPpy.Errors import HTTPError
from lxml.etree import _ElementStringResult, _Element, tostring, fromstring
from celery.exceptions import SoftTimeLimitExceeded

from sciflo.utils import copyToDir, validateDirectory, getTempfileName
from sciflo.event.pdict import PersistentDict
from .config import GridServiceConfig
from .utils import (generateWorkUnitId, getTb, getThreadSafeRandomObject,
                    getAbsPathForResultFiles, generateScifloId)
from .workUnitTypeMapping import WorkUnitTypeMapping
from .workUnit import workUnitInfo
from .status import *

DEBUG_PROCESSING = False

# enable logging; using processing's logging facility or our own
if DEBUG_PROCESSING:
    import multiprocessing as processing
    LOG_FMT = "%(asctime)s [%(levelname)s/%(processName)s] %(message)s"
    processing.process.enableLogging(None, format=LOG_FMT)
    WORKER_LOGGER = processing.process.getLogger()
else:
    logging._acquireLock()
    try:
        LOG_FMT = "%(asctime)s %(name)s %(id)s %(levelname)s: %(message)s"
        logging.basicConfig(format=LOG_FMT)
        WORKER_LOGGER = logging.getLogger('workUnitWorker')
    finally:
        logging._releaseLock()
WORKER_LOGGER.setLevel(logging.DEBUG)

FORKED_CHILD_DIED_MESSAGE = "Forked child died.  An external entity killed it \
or a segmentation fault may have occurred."

CANCELLED_MESSAGE = "Work unit was scheduled for cancellation and consequently cancelled."


class ForkedChildDied(Exception):
    pass


class ExecuteWorkUnitError(Exception):
    pass


class ExecuteWorkUnitTimeoutError(ExecuteWorkUnitError):
    pass


class WorkUnitWorkerError(Exception):
    pass


class SoapHttpError(Exception):
    pass


class CancelledWorkUnit(Exception):
    pass


class CelerySoftTimeLimitExceeded(Exception):
    pass


def forkChildAndRun(q, func, *args, **kargs):
    """Fork a child and run function.  Detects if process was killed or
    segfaulted.  If q is None, return results.  Otherwise, q is an output
    queue to write results to."""

    pickleFile = getTempfileName(suffix="_%d" % os.getpid())
    pid = os.fork()
    if not pid:
        os.setpgid(0, 0)
        try:
            res = func(*args, **kargs)

            # catch HTTPError from SOAPpy.Errors exception or else unpickle will fail later
            if isinstance(res[0], HTTPError):
                res = (SoapHttpError('SOAPpy.Errors.HTTPError'), res[1])

            # catch SoftTimeLimitExceeded from celery since it can't be pickled
            if isinstance(res[0], SoftTimeLimitExceeded):
                res = (CelerySoftTimeLimitExceeded(str(res[0])), res[1])

            if isinstance(res[0], _Element):
                tres = tostring(res[0], encoding='unicode')
            elif isinstance(res[0], _ElementStringResult):
                tres = str(res[0])
            else:
                tres = res[0]
            res = (tres, res[1])
            with open(pickleFile, 'wb') as p:
                try:
                    pickle.dump(res, p)
                except:
                    pickle.dump((RuntimeError(str(res[0])), res[1]), p)
        except Exception as e:
            WORKER_LOGGER.debug("Error in forkChildAndRun: %s" % getTb(),
                                extra={'id': 'child'})
            with open(pickleFile, 'wb') as p:
                pickle.dump(e, p)
        os._exit(0)

    # install handler for SIGTERM
    if q:
        import signal

        def handler(signum, frame):
            try:
                os.kill(pid, signal.SIGTERM)
            except:
                pass
        signal.signal(signal.SIGTERM, handler)

    # wait
    try:
        retPid, exitStatus = os.waitpid(pid, 0)
    except OSError:
        pass
    try:
        if os.path.isfile(pickleFile):
            with open(pickleFile) as p:
                res = pickle.load(p)
            if os.path.exists(pickleFile):
                os.unlink(pickleFile)
        else:
            # child died with SIGKILL (seg fault or explicitly killed)
            if exitStatus == signal.SIGKILL:
                res = (ForkedChildDied(FORKED_CHILD_DIED_MESSAGE),
                       FORKED_CHILD_DIED_MESSAGE)
            # otherwise assume user cancelled explicitly through SIGINT
            else:
                res = (CancelledWorkUnit(CANCELLED_MESSAGE),
                       CANCELLED_MESSAGE)
    except Exception as e:
        res = (RuntimeError("Got exception in forChildAndRun: %s" % e),
               getTb())

    # handle results
    if q:
        q.put(res)
    else:
        return res


def runWorkUnit(wu):
    """Run work unit.  Returns a tuple contain (result, traceback).  If result
    is not an Exception, traceback will be None."""
    return wu.run()


def workUnitWorker(wu, cacheName, timeout):
    """Worker function that runs a work unit accounting for a timeout.
    Return the results.  Possible 'workerStatus' values: ['working', 'done',
    'cached', 'exception'].  Possible 'status' values: ['ready', 'sent',
    'called back', 'finalizing', 'done', 'exception']."""

    try:
        wuid = wu.getWuid()
        procId = wu.getProcId()
        hex = wu.getHexDigest()

        # get pdict
        if cacheName is None:
            pdict = None
        else:
            try:
                pdict = PersistentDict(cacheName, pickleVals=True)
            except Exception as e:
                WORKER_LOGGER.debug("Caught exception trying to create pdict \
for '%s': %s\n%s" % (procId, str(e), getTb()), extra={'id': wuid})
                pdict = None

        # if cache was not found or if it was and there was no cached value,
        # just run the work unit
        if pdict is not None:
            try:
                jsonFile = pdict[hex]
            except Exception as e:
                WORKER_LOGGER.debug("Caught exception for '%s' trying to query \
pdict with key '%s': %s\n%s" % (procId, hex, str(e), getTb()),
                    extra={'id': wuid})
                jsonFile = None
            if jsonFile is not None and os.path.exists(jsonFile):
                with open(jsonFile) as jfh:
                    val = jfh.read()
                info = json.loads(val)
            else:
                info = None
            if info is not None and info['status'] == doneStatus:
                WORKER_LOGGER.debug("Returning cached results for '%s' under \
key '%s'." % (procId, hex), extra={'id': wuid})
                if not os.path.exists(wu._logFile):
                    with open(wu._logFile, 'w') as logFh:
                        logFh.write("This work unit's result was retrieved from a \
previously cached execution: %s" % info['executionLog'])
                return (procId, workUnitInfo(wu.getInfo(),
                                             workerStatus=cachedStatus, startTime=0., endTime=0.,
                                             result=pickle.loads(
                                                 str(info['unpublicizedResult'])),
                                             exceptionMessage=info['exceptionMessage'],
                                             tracebackMessage=info['tracebackMessage']))

    except Exception as e:
        WORKER_LOGGER.debug("Got error in workUnitWorker for '%s': %s\n%s" %
                            (procId, str(e), getTb()), extra={'id': wuid})
        return (procId, wu.getInfo())

    # get info
    info = wu.getInfo()

    # create process and queue for work unit execution
    import multiprocessing as processing
    q = processing.Queue()
    p = processing.Process(target=forkChildAndRun, args=[q, runWorkUnit, wu])

    # install handler for SIGTERM
    import signal

    def handler(signum, frame):
        try:
            if p.isAlive():
                p.terminate()
            p.join(timeout=0)
        except:
            pass
    signal.signal(signal.SIGTERM, handler)

    WORKER_LOGGER.debug("Starting process for '%s'." % procId,
                        extra={'id': wuid})
    info = workUnitInfo(info, workerStatus=workingStatus,
                        startTime=time.time())
    p.start()
    gotError = True
    try:
        tmpRes = q.get(timeout=timeout)
        # get abs paths
        res = (getAbsPathForResultFiles(tmpRes[0], dir=wu.getWorkDir()),
               tmpRes[1])
        gotError = False
    except Empty as e:
        res = (ExecuteWorkUnitTimeoutError("Got timeout error executing work \
unit %s: %s" % (procId, e)), None)
    except Exception as e:
        res = (e, getTb())
    WORKER_LOGGER.debug("Finished waiting on process for '%s'." % procId,
                        extra={'id': wuid})
    info = workUnitInfo(info, endTime=time.time())
    if gotError:
        WORKER_LOGGER.debug("Calling terminate() for '%s'." % procId,
                            extra={'id': wuid})
        if p.isAlive():
            p.terminate()
    WORKER_LOGGER.debug("Calling join() for '%s'." %
                        procId, extra={'id': wuid})
    p.join(timeout=0)
    WORKER_LOGGER.debug("Finished join() for '%s'." % procId,
                        extra={'id': wuid})
    if gotError or isinstance(res[0], Exception):
        status = exceptionStatus
        exceptionMessage = str(res[0])
    else:
        status = doneStatus
        exceptionMessage = None
    return (procId, workUnitInfo(info, workerStatus=status, result=res[0],
                                 exceptionMessage=exceptionMessage,
                                 tracebackMessage=res[1])
            )


def workUnitCanceller(wu, cacheName, timeout):
    """Worker function that cancels a work unit."""

    wuid = wu.getWuid()
    procId = wu.getProcId()
    info = wu.getInfo()
    e = CancelledWorkUnit(CANCELLED_MESSAGE)
    WORKER_LOGGER.debug("procId '%s' is set for cancellation." % procId,
                        extra={'id': wuid})
    with open(info['executionLog'], 'w') as execLogFh:
        execLogFh.write(str(e))
    return (procId,
            workUnitInfo(info, workerStatus=cancelledStatus,
                         result=e, exceptionMessage=str(e),
                         tracebackMessage='')
            )


def executeWorkUnit(workUnit, pool, timeout=86400, callback=None,
                    cacheName=None, cancelFlag=False):
    """Execute a work unit utilizing a pool of workUnitWorkers or cacheWorkers.
    If callback is defined, an ApplyResult object is immediately returned.
    Otherwise, it blocks waiting for the result or a timeout."""

    # do async with callback or just wait for results
    if cancelFlag:
        worker = workUnitCanceller
    else:
        worker = workUnitWorker
    workerArgs = [workUnit, cacheName, timeout]
    if callback:
        return pool.apply_async(worker, workerArgs, callback=callback)
    else:
        try:
            res = pool.apply_async(worker, workerArgs)
            return res.get()
        except Exception as e:
            return (workUnit.getProcId(),
                    (ExecuteWorkUnitError("Got error executing work unit: %s"
                                          % e), getTb()))


def getWorkUnit(wuConfig, configFile=None, configDict={}):
    """Return work unit id and WorkUnit object from wuConfig.  Localizes
    any stage files."""

    workDir = GridServiceConfig(configFile).getWorkUnitWorkDir()
    validateDirectory(workDir)
    procId = wuConfig.getId()
    wuType = wuConfig.getType()
    wuClass = WorkUnitTypeMapping.get(wuType, None)
    wuid = generateWorkUnitId()
    wuWorkDir = os.path.join(workDir, wuid)
    copyToDir(wuConfig.getStageFiles(), wuWorkDir, unpackBundles=True)
    hex = wuConfig.getHexDigest()
    if wuClass is None:
        raise RuntimeError("Unimplemented WorkUnit subclass: %s" % wuType)
    if wuClass == 'sciflo':
        workUnit = wuClass(wuConfig.getCall(), wuConfig.getArgs(), wuWorkDir,
                           wuid=wuid, procId=procId, hexDigest=hex,
                           scifloid=generateScifloId(), configDict=configDict)
    else:
        workUnit = wuClass(wuConfig.getCall(), wuConfig.getArgs(), wuWorkDir,
                           wuid=wuid, procId=procId, hexDigest=hex, configDict=configDict)
    workUnit.setInfoItem('typ', wuType)
    workUnit.setInfoItem('status', readyStatus)
    workUnit.setInfoItem('procCount', wuConfig.getProcCount())
    return workUnit
