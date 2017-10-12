#-----------------------------------------------------------------------------
# Name:        geolocationTest.py
# Purpose:     Unittest for geolocation module.
#
# Author:      Gerald Manipon
#
# Created:     Mon May 16 13:22:44 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import pickle
from tempfile import mkdtemp
import os

from sciflo.data import *

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#gps geolocation dict pickle file
#gpsDictFile = os.path.join(dirName,'gpsGeolocDict_large')
gpsDictFile = os.path.join(dirName,'gpsGeolocDict')

#gpsDict
gpsDict = pickle.load(open(gpsDictFile,'r'))

#airs geolocation dict pickle file
#airsDictFile = os.path.join(dirName,'airsGeolocDict_large')
airsDictFile = os.path.join(dirName,'airsGeolocDict')

#airs dict
airsDict = pickle.load(open(airsDictFile,'r'))

class GeolocationTestCase(unittest.TestCase):
    """Test case for hdfeos."""

    def testPointGeolocationViaList(self):
        """Test PointGeolocation class instantiation via a list arg."""

        #list arg
        listarg = [345345345345.0,65456745745745645.54545,34.2,-42.3]

        #get object
        obj = PointGeolocation(listarg)

        #try to slice
        #print obj[2:3]

        #print out
        #print obj

        #try with less than four in list
        shortList = ["2003-01-01 00:00:00",34.2,-42.3]

        #try
        try:
            #get object
            obj2 = PointGeolocation(shortList)

        #we should get this
        except PointGeolocationError, e:

            pass

        #try with more than four in list
        longList = [345345345345.0,65456745745745645.54545,34.2,-42.3,"2003-01-01 00:00:00","2003-01-01 23:59:59",34.2,-42.3]

        #try
        try:
            #get object
            obj3 = PointGeolocation(longList)

        #we should get this
        except PointGeolocationError, e:

            pass

    def testPointGeolocationSet(self):
        """Test the PointGeolocationSet class."""

        #create object
        obj = PointGeolocationSet(gpsDict)

        #get objectid list
        objectids = obj.getObjectidList()
        #print objectids

        #get starttime array
        starttimeArray = obj.getStarttimeArray()
        #print "starttimeArray:",starttimeArray

        #get endtime array
        endtimeArray = obj.getEndtimeArray()
        #print "endtimeArray:",endtimeArray
        #f = open('/tmp/array.txt','w')
        #pickle.dump(endtimeArray,f)
        #f.close()


        #get latitude array
        latArray = obj.getLatitudeArray()
        #print "latArray:",latArray

        #get longitude array
        lonArray = obj.getLongitudeArray()
        #print "lonArray:",lonArray

        #remove the following objectid and its data:
        #u'20030103_1252sac_g43': [u'2003-01-03 12:52:59', u'2003-01-03 12:54:47', 54.840390999999997, -45.533856]
        removeId = '20030104_0112chm_g35_1p0'
        obj.removeGeolocation(removeId)

        #get new lon array
        lonArray2 = obj.getLongitudeArray()

        #add removed data back in:
        addId = removeId
        addData = [u'2003-01-03 12:52:59', u'2003-01-03 12:54:47', 54.840390999999997, -45.533856]
        obj.addGeolocation(addId,addData)

        #get lon array again
        lonArray3 = obj.getLongitudeArray()

        #assert that lonArrray 1 and 3 are the same
        assert lonArray == lonArray3

    def testSwathGeolocationViaList(self):
        """Test SwathGeolocation class instantiation via a list arg."""

        #list arg
        listarg = [345345345345.0,65456745745745645.54545,-134.2,42.3,-45.2,54.3]

        #get object
        obj = SwathGeolocation(listarg)

        #try to slice
        #print obj[2:3]

        #print out
        #print obj

        #try with less than four in list
        shortList = ["2003-01-01 00:00:00",34.2,-42.3]

        #try
        try:
            #get object
            obj2 = SwathGeolocation(shortList)

        #we should get this
        except SwathGeolocationError, e:

            pass

        #try with more than six in list
        longList = [345345345345.0,65456745745745645.54545,34.2,-42.3,"2003-01-01 00:00:00","2003-01-01 23:59:59",34.2,-42.3]

        #try
        try:
            #get object
            obj3 = SwathGeolocation(longList)

        #we should get this
        except SwathGeolocationError, e:

            pass

    def testSwathGeolocationSet(self):
        """Test the SwathGeolocationSet class."""

        #create object
        obj = SwathGeolocationSet(airsDict)
        #print "airsdict is",airsDict
        #raise SystemExit

        #get objectid list
        objectids = obj.getObjectidList()
        #print objectids

        #get starttime array
        starttimeArray = obj.getStarttimeArray()
        #print "starttimeArray:",starttimeArray

        #get endtime array
        endtimeArray = obj.getEndtimeArray()
        #print "endtimeArray:",endtimeArray

        #get west bound array
        westArray = obj.getWestArray()
        #print "westArray:",westArray

        #get east bound array
        eastArray = obj.getEastArray()
        #print "eastArray:",eastArray

        #get south bound array
        southArray = obj.getSouthArray()
        #print "southArray:",southArray

        #get north bound array
        northArray = obj.getNorthArray()
        #print "northArray:",northArray

        #remove the following objectid and its data:
        removeId = 'AIRS.2003.01.03.103'
        obj.removeGeolocation(removeId)

        #get new south array
        southArray2 = obj.getSouthArray()

        #add removed data back in:
        addId = removeId
        addData = [1041620726.0, 1041621085.0, 17.931498999999999, 41.602961999999998, 19.877018, 43.482638999999999]
        obj.addGeolocation(addId,addData)

        #get south array again
        southArray3 = obj.getSouthArray()

        #assert that lonArrray 1 and 3 are the same
        assert southArray == southArray3

    def testPointToSwathCoarseMatch(self):
        """Test pointToSwathCoarseMatch() function."""

        timeTol = 7200
        locTol = 200

        #create PointGeolocationSet object
        pointObj = PointGeolocationSet(gpsDict)

        #create SwathGeolocationSet object
        swathObj = SwathGeolocationSet(airsDict)

        #run matchup
        (matchupDict,matchupList)=pointToSwathCoarseMatchup(pointObj,swathObj,timeTol,locTol)
        #print matchup

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    GeolocationTestSuite = unittest.TestSuite()
    GeolocationTestSuite.addTest(GeolocationTestCase("testPointGeolocationViaList"))
    GeolocationTestSuite.addTest(GeolocationTestCase("testPointGeolocationSet"))
    GeolocationTestSuite.addTest(GeolocationTestCase("testSwathGeolocationViaList"))
    GeolocationTestSuite.addTest(GeolocationTestCase("testSwathGeolocationSet"))
    GeolocationTestSuite.addTest(GeolocationTestCase("testPointToSwathCoarseMatch"))

    #return
    return GeolocationTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
