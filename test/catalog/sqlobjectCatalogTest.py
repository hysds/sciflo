#-----------------------------------------------------------------------------
# Name:        sqlobjectCatalogTest.py
# Purpose:     Unit tests for the SqlObjectCatalog class.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 25 14:04:56 2006
# Copyright:   (c) 2006, California Institute of Technology.
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

#scheme i.e. scheme='mysql://user:password@fqdn:port/test'
scheme = 'mysql://127.0.0.1:3306/test'

class SqlObjectCatalogTestCase(unittest.TestCase):
    """Test case for SqlObjectCatalog."""

    def setUp(self):
        """Setup."""
        self.obj = SqlObjectCatalog(scheme)

    def testQueryEmpty(self):
        """Test querying an objectid that doesn't exist."""

        #query
        queryResult = self.obj.query(objectid)
        assert queryResult == []

    def testInsert(self):
        """Test inserting an objectid and single dataObject."""

        #insert item
        insertResult = self.obj.update(objectid,localFile)
        assert insertResult == 1

        #query
        queryResult = self.obj.query(objectid)
        assert queryResult == [localFile]

    def testRemove(self):
        """Test removing an objectid and dataObject."""

        #insert item
        insertResult = self.obj.update(objectid,localFile)
        assert insertResult == 1

        #query
        queryResult = self.obj.query(objectid)
        assert queryResult == [localFile]

        #remove
        removeResult = self.obj.remove(objectid)
        assert removeResult == 1

        #query
        queryResult = self.obj.query(objectid)
        assert queryResult == []

    def testInsertList(self):
        """Test inserting an objectid and list of dataObjects."""

        #add a list of dataObjects
        insert2Result = self.obj.update(objectid,allUrls)
        assert insert2Result == 1

        #query
        queryResult = self.obj.query(objectid)
        assert queryResult == allUrls

    def testGetAllObjectids(self):
        """Test getting all objectids."""

        #add a list of dataObjects
        insert2Result = self.obj.update(objectid,allUrls)
        assert insert2Result == 1
        insert2Result = self.obj.update('test',allUrls)
        assert insert2Result == 1

        #get objectids
        objectids = self.obj.getAllObjectids()
        assert objectids == [objectid,'test']

    def tearDown(self):
        """Cleanup."""
        self.obj.removeAll()

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    SqlObjectCatalogTestSuite = unittest.TestSuite()
    SqlObjectCatalogTestSuite.addTest(SqlObjectCatalogTestCase("testQueryEmpty"))
    SqlObjectCatalogTestSuite.addTest(SqlObjectCatalogTestCase("testInsert"))
    SqlObjectCatalogTestSuite.addTest(SqlObjectCatalogTestCase("testRemove"))
    SqlObjectCatalogTestSuite.addTest(SqlObjectCatalogTestCase("testInsertList"))
    SqlObjectCatalogTestSuite.addTest(SqlObjectCatalogTestCase("testGetAllObjectids"))

    #return
    return SqlObjectCatalogTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
    
