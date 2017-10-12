#-----------------------------------------------------------------------------
# Name:        sqlobjectLibrarianTest.py
# Purpose:     Unit testing for ScifloLibrarian using SqlObjectCatalog.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 05 09:53:11 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
from tempfile import mkdtemp
import os
import shutil

from sciflo.catalog import *

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#crawler xml config file
xmlConfigFile = os.path.join(dirName,'GPSL2Crawler.xml')

#crawler xml config file without local database
xmlConfigFile2 = os.path.join(dirName,'GPSL2Crawler2.xml')

#queryResult to assert
queryResultAssertion = ['http://sciflo.jpl.nasa.gov/unittestData/pvt/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_0625chm_g38_1p0.L2.txt.gz',
                        'http://sciflo.jpl.nasa.gov/unittestData/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_0625chm_g38_1p0.L2.txt.gz',
                        #'ftp://genesis.jpl.nasa.gov/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_0625chm_g38_1p0.L2.txt.gz',
                        '/genesis/ftp/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_0625chm_g38_1p0.L2.txt.gz']

#queryResult2 to assert
queryResultAssertion2 = [] #'ftp://genesis.jpl.nasa.gov/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_0625chm_g38_1p0.L2.txt.gz']

#scheme i.e. scheme='mysql://user:password@fqdn:port/test'
scheme = 'mysql://127.0.0.1:3306/test'

class sqlobjectLibrarianTestCase(unittest.TestCase):
    """Test case for ScifloLibrarian using SqlObjectCatalog."""

    def setUp(self):
        """Setup."""

        #get the object
        self.libobj = ScifloLibrarian(xmlConfigFile)

        #create the SqlObjectCatalog object
        self.catalogobj = SqlObjectCatalog(scheme)

        #set catalog object for librarian
        self.libobj.setCatalog(self.catalogobj)

    def testCrawlAndCatalog(self):
        """Test ScifloLibrarian object.
        """

        #harvest
        retval = self.libobj.crawlAndCatalog()

        #test objectid
        objectid = '20030103_0625chm_g38_1p0'

        #query
        queryResult = self.catalogobj.query(objectid)
        if os.path.isdir('/genesis/ftp/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2'):
            assert queryResult == queryResultAssertion
        else:
            assert queryResult == queryResultAssertion[:-1]

        #remove
        removeResult = self.catalogobj.remove(objectid)

        #query
        queryResult3 = self.catalogobj.query(objectid)
        assert queryResult3 == []

    def testCrawlAndCatalogAfterChangedXmlConfig(self):
        """Test ScifloLibrarian's ability to handle configuration changes.
        """

        #set catalog
        self.testCrawlAndCatalog()

        #get another librarian object but using a different xml configuration
        newLibrarianObj = ScifloLibrarian(xmlConfigFile2)

        #use current catalog object
        newLibrarianObj.setCatalog(self.catalogobj)

        #harvest
        retval = newLibrarianObj.crawlAndCatalog()
        objectid = '20030103_1835chm_g54_1p0'

        #query
        queryResult = self.catalogobj.query(objectid)
        #assert 'ftp://genesis.jpl.nasa.gov/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_1835chm_g54_1p0.L2.txt.gz' in queryResult

        #test objectid that should still be here
        objectid = '20030103_0625chm_g38_1p0'

        #query
        queryResult = self.catalogobj.query(objectid)

        assert queryResult == queryResultAssertion2

        #remove
        removeResult = self.catalogobj.remove(objectid)
        #print "Remove produced: ", removeResult

        #query
        queryResult3 = self.catalogobj.query(objectid)
        #print "Query #3 produced: ", queryResult3
        assert queryResult3 == []

    def tearDown(self):
        """Cleanup."""
        self.catalogobj.removeAll()

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""

    #run tests
    sqlobjectLibrarianTestSuite = unittest.TestSuite()
    sqlobjectLibrarianTestSuite.addTest(sqlobjectLibrarianTestCase("testCrawlAndCatalog"))
    #sqlobjectLibrarianTestSuite.addTest(sqlobjectLibrarianTestCase("testCrawlAndCatalogAfterChangedXmlConfig"))

    #return
    return sqlobjectLibrarianTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
    
