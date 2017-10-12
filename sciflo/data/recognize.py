#-----------------------------------------------------------------------------
# Name:        recognize.py
# Purpose:     The recognize module provides an object recognition service to the
#              entire SfiFlo dataflow network.  The conventional names (pseudo-URIs)
#              of recognizable objects (data files) are registered with the system
#              by providing a regular expression that matches the file name.
#              Every attempt is made to provide a pair of reversible services
#              (recognize <--> resolve) that can convert 'crawled' URLs to URIs
#              (recognize) and translate saved URIs to one or more URLs (resolve)
#              that point to replicas of the object.
#
#              The recognize service is used by the localize module to recognize
#              data objects as they are moved and cached within the SciFlo network.
#              A recognized object will be cached in a known and pre-computable
#              directory location on each node.  Thus, checking the cache for a
#              recognized object is reduced to generating its unique directory
#              location and then checking for the existence of that file on disk.
#              No translation database (URI --> URL) is required to look up
#              recognizable URIs in the cache.  A crawler translation database
#              is used to enable lookup of URLs 'discovered' at the primary (or
#              production) site for each data product.
#
# Author:      Brian Wilson
#              Gerald Manipon
#
# Created:     Mon Aug 06 09:19:36 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import sys, os, re, socket, types, pwd
import lxml.etree
from string import Template

from sciflo.utils import getXmlEtree, runXpath, getUserDatasetsDir

def getSystemLevelUserDir():
    """Return system-level sciflo directory."""
    return os.path.join(pwd.getpwuid(os.stat(sys.prefix)[4])[5], '.sciflo')

class RecognizerError(Exception): pass

class Recognizer:
    def __init__(self, datasetInfo=None, SCIFLO_ROOT=None):
        self.datasetInfo = datasetInfo
        self.startsWithMatcher, self.matchers = self.init(datasetInfo)
        self.currentMatcher = None
        self.currentIpath = None
        self.currentDataset = None
        self.groupDict = None
        self.hostname = socket.getfqdn()
        if SCIFLO_ROOT is None:
            self.scifloRoot = os.path.join(sys.prefix, 'share', 'sciflo')[1:]
        else: self.scifloRoot = SCIFLO_ROOT[1:]
        
    def init(self, datasetInfo):
        """Initialize the recognizer from a collection of datasetInfo (XML) documents.
        """
        #use user's dataset directory if not specified
        if datasetInfo is None: datasetInfo = getUserDatasetsDir()
        
        if os.path.isfile(datasetInfo):
            datasetInfos = [datasetInfo]
        elif os.path.isdir(datasetInfo):
            datasetInfos = [os.path.join(datasetInfo, f) for f in os.listdir(datasetInfo) \
                            if f.endswith('.xml')]
        elif isinstance(datasetInfo, (types.ListType, types.TupleType)):
            datasetInfos = datasetInfo
        else: raise RecognizerError, "Unknown datasetInfo type: %s" % type(datasetInfo)
        
        #append system level datasets xml
        systemLevelDatasetDir = os.path.join(getSystemLevelUserDir(), 'datasets')
        datasetInfos.extend([os.path.join(systemLevelDatasetDir, f) for f in \
                             os.listdir(systemLevelDatasetDir) if f.endswith('.xml')])
        
        patterns = {}; startsWiths = []; matchers = {}
        for f in datasetInfos:
            info, ns = getXmlEtree(f)
            if not ns.has_key('_'): ns['_'] = ns['_default']
            for dataset in info:
                
                #skip if comment
                if isinstance(dataset, lxml.etree._Comment): continue
                
                ipath = runXpath(dataset, './/_:ipath/text()', ns)
                fileTemplate = runXpath(dataset, './/_:fileTemplate/text()', ns)
                startsWith = fileTemplate[0:fileTemplate.index('$')]
                filePattern = runXpath(dataset, './/_:filePattern/text()', ns)
                if matchers.has_key(startsWith):
                    matchers[startsWith].append((re.compile(filePattern), ipath, dataset, ns))
                else: matchers[startsWith] = [(re.compile(filePattern), ipath, dataset, ns)]
                if startsWith != '': startsWiths.append(startsWith)
        startsWithPattern = r'(' + '|'.join(startsWiths) + ')'
        startsWithMatcher = re.compile(startsWithPattern)
        return startsWithMatcher, matchers
    
    def _setCurrent(self, matcher, ipath, dataset, datasetNs, groupDict):
        """Set current matcher, ipath, dataset, datsetNs, and groupDict."""
        self.currentMatcher = matcher
        self.currentIpath = ipath
        self.currentDataset = dataset
        self.currentDatasetNs = datasetNs
        self.groupDict = groupDict
        return True
    
    def _unsetCurrent(self):
        """Clear current matcher, ipath, and datset."""
        self.currentMatcher = None
        self.currentIpath = None
        self.currentDataset = None
        self.currentDatasetNs = None
        self.groupDict = None
        return True
    
    def recognize(self, filename):
        """Recognize and return ipath.  Otherwise return None."""
        fileBasename = os.path.basename(filename)
        startsWithDigit = re.search(r'^\d', fileBasename)
        mat = self.startsWithMatcher.match(fileBasename)
        if not mat and not startsWithDigit:
            return None
        else:
            if mat: startsWith = mat.group(1)
            else: startsWith = ''
            if startsWith == '' and not startsWithDigit: return None
            for matcher, ipath, dataset, ns in self.matchers[startsWith]:
                filePatternMatch = matcher.match(fileBasename)
                if filePatternMatch:
                    self._setCurrent(matcher, ipath, dataset, ns,
                                     filePatternMatch.groupdict())
                    return ipath
            return None
    
    def isRecognized(self, filename):
        """Return True if recognized, False otherwise."""
        if self.recognize(filename) is not None: return True
        else: return False
        
    def getPublishPath(self, filename):
        """Generate and return the publish path for the filename."""
        
        #recognize first
        if not self.isRecognized(filename): return None
        else:
            filename = Template(runXpath(self.currentDataset,
                './/_:fileTemplate/text()', self.currentDatasetNs)).substitute(\
                self.groupDict, hostname=self.hostname, SCIFLO_ROOT=self.scifloRoot)
            publishAtTpls = runXpath(self.currentDataset,
                './/_:publishAt/_:location/_:data/text()',
                self.currentDatasetNs)
            if isinstance(publishAtTpls, (types.ListType, types.TupleType)):
                publishTpl = publishAtTpls[0]
            else: publishTpl = publishAtTpls
            publishAt = Template(publishTpl).substitute(self.groupDict,
                hostname=self.hostname, SCIFLO_ROOT=self.scifloRoot)
            return os.path.join(publishAt, filename)
