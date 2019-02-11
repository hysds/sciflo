import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import signal
import json
import time
from SOAPpy import WSDL

from sciflo.utils import UrlBaseTracker
from .utils import (generateScifloId, pickleArgsList, unpickleArgsList,
                    updateJson, getTb, pickleThis)
from .executor import runSciflo, ScifloExecutorError
from .config import GridServiceConfig


def getWSDLProxy(wsdl):
    """Return proxy object from wsdl."""
    return WSDL.Proxy(urllib.request.urlopen(wsdl).read())


def submitSciflo_server(sflStr, pickledArgs, configFile=None, lookupCache=True):
    """Server function implementation to submit sciflo and args for execution.
    Return scifloid and json url."""

    gsc = GridServiceConfig(configFile)
    workDir = gsc.getWorkUnitWorkDir()
    args = unpickleArgsList(pickledArgs)
    scifloid = generateScifloId()
    pid = os.fork()
    if not pid:
        pid2 = os.fork()
        if pid2:
            os._exit(0)
        os.setpgid(0, 0)
        try:
            results = runSciflo(sflStr, args, scifloid=scifloid, workDir=workDir,
                                outputDir=None, publicize=True,
                                configFile=configFile, lookupCache=lookupCache)
        except Exception as e:
            if not os.path.exists(os.path.join(workDir, scifloid, 'sciflo.json')):
                updateJson(os.path.join(workDir, scifloid, 'sciflo.json'),
                           {'scifloid': scifloid,
                            'scifloName': '',
                            'call': sflStr,
                            'args': args,
                            'workDir': '',
                            'startTime': 0,
                            'endTime': 0,
                            'result': pickleThis(ScifloExecutorError("Encountered error submitting \
sciflo for execution: %s\n%s" % (str(e), getTb()))),
                            'exceptionMessage': None,
                            'status': 'exception',
                            'pid': '',
                            'procIds': '',
                            'procIdWuidMap': '',
                            'outputDir': '',
                            'jsonFile': '',
                            'svgFile': '',
                            'executionLog': ''})
        os._exit(0)
    else:
        baseUrl = gsc.getBaseUrl()
        if baseUrl is None:
            baseUrl = gsc.getGridBaseUrl()
        ubt = UrlBaseTracker(workDir, baseUrl)
        os.waitpid(pid, 0)
        return (scifloid,
                ubt.getUrl(os.path.join(workDir, scifloid, 'sciflo.json')))


def submitSciflo_server_nocache(sflStr, pickledArgs, configFile=None):
    return submitSciflo_server(sflStr, pickledArgs, configFile, lookupCache=False)


def submitSciflo_client(wsdl, funcName, sflStr, args):
    """Client function to submit sciflo and args for execution on the
    server and return scifloid."""

    pickledArgs = pickleArgsList(args)
    p = getWSDLProxy(wsdl)
    soapCall = eval("p.%s" % funcName)
    return soapCall(sflStr, pickledArgs)


def cancelSciflo_server(scifloid, configFile=None):
    """
    Server function implementation to cancel sciflo.
    """

    # get dict of procId->wuid map
    gsc = GridServiceConfig(configFile)
    workDir = gsc.getWorkUnitWorkDir()
    scifloDir = os.path.join(workDir, scifloid)
    jsonFile = os.path.join(scifloDir, 'sciflo.json')
    with open(jsonFile) as jsonFh:
        val = jsonFh.read()
    scifloJson = json.loads(val)
    procIdWuidMap = scifloJson['procIdWuidMap']
    procIds = scifloJson['procIds']

    # try a max of 10 times
    killed = False
    for t in range(10):
        # loop over and kill each proc id
        for procId in procIds:
            try:
                wuid = procIdWuidMap[procId]
                pidFile = os.path.join(workDir, wuid, 'workunit.pid')
                if not os.path.exists(pidFile):
                    continue
                pidFh = open(pidFile)
                pid = int(pidFh.read())
                pidFh.close()
                os.kill(pid, signal.SIGINT)
                killed = True
                break
            except Exception as e:
                print("Error in cancelSciflo_server for pid %d: %s" %
                      (pid, e), file=sys.stderr)
        if killed:
            break
        time.sleep(1)
    return True


def cancelSciflo_client(wsdl, funcName, scifloid):
    """Client function to cancel sciflo."""

    p = getWSDLProxy(wsdl)
    soapCall = eval("p.%s" % funcName)
    return soapCall(scifloid)
