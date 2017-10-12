#-----------------------------------------------------------------------------
# Name:        scifloDbXml.py
# Purpose:     Various Utils
#
# Author:      Gerald Manipon
#
# Created:     Mon Feb 28 08:43:00 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import glob
import types
import urllib

from bsddb3.db import *
from dbxml import *
from sciflo.utils import *

def removeContainers(containers):
    """Remove the containers so we can start with a fresh environment."""

    #if single item create a list of single items
    if isinstance(containers,types.StringType): containers = [containers]

    for container in containers:
        (dirname,basename) = os.path.split(os.path.abspath(container))
        (base,ext) = os.path.splitext(basename)
        os.chdir(dirname)
        files = glob.glob(base + "*.dbxml")
        files += glob.glob("__db*")
        files += glob.glob("log.*")
        for file in files: os.remove(file)

class ScifloXmlDbError(Exception):
    """Exception class for ScifloXmlDb class."""
    pass

class ScifloXmlDb(object):
    """Sciflo xml database class."""

    def __init__(self,dbxmlFile):
        """Constructor."""

        #get dbxml file and dir
        self._dbxmlFile = os.path.abspath(dbxmlFile)
        self._dbxmlDir = os.path.dirname(self._dbxmlFile)

        #create dbxml directory if it doesn't exist
        if not os.path.isdir(self._dbxmlDir): os.makedirs(self._dbxmlDir)

        #create env
        self._dbEnv = DBEnv()

        #set DBEnv flags
        #self._dbEnvFlags = DB_THREAD|DB_INIT_MPOOL|DB_INIT_LOCK|DB_INIT_LOG|DB_CREATE
        self._dbEnvFlags = DB_THREAD|DB_INIT_MPOOL|DB_INIT_LOCK|DB_CREATE

        #apply DBEnv flags
        self._dbEnv.open(self._dbxmlDir,self._dbEnvFlags,0)

        #set xmlmanager's flags
        self._mgrFlags = DBXML_ALLOW_AUTO_OPEN|DBXML_ALLOW_EXTERNAL_ACCESS

        #create manager
        self._mgr = XmlManager(self._dbEnv,self._mgrFlags)

        #set default type to NodeContainer
        self._mgr.setDefaultContainerType(XmlContainer.NodeContainer)

        #set container flags
        ##########################################
        #Turned off Schema validation;  Takes a
        #while to retrieve schema, validate, and
        #input per document being inserted.
        #To check performance differences:
        #run: python -m profile -s test test/data/scifloDbxmlTest.py,
        #uncomment the
        #'self._containerFlags = DBXML_ALLOW_VALIDATION'
        #line below and comment out the
        #'self._containerFlags = 0'
        #and run the same python command.
        ##########################################
        #self._containerFlags = DBXML_ALLOW_VALIDATION
        self._containerFlags = 0

        #get container
        if os.path.exists(self._dbxmlFile):
            self._container = self._mgr.openContainer(self._dbxmlFile,self._containerFlags)
        else:
            self._container = self._mgr.createContainer(self._dbxmlFile,self._containerFlags)

    def getInputStreamType(self, input):
        """Return a string describing the appropriate xml input stream for creation of an XmlDocument."""

        if isinstance(input,types.StringType):
            if input.startswith("<"): return 'string'
            elif input.startswith('http:') or input.startswith('https:') or \
                input.startswith('ftp:'): return 'url'
            else: raise ScifloXmlDbError, "Unknown input stream type for %s." % input

    def __evaluateResults(self,results,returnNodeNamesFlag=None):
        """Private method to evaluate results and create a tuple of string results.

        If returnNodeNamesFlag is set, then we just get the name of the nodes in the results.
        Otherwise we return the xml result itself.

        NOTE: We are losing the XmlValue object because there is a segmentation fault
        upon destruction of this class.  For now we will evaluate all results as
        strings and leave type handling to the user of these results.  Return list.
        """

        #reset to the first item
        results.reset()

        #get number of results
        size = results.size()

        #return
        if size > 0:

            #return the results
            #return results

            #########################################################
            #Until the segfault issue is resolved, we'll extract the
            #results as string.
            #We should be able to use the results (iterator object of
            #XmlValue objects to do all kinds of voodoo.
            #########################################################

            #extract XmlValues into a tuple
            resultList = []

            #build result list
            while 1:
                try:
                    result = results.next()
                    resultType = result.getType()
                    if returnNodeNamesFlag: resultList.append(result.asDocument().getName())
                    else: resultList.append(result.asString())
                except StopIteration: break
            return resultList
        elif size == 0: return list()
        else: raise ScifloXmlDbError, "Unknown length of results: %d" % size

    def xqueryDocument(self,docKey,xpath=''):
        """Run xquery on a specific document and return results if successful.
        Otherwise return None.
        """

        #create query context
        qc = self._mgr.createQueryContext()
        docUri = '''doc("%s/%s")%s''' % (self._dbxmlFile,docKey,xpath)

        #run query and get results
        results = self._mgr.query(docUri,qc)

        #evaluate results and return
        return self.__evaluateResults(results)

    def xqueryCollection(self,xpath=''):
        """Run xquery on a collection and return results if successful.
        Otherwise return None.
        """

        #create query context
        qc = self._mgr.createQueryContext()
        docUri = '''collection("%s")%s''' % (self._dbxmlFile,xpath)

        #run query and get results
        results = self._mgr.query(docUri,qc)

        #evaluate results and return
        return self.__evaluateResults(results)

    def insertDocument(self,docKey,docXml,checkExistence=None):
        """Insert an xml docuement with a given key.  Return 1 upon success.  Otherwise
        returns None.
        """

        #create update context
        uc = self._mgr.createUpdateContext()

        #if checkExistence flag was set, then check if it exists.
        if checkExistence:
            qc = self._mgr.createQueryContext()
            doc = self.xqueryDocument(docKey)
            if doc:
                print "docKey %s already exists." % docKey
                return None

        #get proper input stream
        xmlInputType = self.getInputStreamType(docXml)

        #create document and add to container
        document = self._mgr.createDocument()

        #set content based on type
        if xmlInputType == 'string': document.setContent(docXml)
        elif xmlInputType == 'url':
            inputStream = self._mgr.createURLInputStream(docXml,docXml)
            document.setContentAsXmlInputStream(inputStream)
        else: raise ScifloXmlDbError, "Unknown xmlInputType: %s" % xmlInputType

        #set name
        document.setName(docKey)

        #add document to container
        self._container.putDocument(document, uc)

        #return
        return 1

    def removeDocument(self,docKey):
        """Remove an xml document or multiple documents with a given key or list
        of keys.  Return 1 upon success.  Otherwise returns None.
        """

        #create update context
        uc = self._mgr.createUpdateContext()

        #get list of docKeys to remove
        docKeyList = getListFromUnknownObject(docKey)

        #error flag
        successFlag = 1

        #loop over docKeys
        for key in docKeyList:
            try: self._container.deleteDocument(key,uc)
            except Exception, e:
                print "Encountered error deleting document %s: %s" % (docKey,e)
                successFlag = None
        return successFlag

    def addIndex(self,tag,indexSpecs):
        """Add index on tag using the passed XmlIndexSpecifications.
        Return 1 on success."""

        #create update context
        uc = self._mgr.createUpdateContext()

        #add index
        self._container.addIndex("", tag, indexSpecs, uc)

        #return
        return 1

    def queryDocumentIndex(self,stringVal=None,returnNodeNamesFlag=None):
        """Query all documents in the catalog or for one specified by stringVal.  Returns
        a tuple of xml strings for each result.  If returnNodeNamesFlag is set, it just
        returns a tuple of the results' node names."""

        tagUri = 'http://www.sleepycat.com/2002/dbxml'
        tag = 'name'
        indexSpecs = 'unique-node-metadata-equality-string'

        #run query
        results = self._queryIndex(tag,indexSpecs,stringVal,tagUri)

        #evaluate results and return
        return self.__evaluateResults(results,returnNodeNamesFlag)

    def queryIndex(self,tag,indexSpecs,stringVal=None,tagUri="",returnNodeNamesFlag=None):
        """Query a specified index for all nodes matching the tag, tagUri, and indexSpecs passed.
        If stringVal is specified, try to find matching results.  Return a tuple of xml strings for
        each result.  If returnNodeNamesFlag is set, it just returns a tuple of the results' node
        names."""

        #run query
        results = self._queryIndex(tag,indexSpecs,stringVal,tagUri)

        #evaluate results and return
        return self.__evaluateResults(results,returnNodeNamesFlag)

    def _queryIndex(self,tag,indexSpecs,stringVal=None,tagUri=""):
        """Private method to query in index.

        NOTE: We've only implemented index querying for string type indexes.  Future
        types will be incorporated.
        """

        #check that this is only a string type index
        if isinstance(indexSpecs,types.StringType):
            if not indexSpecs.endswith('-string'):
                raise NotImplementedError, "This methods only accepts queries against string indices."""

        #create query context
        qc = self._mgr.createQueryContext()

        #if value was not specified, query all
        if stringVal is None:
            xmlResults = self._container.lookupIndex(qc,tagUri,tag,indexSpecs)
        #otherwise, create an XmlValue object to match
        else:
            xmlVal = XmlValue(XmlValue.STRING,stringVal)
            xmlResults = self._container.lookupIndex(qc,tagUri,tag,indexSpecs,xmlVal)

        #return xml results
        return xmlResults

    def __del__(self):
        """Destructor."""

        #close container
        self._container.close()

        #close environment
        self._dbEnv.close(0)

