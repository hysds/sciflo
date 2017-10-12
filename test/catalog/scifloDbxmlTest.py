#-----------------------------------------------------------------------------
# Name:        scifloDbxmlTest.py
# Purpose:     Test ScifloDbxml.
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

import sciflo.catalog

#xml document template with remote schema
xmlTemplateRemoteSchema = '''<catalogEntry xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:noNamespaceSchemaLocation="http://sciflo.jpl.nasa.gov/genesis/xsd/catalog.xsd">
 <objectid>20030103_1134chm_g23_1p0_%i</objectid>
 <objectDataSet>
   <objectData>/genesis/ftp/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_1134chm_g23_1p0.L2.txt.gz</objectData>
 </objectDataSet>
</catalogEntry>'''

#xml document template with local schema
xmlTemplateLocalSchema = '''<catalogEntry xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:noNamespaceSchemaLocation="catalog.xsd">
 <objectid>20030103_1134chm_g23_1p0_%i</objectid>
 <objectDataSet>
   <objectData>/genesis/ftp/pub/genesis/glevels/champ/1p0/y2003/2003-01-03/L2/txt/20030103_1134chm_g23_1p0.L2.txt.gz</objectData>
 </objectDataSet>
</catalogEntry>'''

#which xml template to use
xmlTemplate = xmlTemplateLocalSchema
#xmlTemplate=xmlTemplateRemoteSchema

class scifloDbxmlTestCase(unittest.TestCase):
    """Test case for ScifloDbxml object."""

    def setUp(self):
        """Setup."""

        #dbxml file
        self.dbDir = mkdtemp()
        self.dbFile = os.path.join(self.dbDir,'test.dbxml')
        #print "dbFile is",dbFile

        #get sciflo dbxml object (schema validation is turned on by default)
        self.xmldbObj = sciflo.catalog.ScifloXmlDb(self.dbFile)

    def testInsert(self):


        #number of xml docs to insert
        numDocs = 135

        for i in xrange(numDocs):

            #generate doc name
            docname = "objectid_%i" % i
            #print docname

            #generate xml
            xml = xmlTemplate % i
            #print xml

            #initially try to insert
            try: retVal = self.xmldbObj.insertDocument(docname,xml)
            #if it fails to insert
            except Exception, e:

                #remove it
                self.xmldbObj.removeDocument(docname)

                #insert again
                retVal = self.xmldbObj.insertDocument(docname,xml)

    def testIndex(self):
        """Test adding index."""

        #add index
        self.xmldbObj.addIndex('objectid','node-element-equality-string')

        #get container
        container = self.xmldbObj._container

        #get index specs
        foundIndex = None
        for index in container.getIndexSpecification():
            #print "\t%s:%s %s" % (index.get_uri(), index.get_name(), index.get_index())
            if index.get_name() == 'objectid':
                idc = index.get_index()
                if 'node-element-equality-string' in idc: foundIndex = 1

        #if we didn't find index, raise error
        if foundIndex is None: raise RuntimeError, "Failed to find index that was added."

    def testIndexQuery(self):
        """Test querying against index."""

        assertionTest = ['<objectid>20030103_1134chm_g23_1p0_23</objectid>']
        #add index
        self.testIndex()

        #add data
        self.testInsert()

        #query index for all objectid
        results = self.xmldbObj.queryIndex('objectid','node-element-equality-string')
        #print results

        #query index for a single objectid
        results2 = self.xmldbObj.queryIndex('objectid','node-element-equality-string','20030103_1134chm_g23_1p0_23')

        #print results2
        assert results2 == assertionTest

    def testDocnameIndexQuery(self):
        """Test querying against docname index."""

        #document names test
        assertionTest = ['objectid_23',]
        #add index
        self.testIndex()

        #add data
        self.testInsert()

        #query index for all objectid names
        results = self.xmldbObj.queryDocumentIndex()
        #print results

        #query index for all objectid xml documents
        resultsDocs = self.xmldbObj.queryDocumentIndex(returnNodeNamesFlag=1)
        #print resultsDocs

        #query index for a single objectid
        results2 = self.xmldbObj.queryDocumentIndex('objectid_23',returnNodeNamesFlag=1)
        #print results2

        assert results2 == assertionTest

    def testRemove(self):
        """Test remove."""

        #add index
        self.testIndex()

        #add data
        self.testInsert()

        #test query
        self.testIndexQuery()

        #remove objectid
        result = self.xmldbObj.removeDocument('objectid_23')

        assert result == 1

        #query index for it
        #query index for a single objectid
        results2 = self.xmldbObj.queryIndex('objectid','node-element-equality-string','20030103_1134chm_g23_1p0_23')
        #print results2
        assert results2 == []

        #query document index for a single objectid
        results3 = self.xmldbObj.queryDocumentIndex('objectid_23')
        assert results3 == []

    def tearDown(self):
        """Cleanup."""

        #clean out containers
        sciflo.catalog.removeContainers(self.dbFile)

        #remove directory
        shutil.rmtree(self.dbDir)
        #print self.dbDir

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""

    #run tests
    scifloDbxmlTestSuite = unittest.TestSuite()
    scifloDbxmlTestSuite.addTest(scifloDbxmlTestCase("testInsert"))
    scifloDbxmlTestSuite.addTest(scifloDbxmlTestCase("testIndex"))
    scifloDbxmlTestSuite.addTest(scifloDbxmlTestCase("testIndexQuery"))
    scifloDbxmlTestSuite.addTest(scifloDbxmlTestCase("testRemove"))
    scifloDbxmlTestSuite.addTest(scifloDbxmlTestCase("testDocnameIndexQuery"))

    #return
    return scifloDbxmlTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)

