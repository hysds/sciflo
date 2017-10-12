#!/bin/env python
#-----------------------------------------------------------------------------
# Name:      xmldb.py
# Purpose:   Wrapper interface for XML Database functionality:
#              createContainer, createDocument, xquery, addIndex, etc.
#            (First version only wraps single backend, Sleepycat dbxml)
#
# Author:      Brian Wilson
#
# Created:     Thu Feb 2 17:18:44 2006
# Copyright:   (c) 2005, California Institute of Technology / Jet Propulsion Laboratory
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------

USAGE = """
xmldb.py [-q <xquery>] [-u <xqueryUrl>] xmlDocUrls . . . [< <xmlDoc>] [> <queryResults>]

Xmldb performs an XQuery-style query (either XPath 2.0 or XQuery 1.0) on one or
more XML documents and prints the results to stdout.

The query can be supplied as a string to the '-q' switch or read from a specified
file or remote URL using the '-u' switch.  A list of one or more XML documents,
as files or remote URL's, are specified on the command line.  Alternatively, if
no documents are specified, an XML document will be read from stdin.

Of course, a document URL can be also be any HTTP GET request (a one-line URL)
that returns an XML document.  Thus, one can hit a web service and extract or
reformat information from the returned XML in a single call to xmldb.
"""

import sys, os, re, types
from bsddb3 import *
import dbxml
from dbxml import XmlManager, XmlValue
from cStringIO import StringIO
#from tempfile import mkstemp
from datetime import datetime
from urllib import urlopen
from lxml.etree import XML

Verbose = True

def warn(*str): sys.stderr.write(' '.join(str) + '\n')
def die(str, status=1): warn(str); sys.exit(status)

class XmlDb:
    """Holds XML database context like toplevel manager, container, transactionContext, etc.
    Has methods to createContainer, removeContainer, setActiveContainer, putDocument (to active
    container), getDocument, printDocument, commit a transaction, do an xquery, etc. 
    """ 
    def __init__(self, containerFile=None, dbManager=None, container=None,
                 updateContext=None, transactional=False, transaction=None,
                 dbEnv=None, actualDb='dbxml', verbose=False):
        """Set .dbManager, .container, .updateContext, & .queryContext.
        Optionally set self.transactional, .transaction, & .dbEnv.
        """
        self.verbose = verbose
        if actualDb != 'dbxml':
            die('XmlDB: Only Sleepycat dbxml currently implemented as back end.')
        if transactional or transaction or dbEnv is not None:
            self.transactional = True
            if dbEnv is None:
                self.dbEnv = DBEnv()
                self.dbEnv.open(None, dbxml.DB_CREATE|dbxml.DB_INIT_LOCK|dbxml.DB_INIT_LOG|
                                      dbxml.DB_INIT_MPOOL|dbxml.DB_INIT_TXN, 0)
            else:
                self.dbEnv = dbEnv
        else:
            self.transactional = False
            self.transaction = None
            self.dbEnv = None
        if dbManager is None:
            if self.transactional:
                self.dbManager = XmlManager(self.dbEnv, 0)
            else:
                self.dbManager = XmlManager()
        else:
            self.dbManager = xmlManager
        if self.transactional:
            if transaction is None:
                self.transaction = self.dbManager.createTransaction()
            else:
                self.transaction = transaction
        if containerFile and container:
            die('XmlDb: Either create a new containerFile or pass in an existing container.  Not both.')
        self.containerAlias = None
        if container:
            self.container = container
        else:
            if containerFile:
                self.containerFile = containerFile
                if self.transactional:
                    self.container = self.dbManager.createContainer(containerFile, dbxml.DBXML_TRANSACTIONAL)
                else:
                    self.container = self.dbManager.createContainer(containerFile)
                self.containerAlias = os.path.basename(containerFile)
                self.container.addAlias(self.containerAlias)
            else:
                self.container = None
        if updateContext is None:
            self.updateContext = self.dbManager.createUpdateContext()
        else:
            self.updateContext = updateContext
        self.queryContext = self.dbManager.createQueryContext()
    
    def createContainer(self, containerFile):
        """Create a container within the database (can be multiple containers)."""
        self.containerFile = containerFile
        if self.transactional:
            self.container = self.dbManager.createContainer(containerFile, dbxml.DBXML_TRANSACTIONAL)
        else:
            self.container = self.dbManager.createContainer(containerFile)
        return self
    
    def setActiveContainer(self, containerFile):
        """Activate a particular container"""
        self.container = self.dbManager.openContainer(containerFile)
        return self
    
    def removeContainer(self, containerFile):
        self.dbManager.removeContainer(containerFile)
        return self    
    
    def commit(self):
        if self.transactional:
            self.transaction.commit()
        else:
            warn('XmlDb: commit is a no-op on a non-transactional db.')
        return self
    
    def putDocument(self, name, doc):
        if self.verbose: warn('xmldb: inserting %s into %s:\n%s' % \
                      (name, self.containerFile, firstThreeLines(doc)))
        if self.transactional:
            self.container.putDocument(self.transaction, name, doc, self.updateContext)
        else:
            self.container.putDocument(name, doc, self.updateContext)
        return self
    
    def getDocument(self, name): return self.container.getDocument(name)
    
    def printDocument(self, name): print self.getDocument(name).getContent()
    
    def setNamespaces(self, namespaces=None):
        queryContext = self.dbManager.createQueryContext()
        if namespaces is not None:
            for prefix, uri in namespaces.iteritems():
                if self.verbose: warn('xmldb: setNamespace %s: %s' % (prefix, uri)) 
                queryContext.setNamespace(prefix, uri)
        self.queryContext = queryContext
        return self
    
    def getQueryContext(self): return self.queryContext
    
    def xquery(self, query, namespaces=None):
        """Perform an XQuery and return the resultSet.
        If a namespaces dictionary of {prefix: URI} is provided, then the queryContext is replaced.
        """
        if namespaces: self.setNamespaces(namespaces)
        queryProlog = 'declare namespace my = "http://fubar.net/my";\n'
        if self.containerAlias:
            queryProlog += 'declare variable $top := fn:collection("%s");\n\n' % self.containerAlias
        else:
            queryProlog += 'declare variable $top := fn:collection("%s");\n\n' % self.containerFile
    #        queryProlog += 'declare function my:top() {let $r := fn:collection("%s") return $r};\n\n' % self.containerFile
        warn('xmldb: query prolog:\n%s' % queryProlog)
        fullQuery = queryProlog + query.strip()
        if self.verbose: warn('xmldb: query:\n%s' % fullQuery)
        return self.dbManager.query(fullQuery, self.queryContext)
    
    def xqueryResults(self, query, namespaces=None):
        """Perform an XQuery and return the results as a string."""
        results = self.xquery(query, namespaces)
        f = StringIO()
        for item in results:
            print >>f, item.asString().strip()
        return f.getvalue().strip()
    
    def close(self):
        if transactional: self.dbEnv.close()
        
# Simple query functions follow.
def createQueryableDocuments(docs, namespaces=None, tempContainerFile=None, verbose=True):
    """Create a temporary XML database and insert the document."""
    if isinstance(docs, types.StringType): docs = [docs]
    if isinstance(docs, types.TupleType): docs = dict(docs)
    if namespaces is None: namespaces = {}    
    if tempContainerFile is None:
#        fh, tempContainerFile = mkstemp('.dbxml', 'xmldbtemp'); os.close(fh)
        tempContainerFile = '/tmp/xmldb_tmpfile%s.dbxml' % fileTimeStampNow()

    if verbose: warn('xmldb: creating container %s' % tempContainerFile)
    db = XmlDb(tempContainerFile, verbose=True)
    if isinstance(docs, types.ListType):
        for i, doc in enumerate(docs):
            if not doc.strip().startswith('<'):
                if verbose: warn('xmldb: Retrieving %s' % doc)
                doc = urlopen(doc).read()
            name = 'doc%6.6d' % (i+1)
            db.putDocument(name, doc)
            namespaces.update( extractNamespaces(doc) )
    elif isinstance(docs, types.DictType):
        for name, doc in docs.iteritems():
            if not doc.strip().startswith('<'):
                if verbose: warn('xmldb: Retrieving %s' % doc)
                doc = urlopen(doc).read()
            db.putDocument(name, doc)
            namespaces.update( extractNamespaces(doc) )            
    else:
        die('xmldb.py: createQueryableDocuments: Bad docs array or dict.')
    return (db, namespaces)

def doXQuery(docs, query, namespaces=None, tempContainerFile=None, verbose=False):
    """XQuery the document and return the resultSet and reusable queryContext."""
    db, namespaces = createQueryableDocuments(docs, namespaces, tempContainerFile, verbose)
    results = db.xquery(query, namespaces)
    return (results, db) 

def getXQueryResults(docs, query, namespaces=None, tempContainerFile=None, verbose=False):
    """XQuery the document and return the results as a string, discarding temporary db."""
    db,namespaces = createQueryableDocuments(docs, namespaces, tempContainerFile, verbose)
    return db.xqueryResults(query, namespaces)

def xquerySingleDoc(doc, query, namespaces={}, verbose=False):
    """XQuery the document and return the results as a string."""
    if not doc.strip().startswith('<'): doc = urlopen(doc).read()
    mgr = XmlManager(dbxml.DBXML_ALLOW_EXTERNAL_ACCESS)
    queryContext = mgr.createQueryContext()
    namespaces.update( extractNamespaces(doc) )
    for prefix, uri in namespaces.iteritems():
        if verbose: warn('xmldb: setNamespace %s: %s' % (prefix, uri))
        queryContext.setNamespace(prefix, uri)

    queryProlog = 'declare namespace my = "http://fubar.net/my";\n'
    queryProlog += "declare variable $top := '.';\n\n"
    warn('xmldb: query prolog:\n%s' % queryProlog)
    fullQuery = queryProlog + query.strip()
    if verbose: warn('xmldb: query:\n%s' % fullQuery)

    xdoc = mgr.createDocument()
    xdoc.setContent(doc)
    xval = XmlValue(xdoc)
    queryExpr = mgr.prepare(fullQuery, queryContext)
    results = queryExpr.execute(xval, queryContext)

    f = StringIO()
    for item in results:
        print >>f, item.asString().strip()
    return f.getvalue().strip()

def extractNamespaces(doc):
    """Extract xmlns:prefix="namespace" pairs from the root element of the
    XML document and return a dictionary.  The default namespace (xmlns="ns")
    is also extracted and saved under the null ('') prefix.
    """
    ns = {}
    match = re.search(r'<\w+ .*?>', doc, re.DOTALL)
    if match:
        rootElement = match.group(0)
        match = re.search(r'xmlns=[\'"](.*?)[\'"]', rootElement, re.DOTALL)
        if match:
            ns['_'] = match.group(1)   # default namespace
            ns[''] = match.group(1)
            ns['_default'] = match.group(1)
        matches = re.finditer(r'xmlns:(\w+?)=[\'"](.*?)[\'"]', rootElement, re.DOTALL)
        for match in matches:
            ns[match.group(1)] = match.group(2)   # prefix = ns
    return ns

def extractNamespaces2(doc):
    """Extract xmlns:prefix="namespace" pairs from the root element of the
    XML document and return a dictionary.  The default namespace (xmlns="ns")
    is also extracted and saved under the null ('') prefix.
    """
    ns = {}
    tree = XML(doc)
    for elt in tree.getiterator():
        for key, ns in elt.attrib.iteritems():
            if key.startswith('xmlns'):
                if key.find(':') > 0:
                    junk, prefix = key.split(':')
                else:
                    prefix = '_default'
                ns[prefix] = ns
    return ns

def extractNamespaces3(doc):
    """Extract xmlns:prefix="namespace" pairs from the root element of the
    XML document and return a dictionary.  The default namespace (xmlns="ns")
    is also extracted and saved under the null ('') prefix.
    """
    def getPrefix(attrib):
        if attrib.find(':') > 0:
            return attrib.split(':')[1]
        else:
            return '_default'
    
    return dict([ (getPrefix(attrib), ns) for attrib, ns in elt.attrib.iteritems()
                      if attrib.startswith('xmlns') for elt in XML(doc).getiterator() ])

    
# Utilities follow.
def fileTimeStampNow(utc=False):
    if utc:
        time = datetime.utcnow().isoformat()
    else:
        time = datetime.now().isoformat()
    return ''.join( re.match(r'(....)-(..)-(..T..):(..):(.*)', time).groups() )

def firstThreeLines(s):
    return s[0:s.find('\n',s.find('n',s.find('\n', 0)+1)+1)]


if __name__ == "__main__":
    from sys import argv
    import getopt
#    if len(argv) < 1: die(USAGE)
    try:
        opts, argv = getopt.getopt(argv[1:], 'hn:p:q:u:v',
            ['help', 'namespace', 'prefix', 'query', 'queryUrl', 'verbose'])
    except getopt.GetoptError, (msg, bad_opt):
        die("%s error: Bad option: %s, %s" % (argv[0], bad_opt, msg))

    query = None; queryUrl = None; namespaces = []; prefixes = []; Verbose = False    
    for opt, val in opts:
        if opt   in ('-h', '--help'):      die(USAGE)
        elif opt in ('-n', '--namespace'): namespaces.append(val)      
        elif opt in ('-p', '--prefix'):
            if val == 'default': val = ''
            prefixes.append(val)      
        elif opt in ('-q', '--query'):     query=val      
        elif opt in ('-u', '--queryUrl'):  queryUrl=val
        elif opt in ('-v', '--verbose'):   Verbose=True
    
    if queryUrl: query = urlopen(queryUrl).read()
    if query is None: warn('XmlDB error: No query specified.'); die(USAGE)
    namespaceDict = {}
    for prefix, namespace in zip(prefixes, namespaces):
        namespaceDict[prefix] = namespace

    docs = argv
    if len(docs) == 0: docs['stdin'] = sys.stdin.read()

    if len(docs) == 1:
        print xquerySingleDoc(docs[0], query, namespaceDict, verbose=Verbose)
    else:
        print getXQueryResults(docs, query, namespaceDict, verbose=Verbose)

#    results, db = doXQuery(docs, query, namespaceDict, verbose=Verbose)
#    for item in results:
#        print item.asString()
    
# Examples follow:
"""
xmldb.py -v -p default -n http://schemas.xmlsoap.org/wsdl/ -q /definitions/portType/operation http://gen-dev.jpl.nasa.gov:8080/genesis/wsdl/L2AIRSData.wsdl
xmldb.py -v -p default -n http://schemas.xmlsoap.org/wsdl/ -q 'doc("http://gen-dev.jpl.nasa.gov:8080/genesis/wsdl/L2AIRSData.wsdl")/definitions/portType/operation'
"""
