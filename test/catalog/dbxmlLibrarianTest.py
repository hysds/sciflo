#-----------------------------------------------------------------------------
# Name:        dbxmlLibrarianTest.py
# Purpose:     Unit testing for ScifloLibrarian using DbxmlCatalog.
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

#catalog schema
schemaUrl = os.path.join(dirName,'catalog.xsd')

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

class dbxmlLibrarianTestCase(unittest.TestCase):
    """Test case for ScifloLibrarian using DbxmlCatalog."""

    def setUp(self):
        """Setup."""

        #dbxml database directory
        self.dbDir = mkdtemp()

        #get the object
        self.libobj = ScifloLibrarian(xmlConfigFile)

        #get instrument
        instr = self.libobj.getInstrument()
        assert instr == 'GPS'

        #get level
        level = self.libobj.getLevel()
        assert level == 'L2'

        #create the DbxmlCatalog object
        self.container = "%s/%s_%s.dbxml" % (self.dbDir,instr,level)
        #self.catalogobj = DbxmlCatalog(self.container,schemaUrl=schemaUrl)
        self.catalogobj = DbxmlCatalog(self.container) #no schema validation

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

        #query
        queryResult3 = self.catalogobj.query(objectid)
        assert queryResult3==[]

    def tearDown(self):
        """Cleanup."""

        #remove container and dbDir
        removeContainers(self.container)
        shutil.rmtree(self.dbDir)

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""

    #run tests
    dbxmlLibrarianTestSuite = unittest.TestSuite()
    dbxmlLibrarianTestSuite.addTest(dbxmlLibrarianTestCase("testCrawlAndCatalog"))
    #dbxmlLibrarianTestSuite.addTest(dbxmlLibrarianTestCase("testCrawlAndCatalogAfterChangedXmlConfig"))

    #return
    return dbxmlLibrarianTestSuite

#main
if __name__=="__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)

