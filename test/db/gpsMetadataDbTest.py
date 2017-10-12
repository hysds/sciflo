#-----------------------------------------------------------------------------
# Name:        gpsMetadataDbTest.py
# Purpose:     Unit test for inserting GPS metadata into db.
#
# Author:      Gerald Manipon
#
# Created:     Fri Jun 16 08:42:15 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import os
from sqlobject import *

import sciflo

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#test gps data dir
gpsDataDir = os.path.join(dirName,'gpsData')

#gps data files
gpsDataFiles = [os.path.join(gpsDataDir,i) for i in os.listdir(gpsDataDir)]

#gps objectids
objectids = ['20030101_1803sac_g54_2p4', '20050101_1810sac_g34_1p0',
'20040101_2322chm_g33_1p0', '20060101_2213chm_g46_2p3']

#database location
location = 'mysql://127.0.0.1:3306/test'

#xml schema
xmlSchemaFile = os.path.join(dirName, 'gpsDbSchema.xml')

class GpsMetadataDbTestCase(unittest.TestCase):
    """Test case for GPS metadata database."""

    def setUp(self):
        """Setup."""

        #get sciflo database table
        self.metadataDb = sciflo.db.ScifloDbTable(location, xmlSchemaFile)

        #loop over data files and insert metadata
        for file in gpsDataFiles:
            if not os.path.isfile(file): continue
            occObj = sciflo.data.gps.occultation.L2TextOccultation(file)
            metadataXml = occObj.getMetadataXml()
            retVal = self.metadataDb.update(metadataXml)
            self.assertEqual(True, retVal)

    def testInsert(self):
        """Test insert into database."""

        #query
        res = self.metadataDb.query('20040101_2322chm_g33_1p0')
        self.assertEqual(res.northboundingcoordinate, -60.302759)

    def testUpdate(self):
        """Test update of database entry."""

        #query
        res = self.metadataDb.query('20040101_2322chm_g33_1p0')
        self.assertEqual(res.northboundingcoordinate, -60.302759)

        #new xml
        updateXml='''<?xml version="1.0" ?>
<Metadata><objectid>20040101_2322chm_g33_1p0</objectid>
<northboundingcoordinate>123.4321</northboundingcoordinate></Metadata>'''

        #update and query again
        self.metadataDb.update(updateXml)
        self.assertEqual(res.northboundingcoordinate, 123.4321)

    def testRemove(self):
        """Test removal of entry in database."""

        #query
        res = self.metadataDb.query('20040101_2322chm_g33_1p0')
        self.assertEqual(res.northboundingcoordinate, -60.302759)

        #remove
        res = self.metadataDb.remove('20040101_2322chm_g33_1p0')
        self.assertEqual(res, True)

        #remove it a second time; should get false since not there anymore
        res = self.metadataDb.remove('20040101_2322chm_g33_1p0')
        self.assertEqual(res, False)

    def tearDown(self):
        """Cleanup."""

        self.metadataDb.removeAll()
        self.metadataDb.dropTable()

class GpsMetadataDbViaFunctionsTestCase(unittest.TestCase):
    """Test case for GPS metadata database using functions."""

    def setUp(self):
        """Setup."""

        #loop over data files and get occ metadata xml
        self.metadataXmlDict = {}
        for file in gpsDataFiles:
            if not os.path.isfile(file): continue
            occObj = sciflo.data.gps.occultation.L2TextOccultation(file)
            self.metadataXmlDict[occObj.objectid] = occObj.getMetadataXml()
        self.connection = connectionForURI(location)
        sqlhub.processConnection = self.connection
        self.connection.debug = False

    def testGetInsertSql(self):
        """Test generating insert SQL."""
        for xml in self.metadataXmlDict.values():
            sql = sciflo.db.getInsertSql('l2header2', xml, 'metadata')

    def testGetUpdateSql(self):
        """Test generating update SQL."""
        for xml in self.metadataXmlDict.values():
            sql = sciflo.db.getUpdateSql('l2header2', xml, 'metadata', 'objectid')

    def testGetDeleteSql(self):
        """Test generating delete SQL."""
        for xml in self.metadataXmlDict.values():
            sql = sciflo.db.getDeleteSql('l2header2', xml, 'metadata', 'objectid')

    def testGetCreateSql(self):
        """Test generating create SQL."""
        for xml in self.metadataXmlDict.values():
            self.connection.query(sciflo.db.getCreateSql('l2header2', xml,
                'metadata', autoKey=True))
            self.connection.query("drop table l2header2")

    def testInsertXml(self):
        """Test inserting xml."""
        for xml in self.metadataXmlDict.values():
            ret = sciflo.db.insertXml(location,'l2header2', xml, 'metadata',
                                      autoKey=True, createIfNeeded=True)
        sciflo.db.dropTable(location,'l2header2')

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    GpsMetadataDbTestSuite = unittest.TestSuite()
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbTestCase("testInsert"))
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbTestCase("testUpdate"))
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbTestCase("testRemove"))
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbViaFunctionsTestCase("testGetInsertSql"))
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbViaFunctionsTestCase("testGetUpdateSql"))
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbViaFunctionsTestCase("testGetDeleteSql"))
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbViaFunctionsTestCase("testGetCreateSql"))
    GpsMetadataDbTestSuite.addTest(GpsMetadataDbViaFunctionsTestCase("testInsertXml"))

    #return
    return GpsMetadataDbTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
