# -----------------------------------------------------------------------------
# Name:        xml.py
# Purpose:     Various xml converter functions.
#
# Author:      Gerald Manipon
#
# Created:     2004/05/17
# Copyright:   (c) 2004, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# Licence:
# -----------------------------------------------------------------------------
from io import StringIO
from xml.dom.minidom import getDOMImplementation, parseString, Document
import types
import sys
from tempfile import mkstemp, mkdtemp
import os
import re
import base64
import datetime
import lxml.etree
from urllib.request import urlopen, Request
from urllib.parse import urlparse
import http.client
import traceback
import socket

import sciflo
from .misc import (getListFromUnknownObject, getUserScifloConfig,
                   getDictFromUnknownObject, getTempfileName)
from .namespaces import *


def isXml(obj):
    """Return True if xml is detect and False otherwise."""

    try:
        lxml.etree.XML(obj)
        return True
    except:
        return False


def isUrl(obj):
    """Return True if xml is detect and False otherwise."""

    if isinstance(obj, str):
        obj.strip()
        if re.search(r'^\w*?:', obj):
            return True
    return False


def writeXmlFile(xmlString, outputFile=None):
    """Write xml to file."""

    if isinstance(xmlString, (list, tuple)):
        xmlString = '\n'.join(xmlString)
    # if output file not specified, get random name
    if outputFile is None:
        outputFile = os.path.abspath(
            os.path.basename(getTempfileName(suffix='.xml')))
    f = open(outputFile, 'w')
    f.write(str(xmlString))
    f.close()
    return outputFile


def getXmlEtree(xml):
    """Return a tuple of [lxml etree element, prefix->namespace dict].
    """

    parser = lxml.etree.XMLParser(remove_blank_text=True)
    if xml.startswith('<?xml') or xml.startswith('<'):
        return (lxml.etree.parse(StringIO(xml), parser).getroot(), getNamespacePrefixDict(xml))
    else:
        protocol, netloc, path, params, query, frag = urlparse(xml)
        if protocol == '': xml = "file://{}".format(xml)
        xmlStr = urlopen(xml).read().decode('utf-8')
        return (lxml.etree.parse(StringIO(xmlStr), parser).getroot(), getNamespacePrefixDict(xmlStr))


def getNamespacePrefixDict(xmlString):
    """Take an xml string and return a dict of namespace prefixes to
    namespaces mapping."""

    nss = {}
    matches = re.findall(r'\s+xmlns:?(\w*?)\s*=\s*[\'"](.*?)[\'"]', xmlString)
    for match in matches:
        prefix = match[0]
        ns = match[1]
        if prefix == '':
            prefix = '_default'
        nss[prefix] = ns
    return nss


def addDefaultPrefixToXpath(xpathStr):
    """Add default prefixes to xpath and return new xpath."""

    for sep in '/@[':
        xpathTokens = [i.strip() for i in xpathStr.split(sep)]
        for i in range(len(xpathTokens)):
            if xpathTokens[i] == '' or \
               xpathTokens[i].startswith('.') or \
               re.search(r'^\w+(\s*:|\()', xpathTokens[i]):
                   pass
            else:
                xpathTokens[i] = '_default:' + xpathTokens[i]
        xpathStr = sep.join(xpathTokens)
    return xpathStr


def runXpath(xml, xpathStr, nsDict={}):
    """Run XPath on xml and return result."""

    lxml.etree.clear_error_log()
    if isinstance(xml, lxml.etree._Element):
        root = xml
    else:
        root, nsDict = getXmlEtree(xml)

    # add '_' as default namespace prefix also
    if '_default' in nsDict:
        nsDict['_'] = nsDict['_default']

    gotException = False
    if re.search(r'(?:/|\[|@){.*}', xpathStr):
        expr = lxml.etree.ETXPath(xpathStr)
        res = expr.evaluate(root)
    else:
        try:
            res = root.xpath(xpathStr)
        except Exception as e:
            if isinstance(e, lxml.etree.XPathSyntaxError):
                if re.search(r'XPATH_UNDEF_PREFIX_ERROR', str(e.error_log)):
                    pass
                else:
                    raise RuntimeError(
                        "Error in xpath expression %s: %s" % (xpathStr, e.error_log))
            try:
                res = root.xpath(xpathStr, namespaces=nsDict)
            except lxml.etree.XPathSyntaxError as e:
                raise RuntimeError(
                    "Error in xpath expression %s: %s" % (xpathStr, e.error_log))
            except:
                gotException = True
                res = []
        if isinstance(res, (list, tuple)) and (gotException or len(res) == 0):
            xpathStr = addDefaultPrefixToXpath(xpathStr)
            lxml.etree.clear_error_log()
            try:
                res = root.xpath(xpathStr, namespaces=nsDict)
            except lxml.etree.XPathSyntaxError as e:
                raise RuntimeError(
                    "Error in xpath expression %s: %s" % (xpathStr, e.error_log))
            except:
                raise
    if isinstance(res, (list, tuple)):
        for i in range(len(res)):
            if isinstance(res[i], lxml.etree._Element):
                res[i] = lxml.etree.tostring(res[i], pretty_print=True, encoding='unicode')
            if isinstance(res[i], lxml.etree._ElementStringResult):
                res[i] = str(res[i])
    elif isinstance(res, lxml.etree._Element):
        res = lxml.etree.tostring(res, pretty_print=True, encoding='unicode')
    elif isinstance(res, lxml.etree._ElementStringResult):
        res = str(res)
    else:
        pass
    if len(res) == 1:
        return res[0]
    else:
        return res


def postCall(url, data, headers, verbose=False):
    """Post data to a url and return result."""

    if verbose:
        print(('postCall to %s:\n' % url, data))
    protocol, netloc, path, params, query, frag = urlparse(url)
    port = None
    matchPort = re.search(r'^(.+):(\d+)$', netloc)
    if matchPort:
        netloc, port = matchPort.groups()
        port = int(port)
    if protocol == 'https':
        c = http.client.HTTPSConnection(netloc, port)
    else:
        c = http.client.HTTPConnection(netloc, port)
    c.connect()
    try:
        if isXml(data):
            headers['Content-type'] = 'text/xml'
            if not data.startswith('<?xml'):
                data = '<?xml version="1.0" encoding="UTF-8"?>' + data
        else:
            headers['Content-type'] = 'application/x-www-form-urlencoded'
        headers['Content-length'] = str(len(data))
        c.putrequest("POST", path)
        for key, val in list(headers.items()):
            c.putheader(key, val)
        c.endheaders()
        c.send(data)
        r = c.getresponse()
        # 200 means OK. Anything other is a failure.
        if r.status != 200:
            msg = r.read()
            raise RuntimeError('http-error:' + repr(r.status) +
                               ' ' + repr(r.reason) + ' ' + msg)
        xmlOut = r.read()
    finally:
        c.close()
    if verbose:
        print(('postResponse:\n', xmlOut))
    return xmlOut


def getMinidomXmlDocument(rootTag, defaultNamespace=None, xsdNamespace=None,
                          schemaUrl=None, xsiNamespace=None, rootAttribsDict=None,
                          xslPath=None):
    """Return a minidom XML document with the root element set with the specified
    tagname, default namespace, ,xsd namespace (XML Schema), xsi namespace
    (XML Schema-instance), XSLT (XML Transform) processing instruction, and
    root attributes.
    """

    # create document
    implementation = getDOMImplementation()
    xmlDoc = implementation.createDocument(None, None, None)

    # add xslt processing instruction
    if xslPath:
        pi = xmlDoc.createProcessingInstruction('xml-stylesheet',
                                                'type="text/xsl" href="%s"' % xslPath)
        xmlDoc.appendChild(pi)

    # create root element
    rootElem = xmlDoc.createElement(rootTag)
    xmlDoc.appendChild(rootElem)

    # create default namespace attribute
    if defaultNamespace:
        xmlns = xmlDoc.createAttribute('xmlns')
        xmlns.value = defaultNamespace
        rootElem.setAttributeNode(xmlns)

    # create xsd namespace attribute
    if xsdNamespace:
        xsd = xmlDoc.createAttribute('xmlns:xs')
        xsd.value = xsdNamespace
        rootElem.setAttributeNode(xsd)

    # create xsi namespace and schemaLocation attributes if both are set
    if schemaUrl and xsiNamespace:
        xsi = xmlDoc.createAttribute('xmlns:xsi')
        xsi.value = xsiNamespace
        rootElem.setAttributeNode(xsi)
        schema = xmlDoc.createAttribute('xsi:schemaLocation')
        schema.value = schemaUrl
        rootElem.setAttributeNode(schema)

    # add root attributes if they exist
    if rootAttribsDict and isinstance(rootAttribsDict, dict):

        # loop over each key and value pair
        for key in list(rootAttribsDict.keys()):
            val = rootAttribsDict[key]
            attr = xmlDoc.createAttribute(key)
            attr.value = val
            rootElem.setAttributeNode(attr)

    # return xml doc
    return xmlDoc


def simpleList2Xml(LL, rootElement="Rows", rowElement="row", rootAttribsDict=None,
                   defaultNamespace=SCIFLO_NAMESPACE, xsdNamespace=XSD_NAMESPACE,
                   schemaUrl=None, xsiNamespace=XSI_NAMESPACE, xslPath=None,
                   rootAttribsDictNonNS=None):
    """Return xml from a simple list."""

    # get xml doc and root element
    # xmlDoc = getMinidomXmlDocument(rootElement,defaultNamespace,xsdNamespace,
    #                              schemaUrl,xsiNamespace,rootAttribsDict,xslPath)
    #rootElem = xmlDoc.documentElement
    if not isinstance(rootAttribsDict, dict):
        rootAttribsDict = {}
    if defaultNamespace is not None:
        rootAttribsDict[None] = defaultNamespace
    else:
        rootAttribsDict[None] = SCIFLO_NAMESPACE
    if xsdNamespace is not None:
        rootAttribsDict['xs'] = xsdNamespace
    if schemaUrl is not None:
        rootAttribsDict['schemaLocation'] = schemaUrl
    if xsiNamespace is not None:
        rootAttribsDict['xsi'] = xsiNamespace
    rootElem = lxml.etree.Element(rootElement, nsmap=rootAttribsDict)

    # set non-namespace attributes
    if isinstance(rootAttribsDictNonNS, dict):
        for k in rootAttribsDictNonNS:
            rootElem.set(k, str(rootAttribsDictNonNS[k]))

    # loop over each record and populate dom
    for row in LL:

        # create row element
        #rowElem = xmlDoc.createElement(rowElement)
        # rowElem.appendChild(xmlDoc.createTextNode(str(row)))
        # rootElem.appendChild(rowElem)
        recElem = lxml.etree.SubElement(rootElem, rowElement)
        recElem.text = str(row)

        # set type
        if isinstance(row, float):
            #floatAttr = xmlDoc.createAttribute('type')
            #floatAttr.value = 'xs:float'
            # rowElem.setAttributeNode(floatAttr)
            recElem.set('type', 'xs:float')
        elif isinstance(row, int):
            #intAttr = xmlDoc.createAttribute('type')
            #intAttr.value = 'xs:int'
            # rowElem.setAttributeNode(intAttr)
            recElem.set('type', 'xs:int')
        elif isinstance(row, bool):
            #boolAttr = xmlDoc.createAttribute('type')
            #boolAttr.value = 'xs:boolean'
            # rowElem.setAttributeNode(boolAttr)
            recElem.set('type', 'xs:boolean')
        else:
            pass

    # get string and return
    return lxml.etree.tostring(rootElem, pretty_print=True, encoding='unicode')


def xml2SimpleList(xmlString):
    """Return a simple list from xml."""

    # create dom object
    domObj = parseString(xmlString)

    # get root element
    rootElem = domObj.documentElement
    rootElemName = rootElem.nodeName

    # get child nodes of root element
    childNodes = rootElem.childNodes

    # loop over childnodes and make sure they are
    # text_nodes.  If so, append to final list
    finalList = []
    for node in childNodes:
        if node.firstChild is not None and node.firstChild.nodeType == 3:
            finalList.append(node.firstChild.data)
    return finalList


def list2Xml(LL, headingsTuple=(), rootElement="Rows", rowElement="row",
             rootAttribsDict=None, defaultNamespace=SCIFLO_NAMESPACE,
             xsdNamespace=XSD_NAMESPACE, schemaUrl=None, xsiNamespace=XSI_NAMESPACE,
             xslPath=None, rootAttribsDictNonNS=None):
    """Return xml from lists of lists."""

    # get headings (will be tags within each row)
    if len(headingsTuple) == 0:
        headingsTuple = LL.pop(0)

    # get number of headings
    numHeadings = len(headingsTuple)

    # get number of records
    numRecs = len(LL)

    # get xml doc and root element
    # xmlDoc = getMinidomXmlDocument(rootElement,defaultNamespace,xsdNamespace,
    #                               schemaUrl,xsiNamespace,rootAttribsDict,xslPath)
    #rootElem = xmlDoc.documentElement
    if not isinstance(rootAttribsDict, dict):
        rootAttribsDict = {}
    if defaultNamespace is not None:
        rootAttribsDict[None] = defaultNamespace
    else:
        rootAttribsDict[None] = SCIFLO_NAMESPACE
    if xsdNamespace is not None:
        rootAttribsDict['xs'] = xsdNamespace
    if schemaUrl is not None:
        rootAttribsDict['schemaLocation'] = schemaUrl
    if xsiNamespace is not None:
        rootAttribsDict['xsi'] = xsiNamespace
    rootElem = lxml.etree.Element(rootElement, nsmap=rootAttribsDict)

    # set non-namespace attributes
    if isinstance(rootAttribsDictNonNS, dict):
        for k in rootAttribsDictNonNS:
            rootElem.set(k, str(rootAttribsDictNonNS[k]))

    # loop over each record, get heading and data, and populate dom
    for rec in LL:
        # check number of items in the rec, skip if not
        if len(rec) != numHeadings:
            continue

        # create record element (corresponsds to a row)
        #recElem = xmlDoc.createElement(rowElement)
        # rootElem.appendChild(recElem)
        recElem = lxml.etree.SubElement(rootElem, rowElement)

        # loop over data and append
        for x in range(numHeadings):
            heading = headingsTuple[x]
            if isinstance(heading, list) or isinstance(heading, tuple):
                recItems = getListFromUnknownObject(rec[x])
                #xElem = xmlDoc.createElement(heading[0])
                # recElem.appendChild(xElem)
                xElem = lxml.etree.SubElement(recElem, heading[0])
                for listItem in recItems:
                    addChildTextNodeToParentNode(xElem, heading[1], listItem)
            else:
                addChildTextNodeToParentNode(recElem, heading, rec[x])
    return lxml.etree.tostring(rootElem, pretty_print=True, encoding='unicode')


def addChildTextNodeToParentNode(parentNode, childTag, childValue):
    """Pass in a xml.dom.minidom node, child tag, and child value
    and it creates a child text node and appends it to the parent.
    Return 1 upon success.
    """

    # get xml document object
    #xmlDoc = parentNode.ownerDocument

    # create child node
    #childNode = xmlDoc.createElement(childTag)
    # childNode.appendChild(xmlDoc.createTextNode(str(childValue)))
    # parentNode.appendChild(childNode)
    childNode = lxml.etree.SubElement(parentNode, childTag)
    childNode.text = str(childValue)

    # set type attribute
    if isinstance(childValue, float):
        #floatAttr = xmlDoc.createAttribute('type')
        #floatAttr.value = 'xs:float'
        # childNode.setAttributeNode(floatAttr)
        childNode.set('type', 'xs:float')
    elif isinstance(childValue, int):
        #intAttr = xmlDoc.createAttribute('type')
        #intAttr.value = 'xs:int'
        # childNode.setAttributeNode(intAttr)
        childNode.set('type', 'xs:int')
    elif isinstance(childValue, bool):
        #boolAttr = xmlDoc.createAttribute('type')
        #boolAttr.value = 'xs:boolean'
        # childNode.setAttributeNode(boolAttr)
        childNode.set('type', 'xs:boolean')
    else:
        pass
    return 1


def xml2List(xmlString):
    """Return an equal length list of lists from xml."""

    # create dom object
    domObj = parseString(xmlString)

    # get root element
    rootElem = domObj.documentElement
    rootElemName = rootElem.nodeName

    # get child nodes of root element
    childNodes = rootElem.childNodes

    # number of child nodes (corresponds to number of lists in data structure)
    numChildNodes = childNodes.length

    # we'll get tagnames and number of items from the TEXT_NODES of
    # the first child
    firstChild = rootElem.firstChild
    tagNames = []
    for node in firstChild.childNodes:
        if node.firstChild.nodeType == 3:
            tagNames.append(node.nodeName)

    # print "Tagnames are:",',\n'.join(tagNames)

    # the list of tagnames is the first item in the final list of lists
    finalList = []
    finalList.append(tagNames)

    # now loop over child nodes and get the value of the items within
    # each child node from the tagnames.
    # Append the list to the list of lists.
    # PLEASE NOTE: Since we extract the data according to the list of
    # text_node tagnames that we extracted from the first child, there is no
    # check for uniformity, except that the tagname exists, in the subsequent
    # childNodes.  Thus, additional tagnames (elements) can exist and should
    # not break this call.
    for i in range(numChildNodes):
        # get current iteration of child nodes
        node = childNodes.item(i)

        # get list of tagname nodes in current child node
        tagNodes = node.childNodes

        # get clean datalist
        datalist = []

        # loop over tagnames
        for tagName in tagNames:
            try:
                thisTagNode = node.getElementsByTagName(tagName)[0]
            except IndexError as e:
                raise RuntimeError(e)

            # get data value for the tag
            dataVal = thisTagNode.firstChild.data

            # append data value to datalist
            datalist.append(dataVal)

        # append datalist to finalList
        finalList.append(datalist)

    # return the final list
    return finalList


def getListDictFromXml(xml, recordTag='Result', keyTag='objectid',
                       defaultNamespace=SCIFLO_NAMESPACE):
    """Return a dict of lists indexed by tagnames from xml."""

    # get elementtree doc
    doc = lxml.etree.parse(StringIO(xml))

    # namespace string
    namespaceString = '{%s}' % defaultNamespace

    # get results
    results = doc.findall(namespaceString+recordTag)

    # metadatadict
    metadataDict = {}

    # loop over results
    for result in results:

        # get subresults
        subresults = result.findall('*')

        # make sure first subresult is 'objectid'
        if subresults[0].tag == namespaceString+keyTag:
            objectid = subresults[0].text
        else:
            raise RuntimeError('''Error parsing xml into metadata dict.  First record
is not 'objectid' tag: %''' % subresult[0].tag)

        # metadata list
        list = []

        # loop over the rest
        for subresult in subresults[1:]:

            # get tag
            tag = subresult.tag
            value = subresult.text

            # get the type so that we can type it accordingly
            type = subresult.get('type', 'xs:string')
            if type == 'xs:int':
                value = int(value)
            elif type == 'xs:float':
                value = float(value)
            elif type == 'xs:boolean':
                value = bool(value)
            else:
                pass

            # append to list
            list.append(value)

        metadataDict[objectid] = list

    # return metadataDict
    return metadataDict


def getEltsAsList(eltsList):
    """Return list of values from list of elements."""

    retList = []
    for elt in eltsList:
        tag = elt.tag
        value = elt.text
        if value is None or re.search(r'\s*', str(value)):
            subElts = elt.findall('*')
            if len(subElts) > 0:
                value = getEltsAsList(subElts)
        type = elt.get('type', 'xs:string')
        if type == 'xs:int':
            value = int(value)
        elif type == 'xs:float':
            value = float(value)
        elif type == 'xs:boolean':
            value = bool(value)
        else:
            pass
        retList.append(value)
    return retList


def xmlLoL2PyDoL(xml, defaultNamespace=SCIFLO_NAMESPACE):
    """Return a dict of lists indexed by values of first items from xml."""

    # get elementtree doc
    doc = lxml.etree.parse(StringIO(xml))

    # namespace string
    namespaceString = '{%s}' % defaultNamespace

    # metadatadict
    metadataDict = {}

    # loop over items
    for elt in doc.findall('*'):

        # get subelts
        subElts = elt.findall('*')

        # get key
        key = subElts[0].text
        if key is None:
            raise RuntimeError('''Error parsing xml into metadata dict.  First record %s
                cannot be None.''' % subElts[0].tag)
        # set list
        metadataDict[key] = getEltsAsList(subElts[1:])

    # return metadataDict
    return metadataDict


def pyDoL2XmlList(infoDict, rootElement="resultSet", rowElement="objectid"):
    """Return xml list of the dict keys."""

    keys = list(infoDict.keys())
    keys.sort()
    return simpleList2Xml(keys, rootElement=rootElement, rowElement=rowElement)


def xmlList2PyLoD(xml, recordTag):
    """Return list of dict from xml.  Specify recordTag to specify tag that enumerates
    each record."""

    root, nsDict = getXmlEtree(xml)
    if root.tag == recordTag:
        recElts = [root]
    else:
        try:
            recElts = root.xpath('.//_default:%s' %
                                 recordTag, namespaces=nsDict)
        except:
            recElts = root.xpath('.//%s' % recordTag)
    retList = []
    for recElt in recElts:
        recDict = {}
        for subElt in recElt:
            recDict[subElt.tag] = subElt.text
        retList.append(recDict)
    return retList


def xmlList2PyLoX(xml, recordTag):
    """Return list of xml fragments from xml.  Specify recordTag to specify tag
    that enumerates each record."""

    root, nsDict = getXmlEtree(xml)
    if root.tag == recordTag:
        recElts = [root]
    else:
        try:
            recElts = root.xpath('.//_default:%s' %
                                 recordTag, namespaces=nsDict)
        except:
            recElts = root.xpath('.//%s' % recordTag)
    retList = []
    for recElt in recElts:
        retList.append(lxml.etree.tostring(recElt,
                                           pretty_print=True, encoding='unicode'))
    return retList


class XmlValidationError(Exception):
    """Exception class for xml schema validation errors."""
    pass


def validateXml(inputXml, schemaXml):
    """Return a 2-item tuple of (validationPassed, exception).  Upon successful
    validation of an xml file/string against a schema file/string, tuple
    (True, None) is returned.  Otherwise, returns (False, exception instance).
    """

    try:
        if os.path.isfile(inputXml):
            f = open(inputXml)
        else:
            f = StringIO(inputXml)
        if os.path.isfile(schemaXml):
            s = open(schemaXml)
        else:
            s = StringIO(schemaXml)
        lxml.etree.clear_error_log()
        try:
            schemaDoc = lxml.etree.parse(s)
        except lxml.etree.XMLSyntaxError as e:
            if str(e) == '':
                e = lxml.etree.XMLSyntaxError("Error in schema xml: %s" %
                                              str(e.error_log.filter_levels(lxml.etree.ErrorLevels.FATAL)))
            return (False, e)
        xmlSchema = lxml.etree.XMLSchema(schemaDoc)
        lxml.etree.clear_error_log()
        try:
            doc = lxml.etree.parse(f)
        except Exception as e:
            if str(e) == '':
                e = lxml.etree.XMLSyntaxError("Error in input xml: %s" %
                                              str(e.error_log.filter_levels(lxml.etree.ErrorLevels.FATAL)))
            return (False, e)
        ret = xmlSchema.validate(doc)
    except Exception as e:
        return (False, e)

    if ret == 0:
        return (False, XmlValidationError("Failed to validate xml: %s" %
                                          xmlSchema.error_log.filter_from_errors()))
    else:
        return (True, None)


def getPrettyPrintXmlFromDom(xmlDoc):
    '''Return pretty-printed xml from minidom xml document.
    '''

    if not isinstance(xmlDoc, Document):
        xmlDoc = parseString(xmlDoc)
    return xmlDoc.toprettyxml()


class ScifloConfigParserError(Exception):
    """Exception class for the ScifloConfigParser class."""
    pass


class ScifloConfigParser(object):
    """Class that parses the sciflo configuration xml file and provides
    parameter values.
    """

    def __init__(self, file=None):
        "Constructor."

        # if config file was specified, use it
        if file:
            self._configFile = file
        else:
            self._configFile = getUserScifloConfig()

        # check to make sure sciflo xml config exists
        if not os.path.isfile(self._configFile):
            raise ScifloConfigParserError("Cannot find sciflo configuration file at %s." %
                                          self._configFile)

        # get elementtree doc
        self._xmlDoc = lxml.etree.parse(self._configFile)

    def getParameter(self, param):
        """Return the parameter value.  Returns None if not specified."""

        param2Get = ".//{%s}%s" % (SCIFLO_NAMESPACE, param)
        result = self._xmlDoc.find(param2Get)
        if result in [None, 'None', ''] or result.text in [None, 'None', '']:
            return None
        else:
            return str(result.text)

    def getMandatoryParameter(self, param):
        """Return the parameter value.  If empty or not defined, raise error.
        """

        val = self.getParameter(param)
        if val is None or val == '':
            raise ScifloConfigParserError("Value %s is undefined in sciflo config file %s." %
                                          (param, self._configFile))
        return val

    def getParameterViaXPath(self, xpath):
        """Return the parameter value described by the xpath arg.
        Returns None if not specified."""

        # get all results
        result = self._xmlDoc.find(xpath)
        if result in [None, 'None', '']:
            return None
        else:
            return str(result.text)

    def getMandatoryParameterViaXPath(self, xpath):
        """Return the parameter value via xpath.  If empty or not defined, raise error.
        """

        val = self.getParameterViaXPath(xpath)
        if val is None or val == '':
            raise ScifloConfigParserError("Value %s is undefined in sciflo config file %s." %
                                          (param, self._configFile))
        return val


def parseTag(eltTag):
    """Parse an element tree tag, i.e. {http://genesis.jpl.nasa.gov}tag, and
    return a tuple of namespace and tag."""

    match = re.search(r'\s*(?:{\s*(.+)\s*})?\s*(\w+)', eltTag)
    if match is None:
        raise RuntimeError(
            "Failed to parse namespace and tag from elementtree tag %s." % eltTag)
    (namespace, tag) = match.groups()
    return (namespace, tag)


def parseElement(elt, returnChildren=False):
    """Parse an element and return a tuple consisting of namespace, tag, type,
    and value."""

    kids = None
    if elt.tag is None:
        if returnChildren:
            return (None, None, None, None, kids)
        else:
            return (None, None, None, None)
    (namespace, tag) = parseTag(elt.tag)
    typ = elt.get('type', None)
    if 'from' in elt.attrib:
        value = elt.get('from', None)
    else:
        eltKids = elt.getchildren()
        if len(eltKids) > 0:
            kids = eltKids
            if len(kids) == 1:
                value = lxml.etree.tostring(kids[0], pretty_print=True, encoding='unicode').strip()
            else:
                value = '\n'.join([lxml.etree.tostring(
                    i, pretty_print=True, encoding='unicode').strip() for i in kids])
                value = value.strip()
        else:
            value = elt.text
            if value is not None:
                value = value.strip()
    if returnChildren:
        return (namespace, tag, typ, value, kids)
    return (namespace, tag, typ, value)


# dict mapping xsd type to python type as defined at
# http://ose.sourceforge.net/browse.php?group=python-manual&entry=encoding.htm
XML_DATA_TYPE_MAPPING = {
    'string': str,
    'int': int,
    'integer': int,
    'byte': int,
    'short': int,
    'unsignedByte': int,
    'unsignedShort': int,
    'unsignedInt': int,
    'long': int,
    'unsignedLong': int,
    'float': float,
    'double': float,
    'real': float,
    'boolean': bool,
    'base64Binary': base64.decodestring,
    'date': datetime.date,
    'dateTime': datetime.datetime,
    'ISODateTime': datetime.datetime,
    'time': datetime.time
}

# dict mapping for python types
PYTHON_DATA_TYPE_MAPPING = {
    'list': getListFromUnknownObject,
    'dict': getDictFromUnknownObject,
}

# data mapping by namespace prefix
DATA_TYPE_MAPPING = {
    'xs': XML_DATA_TYPE_MAPPING,
    'py': PYTHON_DATA_TYPE_MAPPING,
}


def getTypedValue(typ, val):
    """Return a typed value."""

    if typ is None:
        return val
    match = re.search(r'(\w+):(\w+)', typ)
    if match:
        nsPrefix, typ = match.groups()
    else:
        raise RuntimeError("Unknown namespace prefix for type %s." % typ)

    # based on xsd type, coerce values to python equivalent
    nsMap = DATA_TYPE_MAPPING[nsPrefix]
    coerceFunction = nsMap[typ]

    # return typed val
    if typ in ('base64Binary', 'date', 'dateTime', 'ISODateTime', 'time'):
        return val
    else:
        return coerceFunction(val)

    ##########################################################
    # Code below coerces values into their python types.
    # For now we'll leave it up to the endpoint (soap service,
    # function, etc.) to handle type conversion.
    ##########################################################
    '''
    #return typed val
    #if date
    if xsdType == 'date':
        match = re.search(r'^(\d{4})[-/\s](\d{2})[-/\s](\d{2})$', val)
        if match:
            (year,month,date) = map(int,match.groups())
            return coerceFunction(year,month,date)
        else:
            raise RuntimeError, "Failed to extract year, month and date from %s." % val

    #if datetime
    elif xsdType == 'dateTime' or xsdType == 'ISODateTime':

        #match datetime variations
        match = re.search(r'^(\d{4})[-/\s](\d{2})[-/\s](\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})\.(\d+)$', val)
        if match:
            (year,month,date,hour,min,sec,ms) = map(int,match.groups())
            return coerceFunction(year,month,date,hour,min,sec,ms)

        #no microseconds
        match = re.search(r'^(\d{4})[-/\s](\d{2})[-/\s](\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})$', val)
        if match:
            (year,month,date,hour,min,sec) = map(int,match.groups())
            return coerceFunction(year,month,date,hour,min,sec)

        #no microseconds or seconds
        match = re.search(r'^(\d{4})[-/\s](\d{2})[-/\s](\d{2})[Tt ](\d{2}):(\d{2})$', val)
        if match:
            (year,month,date,hour,min) = map(int,match.groups())
            return coerceFunction(year,month,date,hour,min)

        #raise error
        raise RuntimeError, "Failed to extract datetime elements from %s." % val

    #if time
    elif xsdType == 'time':

        #match time variations
        match = re.search(r'^(\d{2}):(\d{2}):(\d{2})\.(\d+)$', val)
        if match:
            (hour,min,sec,ms) = map(int,match.groups())
            return coerceFunction(hour,min,sec,ms)

        #no microseconds
        match = re.search(r'^(\d{2}):(\d{2}):(\d{2})$', val)
        if match:
            (hour,min,sec) = map(int,match.groups())
            return coerceFunction(hour,min,sec)

        #no microseconds or seconds
        match = re.search(r'^(\d{2}):(\d{2})$', val)
        if match:
            (hour,min) = map(int,match.groups())
            return coerceFunction(hour,min)

        #raise error
        raise RuntimeError, "Failed to extract time elements from %s." % val

    else:
        return coerceFunction(val)
    '''


def transformXml(xmlFileOrString, xslFileOrString):
    """Transfrom xml using XSLT.  Return transformed xml string."""

    # get xml doc
    doc, nsdict = getXmlEtree(xmlFileOrString)

    # get xsl doc
    styledoc, styledict = getXmlEtree(xslFileOrString)

    # get style
    transform = lxml.etree.XSLT(styledoc)

    # get result
    res_tree = transform(doc)

    # return xml
    return lxml.etree.tostring(res_tree, pretty_print=True, encoding='unicode')


def getHtmlBaseHref():
    """Return value for <htmlBaseHref/> configuration parameter."""
    val = sciflo.utils.ScifloConfigParser().getParameter('htmlBaseHref')
    if val is None:
        val = "http://%s/sciflo/web/" % socket.getfqdn()
    return val


def getCgiBaseHref():
    """Return value for <cgiBaseHref/> configuration parameter."""
    val = sciflo.utils.ScifloConfigParser().getParameter('cgiBaseHref')
    if val is None:
        val = "http://%s/sciflo/cgi-bin/" % socket.getfqdn()
    return val


def getExposerProxyUrl():
    """Return value for <exposerProxyUrl/> configuration parameter."""
    return sciflo.utils.ScifloConfigParser().getParameter('exposerProxyUrl')


def getGMapKey():
    """Return value for <gmapKey/> configuration parameter."""
    return sciflo.utils.ScifloConfigParser().getParameter('gmapKey')


def iter2Xml(iter):
    """Return xml list of an iterable."""
    return simpleList2Xml(iter, "list", "item")


def escapeCharsForCDATA(obj):
    """Escape [,],>, and < for CDATA section.  Needed since some browsers (Firefox)
    crap out on them."""
    return obj.replace('>', '&#62;').replace('<', '&#60;').replace('[', '&#91;').replace(']', '&#93;')


# sciflo config xml to grid endpoint xml xsl
GRID_ENDPOINT_CONFIG_XSL = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:transform version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf"
                xmlns:xs ="http://www.w3.org/2001/XMLSchema"
                xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf"
                xmlns:str="http://exslt.org/strings"
                extension-element-prefixes="str"
                exclude-result-prefixes="str">

    <xsl:template match="/">
        <soapEndpoint>
            <endpointName><xsl:value-of select="/sf:scifloConfig/sf:gridNamespace/text()"/></endpointName>
            <soapMethodSet>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:addWorkUnitMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:addWorkUnitMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:queryWorkUnitMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:queryWorkUnitMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:cancelWorkUnitMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:cancelWorkUnitMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:callbackMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:callbackMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:submitScifloMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:submitScifloMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:submitScifloNoCacheMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:submitScifloNoCacheMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:cancelScifloMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:cancelScifloMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
            </soapMethodSet>
        </soapEndpoint>
    </xsl:template>

</xsl:transform>
'''
