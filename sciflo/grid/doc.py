# -----------------------------------------------------------------------------
# Name:        doc.py
# Purpose:     Various classes and functions related to the handling of
#              sciflo docs.
#
# Author:      Brian Wilson/Gerald Manipon
#
# Created:     Mon Sep 12 09:11:01 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import os
import re
import types
import copy
import urllib.request
import urllib.parse
import urllib.error
from urllib.parse import urlparse
import sys
import lxml.etree
from pkg_resources import resource_string

from sciflo.utils import (validateXml, getXmlEtree, SCIFLO_NAMESPACE,
                          XSD_NAMESPACE, PY_NAMESPACE, parseTag, isBundle, parseElement, getTypedValue,
                          IMPLICIT_CONVERSIONS, runXpath, runDot)
from .utils import (generateWorkUnitConfigId, getHexDigest, getFunction,
                    dotFlowChartFromDependencies)
from .postExecution import getConversionFunctionString

NS = {'sf': '{' + SCIFLO_NAMESPACE + '}',
      'xs': '{' + XSD_NAMESPACE + '}',
      'py': '{' + PY_NAMESPACE + '}'}


def translatePrefixes(xpath, namespaces):
    """Translate prefix:tag elements in an XPath into qualified names."""
    elts = []
    for elt in xpath.split('/'):
        if elt.find(':') > 0:
            prefix, tag = elt.split(':')
            if prefix in namespaces:
                elts.append(namespaces[prefix] + tag)
            else:
                raise RuntimeError(
                    'Unknown namespace with prefix %s in XPath: %s' % (prefix, xpath))
        else:
            elts.append(elt)
    return '/'.join(elts)


def ns(xpath): return translatePrefixes(xpath, namespaces=NS)


# sciflo schema xml
SCIFLO_SCHEMA_XML = resource_string(__name__, 'sciflo.xsl').decode()


class WorkUnitConfig(object):
    """Class containing work unit configuration."""

    def __init__(self, procCount, id, typ, call, args, stageFiles=[],
                 argIdxsResolvedGloballyDict={}):
        self._procCount = procCount
        self._id = id
        self._type = typ
        self._call = call
        self._args = args
        self._stageFiles = stageFiles
        self.argIdxsResolvedGloballyDict = argIdxsResolvedGloballyDict
        self._postExecutionTypeList = []
        self._workUnitConfigId = generateWorkUnitConfigId()
        # flag indicating if work unit is fully resolved and can be spawned
        self._resolvedFlag = 0
        self._implicitFlag = False

    def getWorkUnitConfigId(self): return self._workUnitConfigId
    def getResolvedFlag(self): return self._resolvedFlag
    def setResolvedFlag(self, val): self._resolvedFlag = val
    def getProcCount(self): return self._procCount
    def getId(self): return self._id
    def getType(self): return self._type
    def getCall(self): return self._call
    def getArgs(self): return self._args
    def getStageFiles(self): return self._stageFiles
    def getPostExecutionTypeList(self): return self._postExecutionTypeList
    def setImplicitFlag(self, val): self._implicitFlag = val
    def getImplicitFlag(self): return self._implicitFlag

    def getAll(self):
        "Return all attributes as a list."
        return [self._workUnitConfigId, self._resolvedFlag, self._procCount,
                self._id, self._type, self._call, self._args, self._stageFiles,
                self._postExecutionTypeList]

    def getHexDigest(self):
        return getHexDigest([self._type, self._call, self._args, self._stageFiles])

    def addPostExecutionType(self, outputIndex, postExecutionType):
        """Add a postExecution type to be performed on the output indexed
        by the first arg.  Returns the index of the post execution result
        in the post execution result list.  If it already exists, just return
        the index."""
        try:  # check if conversion already exists
            return self._postExecutionTypeList.index((outputIndex, postExecutionType))
        except:
            # append output index and postexecution type
            self._postExecutionTypeList.append(
                (outputIndex, postExecutionType))
            # return index of post execution type list;
            return len(self._postExecutionTypeList)-1


class UnresolvedArgumentError(Exception):
    """UnresolvedArgument Exception class."""
    pass


class UnresolvedArgument(object):
    """Class representing an unresolved argument."""

    def __init__(self, procId, outputIndex=None):
        self._procId = procId
        self._outputIndex = outputIndex
        self._getFromPostExecutionOutput = False
        self._postExecutionOutputIndex = None
        self._rewriteFile = None
        self._error = None

    def getId(self): return self._procId
    def getOutputIndex(self): return self._outputIndex
    def setOutputIndex(self, index): self._outputIndex = index
    def getPostExecutionOutputIndex(
        self): return self._postExecutionOutputIndex

    def setPostExecutionOutputIndex(self, index):
        self._getFromPostExecutionOutput = True
        self._postExecutionOutputIndex = index

    def getError(self): return self._error
    def setError(self, error): self._error = error
    def getRewriteFile(self): return self._rewriteFile

    def addRewrite(self, outputFile):
        """Rewrite output to output file."""
        self._rewriteFile = outputFile
        return True

    def getOutputFromPostExecution(self):
        """Return true if output to be returned is from post execution results.
        False if output to be returned is from normal output."""
        return self._getFromPostExecutionOutput


class DocumentArgsList(list):
    """Document argument list class."""

    def __init__(self, docStr, *args, **kwargs):
        self.docStr = docStr
        super(DocumentArgsList, self).__init__(*args, **kwargs)


class ScifloError(Exception):
    """Sciflo Exception class."""
    pass


class Sciflo(object):
    """Class representing a SciFlo document."""
    # Class attributes
    typeAttribute = 'type'
    unitAttribute = 'unit'
    kindAttribute = 'kind'
    defaultValueAttribute = 'defaultValue'

    # Regex patterns
    inputsPattern1 = re.compile(r'^\s*(in$|inputs$|in[a-z]*\.(\S+))')
    inputsPattern2 = re.compile(r'^\s*in[a-z]*\.(\S+)')
    previousPattern = re.compile(r'^\s*prev[a-z]*\.*(\S*)')
    embeddedAtPattern = re.compile(r'([^@]*)@(@[^@]+)@([^@]*)')
    twoPartNamePattern = re.compile(r'^([^\.]+)\.(.+)$')

    def __init__(self, xmlDoc, globalInputArgs=[], globalInputDict={}, debugMode=False):
        self._xmlString = xmlDoc
        self._globalInputArgs = globalInputArgs
        self._globalInputDict = globalInputDict
        self._debugMode = debugMode

        # Make sure not both globalInputArgs and globalInputDict were specified
        if len(self._globalInputArgs) > 0 and len(self._globalInputDict) > 0:
            raise ScifloError(
                "Cannot specify both globalInputArgs and globalInputDict args.")

        # Validate sciflo xml with xsd
        validated, validationError = validateXml(
            self._xmlString, SCIFLO_SCHEMA_XML)
        if not validated:
            raise ScifloError(
                "Validation of sciflo xml failed: %s" % str(validationError))

        # Parse XML doc
        self._eltDoc, self._namespacePrefixDict = getXmlEtree(xmlDoc)
        doc = self._eltDoc

        # attributes
        self._flowName = doc.find(ns('sf:flow')).get('id')
        self._description = doc.find(ns('sf:flow/sf:description')).text
        self._flowInputs = doc.find(ns('sf:flow/sf:inputs'))
        self._flowOutputs = doc.find(ns('sf:flow/sf:outputs'))
        self._flowProcesses = doc.find(ns('sf:flow/sf:processes'))
        self._flowProcessesProcess = doc.findall(
            ns('sf:flow/sf:processes/sf:process'))

        self._workUnitConfigs = []
        self._workUnitConfigsForDot = []
        self._implicitWorkUnitConfigs = []
        self._flowOutputConfigs = []

        # Create input dict, making sure that a global input tagname is not used more than once
        if len(self._globalInputDict) > 0:
            self._inputDict = self._globalInputDict
        else:
            self._inputDict = {}
        self.globalInputs = []
        inputIndex = 0
        for globalInputElt in self._flowInputs:
            inputTag = globalInputElt.tag
            if inputTag is None:
                continue
            if inputTag in self.globalInputs:
                raise ScifloError(
                    "Global input tag '%s' already in use." % inputTag)
            else:
                self.globalInputs.append(inputTag)

            # Fill inputDict
            eltNs, eltTag = parseTag(inputTag)
            try:
                self._inputDict[eltTag] = self._globalInputArgs[inputIndex]
            except:
                pass
            inputIndex += 1

        # overwrite global inputs in doc
        if len(self._inputDict) > 0:
            for k in list(self._inputDict.keys()):
                o = doc.find(ns('sf:flow/sf:inputs/%s' % k))
                if o is None:
                    raise ScifloError(
                        "Unknown global input %s (%s)." % (k, self._inputDict[k]))
                o.text = str(self._inputDict[k])

        # Make sure that global output tagnames were not used more than once
        self.globalOutputs = []
        for globalOutputElt in self._flowOutputs:
            outputTag = globalOutputElt.tag
            if outputTag is None:
                continue
            if outputTag in self.globalOutputs:
                raise ScifloError(
                    "Global output tag '%s' already in use." % outputTag)
            else:
                self.globalOutputs.append(outputTag)

        # Make sure that process id's were not used more than once
        procIds = []
        for procElt in self._flowProcessesProcess:
            procId = procElt.get('id')
            if procId in procIds:
                raise ScifloError(
                    "Id '%s' has been used by a previous process." % procId)
            else:
                procIds.append(procId)

        # resolved flag
        self.resolved = False

        # dot strings
        self.dot = None
        self.fullDot = None

        # svg strings
        self.svg = None
        self.fullSvg = None

    def getName(self): return self._flowName
    def getDescription(self): return self._description
    def getWorkUnitConfigs(self): return self._workUnitConfigs
    def getWorkUnitConfigsForDot(self): return self._workUnitConfigsForDot
    def getImplicitWorkUnitConfigs(self): return self._implicitWorkUnitConfigs
    def getFlowOutputConfigs(self): return self._flowOutputConfigs

    def _resolveInlineBinding(self, bindingElt):
        """Resolve a work unit's inline binding and return its type, call endpoint,
        and call."""

        bindingChildren = bindingElt.getchildren()
        headerDict = {}
        if len(bindingChildren) > 0:
            bindingVal = bindingChildren[0].text
            headersElt = bindingChildren[1]
            for headerElt in headersElt:
                headerDict[headerElt[0].text] = headerElt[1].text
        else:
            bindingVal = bindingElt.text.strip()
        match = re.search(r'^(.*?):(.*)$', bindingVal, re.S)
        if match:
            typ, val = match.groups()
        else:
            raise ScifloError("Failed to parse binding: %s" %
                              bindingElt.text.strip())

        # inline python code
        matchPyFunc = re.search(r'(def\s+.*)$', val, re.S)
        if typ == 'python' and matchPyFunc:
            wuType = 'inline python function'
            endpoint = None
            call = matchPyFunc.group(1)
        # sciflo
        elif typ == 'sciflo':
            wuType = typ
            endpoint = val
            protocol, netloc, path, params, query, frag = urlparse(val)
            if protocol == '':
                with open(val) as f:
                    call = f.read()
            else:
                call = urllib.request.urlopen(val).read()
        # rest
        elif typ in ('rest', 'template', 'cmdline'):
            wuType = typ
            endpoint = None
            call = re.search(r'\??\s*(.*)$', val, re.S).group(1)
        # post
        elif typ == 'post':
            wuType = typ
            endpoint = headerDict
            call = val
        # xpath
        elif typ == 'xpath':
            wuType = typ
            endpoint = None
            call = re.search(r'\??(.*)$', val, re.S).group(1)
        # parallel map python
        elif typ == 'map':
            wuType = 'map python function'
            endpoint = None
            job_queue = bindingElt.get('job_queue', None)
            async_flag = bindingElt.get('async', 'false').lower()
            if job_queue is None:
                raise ScifloError(
                    "You must specify 'job_queue' attribute for binding type 'map'.")
            call = '%s|%s|%s' % (val, job_queue, async_flag)
            return (wuType, endpoint, call)
        # parallel python
        elif typ == 'parallel':
            wuType = 'parallel python function'
            endpoint = None
            job_queue = bindingElt.get('job_queue', None)
            async_flag = bindingElt.get('async', 'false').lower()
            if job_queue is None:
                raise ScifloError(
                    "You must specify 'job_queue' attribute for binding type 'parallel'.")
            call = '%s|%s|%s' % (val, job_queue, async_flag)
            return (wuType, endpoint, call)
        # handle python function, soap, binary, script, xquery, and bindings
        else:
            if typ in ('binary', 'script'):
                wuType = 'executable'
            elif typ == 'python':
                wuType = 'python function'
            else:
                wuType = typ
            match = re.search(r'^(.*)\?(.*)$', val, re.S)
            if match:
                endpoint, method = match.groups()
                if wuType == 'executable':
                    match2 = re.search(r'^(\w+?)(?::(.*))?$', endpoint)
                    if match2:
                        archOrLang, endpoint = match2.groups()
                        if endpoint is None:
                            endpoint = ''
                    else:
                        raise ScifloError(
                            "Cannot parse executable binding: %s" % endpoint)
                call = method
            else:
                raise ScifloError(
                    "Failed to parse %s binding: %s" % (typ, val))
        # import and eval python if debugMode
        if self._debugMode:
            sys.path.insert(1, getUserPubPackagesDir())
            sys.path.insert(1, getUserPvtPackagesDir())
            if wuType == 'python function':
                try:
                    getFunction(call)
                except Exception as e:
                    print(('''Got exception trying to load module in debug mode.  \
This module may be a staged file or bundle: %s''' % str(e)))
            elif wuType == 'inline python function':
                try:
                    eval(call)
                except Exception as e:
                    print(
                        ('''Got exception trying to eval inline python in debug mode: %s''' % str(e)))
        isBundle(endpoint)
        return (wuType, endpoint, call)

    def _resolveFromGlobalInputs(self, tag, val):
        """Resolve a work unit input from global inputs section."""

        # If '@#inputs' was specified, find the matching top level input with the same tag
        matchingElt = None
        if val == '@#inputs':
            matchingElt = self._flowInputs.find(NS['sf']+tag)
            if matchingElt is None:
                matchingElt = self._flowInputs.find(tag)
        else:
            match = re.search(r'^@#inputs\.(\w+)$', val)
            if match:
                matchingElt = self._flowInputs.find(NS['sf']+match.group(1))
                if matchingElt is None:
                    matchingElt = self._flowInputs.find(match.group(1))
            else:
                match = re.search(r'^@#inputs\?(.*)$', val)
                if match:
                    xpathStr = match.group(1)
                    return (None, None, runXpath(self._flowInputs, xpathStr, self._namespacePrefixDict))
        if matchingElt is None:
            raise ScifloError("Failed to find %s in top level inputs." % tag)

        # Parse matching element
        (eltNs, eltTag, eltType, eltVal) = parseElement(matchingElt)

        # Get typed value
        typedEltVal = getTypedValue(eltType, eltVal)
        return (eltTag, eltType, typedEltVal)

    def _resolveFromProcessId(self, tag, val, resolvingProcId):
        """Resolve a work unit input from process specified by id."""

        resolvingProcElts = self._flowProcesses.xpath(
            './sf:process[@id="%s"]' % resolvingProcId,
            namespaces=self._namespacePrefixDict)
        if len(resolvingProcElts) == 0:
            raise ScifloError(
                "Failed to find a resolving process with id %s." % resolvingProcId)
        else:
            resolvingProcElt = resolvingProcElts[0]

        outputElts = resolvingProcElt.findall(ns('sf:outputs/*'))
        numOutputs = len(outputElts)
        outputTagIndex = None
        outputElement = None
        xpathStr = None

        # If input was implied, look for matching tag in resolving process' output
        match = re.search(r'^@#\w+?\?(.+)$', val)
        if val in ('@#%s' % resolvingProcId, '@#previous') or match:
            if match:
                xpathStr = match.group(1)
            if numOutputs == 1:
                outputTagIndex = None
                outputElement = outputElts[0]
            else:
                for index, outputElt in enumerate(outputElts):
                    outputNs, outputTag = parseTag(outputElt.tag)
                    if outputTag == tag:
                        outputTagIndex = index
                        outputElement = outputElt
                        break
        else:
            match = re.search(r'^@#\w+?\.(.+)$', val)
            if match:
                match2 = re.search(r'^(\w+)(?:\?(.*))?$', match.group(1))
                if match2:
                    inputName, xpathStr = match2.groups()
                    for index, outputElt in enumerate(outputElts):
                        outputNs, outputTag = parseTag(outputElt.tag)
                        if outputTag == inputName:
                            if numOutputs == 1:
                                outputTagIndex = None
                            else:
                                outputTagIndex = index
                            outputElement = outputElt
                            break
                else:
                    raise ScifloError(
                        "Failed to extract input name from %s." % val)
            else:
                raise ScifloError("Failed to extract  %s." % val)

        # Raise error if outputTagIndex is None
        if outputElement is None:
            raise ScifloError("Failed to find output tag %s in resolving process %s." %
                              (tag, resolvingProcId))

        # Parse matching element
        (eltNs, eltTag, eltType, eltVal) = parseElement(outputElement)
        # print eltNs, eltTag, eltType, eltVal
        argObj = UnresolvedArgument(resolvingProcElt.get('id'), outputTagIndex)
        if xpathStr:
            if xpathStr.startswith('xpath:'):
                xpathStr = 'sf:%s' % xpathStr
            if not xpathStr.startswith('sf:xpath:'):
                xpathStr = 'sf:xpath:%s' % xpathStr
        if xpathStr:
            eltType = xpathStr
        return (eltType, argObj)

    def _resolveFromRedirect(self, tag, val, resolvingProcId):
        """Resolve a work unit input from a redirect."""
        raise NotImplementedError("Not yet implemented.")

    def resolve(self):
        """Resolve:
            1.  Explicit argument dependencies
            2.  Implicit argument dependency conversion by adding additional
                post execution instructions and redirecting that output to the
                work unit.
            3.  Final output post execution instructions.
            4.  executionNode info for work units w/o it
            5.  Unresolved input arguments by prompting for input where unresolved
                can mean:
                    a.  argument intentionally left out
                    b.  exception in dependent work unit
        """
        globallyResolvedInputIdxsDict = {}

        def _resolveInputs(wuArgs, previousProcId, processCount, inputsType, inputsElt, root=True):
            # get inputs
            inputTags = []
            if inputsType == 'arglist':
                inputsList = inputsElt
            elif inputsType == 'document':
                inputsList = inputsElt.getiterator()
            else:
                raise ScifloError("Unknown inputsType: %s" % inputsType)

            # check
            if inputsType == 'document' and wuType in ('rest', 'template', 'xquery', 'cmdline'):
                raise ScifloError("""Cannot specify 'document' inputs type with rest, template,
                    cmdline, or xquery work units.""")

            # Loop over input elements
            inputEltIdx = 0
            for inputElt in inputsList:

                # skip if comment
                if isinstance(inputElt, lxml.etree._Comment):
                    continue

                # get input info
                (inputNs, inputTag, inputType, inputVal, eltKids) = parseElement(
                    inputElt, returnChildren=True)

                # implicit document type
                if root and inputsType == 'arglist' and inputType is None and eltKids is not None:
                    inputType = 'document'

                # check that inputTag is not already used if argslist mode
                if inputsType == 'arglist':
                    if inputElt.tag in inputTags:
                        raise ScifloError(
                            "Input tag '%s' already in use." % inputElt.tag)
                    else:
                        inputTags.append(inputElt.tag)

                # implicit?
                if inputVal is None:
                    if inputsType == 'arglist':
                        inputVal = '@#inputs.%s' % inputTag
                    else:
                        inputVal = ''

                # indicator to say if resolving input was from global inputs or
                # another process
                resolvedFrom = None

                #resolve @-links
                if inputVal.startswith('@#inputs.') or \
                   inputVal.startswith('@#inputs?') or \
                   inputVal == '@#inputs':

                    # get type and inputArgVal from top level inputs
                    (resolvedInputTag, resolvedInputType, resolvedInputArg) = \
                        self._resolveFromGlobalInputs(inputTag, inputVal)

                    # set resolving type
                    resolvedFrom = 'global input'

                    # append input index
                    globallyResolvedInputIdxsDict[inputEltIdx] = resolvedInputTag

                elif inputVal.startswith('@#previous.') or \
                        inputVal.startswith('@#previous?') or \
                        inputVal == '@#previous':

                    # get inputArgVal
                    (resolvedInputType, resolvedInputArg) = self._resolveFromProcessId(
                        inputTag, inputVal, previousProcId)

                    # set resolving type
                    resolvedFrom = 'process output'

                elif inputVal.startswith('@#'):

                    # get resolving proc id
                    match = re.search(r'@#(\w+)[\.\?]?', inputVal)
                    if match:
                        resolvingProcId = match.group(1)
                    else:
                        raise ScifloError(
                            "Couldn't parse process id from %s." % inputVal)

                    # get inputArgVal
                    (resolvedInputType, resolvedInputArg) = self._resolveFromProcessId(
                        inputTag, inputVal, resolvingProcId)

                    # set resolving type
                    resolvedFrom = 'process output'

                elif inputType == 'document' and inputsType == 'arglist':
                    # resolve inputs
                    newElt = lxml.etree.Element(inputElt.tag)
                    for child in inputElt.getchildren():
                        newElt.append(child)
                    (thisWuArgs, processCount) = _resolveInputs([], previousProcId,
                                                                processCount, inputType, newElt, root=False)
                    resolvedInputArg = wuArgs.append(thisWuArgs)
                    continue

                else:
                    match = re.search(r'^@(.+)#(.+)$', inputVal)
                    if match:

                        # get redirect link and component
                        redirectLink, comp = match.groups()

                        # get inputArgVal
                        (resolvedInputType, resolvedInputArg) = self._resolveFromRedirect(
                            inputTag, inputVal, redirectLink, comp)

                        # set resolving type
                        resolvedFrom = 'redirect'

                    else:

                        if inputVal.startswith('@'):
                            raise ScifloError(
                                "Cannot handle input value %s." % inputVal)
                        # no resolving needed
                        else:

                            # if arglist type
                            if inputsType == 'arglist':
                                # if inputVal is None, then we need to prompt
                                if inputVal is None:

                                    # prompt for input
                                    (resolvedInputType,
                                     resolvedInputArg) = self._promptForInput()

                                else:
                                    resolvedInputArg = inputVal
                                    resolvedInputType = inputType

                                # coerce inputType if not None
                                if resolvedInputType is not None:
                                    convFunc = getFunction(
                                        getConversionFunctionString(None, resolvedInputType,
                                                                    self._namespacePrefixDict))
                                    resolvedInputArg = convFunc(
                                        resolvedInputArg)
                            # do document
                            else:
                                wuArgs.append(None)
                                continue

                # check for implicit xpath
                if isinstance(resolvedInputType, str):
                    xpathMatch = re.search(
                        r'^sf:xpath:(.*)$', resolvedInputType, re.IGNORECASE)
                    if xpathMatch:
                        xpathMatchStr = xpathMatch.group(1)
                        xpathDigest = getHexDigest(
                            ['xpath', xpathMatchStr, [resolvedInputArg], []])
                        foundXpathWu = None
                        for implicitWuConfig in self._implicitWorkUnitConfigs:
                            if xpathDigest == implicitWuConfig.getHexDigest():
                                foundXpathWu = implicitWuConfig.getId()
                        if foundXpathWu:
                            resolvedInputArg = UnresolvedArgument(foundXpathWu)
                        else:
                            xpathWuId = "implicit_%05d" % processCount
                            implicitXpathWorkUnitConfig = WorkUnitConfig(processCount, xpathWuId,
                                                                         'xpath', xpathMatchStr, [resolvedInputArg], [])
                            implicitXpathWorkUnitConfig.setImplicitFlag(True)
                            self._workUnitConfigs.append(
                                implicitXpathWorkUnitConfig)
                            self._workUnitConfigsForDot.append(
                                copy.deepcopy(implicitXpathWorkUnitConfig))
                            self._implicitWorkUnitConfigs.append(
                                implicitXpathWorkUnitConfig)
                            resolvedInputArg = UnresolvedArgument(xpathWuId)
                            processCount += 1

                # if input type and resolvedInputType are not the same, we need to
                # add a postExecution type to the resolving process or
                # create a work unit to do conversion if it resolved to a global
                # input.  If input type is None, then no conversion is needed since
                # we assume no conversion was needed.
                # print "######",id, inputType, resolvedInputType
                if inputType is None or inputType == resolvedInputType:
                    pass
                else:

                    # if came from a global input or a process output with an implicit conversion,
                    # need a conversion work unit ahead of this one
                    if resolvedFrom in ('global input', 'redirect') or \
                        (resolvedFrom == 'process output' and (
                            re.search(r'^(sf:xpath:|xpath:)', inputType, re.IGNORECASE) or
                            inputType in IMPLICIT_CONVERSIONS)):

                        # get xpath
                        xpathMatch = re.search(
                            r'^(?:sf:)?(?:xpath:)(.*)$', inputType, re.IGNORECASE)
                        if xpathMatch:
                            implicitType = 'xpath'
                            convFuncStr = xpathMatch.group(1)
                        else:
                            implicitType = 'python function'
                            convFuncStr = getConversionFunctionString(resolvedInputType,
                                                                      inputType, self._namespacePrefixDict)

                        # get conversion hex digest
                        convHexDigest = getHexDigest([implicitType, convFuncStr,
                                                      [resolvedInputArg], []])

                        # check if there already exists an implicit work unit
                        # for this conversion
                        found = None
                        for implicitWuConfig in self._implicitWorkUnitConfigs:

                            # match
                            if convHexDigest == implicitWuConfig.getHexDigest():
                                found = implicitWuConfig.getId()

                        # if found, use that implicit work unit's output
                        if found:
                            resolvedInputArg = UnresolvedArgument(found)
                        # otherwise add an implicit work unit
                        else:
                            # get id
                            wuId = "implicit_%05d" % processCount

                            # get implicit work unit config
                            implicitWorkUnitConfig = WorkUnitConfig(processCount, wuId,
                                                                    implicitType, convFuncStr, [
                                                                        resolvedInputArg],
                                                                    [])
                            implicitWorkUnitConfig.setImplicitFlag(True)

                            # append to list of work units and implicit work units
                            self._workUnitConfigs.append(
                                implicitWorkUnitConfig)
                            self._workUnitConfigsForDot.append(
                                copy.deepcopy(implicitWorkUnitConfig))
                            self._implicitWorkUnitConfigs.append(
                                implicitWorkUnitConfig)

                            # set resolved input arg as the output of this implicit
                            # work unit
                            resolvedInputArg = UnresolvedArgument(wuId)

                            # increment counter
                            processCount += 1

                    # if came from another process' output not with an implicit conversion, just add a postexecution
                    # type to that process' postExecution list.
                    elif resolvedFrom == 'process output':

                        # make sure resolvedInputArg is a UnresolvedArgument type
                        if not isinstance(resolvedInputArg, UnresolvedArgument):
                            raise ScifloError(
                                "Resolved input argument is not UnresolvedArgument type.")

                        # get resolving proc id
                        resolvingProcId = resolvedInputArg.getId()

                        # get WorkUnitConfig from list
                        postExecIndex = None
                        for wuConfig in self._workUnitConfigs:

                            # make sure
                            # if id matches, add conversion post exec
                            if wuConfig.getId() == resolvingProcId:

                                # add post execution instructions
                                # print resolvedInputType, inputType
                                postExecIndex = wuConfig.addPostExecutionType(
                                    resolvedInputArg.getOutputIndex(),
                                    getConversionFunctionString(resolvedInputType,
                                                                inputType, self._namespacePrefixDict))

                                # changed resolvedInputArg to look at postExecution results
                                resolvedInputArg.setPostExecutionOutputIndex(
                                    postExecIndex)

                                break

                        # raise error if postExecIndex was not set
                        if postExecIndex is None:
                            raise ScifloError(
                                "Failed to set post execution result index.")

                    # fail
                    else:
                        raise ScifloError(
                            "Unrecognized value for resolvedFrom: %s" % resolvedFrom)

                # append to wuArgs; if this is a rest, template or cmdline work unit,
                # this hack allows these work units to create the dict; it needs to
                # fill the template
                if wuType in ('rest', 'template', 'cmdline'):
                    wuArgs.extend([inputTag, resolvedInputArg])
                else:
                    wuArgs.append(resolvedInputArg)

                inputEltIdx += 1

            # if document inputs type
            if inputsType == 'document':
                wuArgs = DocumentArgsList(lxml.etree.tostring(
                    inputsElt, pretty_print=True, encoding='unicode'), wuArgs)

            # print "##########all:",processCount,id,wuType,wuCall, wuArgs,stageFiles
            # print "##########previousProcId:",previousProcId
            return (wuArgs, processCount)

        # return if already resolved
        if self.resolved:
            return

        self._workUnitConfigs = []
        self._workUnitConfigsForDot = []
        self._implicitWorkUnitConfigs = []
        procs = self._flowProcessesProcess

        # Loop over processes and create work unit configs
        processCount = 0
        previousProcId = None
        for proc in procs:
            processCount += 1
            id = proc.get('id', None)
            # If id is none, add attribute to elementtree doc
            if id is None:
                id = 'process_%05d' % processCount
                proc.set('id', id)

            inputsElt = proc.find(ns('sf:inputs'))
            inputsType = inputsElt.get('type', 'arglist')
            if inputsType not in ('document', 'arglist'):
                raise ScifloError("Unknown inputs type: %s"
                                  % inputsType)
            outputsElt = proc.find(ns('sf:outputs'))
            operatorElt = proc.find(ns('sf:operator'))
            opElt = operatorElt.find(ns('sf:op'))
            inlineBindingElt = opElt.find(ns('sf:binding'))
            wuType, wuCallEndpoint, wuCall = self._resolveInlineBinding(
                inlineBindingElt)

            stageFiles = []
            wuArgs = []
            # Add module or binary files if type is python function or executable
            if wuType == 'python function' or wuType == 'executable':
                if wuCallEndpoint:
                    stageFiles.append(wuCallEndpoint)
            elif wuType in ('soap', 'post'):
                wuArgs.append(wuCallEndpoint)

            # resolve inputs
            (wuArgs, processCount) = _resolveInputs(wuArgs, previousProcId, processCount, inputsType,
                                                    inputsElt)

            # append WorkUnitConfig to list
            thisWuConfig = WorkUnitConfig(processCount, id, wuType, wuCall, wuArgs, stageFiles,
                                          globallyResolvedInputIdxsDict)
            self._workUnitConfigs.append(thisWuConfig)
            self._workUnitConfigsForDot.append(copy.deepcopy(thisWuConfig))

            # set previousProcId
            previousProcId = id

        # clear flow output configs list
        self._flowOutputConfigs = []

        # loop over outputs
        for flowOutput in self._flowOutputs:
            # skip if comment
            if isinstance(flowOutput, lxml.etree._Comment):
                continue

            # parse output element
            (eltNs, eltTag, eltType, eltVal) = parseElement(flowOutput)

            # check if processOutput attribute was specified
            globalOutputVal = None
            procOutputAttr = flowOutput.get('from', None)
            if procOutputAttr:
                globalOutputVal = flowOutput.text
                eltVal = procOutputAttr

            # get resolving proc id
            match = re.search(r'^@#(\w+)\.?', eltVal)
            if match:
                resolvingProcId = match.group(1)
            else:
                raise ScifloError(
                    "Couldn't parse process id from %s." % eltVal)

            # get resolved type and UnresolvedArgument object
            (resolvedType, resolvedArg) = self._resolveFromProcessId(eltTag,
                                                                     eltVal, resolvingProcId)

            # add implicit xpath if detected
            if isinstance(resolvedType, str):
                xpathMatch = re.search(
                    r'^sf:xpath:(.*)$', resolvedType, re.IGNORECASE)
                if xpathMatch:
                    xpathMatchStr = xpathMatch.group(1)
                    xpathDigest = getHexDigest(
                        ['xpath', xpathMatchStr, [resolvedArg], []])
                    foundXpathWu = None
                    for implicitWuConfig in self._implicitWorkUnitConfigs:
                        if xpathDigest == implicitWuConfig.getHexDigest():
                            foundXpathWu = implicitWuConfig.getId()
                    if foundXpathWu:
                        resolvedArg = UnresolvedArgument(foundXpathWu)
                    else:
                        processCount = len(self._workUnitConfigs)+1
                        xpathWuId = "implicit_%05d" % processCount
                        implicitXpathWorkUnitConfig = WorkUnitConfig(processCount, xpathWuId,
                                                                     'xpath', xpathMatchStr, [resolvedArg], [])
                        implicitXpathWorkUnitConfig.setImplicitFlag(True)
                        self._workUnitConfigs.append(
                            implicitXpathWorkUnitConfig)
                        self._workUnitConfigsForDot.append(
                            copy.deepcopy(implicitXpathWorkUnitConfig))
                        self._implicitWorkUnitConfigs.append(
                            implicitXpathWorkUnitConfig)
                        resolvedArg = UnresolvedArgument(xpathWuId)

            # need conversion?
            if eltType is None or eltType == resolvedType:

                # if global output val is defined, set up a rewrite;
                # otherwise no conversion needed
                if globalOutputVal:
                    resolvedArg.addRewrite(globalOutputVal)

            # need to add post execution
            else:

                # get WorkUnitConfig from list
                postExecIndex = None
                for wuConfig in self._workUnitConfigs:

                    # if id matches, add conversion post exec
                    if wuConfig.getId() == resolvingProcId:

                        # add post execution instructions
                        postExecIndex = wuConfig.addPostExecutionType(
                            resolvedArg.getOutputIndex(),
                            getConversionFunctionString(resolvedType,
                                                        eltType, self._namespacePrefixDict))

                        # changed resolvedInputArg to look at postExecution results
                        resolvedArg.setPostExecutionOutputIndex(postExecIndex)

                        # if global output val is defined, set up a rewrite
                        if globalOutputVal:
                            if re.search(r'File$', eltType):
                                resolvedArg.addRewrite(globalOutputVal)
                            else:
                                raise ScifloError("Cannot rewrite output from process %s.  Specify file type in global output %s." %
                                                  (resolvingProcId, eltTag))
                        # otherwise get rewrite file from file type and extension
                        else:
                            extMatch = re.search(r'^\w+:(\w+)File$', eltType)
                            if extMatch:
                                thisExt = extMatch.group(1)
                                for flowProc in self._flowProcessesProcess:
                                    if str(flowProc.get('id')) == resolvingProcId:
                                        procOutputs = flowProc.find(
                                            ns('sf:outputs'))
                                        idx = resolvedArg.getOutputIndex()
                                        if idx is None:
                                            idx = 0
                                        procOutputFile = procOutputs.getchildren()[
                                            idx].text
                                        if procOutputFile is None:
                                            break
                                        origBase = os.path.splitext(
                                            os.path.basename(str(procOutputFile)))[0]
                                        resolvedArg.addRewrite(
                                            '.'.join([origBase, thisExt]))
                                        break
                        break

                # raise error if postExecIndex was not set
                if postExecIndex is None:
                    raise ScifloError(
                        "Failed to resolve flow output %s." % eltTag)

            # append
            self._flowOutputConfigs.append(resolvedArg)

        # set resolve flag
        self.resolved = True

    def getDot(self):
        """Return GraphViz dot commands string for the sciflo."""

        # return if already got dot
        if self.dot is not None:
            return self.dot

        # resolve first if not yet resolved
        self.resolve()

        # get processes list
        processConfigList = []
        processId2IdxMap = {}
        idx = 0
        for wuConfig in self._workUnitConfigsForDot:
            id = wuConfig.getId()
            processId2IdxMap[id] = idx
            if wuConfig.getImplicitFlag():
                typ = 'implicit'
            else:
                typ = 'explicit'
            deps = []
            args = wuConfig.getArgs()
            for arg in args:
                if isinstance(arg, UnresolvedArgument):
                    deps.append(processId2IdxMap[arg.getId()])
            processConfigList.append((id, typ, deps))
            idx += 1

        # get outputs list
        outputConfigList = []
        outputIdx = 0
        for flowOutput in self._flowOutputs:
            (eltNs, eltTag, eltType, eltVal) = parseElement(flowOutput)
            if eltNs is None and eltTag is None and eltType is None and eltVal is None:
                continue
            outputConfigList.append(
                (eltTag, processId2IdxMap[self._flowOutputConfigs[outputIdx].getId()]))
            outputIdx += 1
        self.dot = dotFlowChartFromDependencies(
            processConfigList, outputConfigList)
        return self.dot

    def getFullDot(self):
        """Return full GraphViz dot commands string for the sciflo."""

        # return if already got dot
        if self.fullDot is not None:
            return self.fullDot

        # resolve first if not yet resolved
        self.resolve()

        # create xml and add global inputs
        rtElt = lxml.etree.Element('dotInfo')
        globalInputsElt = lxml.etree.SubElement(rtElt, 'globalInputs')
        for globalInput in self.globalInputs:
            lxml.etree.SubElement(
                globalInputsElt, 'input').set('id', globalInput)

        # add processes
        processesElt = lxml.etree.SubElement(rtElt, 'processes')
        for wuConfig in self._workUnitConfigsForDot:

            # process elt
            processElt = lxml.etree.SubElement(processesElt, 'process')

            # set id from config
            id = wuConfig.getId()
            processElt.set('id', id)

            # inputs/outputs elt
            inputsElt = lxml.etree.SubElement(processElt, 'inputs')
            outputsElt = lxml.etree.SubElement(processElt, 'outputs')

            # if implicit, inputs/outputs/etc. are not in sciflo doc;
            #fill in placeholders
            if wuConfig.getImplicitFlag():
                typ = 'implicit'
                processElt.set('type', typ)
                inputElt = lxml.etree.SubElement(inputsElt, 'input')
                inputElt.set('id', 'implicit_input')
                outputElt = lxml.etree.SubElement(outputsElt, 'output')
                outputElt.set('id', 'implicit_output')
            else:
                typ = 'explicit'
                processElt.set('type', typ)
                origInElts = self._eltDoc.xpath('sf:flow/sf:processes/sf:process[@id="%s"]/sf:inputs' % id,
                                                namespaces=self._namespacePrefixDict)[0]
                for origInElt in origInElts:
                    if isinstance(origInElt, lxml.etree._Comment):
                        continue
                    (inNs, inTag, inType, inVal) = parseElement(origInElt)
                    inputElt = lxml.etree.SubElement(inputsElt, 'input')
                    inputElt.set('id', inTag)
                origOutElts = self._eltDoc.xpath('sf:flow/sf:processes/sf:process[@id="%s"]/sf:outputs' % id,
                                                 namespaces=self._namespacePrefixDict)[0]
                for origOutElt in origOutElts:
                    if isinstance(origOutElt, lxml.etree._Comment):
                        continue
                    (outNs, outTag, outType, outVal) = parseElement(origOutElt)
                    outputElt = lxml.etree.SubElement(outputsElt, 'output')
                    outputElt.set('id', outTag)

            # get args from config adjusting to workUnit types
            args = wuConfig.getArgs()
            mode = wuConfig.getType()
            if mode in ('soap', 'post'):
                args = args[1:]
            if mode in ('rest', 'template', 'cmdline'):
                args = args[1::2]

            # loop over args and fill in xml with:
            # from and val attributes for inputs,
            #
            for i in range(len(args)):
                if isinstance(args[i], UnresolvedArgument):
                    resolvingProcId = args[i].getId()
                    resolvingProcOutputIndex = args[i].getOutputIndex()
                    if resolvingProcOutputIndex is None:
                        resolvingProcOutputIndex = '0'
                    inputsElt[i].set('from', 'process')
                    inputsElt[i].set('val', '%s:%s' % (
                        resolvingProcId, resolvingProcOutputIndex))
                else:
                    if i in wuConfig.argIdxsResolvedGloballyDict:
                        inputsElt[i].set('from', 'global')
                        inputsElt[i].set(
                            'val', wuConfig.argIdxsResolvedGloballyDict[i])
                    else:
                        inputsElt[i].set('from', 'static')
                        inputsElt[i].set('val', str(args[i]))

        # add and resolve global outputs info
        globalOutputsElt = lxml.etree.SubElement(rtElt, 'globalOutputs')
        globalOutputIdx = 0
        for flowOutput in self._flowOutputs:
            if isinstance(flowOutput, lxml.etree._Comment):
                continue

            (eltNs, eltTag, eltType, eltVal) = parseElement(flowOutput)

            # create output elt
            outputElt = lxml.etree.SubElement(globalOutputsElt, 'output')
            outputElt.set('id', eltTag)

            # get val attribute from resolving proc
            resProcConfig = self._flowOutputConfigs[globalOutputIdx]
            resProcId = resProcConfig.getId()
            resProcOutputIdx = resProcConfig.getOutputIndex()
            if resProcOutputIdx is None:
                resProcOutputIdx = '0'
            outputElt.set('val', '%s:%s' % (resProcId, resProcOutputIdx))
            globalOutputIdx += 1

        self.fullDot = fullDotFlowChartFromDependencies(rtElt)
        return self.fullDot

    def _annotateSvg(self, svgStr):
        """Helper function to append additional info to SVG graph for the
        purpose of being able to convert back to a sciflo document."""

        svgElt, svgNsDict = getXmlEtree(svgStr)
        descElt = lxml.etree.Element('desc')
        descElt.text = str(self._description).strip()
        svgElt.insert(0, descElt)
        metadataElt = lxml.etree.Element('metadata')
        svgElt.insert(1, metadataElt)
        sflNsDict = {}
        for pre in self._namespacePrefixDict:
            if pre == '_default':
                sflNsDict[None] = self._namespacePrefixDict[pre]
            else:
                sflNsDict[pre] = self._namespacePrefixDict[pre]
        if None not in sflNsDict:
            sflNsDict[None] = self._namespacePrefixDict['sf']
        scifloElt = lxml.etree.Element('sciflo', nsmap=sflNsDict)
        metadataElt.append(scifloElt)
        flowElt = lxml.etree.SubElement(scifloElt, 'flow')
        flowElt.set('id', self._flowName)
        sflDescElt = lxml.etree.SubElement(flowElt, 'description')
        sflDescElt.text = str(self._description).strip()
        sflInputsElt = lxml.etree.SubElement(flowElt, 'inputs')
        for inputElt in self._flowInputs:
            sflInputsElt.append(inputElt)
        return lxml.etree.tostring(svgElt, pretty_print=True, encoding='unicode')

    def getSvg(self):
        """Return annotated SVG graph."""

        # return if already set
        if self.svg is not None:
            return self.svg
        self.svg = self._annotateSvg(
            runDot(self.getDot(), None))  # None forces svg
        return self.svg

    def getFullSvg(self):
        """Return full SVG graph annotated."""

        # return if already set
        if self.fullSvg is not None:
            return self.fullSvg
        self.fullSvg = self._annotateSvg(
            runDot(self.getFullDot(), None))  # None forces svg
        return self.fullSvg

    def writeGraph(self, outputFile):
        """Write GraphViz graph to output file in the format specified by
        the extension."""

        if outputFile.endswith('.svg') or outputFile is None:
            with open(outputFile, 'w') as f:
                f.write(self.getSvg())
        else:
            runDot(self.getDot(), outputFile)

    def writeFullGraph(self, outputFile):
        """Write full GraphViz graph to output file in the format specified by
        the extension."""

        if outputFile.endswith('.svg') or outputFile is None:
            with open(outputFile, 'w') as f:
                f.write(self.getFullSvg())
        else:
            runDot(self.getFullDot(), outputFile)
