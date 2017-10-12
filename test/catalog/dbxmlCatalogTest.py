#-----------------------------------------------------------------------------
# Name:        dbxmlCatalogTest.py
# Purpose:     Unit testing for dbxmlCatalog.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 05 09:53:11 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import os
from tempfile import mkdtemp
import shutil

from sciflo.catalog import *

#gps objectid
objectid = '20040629_1023chm_g34_1p0'

#local file path
localFile = '/genesis/ftp/pub/genesis/glevels/champ/1p0/y2004/2004-06-29/L2/txt/20040629_1023chm_g34_1p0.L2.txt.gz'

#local file url
localFileUrl = 'file:///genesis/ftp/pub/genesis/glevels/champ/1p0/y2004/2004-06-29/L2/txt/20040629_1023chm_g34_1p0.L2.txt.gz'

#http url
httpUrl = 'http://sciflo.jpl.nasa.gov/genesis/glevels/champ/1p0/y2004/2004-06-29/L2/txt/20040629_1023chm_g34_1p0.L2.txt.gz'

#ftp url
ftpUrl = 'ftp://sciflo.jpl.nasa.gov/genesis/glevels/champ/1p0/y2004/2004-06-29/L2/txt/20040629_1023chm_g34_1p0.L2.txt.gz'

#dods url
dodsUrl = 'http://sciflo.jpl.nasa.gov/sciflo/cgi-bin/nph-dods/genesis/gps/glevels/champ/1p0/y2004/2004-06-29/L2/txt/20040629_1023chm_g34_1p0.L2.txt'

#all urls
allUrls = [localFile,localFileUrl,httpUrl,ftpUrl,dodsUrl]

#instrument
instrument = 'GPS'

#level
level = 'L2'

#schema url
schemaUrl = 'catalog.xsd'

class dbxmlCatalogTestCase(unittest.TestCase):
    """Test case for dbxmlCatalog."""

    def setUp(self):
        """Setup."""

        #dbxml dir
        self.dbDir = mkdtemp()

        #get filename
        self.dbxmlFile = os.path.join(self.dbDir,"%s_%s.dbxml" % (instrument,level))

        #print "dbxmlFile is",self.dbxmlFile

        #get the object
        self.obj = DbxmlCatalog(self.dbxmlFile,schemaUrl=schemaUrl)

    def testQueryEmpty(self):
        """Test querying an objectid that doesn't exist."""

        #query
        queryResult = self.obj.query(objectid)
        #print "Query produced: ", queryResult
        assert queryResult == []

    def testInsert(self):
        """Test inserting an objectid and single dataObject."""

        #insert item
        insertResult = self.obj.update(objectid,localFile)
        #print "Insert produced: ", insertResult
        assert insertResult == 1

        #query
        queryResult = self.obj.query(objectid)
        #print "Query produced: ", queryResult
        assert queryResult == [localFile]

    def testRemove(self):
        """Test removing an objectid and dataObject."""

        #insert item
        insertResult = self.obj.update(objectid,localFile)
        #print "Insert produced: ", insertResult
        assert insertResult == 1

        #query
        queryResult = self.obj.query(objectid)
        #print "Query produced: ", queryResult
        assert queryResult == [localFile]

        #remove
        removeResult = self.obj.remove(objectid)
        #print "Remove produced: ", removeResult
        assert removeResult == 1

        #query
        queryResult = self.obj.query(objectid)
        #print "Query produced: ", queryResult
        assert queryResult == []

    def testInsertList(self):
        """Test inserting an objectid and list of dataObjects."""

        #add a list of dataObjects
        insert2Result = self.obj.update(objectid,allUrls)
        #print "Insert #2 produced: ", insert2Result
        assert insert2Result == 1

        #query
        queryResult = self.obj.query(objectid)
        #print "Query produced: ", queryResult
        assert queryResult == allUrls

    def testGetAllObjectids(self):
        """Test getting all objectids."""

        #add a list of dataObjects
        insert2Result = self.obj.update(objectid,allUrls)
        #print "Insert #2 produced: ", insert2Result
        assert insert2Result == 1

        #get objectids
        objectids = self.obj.getAllObjectids()
        #print objectids
        assert objectids == [objectid]

    def tearDown(self):
        """Cleanup."""

        #remove container files and dbDir
        removeContainers(self.dbxmlFile)
        shutil.rmtree(self.dbDir)

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    dbxmlCatalogTestSuite = unittest.TestSuite()
    dbxmlCatalogTestSuite.addTest(dbxmlCatalogTestCase("testQueryEmpty"))
    dbxmlCatalogTestSuite.addTest(dbxmlCatalogTestCase("testInsert"))
    dbxmlCatalogTestSuite.addTest(dbxmlCatalogTestCase("testRemove"))
    dbxmlCatalogTestSuite.addTest(dbxmlCatalogTestCase("testInsertList"))
    dbxmlCatalogTestSuite.addTest(dbxmlCatalogTestCase("testGetAllObjectids"))

    #return
    return dbxmlCatalogTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)


