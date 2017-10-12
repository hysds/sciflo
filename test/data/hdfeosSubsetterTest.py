#-----------------------------------------------------------------------------
# Name:        hdfeosSubsetterTest.py
# Purpose:     Unit testing for hdfeosSubsetter.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 05 09:53:11 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import md5
from tempfile import mkdtemp
import os
import shutil

from sciflo.data import *
import hdfeos

#dods url to hdf file
dodsUrl='http://sciflo.jpl.nasa.gov/sciflo/cgi-bin/nph-dods/genesis/unittestData/AIRS.2003.02.28.240.L2.RetStd.v3.0.8.0.G04136100421.hdf'

#http url to the same hdf file
fileUrl='http://sciflo.jpl.nasa.gov/genesis/unittestData/AIRS.2003.02.28.240.L2.RetStd.v3.0.8.0.G04136100421.hdf'

#single variable
varListSingleItem=['TAirStd']

#single variable list
singleVar='TAirStd'

#list of variables
varList=['TAirStd','H2OMMRStd']

#swath
swath='L2_Standard_atmospheric&surface_product'

#temp directory
tempDir=mkdtemp()

class hdfeosTestCase(unittest.TestCase):
    """Test case for hdfeos."""

    def testStringArgLocal(self):
        """Test getting a single variable using a string as the arg to
        the constructor.
        """

        #output file
        outFile=os.path.join(tempDir,'singleStrLocal.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(fileUrl,swath,singleVar,
                                        outFile)

        #subset it
        obj.subset()

    def testSingleListArgLocal(self):
        """Test the same except using a list with the same single
        variable."""

        #output file
        outFile=os.path.join(tempDir,'singleListLocal.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(fileUrl,swath,varListSingleItem,
                                        outFile)

        #subset it
        obj.subset()

    def testStringArgDods(self):
        """Test getting a single variable using a string as the arg to
        the constructor over dods.
        """

        #output file
        outFile=os.path.join(tempDir,'singleStrDods.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(dodsUrl,swath,singleVar,
                                        outFile)

        #subset it
        obj.subset()

    def testSingleListArgDods(self):
        """Test the same except using a list with the same single
        variable over dods.
        """

        #output file
        outFile=os.path.join(tempDir,'singleListDods.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(dodsUrl,swath,varListSingleItem,
                                        outFile)

        #subset it
        obj.subset()

    def testListArgLocal(self):
        """Test getting 2 vars in a list locally."""

        #output file
        outFile=os.path.join(tempDir,'listLocal.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(fileUrl,swath,varList,outFile)

        #subset it
        obj.subset()

    def testListArgDods(self):
        """Test getting 2 vars in a list over DODS."""

        #output file
        outFile=os.path.join(tempDir,'listDods.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(dodsUrl,swath,varList,outFile)

        #subset it
        obj.subset()

    def testListArgLocalExclude(self):
        """Test excluding 2 vars in a list locally."""

        #output file
        outFile=os.path.join(tempDir,'listLocalExclude.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(fileUrl,swath,varList,outFile,excludeFlag=1)

        #subset it
        obj.subset()

    def testListArgDodsExclude(self):
        """Test getting 2 vars in a list over DODS."""

        #output file
        outFile=os.path.join(tempDir,'listDodsExclude.hdf')

        #create object
        obj=HdfeosFileVariableSubsetter(dodsUrl,swath,varList,outFile,excludeFlag=1)

        #subset it
        obj.subset()

    def testArrayEquality(self):
        """Test that the array variables in these hdf files match."""

        #get TAirStd arrays
        air1=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'singleStrLocal.hdf'),swath,singleVar)
        air2=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'singleListLocal.hdf'),swath,singleVar)
        air3=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'singleStrDods.hdf'),swath,singleVar)
        air4=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'singleListDods.hdf'),swath,singleVar)
        air5=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'listLocal.hdf'),swath,singleVar)
        air6=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'listDods.hdf'),swath,singleVar)

        #get TSurfStd
        surf1=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'listLocalExclude.hdf'),swath,'TSurfStd')
        surf2=hdfeos.hdfeos.swath_field_read(os.path.join(tempDir,'listDodsExclude.hdf'),swath,'TSurfStd')

        #assert all TAirStd arrays are the same
        assert air1 == air2 == air3 == air4 == air5 == air6

        #assert all TSurtStd arrays are the same
        assert surf1 == surf2

        #remove tmpDir
        shutil.rmtree(tempDir)

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    hdfeosTestSuite = unittest.TestSuite()
    hdfeosTestSuite.addTest(hdfeosTestCase("testStringArgLocal"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testSingleListArgLocal"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testStringArgDods"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testSingleListArgDods"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testListArgLocal"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testListArgDods"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testListArgLocalExclude"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testListArgDodsExclude"))
    hdfeosTestSuite.addTest(hdfeosTestCase("testArrayEquality"))

    #return
    return hdfeosTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite=getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
