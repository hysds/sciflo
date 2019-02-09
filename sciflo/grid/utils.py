# -----------------------------------------------------------------------------
# Name:        utils.py
# Purpose:     Various SciFlo grid utilities.
#
# Author:      Gerald Manipon
#
# Created:     Mon Jun 27 12:52:36 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import time
import hashlib
import re
import types
import os
import shutil
import traceback
import sys
import json
import copy
from random import Random
from socket import getfqdn
import pickle as pickle
from SOAPpy import SOAPProxy
from collections import UserList
from urllib.parse import urlparse
from io import StringIO
import lxml.etree
from string import Template
import urllib.request
import urllib.error
import urllib.parse
import contextlib
from pprint import pprint
import base64
import magic

from sciflo.utils import (getListFromUnknownObject, ScifloConfigParser, SCIFLO_NAMESPACE,
                          linkFile, runDot, getXmlEtree, validateDirectory,
                          getThreadSafeRandomObject)
import sciflo.grid

# fqdn digest
FQDN_DIGEST = hashlib.md5(getfqdn().encode('utf-8')).hexdigest()


def publicizeResultFiles(result, ubt, dir=None):
    """Recursively loop through result and check for filenames.  If detected,
    replace with url to that file.  Return the converted result."""

    # if string, try to get url
    if isinstance(result, (bytes, str)):
        try:
            thisResult = result
            if thisResult.startswith('/'):
                return ubt.getUrl(thisResult)
            if dir:
                thisResult = os.path.join(dir, thisResult)
            if os.path.exists(thisResult):
                return ubt.getUrl(thisResult)
            else:
                return result
        except:
            return result
    elif isinstance(result, (list, tuple)):
        newResult = []
        for r1 in result:
            newResult.append(publicizeResultFiles(r1, ubt, dir=dir))
        if isinstance(result, tuple):
            return tuple(newResult)
        else:
            return newResult
    else:
        return result


def getAbsPathForResultFiles(result, dir=None):
    """Recursively loop through result and check for filenames.  If detected,
    replace with abs path to that file.  Return the converted result."""

    # store curdir
    try:
        curDir = os.getcwd()
    except:
        curDir = None

    # change dir if need be
    if dir is not None:
        os.chdir(dir)

    try:
        # if string, try to get url
        if isinstance(result, (bytes, str)):
            if os.path.exists(result):
                result = os.path.abspath(result)
        elif isinstance(result, (tuple, list)):
            newResult = []
            for r1 in result:
                newResult.append(getAbsPathForResultFiles(r1))
            if isinstance(result, tuple):
                result = tuple(newResult)
            else:
                result = newResult
        else:
            pass
    finally:
        if dir and curDir:
            os.chdir(curDir)
    return result


def loadJson(jsonFile, unpickleKeys=[]):
    """Decode json."""

    tryNum = 1
    while True:
        try:
            with contextlib.closing(urllib.request.urlopen(jsonFile)) as f:
                val = f.read()
            obj = json.loads(val)
            break
        except:
            if tryNum < 5:
                tryNum += 1
                time.sleep(1)
            else:
                raise
    # unpickle keys
    if isinstance(obj, dict) and len(unpickleKeys) > 0:
        for k in unpickleKeys:
            if obj.get(k, None) is not None:
                obj[k] = unpickleThis(obj[k])
    return obj


def updateJson(jsonFile, obj, stringifyKeys=[], ubt=None, publicizeKeys=[],
               pickleKeys=[]):
    """Write obj in JSON format to file or update it."""

    # publicize
    if isinstance(obj, dict) and ubt is not None and \
            len(publicizeKeys) > 0:
        obj = copy.deepcopy(obj)
        for k in publicizeKeys:
            obj[k] = publicizeResultFiles(obj[k], ubt)

    # make sure result is stringified
    if isinstance(obj, dict) and len(stringifyKeys) > 0:
        obj = copy.deepcopy(obj)
        for k in stringifyKeys:
            if obj.get(k, None) is not None:
                obj[k] = str(obj[k])

    # pickle keys
    if isinstance(obj, dict) and len(pickleKeys) > 0:
        obj = copy.deepcopy(obj)
        for k in pickleKeys:
            if obj.get(k, None) is not None:
                obj[k] = pickleThis(obj[k])

    validateDirectory(os.path.dirname(jsonFile))
    with open(jsonFile, 'w') as f:
        #pprint(obj)
        json.dump(obj, f)


def updatePdict(pdict, k, v):
    """Update wrapper."""

    try:
        if pdict is not None:
            pdict[k] = v
    except Exception as e:
        print(("Got exception trying to update pdict key '%s': %s" % (k, str(e))))


def runFuncWithRetriesAndSleep(retries, sleep, f, *args, **kargs):
    """Run a function in a retry loop with sleeps."""

    e = None
    for i in range(retries):
        try:
            return f(*args, **kargs)
        except Exception as e:
            print(("Got error in runFuncWithRetriesAndSleep() on try %i for \
function '%s': %s\n%s" % (i + 1, str(f), str(e), getTb())))
        time.sleep(sleep)
    raise e


def runFuncWithRetries(retries, f, *args, **kargs):
    """Run a function in a retry loop."""
    return runFuncWithRetriesAndSleep(retries, 0, f, *args, **kargs)


def runLockedFunction(mutex, f, *args, **kargs):
    """Run a function within a thread-safe lock."""

    runFuncWithRetriesAndSleep(3, 1, mutex.acquire)
    gotError = False
    try:
        res = f(*args, **kargs)
    except Exception as e:
        gotError = True
        res = e
        print(("Got error in runLockedFunction() for function '%s': %s\n%s" %
               (str(f), str(e), getTb())))
    finally:
        runFuncWithRetriesAndSleep(3, 1, mutex.release)
    if gotError:
        raise res
    return res


def getTb():
    """Return traceback message."""

    tb = "Exception Type: %s\n" % str(sys.exc_info()[0])
    tb += "Exception Value: %s\n" % str(sys.exc_info()[1])
    tb += traceback.format_exc()
    return tb


def normalizeScifloArgs(args):
    """Normalize sciflo args to either a list or dict."""

    if isinstance(args, dict) or \
            (isinstance(args, (list, tuple)) and (len(args) != 1)):
            return args
    elif isinstance(args, (list, tuple)):
        if isinstance(args[0], (list, tuple, dict)):
            return args[0]
        else:
            return args
    else:
        raise RuntimeError(
            "Unrecognized type for sciflo args: %s" % type(args))


def generateUniqueId(prefix='id'):
    """Return a randomly id."""

    # get random object
    rndm = getThreadSafeRandomObject()

    t = time.time()
    (year, month, day, hour, minute, sec) = (time.localtime(t))[:6]
    return '%s-%02d%s%02d-%02d%02d%04d-%04d%02d%04d-%s' % \
        (prefix, sec, str(t-int(t))[-4:], hour, month, minute,
         rndm.randrange(1, 9999), rndm.randrange(1, 9999), day,
         year, FQDN_DIGEST)


def generateWorkUnitId(): return generateUniqueId('sciflowuid')


def generateScifloId(): return generateUniqueId('scifloid')


def generateWorkUnitConfigId(): return generateUniqueId('workunitconfigid')


def getArgsString(args):
    """Return string representation of args."""

    retString = ''
    if isinstance(args, (list, tuple, set, UserList)):
        for arg in args:
            retString += getArgsString(arg)
        return retString
    elif isinstance(args, dict):
        keys = list(args.keys())
        keys.sort()
        for key in keys:
            retString += "%s|%s" % (key, getArgsString(args[key]))
        return retString
    else:
        return str(args)


def getStageFilesString(stageFiles):
    """Return stage files basenames."""

    stageFilesStr = ''
    for file in stageFiles:
        if file is None:
            stageFilesStr += 'None'
        else:
            stageFilesStr += os.path.basename(urlparse(file)[2])
    return stageFilesStr


def generateWorkUnitHexDigest(owner, type, call, args, stageFiles, postExecIds):
    """Return a md5 hex digest of the objects passed in."""

    # get md5 hex digest
    return hashlib.md5("%s %s %s %s %s %s" % (owner, type, call, getArgsString(args),
                                              getStageFilesString(
                                                  getListFromUnknownObject(stageFiles)),
                                              getArgsString(postExecIds))).hexdigest()


def verifyExecutable(path):
    """Return 1 if path specifies a binary executable or a script with proper interpreter
    declaration, i.e. #!/bin/sh.  Otherwise, return None."""

    # get type
    type = magic.from_file(path)

    # if binary executable, return 1
    if type.startswith('ELF'):
        return 1
    # get first line and see if it contains an interpreter declaration
    else:
        lines = open(path).readlines()
        if re.match(r'^#!.+$', lines[0]):
            return 1
        else:
            return None


def pickleArgsList(argsList):
    """Return pickled string or argument list."""
    return pickleThis(argsList)


def unpickleArgsList(pickledString):
    """Return unpickled argument list from string."""
    return unpickleThis(pickledString)


def pickleThis(this):
    """Return pickled string."""
    return base64.b64encode(pickle.dumps(this)).decode('utf-8')


def unpickleThis(this):
    """Return unpickled object from string."""
    return pickle.loads(base64.b64decode(this.encode('utf-8')))


def getHexDigest(args):
    """Return a md5 hex digest of the objects passed in."""

    # create string from args
    argsString = str(getArgsString(getListFromUnknownObject(args)))

    # get md5 hex digest
    return hashlib.md5(argsString.encode('utf-8')).hexdigest()


def getFunction(funcStr, addToSysPath=None):
    """Automatically parse a function call string to import any libraries
    and return a pointer to the function.  Define addToSysPath to prepend a
    path to the modules path."""

    # check if we have to import a module
    libmatch = re.match(r'^((?:\w|\.)+)\.\w+\(?.*$', funcStr)
    if libmatch:
        importLib = libmatch.group(1)
        if addToSysPath:
            exec("import sys; sys.path.insert(1,'%s')" % addToSysPath)
        exec("import %s" % importLib)
        exec("import importlib")
        exec("importlib.reload(%s)" % importLib)

    # check there are args
    argsMatch = re.search(r'\((\w+)\..+\)$', funcStr)
    if argsMatch:
        importLib2 = argsMatch.group(1)
        if addToSysPath:
            exec("import sys; sys.path.insert(1,'%s')" % addToSysPath)
        exec("import %s" % importLib2)
        exec("import importlib")
        exec("reload(%s)" % importLib2)

    # return function
    return eval(funcStr)


class StdIOFaker(StringIO):
    def __init__(self, stderr):
        self.stderr = stderr
        StringIO.__init__(self)

    def write(self, strToWrite):
        strToWrite = str(strToWrite)
        self.stderr.write(strToWrite)
        return StringIO.write(self, strToWrite)


class Tee(object):
    def __init__(self, stream, *args, **kargs):
        self.stream = stream
        self.file = open(*args, **kargs)

    def write(self, strToWrite):
        strToWrite = str(strToWrite)
        self.stream.write(strToWrite)
        return self.file.write(strToWrite)

    def flush(self):
        self.stream.flush()
        return self.file.flush()

    def __del__(self): self.file.close()


def linkResult(res, outputDir, newName=None):
    """Link result to final output directory."""

    if newName:
        dest = os.path.abspath(os.path.join(outputDir, newName))
    else:
        dest = os.path.abspath(os.path.join(outputDir, os.path.basename(res)))
    if os.path.exists(dest):
        return dest
    if os.path.isfile(res):
        res = os.path.abspath(res)
        if res != dest:
            linkFile(res, dest)
    else:
        raise RuntimeError("Unknown file type for %s" % res)
    return dest


def dotFlowChartFromDependencies(processes, outputs, inputs=None):
    """Create a DOT-language GraphViz flowchart that depicts the process steps,
    the outputs of the flow, and the connecting lines.  Explicit processes are
    full nodes (style 'node') connected by simple edges, while implicit transforms
    are minor nodes drawn on a two-part edge (styles linkNode & linkEdge).
    """
    styles = {'node': ' [shape = box]', 'edge': ' ',
              'linkNode': ' [shape = box, style=dotted]', 'linkEdge': ' ',
              'terminal': ' [shape = ellipse, style=filled, color="gray89"]'}
    dot = ['digraph G {\n  size = "8,8";\n  rankdir = LR']
    # Add processes and their links to the graph
    for process in processes:
        name, type, deps = process
        if type == 'explicit':
            dot.append(name + styles['node'])
        else:   # type == 'implicit'
            dot.append(name + styles['linkNode'])
        if deps is None:
            continue
        for i in deps:
            edge = processes[i][0] + ' -> ' + name
            if type == 'implicit' or processes[i][1] == 'implicit':
                dot.append(edge + styles['linkEdge'])
            else:
                dot.append(edge + styles['edge'])

    # Add flow outputs to the graph
    for output in outputs:
        name, dep = output
        dot.append(name + styles['terminal'])
        if dep < 0:
            continue   # an flow output might come from the flow inputs, so no edge shown
        edge = processes[dep][0] + ' -> ' + name
        inputType = processes[dep][1]
        if inputType == 'implicit':
            dot.append(edge + styles['linkEdge'])
        else:
            dot.append(edge + styles['edge'])

    return ';\n  '.join(dot) + '\n}\n'


# full dot template
FULL_DOT_TEMPLATE = Template('''
digraph G {
 rankdir = LR;
${globalInputs}
${wuProcesses}
${globalOutputs}
${globalInput2ProcessEdges}
${process2ProcessEdges}
${process2GlobalOutputEdges}
}
''')

# process template
PROCESS_TEMPLATE = Template('''
  ${processId} [ ${shapeInfo}, label=<
<table border="0" cellborder="0" cellspacing="0" cellpadding="0">
  <tr>
    <td>
      <table border="0" cellborder="1" cellspacing="0" cellpadding="0">
${inputStubs}
      </table>
    </td>
    <td>
      <table border="0" cellborder="1" cellspacing="0" cellpadding="0">
        <tr><td width="100%">${processId}</td></tr>
      </table>
    </td>
    <td>
      <table border="0" cellborder="1" cellspacing="0" cellpadding="0">
${outputStubs}
      </table>
    </td>
  </tr>
</table>
>];''')

# input/output stub template
STUB_TEMPLATE = Template(
    '''        <tr><td port="${stubId}" width="7" height="7" fixedsize="TRUE"></td></tr>''')


def fullDotFlowChartFromDependencies(dotInfoElt):
    """Create a DOT-language GraphViz flowchart that depicts the global inputs,
    process steps, the outputs of the flow, and the connecting lines.
    """

    # get global inputs
    globalInputs = '\n'.join(["  %s [shape = hexagon];" % i.get('id') for i in
                              dotInfoElt.xpath('./globalInputs')[0]])

    # get processes
    globalInput2ProcessEdgesList = ['  edge[style=invis];']
    process2ProcessEdgesList = ['  edge[style=solid];']
    wuProcessesList = []
    for process in dotInfoElt.xpath('./processes/process'):
        procId = process.get('id')
        procType = process.get('type')
        procInputsElt = process[0]
        procOutputsElt = process[1]
        if procType == 'explicit':
            shapeInfo = "shape = plaintext"
        elif procType == 'implicit':
            shapeInfo = 'shape = box, style = "rounded,dotted"'
        else:
            raise RuntimeError("Unknown process type %s." % procType)
        inputStubsList = []
        for procInputElt in procInputsElt:
            procInputId = procInputElt.get('id')
            inputStubsList.append(STUB_TEMPLATE.substitute(stubId=procInputId))
            if procInputElt.get('from') == 'global':
                globalInput2ProcessEdgesList.append('  %s:e -> %s:%s:w ;' %
                                                    (procInputElt.get('val'), procId, procInputId))
            elif procInputElt.get('from') == 'process':
                resProcVal = procInputElt.get('val')
                (resProcId, resOutputIdx) = resProcVal.split(':')
                resOutputIdx = int(resOutputIdx)
                resOutputId = dotInfoElt.xpath('./processes/process[@id="%s"]/outputs/output' %
                                               resProcId)[resOutputIdx].get('id')
                process2ProcessEdgesList.append('  %s:%s:e -> %s:%s:w ;'
                                                % (resProcId, resOutputId, procId, procInputId))
            else:
                pass
        inputStubs = '\n'.join(inputStubsList)
        outputStubs = '\n'.join([STUB_TEMPLATE.substitute(
            stubId=i.get('id')) for i in procOutputsElt])
        wuProcessesList.append(PROCESS_TEMPLATE.substitute(processId=procId, shapeInfo=shapeInfo,
                                                           inputStubs=inputStubs, outputStubs=outputStubs))
    wuProcesses = '\n'.join(wuProcessesList)

    # get global outputs
    globalOutputsList = []
    process2GlobalOutputEdgesList = ['  edge[style=dotted];']
    for goElt in dotInfoElt.xpath('./globalOutputs')[0]:
        globalOutputsList.append(
            '  %s [shape = ellipse, style=filled, color="gray89"];' % goElt.get('id'))
        (resProcId, resOutputIdx) = goElt.get('val').split(':')
        resOutputIdx = int(resOutputIdx)
        resOutputId = dotInfoElt.xpath('./processes/process[@id="%s"]/outputs/output' %
                                       resProcId)[resOutputIdx].get('id')
        process2GlobalOutputEdgesList.append(
            '  %s:%s:e -> %s:w ;' % (resProcId, resOutputId, goElt.get('id')))
    globalOutputs = '\n'.join(globalOutputsList)

    # get edges
    globalInput2ProcessEdges = '\n'.join(globalInput2ProcessEdgesList)
    process2ProcessEdges = '\n'.join(process2ProcessEdgesList)
    process2GlobalOutputEdges = '\n'.join(process2GlobalOutputEdgesList)

    # not adding global inputs/edges
    globalInputs = ''
    globalInput2ProcessEdges = ''

    return FULL_DOT_TEMPLATE.substitute(globalInputs=globalInputs, wuProcesses=wuProcesses,
                                        globalOutputs=globalOutputs,
                                        globalInput2ProcessEdges=globalInput2ProcessEdges,
                                        process2ProcessEdges=process2ProcessEdges,
                                        process2GlobalOutputEdges=process2GlobalOutputEdges)


def getSvgFromSciflo(xml, inputArgs=[]):
    """Return SVG graph string of sciflo object/document/string."""
    return sciflo.grid.Sciflo(xml, inputArgs).getSvg()


def getScifloFromSvg(xml):
    """Return sciflo xml string from SVG."""

    # get xml tree
    #svgElt,svgNsDict = getXmlEtree(xml)
    raise NotImplementedError("Not yet implemented.")


def statusUpdateJson(obj, stringifyKeys):
    """Stringify any objects that may not be JSON serializable."""

    if isinstance(obj, dict) and len(stringifyKeys) > 0:
        obj = copy.deepcopy(obj)
        for k in stringifyKeys:
            if obj.get(k, None) is not None:
                try:
                    j = json.dumps(obj[k])
                except:
                    obj[k] = str(obj[k])

    return obj
