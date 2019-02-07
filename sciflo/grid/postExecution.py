# -----------------------------------------------------------------------------
# Name:        postExecution.py
# Purpose:     Various functions for post execution.
#
# Author:      Gerald Manipon
#
# Created:     Fri Sep 16 14:29:27 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import re
from tempfile import mkdtemp
import urllib.request
import urllib.parse
import urllib.error
import urllib.parse
import os
from string import Template
import types

from sciflo.utils import (SCIFLO_NAMESPACE, XSD_NAMESPACE, PY_NAMESPACE,
                          FileConversionFunction, validateDirectory, getXmlEtree,
                          DEFAULT_CONVERSION_FUNCTIONS, getUserInfo, getUserConversionFunctionsDir,
                          LocalizingFunctionWrapper)
from .utils import getFunction


def parseNamespacePrefixAndTypeString(typeString):
    """Parse type string and return namespace key and type."""

    # split on ':' if ':' is there
    if typeString is None:
        nsprefix = '*'
        val = '*'
    elif ':' in typeString:
        (nsprefix, val) = typeString.split(':', 1)
    else:
        nsprefix = None
        val = typeString
    return (nsprefix, val)


def getConversionFunctionString(fromType, toType, namespacePrefixDict={}):
    """Return a string indicating the proper conversion function.
    Namespace prefixes are resolved from the namespacePrefixDict of the
    xml doc."""

    # force xpath type coersion
    if isinstance(fromType, str) and \
            re.search(r'^(sf:)?(xpath:)', fromType, re.IGNORECASE):
            fromType = '*:*'

    # get conv func xml elt and ns prefix dict
    convFuncElt, convNsDict = getXmlEtree(CONVERSION_FUNCTIONS_CONFIG)
    convNsToPrefixDict = dict(
        list(zip(list(convNsDict.values()), list(convNsDict.keys()))))

    # get overwrite conv funcs from user config
    (userName, homeDir, userScifloDir, userConfigFile) = getUserInfo()
    userConfElt, userConfNsDict = getXmlEtree(userConfigFile)
    userConfNsToPrefixDict = dict(
        list(zip(list(userConfNsDict.values()), list(userConfNsDict.keys()))))
    ops = userConfElt.xpath(
        './/_default:conversionOperators/_default:op', namespaces=userConfNsDict)
    for op in ops:
        opFromNs, opFromVal = parseNamespacePrefixAndTypeString(op.get('from'))
        if opFromNs is None:
            opFromNs = userConfNsToPrefixDict[namespacePrefixDict['_default']]
        elif opFromNs == '*':
            pass
        else:
            opFromNs = userConfNsToPrefixDict[namespacePrefixDict[opFromNs]]
        opToNs, opToVal = parseNamespacePrefixAndTypeString(op.get('to'))
        if opToNs is None:
            opToNs = userConfNsToPrefixDict[namespacePrefixDict['_default']]
        elif opToNs == '*':
            raise RuntimeError("Cannot convert to type %s with unspecified namespace prefix %s." %
                               (opToVal, opToNs))
        else:
            opToNs = userConfNsToPrefixDict[namespacePrefixDict[opToNs]]
        overwriteMatch = convFuncElt.xpath(".//_default:op[@from='%s:%s' and @to='%s:%s']" %
                                           (opFromNs, opFromVal, opToNs, opToVal), namespaces=convNsDict)
        if len(overwriteMatch) == 1:
            if str(overwriteMatch[0].text) != str(op.text):
                convFuncElt.remove(overwriteMatch[0])
                convFuncElt.append(op)
            else:
                continue
        elif len(overwriteMatch) == 0:
            convFuncElt.append(op)
        else:
            raise RuntimeError("Found more than one match.")

    # get fromType namespace prefix, type, and namespace
    (fromNsPrefix, fromTypeVal) = parseNamespacePrefixAndTypeString(fromType)
    if fromNsPrefix is None:
        fromNs = convNsToPrefixDict[namespacePrefixDict['_default']]
    elif fromNsPrefix == '*':
        fromNs = '*'
    else:
        fromNs = convNsToPrefixDict[namespacePrefixDict[fromNsPrefix]]

    # get toType namespace prefix, type and namespace
    (toNsPrefix, toTypeVal) = parseNamespacePrefixAndTypeString(toType)
    if toNsPrefix is None:
        toNs = convNsToPrefixDict[namespacePrefixDict['_default']]
    elif toNsPrefix == '*':
        raise RuntimeError("Cannot convert to type %s with unspecified namespace prefix %s." %
                           (toTypeVal, toNsPrefix))
    else:
        toNs = convNsToPrefixDict[namespacePrefixDict[toNsPrefix]]

    # return xpath conversion
    if namespacePrefixDict.get(toNsPrefix, None) == SCIFLO_NAMESPACE and toTypeVal.startswith('xpath:'):
        return toTypeVal

    # xpath to find match
    matches = convFuncElt.xpath(".//_default:op[@from='%s:%s' and @to='%s:%s']" %
                                (fromNs, fromTypeVal, toNs, toTypeVal), namespaces=convNsDict)
    if len(matches) == 0:
        matches = convFuncElt.xpath(".//_default:op[@from='*:*' and @to='%s:%s']" %
                                    (toNs, toTypeVal), namespaces=convNsDict)
        if len(matches) == 0:
            raise RuntimeError("Cannot find conversion function for %s:%s -> %s:%s." %
                               (fromNs, fromTypeVal, toNs, toTypeVal))
    return str(matches[0].text)


# conversion functions config xml
CONVERSION_FUNCTIONS_CONFIG = Template('''<?xml version="1.0"?>
<conversionOperators xmlns="${sflNs}"
        xmlns:sf="${sflNs}"
        xmlns:xs="${xsdNs}"
        xmlns:py="${pyNs}">
    ${defaultOpElts}
</conversionOperators>''').substitute(sflNs=SCIFLO_NAMESPACE, xsdNs=XSD_NAMESPACE,
                                      pyNs=PY_NAMESPACE,
                                      defaultOpElts=DEFAULT_CONVERSION_FUNCTIONS)


class PostExecutionHandlerError(Exception):
    """Exception class for PostExecutionHandler class."""
    pass


class PostExecutionHandler(object):
    """Class that handles the execution of a conversion function on the
    results of a work unit."""

    def __init__(self, resultIndex, conversionFuncStr, outputDir=None):
        """Constructor.  Pass in the index of the work unit result to
        convert.  The conversion function string will be eval'd on this
        result.  If result is None, then the conversion is performed on
        the entire result.
        """

        # set attribs
        self._resultIndex = resultIndex
        self._conversionFuncStr = conversionFuncStr
        self._outputDir = outputDir

    def getIdString(self):
        """Return string to id this PostExecutionHandler."""
        return '|'.join(map(str, [self._resultIndex, self._conversionFuncStr]))

    def execute(self, result, workDir):
        """Wrapper for execute()."""

        curDir = None
        if self._outputDir is not None:
            curDir = os.getcwd()
            os.chdir(self._outputDir)
        try:
            retVal = self._execute(result, workDir)
        finally:
            if curDir:
                os.chdir(curDir)
        return retVal

    def _execute(self, result, workDir):
        """Perform the post execution function.  Pass in the entire result
        of the work unit and this handler will run the conversion function
        on the specified indexed result or on the entire result (if the
        resultIndex is None).  Return the result of the function.
        """

        # get the result to perform function on
        if self._resultIndex is None:
            inputResult = result
        else:
            inputResult = result[self._resultIndex]

        # special case conversions
        xpathMatch = re.search(r'^xpath:(.+)$', self._conversionFuncStr)
        if xpathMatch:
            resultDoc, resultNs = getXmlEtree(inputResult)
            return resultDoc.xpath(xpathMatch.group(1), namespaces=resultNs)

        # eval the conversion function
        convFunc = getFunction(self._conversionFuncStr,
                               addToSysPath=getUserConversionFunctionsDir())

        # if FunctionWrapper, get local files
        tempDir = None
        tmpInputRes = []
        if isinstance(convFunc, LocalizingFunctionWrapper):
            tempDir = os.path.join(workDir, 'fileConversions')
            validateDirectory(tempDir)
            if not isinstance(inputResult, (list, tuple)):
                singleArgFlag = True
                tmpInput = [inputResult]
            else:
                singleArgFlag = False
                tmpInput = inputResult
            for ip in tmpInput:
                if not isinstance(ip, str):
                    raise PostExecutionHandlerError(
                        "Cannot localize input %s.  Please check return value of work unit." % str(ip))
                match = re.search(r'^\w*?://', ip)
                if match:
                    filebase = urllib.parse.urlparse(ip)[2].split('/')[-1]
                else:
                    filebase = os.path.basename(ip)
                tempFile = os.path.join(tempDir, filebase)
                (ip, headers) = urllib.request.urlretrieve(ip, tempFile)
                tmpInputRes.append(tempFile)
            if singleArgFlag:
                inputResult = tmpInputRes[0]
            else:
                inputResult = tmpInputRes

        # do conversion
        if isinstance(convFunc, FileConversionFunction):
            if singleArgFlag:
                retVal = convFunc(inputResult)
            else:
                retVal = [convFunc(ip) for ip in inputResult]
        else:
            retVal = convFunc(inputResult)

        return retVal
