#-----------------------------------------------------------------------------
# Name:        recognizeTest.py
# Purpose:     Unittest for recognize.
#
# Author:      Gerald Manipon
#
# Created:     Mon Aug 06 09:19:36 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import os, socket, sys
from string import Template

from sciflo.utils import *
from sciflo.data import Recognizer

#this dir
thisDir = os.path.dirname(os.path.abspath(__file__))

#datasets xml file
datasetsXmlFile = os.path.join(thisDir, 'datasets.xml')

#test urls
testUrl1 = 'http://www.test.this.out.com/test/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf'
testUrl2 = 'http://www.test.this.out.com/test/AIRS.2003a.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf'
testUrl3 = 'http://www.test.this.out.com/test/AIRS.2003.01.02.L3.RetStd.v4.0.9.0.G06049092452.hdf'
testUrl4 = 'http://www.test.this.out.com/test/AIRS.2003a.01.02.L3.RetStd.v4.0.9.0.G06049092452.hdf'

#hostname
hostname = socket.getfqdn()

#sciflo share path
sharePath = os.path.join(sys.prefix, 'share', 'sciflo')[1:]

#publish template
publishBase = 'file://%s/%s' % (hostname, sharePath)

class recognizeTestCase(unittest.TestCase):
    """Test case for recognize."""

    def testRecognizerInstantiation(self):
        """Test Recognizer object instantiation."""

        #get recognize object
        r = Recognizer(datasetsXmlFile)
        
    def testRecognizerMatch(self):
        """Test Recognizer object match."""
        
        #get recognize object
        r = Recognizer(datasetsXmlFile)
        
        #assert match
        ipath = r.recognize(testUrl1)
        assert ipath == 'eos::data/AIRS/RetStd/L2'
        assert r.isRecognized(testUrl1) == True
        
        ipath = r.recognize(testUrl3)
        assert ipath == 'eos::data/AIRS/RetStd/L3'
        assert r.isRecognized(testUrl3) == True
        
    def testRecognizerNoMatch(self):
        """Test Recognizer object with no match."""
        
        #get recognize object
        r = Recognizer(datasetsXmlFile)
        
        #assert non match
        ipath = r.recognize(testUrl2)
        assert ipath is None
        assert r.isRecognized(testUrl2) == False
        
        ipath = r.recognize(testUrl4)
        assert ipath is None
        assert r.isRecognized(testUrl4) == False
        
    def testGetPublishPath(self):
        """Test the generation of publish path."""
        
        #get recognize object
        r = Recognizer(datasetsXmlFile)
        
        #assert it is recognized
        assert r.isRecognized(testUrl1) == True
        
        #assert publish path
        assert r.getPublishPath(testUrl1) == os.path.join(publishBase,
            'data/airs/L2/2003/01/02/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0G06049092452.hdf')
        assert r.getPublishPath(testUrl3) == os.path.join(publishBase,
            'data/airs/L3/2003/01/02/AIRS.2003.01.02.L3.RetStd.v4.0.9.0G06049092452.hdf')
        assert r.getPublishPath(testUrl2) is None
        assert r.getPublishPath(testUrl4) is None

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    recognizeTestSuite = unittest.TestSuite()
    recognizeTestSuite.addTest(recognizeTestCase("testRecognizerInstantiation"))
    recognizeTestSuite.addTest(recognizeTestCase("testRecognizerMatch"))
    recognizeTestSuite.addTest(recognizeTestCase("testRecognizerNoMatch"))
    recognizeTestSuite.addTest(recognizeTestCase("testGetPublishPath"))

    #return
    return recognizeTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)


