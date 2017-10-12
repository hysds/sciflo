#-----------------------------------------------------------------------------
# Name:        gpsL2TextOccultationTest.py
# Purpose:     Unit test for GPS L2 text occultation classes/functions.
#
# Author:      Gerald Manipon
#
# Created:     Tue Jun 20 10:15:03 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import os
from numarray import array

import sciflo

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#test gps data dir
gpsDataDir = os.path.join(dirName,'..','db','gpsData')

#gps data files
gpsDataFiles = [os.path.join(gpsDataDir,i) for i in os.listdir(gpsDataDir)]
gpsDataFiles.sort()

#gps objectids
objectids = ['20030101_1803sac_g54_2p4', '20040101_2322chm_g33_1p0',
             '20050101_1810sac_g34_1p0', '20060101_2213chm_g46_2p3']

class L2TextOccultationTestCase(unittest.TestCase):
    """Test case for GPS L2 text occultations.."""

    def testInstantiation(self):
        """Test instantiation (parsing) of files."""

        assertVersions = []
        for file in gpsDataFiles:
            if not os.path.isfile(file): continue
            o = sciflo.data.gps.occultation.L2TextOccultation(file)
            assertVersions.append(o.version)
        self.assertEquals(assertVersions, ['2p4', '1p0', '1p0', '2p3'])

    def testMetadataXml(self):
        """Test retrieving metadata xml."""

        assertXml = [ '''<metadata>
  <objectid sqltype="char(30) not null unique">20030101_1803sac_g54_2p4</objectid>
  <starttime sqltype="datetime">2003-01-01 18:03:40.500</starttime>
  <endtime sqltype="datetime">2003-01-01 18:05:10.480</endtime>
  <latitude sqltype="double">51.8662885</latitude>
  <longitude sqltype="double">-106.740067</longitude>
  <westboundingcoordinate sqltype="double">-107.05304</westboundingcoordinate>
  <northboundingcoordinate sqltype="double">52.281254</northboundingcoordinate>
  <eastboundingcoordinate sqltype="double">-106.427094</eastboundingcoordinate>
  <southboundingcoordinate sqltype="double">51.451323</southboundingcoordinate>
  <transmitter sqltype="char(5)">gps54</transmitter>
  <receiver sqltype="char(5)">sacc</receiver>
  <referencetransmitter sqltype="char(5)">gps33</referencetransmitter>
  <referencereceiver sqltype="char(4)">ban2</referencereceiver>
  <lowestaltitude sqltype="double">0.931568</lowestaltitude>
  <ltime sqltype="char(8)">10:52:00</ltime>
  <linkorientation sqltype="double">84.87</linkorientation>
  <angletovelocity sqltype="double">174.5</angletovelocity>
  <starttimeinsecondsfromj2000 sqltype="double unsigned">0.9471622050000000E+08</starttimeinsecondsfromj2000>
  <timeforradiusofcurvaturefromj2000 sqltype="double unsigned">0.9471626200000000E+08</timeforradiusofcurvaturefromj2000>
  <radiusofcurvature sqltype="double">0.6375765939839634E+04</radiusofcurvature>
  <centerofcurvature sqltype="char(100)">{ -.7735675402696739E+00, -.9674189242560356E+01, -.2141504091820346E+02 }</centerofcurvature>
  <ca_startphase sqltype="double">0.19197425E-01</ca_startphase>
  <ca_endphase sqltype="double">0.26767779E+01</ca_endphase>
  <ca_minimumphase sqltype="double">0.19197425E-01</ca_minimumphase>
  <ca_maximumphase sqltype="double">0.26767779E+01</ca_maximumphase>
  <ca_startsnr sqltype="double">0.65259073E+03</ca_startsnr>
  <ca_endsnr sqltype="double">0.19942704E+02</ca_endsnr>
  <ca_minimumsnr sqltype="double">0.95146488E+00</ca_minimumsnr>
  <ca_maximumsnr sqltype="double">0.81902097E+03</ca_maximumsnr>
  <p2_startphase sqltype="double">0.37101484E-01</p2_startphase>
  <p2_endphase sqltype="double">0.40734092E+01</p2_endphase>
  <p2_minimumphase sqltype="double">0.37101484E-01</p2_minimumphase>
  <p2_maximumphase sqltype="double">0.40734092E+01</p2_maximumphase>
  <p2_startsnr sqltype="double">0.15900000E+03</p2_startsnr>
  <p2_endsnr sqltype="double">0.80000000E+01</p2_endsnr>
  <p2_minimumsnr sqltype="double">0.60000000E+01</p2_minimumsnr>
  <p2_maximumsnr sqltype="double">0.17200000E+03</p2_maximumsnr>
</metadata>\n''',
'''<metadata>
  <objectid sqltype="char(30) not null unique">20040101_2322chm_g33_1p0</objectid>
  <starttime sqltype="datetime">2004-01-01 23:22:41.500</starttime>
  <endtime sqltype="datetime">2004-01-01 23:24:04.480</endtime>
  <latitude sqltype="double">-60.6566685</latitude>
  <longitude sqltype="double">-60.034612</longitude>
  <westboundingcoordinate sqltype="double">-60.275679</westboundingcoordinate>
  <northboundingcoordinate sqltype="double">-60.302759</northboundingcoordinate>
  <eastboundingcoordinate sqltype="double">-59.793545</eastboundingcoordinate>
  <southboundingcoordinate sqltype="double">-61.010578</southboundingcoordinate>
  <transmitter sqltype="char(5)">gps33</transmitter>
  <receiver sqltype="char(5)">champ</receiver>
  <referencetransmitter sqltype="char(5)">gps31</referencetransmitter>
  <referencereceiver sqltype="char(4)">hrao</referencereceiver>
  <lowestaltitude sqltype="double">0.080331</lowestaltitude>
  <ltime sqltype="char(8)">19:27:00</ltime>
  <linkorientation sqltype="double">-74.54</linkorientation>
  <angletovelocity sqltype="double">167.0</angletovelocity>
  <starttimeinsecondsfromj2000 sqltype="double unsigned">0.1262713615000000E+09</starttimeinsecondsfromj2000>
  <timeforradiusofcurvaturefromj2000 sqltype="double unsigned">0.1262713980000000E+09</timeforradiusofcurvaturefromj2000>
  <radiusofcurvature sqltype="double">0.6385324676832887E+04</radiusofcurvature>
  <centerofcurvature sqltype="char(100)">{ 0.3870147768688510E+01, 0.2360543959027912E+01, 0.2942804828280143E+02 }</centerofcurvature>
  <ca_startphase sqltype="double">0.14450279E-01</ca_startphase>
  <ca_endphase sqltype="double">0.23001922E+01</ca_endphase>
  <ca_minimumphase sqltype="double">0.14133977E-01</ca_minimumphase>
  <ca_maximumphase sqltype="double">0.23001922E+01</ca_maximumphase>
  <ca_startsnr sqltype="double">0.75542506E+03</ca_startsnr>
  <ca_endsnr sqltype="double">0.14842852E+02</ca_endsnr>
  <ca_minimumsnr sqltype="double">0.76117190E+00</ca_minimumsnr>
  <ca_maximumsnr sqltype="double">0.15672149E+04</ca_maximumsnr>
  <p2_startphase sqltype="double">0.26750684E-01</p2_startphase>
  <p2_endphase sqltype="double">0.37556916E+01</p2_endphase>
  <p2_minimumphase sqltype="double">0.26494426E-01</p2_minimumphase>
  <p2_maximumphase sqltype="double">0.37556916E+01</p2_maximumphase>
  <p2_startsnr sqltype="double">0.25617240E+03</p2_startsnr>
  <p2_endsnr sqltype="double">0.00000000E+00</p2_endsnr>
  <p2_minimumsnr sqltype="double">0.00000000E+00</p2_minimumsnr>
  <p2_maximumsnr sqltype="double">0.12331365E+04</p2_maximumsnr>
</metadata>\n''',
'''<metadata>
  <objectid sqltype="char(30) not null unique">20050101_1810sac_g34_1p0</objectid>
  <starttime sqltype="datetime">2005-01-01 18:10:58.500</starttime>
  <endtime sqltype="datetime">2005-01-01 18:12:24.480</endtime>
  <latitude sqltype="double">-81.6196575</latitude>
  <longitude sqltype="double">69.43926</longitude>
  <westboundingcoordinate sqltype="double">68.155196</westboundingcoordinate>
  <northboundingcoordinate sqltype="double">-81.422965</northboundingcoordinate>
  <eastboundingcoordinate sqltype="double">70.723324</eastboundingcoordinate>
  <southboundingcoordinate sqltype="double">-81.816350</southboundingcoordinate>
  <transmitter sqltype="char(5)">gps34</transmitter>
  <receiver sqltype="char(5)">sacc</receiver>
  <referencetransmitter sqltype="char(5)">gps24</referencetransmitter>
  <referencereceiver sqltype="char(4)">sant</referencereceiver>
  <lowestaltitude sqltype="double">4.031123</lowestaltitude>
  <ltime sqltype="char(8)">22:17:00</ltime>
  <linkorientation sqltype="double">-101.47</linkorientation>
  <angletovelocity sqltype="double">163.9</angletovelocity>
  <starttimeinsecondsfromj2000 sqltype="double unsigned">0.1578750585000000E+09</starttimeinsecondsfromj2000>
  <timeforradiusofcurvaturefromj2000 sqltype="double unsigned">0.1578750960000000E+09</timeforradiusofcurvaturefromj2000>
  <radiusofcurvature sqltype="double">0.6398525206146131E+04</radiusofcurvature>
  <centerofcurvature sqltype="char(100)">{ 0.9903949981289142E-02, 0.1049655989428861E+00, 0.4178034235166390E+02 }</centerofcurvature>
  <ca_startphase sqltype="double">0.16190761E-01</ca_startphase>
  <ca_endphase sqltype="double">0.36180281E+01</ca_endphase>
  <ca_minimumphase sqltype="double">0.16190761E-01</ca_minimumphase>
  <ca_maximumphase sqltype="double">0.36180281E+01</ca_maximumphase>
  <ca_startsnr sqltype="double">0.66050692E+03</ca_startsnr>
  <ca_endsnr sqltype="double">0.11569813E+02</ca_endsnr>
  <ca_minimumsnr sqltype="double">0.11036993E+01</ca_minimumsnr>
  <ca_maximumsnr sqltype="double">0.79968720E+03</ca_maximumsnr>
  <p2_startphase sqltype="double">0.26983817E-01</p2_startphase>
  <p2_endphase sqltype="double">0.72704165E+01</p2_endphase>
  <p2_minimumphase sqltype="double">0.26983817E-01</p2_minimumphase>
  <p2_maximumphase sqltype="double">0.72704165E+01</p2_maximumphase>
  <p2_startsnr sqltype="double">0.16300000E+03</p2_startsnr>
  <p2_endsnr sqltype="double">0.50000000E+01</p2_endsnr>
  <p2_minimumsnr sqltype="double">0.00000000E+00</p2_minimumsnr>
  <p2_maximumsnr sqltype="double">0.17800000E+03</p2_maximumsnr>
</metadata>\n''',
'''<metadata>
  <objectid sqltype="char(30) not null unique">20060101_2213chm_g46_2p3</objectid>
  <starttime sqltype="datetime">2006-01-01 22:13:55.500</starttime>
  <endtime sqltype="datetime">2006-01-01 22:15:28.480</endtime>
  <latitude sqltype="double">41.819826</latitude>
  <longitude sqltype="double">32.8032745</longitude>
  <westboundingcoordinate sqltype="double">32.460555</westboundingcoordinate>
  <northboundingcoordinate sqltype="double">42.097272</northboundingcoordinate>
  <eastboundingcoordinate sqltype="double">33.145994</eastboundingcoordinate>
  <southboundingcoordinate sqltype="double">41.542380</southboundingcoordinate>
  <transmitter sqltype="char(5)">gps46</transmitter>
  <receiver sqltype="char(5)">champ</receiver>
  <referencetransmitter sqltype="char(5)">gps27</referencetransmitter>
  <referencereceiver sqltype="char(4)">sutm</referencereceiver>
  <lowestaltitude sqltype="double">1.237572</lowestaltitude>
  <ltime sqltype="char(8)">00:29:00</ltime>
  <linkorientation sqltype="double">-85.59</linkorientation>
  <angletovelocity sqltype="double">166.3</angletovelocity>
  <starttimeinsecondsfromj2000 sqltype="double unsigned">0.1894256355000000E+09</starttimeinsecondsfromj2000>
  <timeforradiusofcurvaturefromj2000 sqltype="double unsigned">0.1894256890000000E+09</timeforradiusofcurvaturefromj2000>
  <radiusofcurvature sqltype="double">0.6363860038716928E+04</radiusofcurvature>
  <centerofcurvature sqltype="char(100)">{ -.5401277454599675E+01, 0.1691330017851658E+02, -.1267997422086818E+02 }</centerofcurvature>
  <ca_startphase sqltype="double">-0.33780885E-02</ca_startphase>
  <ca_endphase sqltype="double">0.20042864E+01</ca_endphase>
  <ca_minimumphase sqltype="double">-0.33787573E-02</ca_minimumphase>
  <ca_maximumphase sqltype="double">0.20042864E+01</ca_maximumphase>
  <ca_startsnr sqltype="double">0.67972651E+03</ca_startsnr>
  <ca_endsnr sqltype="double">0.10275821E+02</ca_endsnr>
  <ca_minimumsnr sqltype="double">0.72311331E+00</ca_minimumsnr>
  <ca_maximumsnr sqltype="double">0.84421576E+03</ca_maximumsnr>
  <p2_startphase sqltype="double">-0.29206217E-02</p2_startphase>
  <p2_endphase sqltype="double">0.24862979E+01</p2_endphase>
  <p2_minimumphase sqltype="double">-0.29523583E-02</p2_minimumphase>
  <p2_maximumphase sqltype="double">0.24862979E+01</p2_maximumphase>
  <p2_startsnr sqltype="double">0.99218758E+02</p2_startsnr>
  <p2_endsnr sqltype="double">0.00000000E+00</p2_endsnr>
  <p2_minimumsnr sqltype="double">0.00000000E+00</p2_minimumsnr>
  <p2_maximumsnr sqltype="double">0.32490623E+03</p2_maximumsnr>
</metadata>\n''']
        count = 0
        for file in gpsDataFiles:
            if not os.path.isfile(file): continue
            o = sciflo.data.gps.occultation.L2TextOccultation(file)
            metadataXml = o.getMetadataXml()
            self.assertEquals(metadataXml, assertXml[count])
            count += 1

    def testParseData(self):
        """Test parsing of data."""

        for file in gpsDataFiles:
            if not os.path.isfile(file): continue
            o = sciflo.data.gps.occultation.L2TextOccultation(file)
            self.assertEqual(True, o.parseData())
            recArray = o.getRecArrayById()
            dataList = o.getDataListById()
            for i in range(len(dataList[0])):
                self.assertEqual(recArray[0].field(i), dataList[0][i])

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    L2TextOccultationTestSuite = unittest.TestSuite()
    L2TextOccultationTestSuite.addTest(L2TextOccultationTestCase("testInstantiation"))
    L2TextOccultationTestSuite.addTest(L2TextOccultationTestCase("testMetadataXml"))
    L2TextOccultationTestSuite.addTest(L2TextOccultationTestCase("testParseData"))

    #return
    return L2TextOccultationTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
