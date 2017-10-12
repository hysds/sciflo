import cPickle as pickle
import sys, os, re, string, types, shutil
import urllib, time, traceback, urllib2
import httplib
import SOAPpy
from SOAPpy import WSDL
from subprocess import *
from xml.parsers.expat import ExpatError
from pprint import pprint
from celery import group
from celery.result import AsyncResult, GroupResult
import uuid
import json

from sciflo.utils import (validateDirectory, resolvePath, xmldb,
getUserPubPackagesDir, getUserPvtPackagesDir, runXpath, linkFile,
postCall, writePickleFile)
from sciflo.utils.xmlIndent import indent
from utils import verifyExecutable, getFunction, generateScifloId, Tee

from hysds.orchestrator import submit_job


WORK_UNIT_INFO_FIELDS = ['wuid', 'procId', 'procCount', 'hex', 'owner',
                         'status', 'typ', 'call', 'args', 'stageFiles',
                         'workDir', 'startTime', 'endTime', 'result',
                         'exceptionMessage', 'tracebackMessage', 'executionLog',
                         'workerStatus', 'jsonFile', 'scifloid', 'pidFile',
                         'cancelFlag', 'unpublicizedResult']


def workUnitInfo(info=None, **kargs):
    """Wrapper function to return new workUnitInfo dict or modify existing one.
    """
    
    if info is None:
        info = {}
        for f in WORK_UNIT_INFO_FIELDS: info[f] = kargs.get(f, None)
    else:
        for f in kargs:
            if f in WORK_UNIT_INFO_FIELDS: info[f] = kargs[f]
    return info

class WorkUnitError(Exception):
    """Exception class for WorkUnit class."""
    pass

class WorkUnit(object):
    """Sciflo WorkUnit base class."""

    def __init__(self, call, args, workDir, verbose=False, wuid=None,
                 procId=None, hexDigest=None, configDict={}):
        """Save call, args, and working directory."""

        self._call = call; self._args = args;
        self._workDir = workDir; self._verbose = verbose
        self._wuid = wuid
        self._procId = procId
        self._hexDigest = hexDigest
        self._configDict = configDict
        self._cancelFlag = False
        if not validateDirectory(self._workDir):    #make sure workDir exists
            raise WorkUnitError, "Couldn't create work unit work directory: %s." % self._workDir
        self._jsonFile = os.path.join(self._workDir, 'workunit.json')
        self._logFile = os.path.join(self._workDir, 'wu_execution.log')
        self._pidFile = os.path.join(self._workDir, 'workunit.pid')
        self._info = workUnitInfo(None, call=self._call, args=self._args,
                                  workDir=self._workDir, wuid=self._wuid,
                                  procId=self._procId, hex=self._hexDigest,
                                  cancelFlag=self._cancelFlag,
                                  jsonFile=self._jsonFile,
                                  pidFile=self._pidFile,
                                  executionLog=self._logFile)
        
    def getWuid(self): return self._wuid
    def getProcId(self): return self._procId
    def getHexDigest(self): return self._hexDigest
    def getWorkDir(self): return self._workDir
    def getJsonFile(self): return self._jsonFile
    def getInfo(self): return self._info
    def setInfoItem(self, k, v): self._info[k] = v
    def getInfoItem(self, k): return self._info[k]

    def run(self):
        """Fork and execute the work unit."""
        
        #save pid
        pidFh = open(self._pidFile, 'w')
        pidFh.write("%d\n" % os.getpid())
        pidFh.close()

        userPubPackagesDir = getUserPubPackagesDir()
        userPvtPackagesDir = getUserPvtPackagesDir()
        origEnvPath = os.environ['PATH']
        origSysPath = sys.path
        os.environ['PATH'] = '.:%s:%s:%s' % (userPvtPackagesDir,userPubPackagesDir,os.environ['PATH'])
        sys.path.insert(1, userPubPackagesDir)
        sys.path.insert(1, userPvtPackagesDir)
        sys.path.insert(1, self._workDir)
        tracebackMessage = None
        
        #save stdout & stderr and replace with tee
        self.origStdout, self.origStderr = sys.stdout, sys.stderr
        sys.stdout = Tee(sys.stdout, self._logFile, 'a+', 0)
        sys.stderr = sys.stdout
            
        try:
            os.chdir(self._workDir)
            #write configDict to pickle
            writePickleFile(self._configDict, os.path.join(self._workDir, 'WORK_UNIT_CONFIG.pkl'))
            result = self._run()
        except Exception, e:
            result = e
            etype = sys.exc_info()[0]  #get traceback info
            evalue = sys.exc_info()[1]
            etb = traceback.format_exc()
            emessage = "Exception Type: %s\n" % str(etype)  #create error message
            emessage += "Exception Value: %s\n" % str(evalue)
            emessage += etb
            tracebackMessage = emessage
            
        #restore stdout & stderr
        sys.stdout, sys.stderr = self.origStdout, self.origStderr #restore stdout & stderr

        os.environ['PATH'] = origEnvPath  #restore env PATH and module search path
        sys.path = origSysPath
        return (result, tracebackMessage)

    def _run(self):
        """Execute the work unit."""
        pass

class PythonFunctionWorkUnitError(Exception):
    """Exception class for PythonFunctionWorkUnit class."""
    pass

class PythonFunctionWorkUnit(WorkUnit):
    """WorkUnit subclass implementing a python function call."""

    def _run(self):
        """Call the python function work unit and return the result."""

        funcCall = self._call
        funcArgs = self._args
        if self._verbose:
            print "PythonFunctionWorkUnit: %s(*args) where args=%s" % \
                (funcCall, str(funcArgs))
        func = getFunction(funcCall)   #get function, importing any libraries
        return apply(func,funcArgs)

class InlinePythonFunctionWorkUnitError(Exception):
    """Exception class for InlinePythonFunctionWorkUnit class."""
    pass

class InlinePythonFunctionWorkUnit(WorkUnit):
    """WorkUnit subclass to execute inline python code."""

    def _run(self):
        """Execute the inline python code and return the result."""

        code = string.strip(self._call)
        funcArgs = self._args
        match = re.search(r'def\s+(\w+)\s*\(',code)  #get function name
        if match: funcCall = match.group(1)
        else:
            raise InlinePythonFunctionWorkUnitError, "Cannot extract function name from inline code."
        if self._verbose: print "InlinePythonFunctionWorkUnit: %s" % code
        exec code in locals()  #exec the inline python in local namespace
        return apply(eval(funcCall),funcArgs)

class SoapWorkUnitError(Exception):
    """Exception class for SoapWorkUnit class."""
    pass

class SoapWorkUnit(WorkUnit):
    """WorkUnit subclass to call a SOAP service."""

    def _run(self):
        """Call the SOAP service and return the result."""
        
        def _adjustSoapArg(arg):
            if isinstance(arg, types.StringTypes): newArg = "'''%s'''" % arg
            elif isinstance(arg, SOAPpy.Types.arrayType): newArg = "%s" % arg._aslist()
            elif isinstance(arg, SOAPpy.Types.structType): newArg = "%s" % arg._asdict()
            else: newArg = "%s" % arg
            return newArg
            
        soapCall = self._call  #generate call
        wsdlFile = self._args[0]
        soapArgs = self._args[1:]

        if self._verbose: SOAPpy.Config.debug = 1

        #get proxy
        if wsdlFile.startswith('https://'): wsdlFile = urllib2.urlopen(wsdlFile)
        try: server = WSDL.Proxy(wsdlFile)  #get soap server
        except ExpatError, e:
            try: wsdlStr = urllib.urlopen(wsdlFile).read()
            except Exception, e:
                raise SoapWorkUnitError, "Got error accessing wsdl at %s.  Check url?\n%s" % (wsdlFile, e)
            raise SoapWorkUnitError, "Got error parsing wsdl at %s.  Check url?\n%s" % (wsdlFile, e)

        argsStrList = []
        for soapArg in soapArgs: argsStrList.append(_adjustSoapArg(soapArg))
        callLine = 'server.%s(%s)' % (soapCall,",".join(argsStrList))
        if self._verbose: print "SoapWorkUnit: %s" % callLine
        res = eval(callLine)
        
        #check if AsyncResult
        if isinstance(res, types.StringTypes) and res.startswith('scifloAsync:'):
            res = res[12:]
            print "Querying for async result..."
            retries = 17280
            sleep = 5
            for i in range(retries):
                try: return pickle.loads(urllib2.urlopen(res).read())
                except urllib2.HTTPError, e:
                    if re.search(r'HTTP Error 404', str(e)):
                        print "Got 404(Not Found).  Going to sleep and will retry again."
                    else: raise
                time.sleep(sleep)
            raise SoapWorkUnitError('Timed out trying to query for AsyncResult.')
        else: return res

class ExecutableWorkUnitError(Exception):
    """Exception class for ExecutableWorkUnit class."""
    pass

class ExecutableWorkUnit(WorkUnit):
    """WorkUnit subclass to run a command-line executable."""

    #outputfile regex list
    outputFileRegexList = [re.compile(r'>>?\s*(\S+)\s*$'), #detect > or >>
                           re.compile(r'-out\s+(\S+)\s+'), #detect -out <file>
                          ]

    def _getExePath(self, call):
        """Return resolved path to executable."""

        exePath = resolvePath(call, os.environ['PATH'])
        if not os.access(exePath,5): os.chmod(exePath,0755)

        #make sure call is a binary executable or if it's a script,
        #the interpreter is specified at the top of the file, i.e. #!/bin/sh
        if not verifyExecutable(exePath):
            raise ExecutableWorkUnitError, """Please make sure executable is a binary executable
            or, if it is a script, specify the interpreter on the first line, i.e. #!/bin/sh."""
        return exePath

    def _getCommandLineList(self):
        """Return commandLineList."""

        exePath = self._getExePath(self._call)
        commandLineList = [exePath]
        commandLineList.extend(self._args)
        return map(str,commandLineList)

    def _run(self):
        """Call the command-line executable and return the result."""

        commandLineList = self._getCommandLineList()
        commandLineStr = ' '.join(commandLineList)
        if '|' in commandLineStr:
            raise ExecutableWorkUnitError, "Shell pipelines not allowed: %s" % commandLineStr
        if self._verbose: print "ExecutableWorkUnit: %s" % commandLineStr

        #detect output file specification
        outputFileMatch = None
        for i in self.outputFileRegexList:
            outputFileMatch = re.search(i, commandLineStr)
            if outputFileMatch: break

        #if output file is detected, use call
        if outputFileMatch:
            #set output file as result
            result = os.path.join(self._workDir, outputFileMatch.group(1))

            #run it
            try:
                status = call(commandLineStr, shell=True)
                if status < 0: stdErr = "Child was terminated by signal %s" % str(-status)
                else: stdErr = "Child returned %s" % str(status)
            except OSError, e:
                if re.search(r'No child processes', str(e), re.IGNORECASE):
                    status = 0
                    print >>sys.stderr, "Caught 'No child processes' exception for %s." % \
                        commandLineStr
                else:
                    stdErr = "Execution failed: %s" % e
                    status = 9999
        #otherwise use Popen
        else:
            pop = Popen(commandLineList, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=os.environ)
            try: sts = pop.wait()  #wait for child to terminate and get status
            except Exception, e: pass
            status = pop.returncode
            #print "returncode is:",status
            result = pop.stdout.read()
            stdErr = pop.stderr.read()
        if status:
            raise ExecutableWorkUnitError, "Executable failed to give a 0 exit status: %s" % stdErr

        return result

def runTemplateSub(tpl, args):
    """Run template substitution and return string."""

    template = string.strip(tpl)
    keyList = []; valList = []
    if (len(args)%2) != 0: raise RuntimeError, "Uneven number of arguments: %s" % str(args)
    for i in range(len(args)):
        if (i%2) == 0: keyList.append(args[i])
        elif (i%2) == 1: valList.append(args[i])
        else: raise RuntimeError, "Unknown remainder for %d%%2." % i
    substs = dict(zip(keyList,valList))
    template = ''.join(template.strip(' \t\r\n').splitlines())
    return string.Template(template).substitute(substs)

class TemplateWorkUnitError(Exception):
    """TemplateWorkUnit Exception class."""
    pass

class TemplateWorkUnit(WorkUnit):
    """WorkUnit subclass to interpolate a python template."""

    def _run(self):
        """Execute the template interpolation and return the result."""

        val = runTemplateSub(self._call, self._args)
        if self._verbose: print "TemplateWorkUnit: %s" % val
        return val

class RestWorkUnitError(Exception):
    """RestWorkUnit Exception class."""
    pass

class RestWorkUnit(WorkUnit):
    """WorkUnit subclass to execute a REST (one-line URL) call."""

    def _run(self):
        """Execute the REST call and return the result.
        Variables are interpolated into the REST URL template before it is executed."""

        restCall = runTemplateSub(self._call, self._args)
        encodedUrl = urllib.quote(restCall, safe=':/?&=,%')
        if self._verbose: print "RestWorkUnit: %s" % encodedUrl
        f,h = urllib.urlretrieve(encodedUrl)
        mimeType = h.gettype()
        mimeMainType, mimeSubType = mimeType.split('/')
        newFile = '%s.%s' % (os.path.basename(f),mimeSubType)
        shutil.move(f,newFile)
        os.chmod(newFile,0644)
        return newFile

class CommandLineWorkUnitError(Exception):
    """CommandLineWorkUnit Exception class."""
    pass

class CommandLineWorkUnit(ExecutableWorkUnit):
    """WorkUnit subclass to execute a command line template."""

    def _getCommandLineList(self):
        """Return commandLineList."""

        cmdLineStr = runTemplateSub(self._call, self._args)

        #get exePath and replace command with resolved path
        commandLineList = cmdLineStr.split(' ')
        exePath = self._getExePath(commandLineList[0])
        del commandLineList[0]; commandLineList.insert(0, exePath)

        #return
        return map(str,commandLineList)

class XqueryWorkUnitError(Exception):
    """XqueryWorkUnit Exception class."""
    pass

class XqueryWorkUnit(WorkUnit):
    """WorkUnit subclass to execute an XQuery and return the result."""

    def _run(self):
        """Execute the XQuery and return the result."""

        query = self._call    # XQuery as string
        xmlDocs = self._args  # XML docs, fragments, or URL's pointing to such
        if self._verbose: print "XqueryWorkUnit: %s" % query
        return indent( xmldb.getXQueryResults(xmlDocs, query) )

class XpathWorkUnitError(Exception):
    """XpathWorkUnit Exception class."""
    pass

class XpathWorkUnit(WorkUnit):
    """WorkUnit subclass to execute an XPath and return the result."""

    def _run(self):
        """Execute the XPath and return the result."""

        xpath = self._call    # XQuery as string
        xml = self._args[0]  # XML docs, fragments, or URL's pointing to such
        if self._verbose: print "XpathWorkUnit: %s" % xpath
        return runXpath(xml, xpath)

class PostWorkUnitError(Exception):
    """PostWorkUnit Exception class."""
    pass

class PostWorkUnit(WorkUnit):
    """WorkUnit subclass to execute an post and return the result."""

    def _run(self):
        """Execute the post and return the result."""

        url = self._call
        headersDict = self._args[0]
        postData = self._args[1]
        if self._verbose: print "PostWorkUnit: %s %s %s" % (url, str(headersDict), postData)
        return postCall(url, postData, headersDict, self._verbose)

class ScifloWorkUnitError(Exception):
    """Exception class for ScifloWorkUnit class."""
    pass

class ScifloWorkUnit(WorkUnit):
    """WorkUnit subclass to execute a recursive (embedded) SciFlo workflow document."""
    def __init__(self, call, args, workDir, verbose=False, wuid=None,
                 procId=None, hexDigest=None, scifloid=None, configDict={}):
        
        super(ScifloWorkUnit,self).__init__(call, args, workDir, verbose, wuid,
                                            procId, hexDigest, configDict=configDict)
        if scifloid is None: self._scifloid = generateScifloId()
        else: self._scifloid = scifloid
        self._rootWorkDir = os.path.dirname(self._workDir)
        self._scifloOutputDir = os.path.join(self._rootWorkDir, self._scifloid)
        self.setInfoItem('scifloid', self._scifloid)
        linkFile(self._scifloOutputDir,
                 os.path.join(self._workDir, 'scifloOutputDir'))

    def _run(self):
        """Execute the embedded SciFlo work unit and return the result."""
        from executor import runSciflo
        return runSciflo(self._call, self._args, scifloid=self._scifloid,
                         workDir=self._rootWorkDir,
                         outputDir=self._scifloOutputDir)

class ParMapWorkUnitError(Exception):
    """ParMapWorkUnit Exception class."""
    pass

class ParMapWorkUnit(PythonFunctionWorkUnit):
    """WorkUnit subclass to execute a number of jobs in parallel using HyCSDS."""

    def __init__(self, call, args, workDir, verbose=False, wuid=None,
                 procId=None, hexDigest=None, configDict={}):
        """Save call, args, and working directory."""

        # get call, queue name, and async flag; amqp endpoint is specified by celeryconfig.py in hysds
        call, self._job_queue, self._async = call.split('|')
        typ, call = call.split(':?')
        if typ != 'python':
            raise ParMapWorkUnitError("Invalid specification for ParMapWorkUnit binding: %s" % typ)

        # set async flag
        self._async = True if self._async == 'true' else False

        # get HySDS context if exists
        ctx_file = os.path.abspath('_context.json')
        self._ctx = {}
        if os.path.exists(ctx_file):
            print "Loading HySDS context JSON from %s." % ctx_file
            f = open(ctx_file)
            self._ctx = json.load(f)
            f.close()
        else:
            print "No HySDS context JSON found at %s. Proceeding without it." % ctx_file

        super(ParMapWorkUnit,self).__init__(call, args, workDir, verbose, wuid,
                                            procId, hexDigest, configDict=configDict)

    def _run(self):
        """Submit the parallel work jobs, wait for all to complete, and return the results."""

        # get map and work functions
        workFunc = getFunction(self._call)

        # get list of jobs
        jobs = []
        if not isinstance(self._args[0], (types.ListType, types.TupleType)):
            raise ParMapWorkUnitError("Invalid type for ParWorkUnit argument 1: %s\n%s" % (type(self._args[0]), self._args[0]))
        
        for i, arg in enumerate(self._args[0]):
            workArgs = [arg]
            for mapArg in self._args[1:]:
                if isinstance(mapArg, (types.ListType, types.TupleType)) and len(mapArg) == len(self._args[0]):
                    workArgs.append(mapArg[i])
                else: workArgs.append(mapArg)

            # append work unit id and job number for job tracking
            job = apply(workFunc, workArgs, {
                'wuid': self._wuid,
                'job_num': i
            })

            # update context in job payload
            job.setdefault('context', {}).update(self._ctx)
 
            # propagate priority and container configs from HySDS context
            job['priority'] = int(self._ctx.get('job_priority', 0))
            job['username'] = self._ctx.get('username', None)
            job['container_image_name'] = self._ctx.get('container_image_name', None)
            job['container_image_url'] = self._ctx.get('container_image_url', None)
            job['container_mappings'] = self._ctx.get('container_mappings', {})
            
            # set tag from HySDS context
            if 'tag' in self._ctx: job['tag'] = self._ctx['tag']
            
            jobs.append(job)

        # submit jobs and wait for execution
        group_res = group(submit_job.s(job).set(queue=self._job_queue) for job in jobs)()
        while True:
            ready = group_res.ready()
            if ready: break
            time.sleep(5)
        task_ids = group_res.join(timeout=10.)

        # if async, return task IDs; otherwise harvest results in a group then return
        if self._async: return [id for id in task_ids]
        else:
            res = GroupResult(id=uuid.uuid4(), results=[AsyncResult(id[0]) for id in task_ids])
            while True:
                ready = res.ready()
                if ready: break
                time.sleep(5)
            return [i for i in res.join(timeout=10.)]

class ParWorkUnitError(Exception):
    """ParWorkUnit Exception class."""
    pass

class ParWorkUnit(ParMapWorkUnit):
    """WorkUnit subclass to execute a job using HyCSDS."""

    def __init__(self, call, args, workDir, verbose=False, wuid=None,
                 procId=None, hexDigest=None, configDict={}):
        args[0] = [args[0]]
        super(ParWorkUnit,self).__init__(call, args, workDir, verbose, wuid,
                                         procId, hexDigest, configDict=configDict)

    def _run(self):
        results = super(ParWorkUnit,self)._run()
        return results[0]
