import os
import copy
import re
import socket
import pwd
from lxml.etree import Element, SubElement, _Comment, tostring
from string import Template

from sciflo.utils.xmlUtils import isXml, getXmlEtree
from sciflo.utils.timeUtils import getISODateTimeString

XML_CHAR_CMP = re.compile(r'(?:<|>|&)')


class AnnotatedDocError(Exception):
    pass


class AnnotatedDoc(object):
    def __init__(self, sflDoc, outputDir):
        """Constructor."""

        self.host = socket.getfqdn()
        self.user = pwd.getpwuid(os.getuid())[0]
        self.pid = os.getpid()
        self.sflDoc = sflDoc
        self.outputDir = outputDir
        self.rootElt = copy.deepcopy(self.sflDoc._eltDoc)
        self.nsDict = copy.deepcopy(self.sflDoc._namespacePrefixDict)

        self.sfEltTagTpl = Template('{%s}$tag' % self.nsDict['sf'])
        self.flowElt = self.rootElt.xpath('sf:flow', namespaces=self.nsDict)[0]
        self.resultsElt = SubElement(self.flowElt,
                                     self.sfEltTagTpl.substitute(tag='results'))
        self.resultsOutputsElt = SubElement(self.resultsElt,
                                            self.sfEltTagTpl.substitute(tag='outputs'))
        for otElt in self.rootElt.xpath('sf:flow/sf:outputs', namespaces=self.nsDict)[0]:
            if isinstance(otElt, _Comment) or otElt.tag is None:
                continue
            ot = SubElement(self.resultsOutputsElt, otElt.tag)
        self.resultsProcessesElt = SubElement(self.resultsElt,
                                              self.sfEltTagTpl.substitute(tag='processes'))
        for thisProcId in [i.getId() for i in self.sflDoc.getWorkUnitConfigs()]:
            thisProcElt = self.rootElt.xpath(
                'sf:flow/sf:processes/sf:process[@id="%s"]' % thisProcId,
                namespaces=self.nsDict)
            if len(thisProcElt) == 1:
                thisProcElt = thisProcElt[0]
            else:
                thisProcElt = None
            thisResProcElt = SubElement(self.resultsProcessesElt,
                                        self.sfEltTagTpl.substitute(tag='process'))
            thisResProcElt.set('procId', thisProcId)
            thisResProcOutputElt = SubElement(thisResProcElt,
                                              self.sfEltTagTpl.substitute(tag='outputs'))
            if thisProcElt is None:
                resProcOutputElt = SubElement(thisResProcOutputElt,
                                              'implicitOutput')
            else:
                for thisProcOutputElt in thisProcElt.xpath('sf:outputs',
                                                           namespaces=self.nsDict)[0]:
                    if isinstance(thisProcOutputElt, _Comment) or \
                            thisProcOutputElt.tag is None:
                            continue
                    resProcOutputElt = SubElement(thisResProcOutputElt,
                                                  thisProcOutputElt.tag)

        # write info for provenance: host, user, pid, version
        self.resultsElt.set('host', self.host)
        self.resultsElt.set('user', self.user)
        self.resultsElt.set('pid', str(self.pid))
        self.version = self.flowElt.get('version', None)
        if self.version is None:
            self.resultsElt.set('version', 'v0.1')
        else:
            self.resultsElt.set('version', self.version)

        self.file = os.path.join(self.outputDir, 'sciflo.sf.xml')
        self.write()

    def update(self, elt, val, doCDATA=False):
        """Updated annotated sciflo element."""

        # add CDATA placeholders
        if doCDATA:
            elt.text = "SCIFLO_CDATA_BEGIN\n%sSCIFLO_CDATA_END" % str(val)
        else:
            if isXml(val):
                valElt, valNs = getXmlEtree(val)
                elt.append(valElt)
            else:
                val = str(val)
                if XML_CHAR_CMP.search(val):
                    return self.update(elt, val, doCDATA=True)
                else:
                    elt.text = val
        return True

    def write(self, resolveCDATA=True):
        """Write current annotated sciflo xml to file."""

        f = open(self.file, 'w')
        if resolveCDATA:
            retVal = f.write('%s\n' %
                             tostring(self.rootElt, pretty_print=True, encoding='unicode').replace(
                                 'SCIFLO_CDATA_BEGIN', '<![CDATA[').replace(
                                 'SCIFLO_CDATA_END', ']]>').replace(
                                 '&lt;', '<').replace(
                                 '&gt;', '>').replace(
                                 '&amp;', '&')
                             )
        else:
            retVal = f.write('%s\n' %
                             tostring(self.rootElt, pretty_print=True, encoding='unicode'))
        f.close()
        return retVal

    def addScifloStarted(self, executable):
        """Add info for startup of sciflo execution."""

        self.resultsElt.set('starttime', getISODateTimeString(True))
        self.resultsElt.set('executable', executable)
        self.write()

    def addScifloFinished(self):
        """Add info for shutdown of sciflo execution."""

        self.resultsElt.set('endtime', getISODateTimeString(True))
        self.write()

    def addProcessStarted(self, procId):
        """Add info for startup of a processing step."""

        xpath = 'sf:flow/sf:results/sf:processes/sf:process[@procId="%s"]' % procId
        thisProcElt = self.rootElt.xpath(xpath, namespaces=self.nsDict)[0]
        thisProcElt.set('starttime', getISODateTimeString(True))
        self.write()

    def addProcessFinished(self, procId, pidFile):
        """Add info for a processing step that finished."""

        try:
            f = open(pidFile, 'r')
            pid = f.read()
            f.close()
        except:
            pid = 'unknown'
        xpath = 'sf:flow/sf:results/sf:processes/sf:process[@procId="%s"]' % procId
        thisProcElt = self.rootElt.xpath(xpath, namespaces=self.nsDict)[0]
        thisProcElt.set('endtime', getISODateTimeString(True))
        thisProcElt.set('pid', pid.strip())
        self.write()

    def addResultForImplicitProcess(self, procId):
        """Add process to result section."""

        thisResProcElt = SubElement(self.resultsProcessesElt,
                                    self.sfEltTagTpl.substitute(tag='process'))
        thisResProcElt.set('procId', procId)
        thisResProcOutputElt = SubElement(thisResProcElt,
                                          self.sfEltTagTpl.substitute(tag='outputs'))
        resProcOutputElt = SubElement(thisResProcOutputElt, 'output')
        self.write()

    def addProcessResult(self, procId, result):
        """Annotate sciflo document with result."""

        # get result procid output elements
        outputElts = self.rootElt.xpath(
            "sf:flow/sf:results/sf:processes/sf:process[@procId='%s']/sf:outputs/*" %
            procId, namespaces=self.nsDict)

        # if only one, set result
        if len(outputElts) == 1:
            self.update(outputElts[0], result)
        else:
            for i, otElt in enumerate(outputElts):
                self.update(otElt, result[i])
        self.write()

    def addProcessException(self, procId, tracebackMessage):
        """Annotate sciflo document with exception."""

        # clean out outputs elements
        outputElt = self.rootElt.xpath(
            "sf:flow/sf:results/sf:processes/sf:process[@procId='%s']/sf:outputs" % procId,
            namespaces=self.nsDict)
        if len(outputElt) == 0:
            self.addResultForImplicitProcess(procId)
        outputElt = self.rootElt.xpath(
            "sf:flow/sf:results/sf:processes/sf:process[@procId='%s']/sf:outputs" % procId,
            namespaces=self.nsDict)[0]
        outputElt.clear()

        # write error
        self.update(outputElt, tracebackMessage, doCDATA=True)
        self.write()

    def addGlobalOutput(self, outputIdx, result):
        """Annotate sciflo document with a global output result."""

        if isinstance(result, Exception) or outputIdx is None:
            self.resultsOutputsElt.clear()
            sflErrorElt = SubElement(self.resultsOutputsElt,
                                     'ScifloExecutorError')
            self.update(sflErrorElt, result, doCDATA=True)
        else:
            ot = self.resultsOutputsElt[outputIdx]
            self.update(ot, result)
        self.write()
