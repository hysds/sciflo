#-----------------------------------------------------------------------------
# Name:        localizeTest.py
# Purpose:     Unittest for localize.
#
# Author:      Gerald Manipon
#
# Created:     Mon Aug 06 09:19:36 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import os, socket, sys, shutil
from string import Template
from tempfile import mkdtemp, mktemp

from sciflo.data import localize

#this dir
thisDir = os.path.dirname(os.path.abspath(__file__))

#datasets xml file
datasetsXmlFile = os.path.join(thisDir, 'datasets.xml')

#hostname
hostname = socket.getfqdn()

#sciflo share path
sharePath = os.path.join(sys.prefix, 'share', 'sciflo')[1:]

#publish template
publishBase = 'file://%s/%s' % (hostname, sharePath)

#test urls
testUrl1 = 'file://%s/usr/local/test.file' % hostname
testUrl2 = 'file:///usr/local/test.file'
testUrl3 = 'http://www.test.this.out.com/test/test.file'
dapUrl1 = 'dap:http://www.test.this.out.com/test/dap/test.file'
dapUrl2 = 'http://www.test.this.out.com/test/dap/test.file'
dapUrl3 = 'http://www.test.this.out.com/testdap/test.file'
dapUrl4 = 'dap:http://www.test.this.out.com/test/nph-dods/test.file'
dapUrl5 = 'http://www.test.this.out.com/test/nph-dods/test.file'
dapUrl6 = 'http://www.test.this.out.com/testnph-dods/test.file'

#assert results
assertRes1 = '/usr/local/test.file'

#filter list
filterList = [testUrl1, testUrl2, testUrl3, dapUrl1, dapUrl2, dapUrl3, dapUrl4,
              dapUrl5, dapUrl6]
filterList2 = [testUrl3, dapUrl1, dapUrl2, dapUrl3, dapUrl4, dapUrl5, dapUrl6]
filterList3 = [testUrl1, testUrl2, testUrl3, dapUrl3, dapUrl6]

#dods url to hdf file
dodsUrl = 'http://sciflo.jpl.nasa.gov/sciflo/cgi-bin/nph-dods/genesis/unittestData/AIRS.2003.02.28.240.L2.RetStd.v3.0.8.0.G04136100421.hdf'

#http url to the same hdf file
fileUrl = 'http://sciflo.jpl.nasa.gov/genesis/unittestData/AIRS.2003.02.28.240.L2.RetStd.v3.0.8.0.G04136100421.hdf'

#temp directories
scifloRootDir = mkdtemp()
testDir = mkdtemp()

#geo info xml file
geoInfoXmlFile = os.path.join(thisDir, 'AIRSUrls.xml')

#fake AIRS data dir
fakeAirsDataDir = os.path.join(thisDir, 'fakeAirsData')

#assert best urls results
if hostname != 'sciflo.jpl.nasa.gov':
    bestUrlsDap = ['http://g0dup05u.ecs.nasa.gov/opendap-bin/nph-dods/OPENDAP_DP/long_term/AIRS/AIRX2RET.003/2003.01.02/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf',
             'http://g0dup05u.ecs.nasa.gov/opendap-bin/nph-dods/OPENDAP_DP/long_term/AIRS/AIRX2RET.003/2003.01.03/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
             'http://sciflo.jpl.nasa.gov/sciflo/cgi-bin/nph-dods/genesis/data/airs/v4/2003/01/03/airx2ret/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf']
    bestUrlsNonDap = ['ftp://g0dps01u.ecs.nasa.gov/long_term/AIRS/AIRX2RET.003/2003.01.02/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf',
                      'ftp://g0dps01u.ecs.nasa.gov/long_term/AIRS/AIRX2RET.003/2003.01.03/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
                      'ftp://g0dps01u.ecs.nasa.gov/long_term/AIRS/AIRX2RET.003/2003.01.03/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf']
    bestUrlsLocalDap = ['%s/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf' % fakeAirsDataDir,
                        'http://g0dup05u.ecs.nasa.gov/opendap-bin/nph-dods/OPENDAP_DP/long_term/AIRS/AIRX2RET.003/2003.01.03/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
                        '%s/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf' % fakeAirsDataDir]
    bestUrlsLocalNonDap = ['%s/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf' % fakeAirsDataDir,
                           'ftp://g0dps01u.ecs.nasa.gov/long_term/AIRS/AIRX2RET.003/2003.01.03/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
                           '%s/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf' % fakeAirsDataDir]
else:
    bestUrlsDap = ['http://g0dup05u.ecs.nasa.gov/opendap-bin/nph-dods/OPENDAP_DP/long_term/AIRS/AIRX2RET.003/2003.01.02/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf',
                   '/home/www/genesis/data/airs/v4/2003/01/03/airx2ret/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
                   'http://sciflo.jpl.nasa.gov/sciflo/cgi-bin/nph-dods/genesis/data/airs/v4/2003/01/03/airx2ret/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf']
    bestUrlsNonDap = ['ftp://g0dps01u.ecs.nasa.gov/long_term/AIRS/AIRX2RET.003/2003.01.02/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf',
                      '/home/www/genesis/data/airs/v4/2003/01/03/airx2ret/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
                      'ftp://g0dps01u.ecs.nasa.gov/long_term/AIRS/AIRX2RET.003/2003.01.03/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf']
    bestUrlsLocalDap = ['%s/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf' % fakeAirsDataDir,
                        '/home/www/genesis/data/airs/v4/2003/01/03/airx2ret/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
                        '%s/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf' % fakeAirsDataDir]
    bestUrlsLocalNonDap = ['%s/AIRS.2003.01.02.240.L2.RetStd.v4.0.9.0.G06049092452.hdf' % fakeAirsDataDir,
                           '/home/www/genesis/data/airs/v4/2003/01/03/airx2ret/AIRS.2003.01.03.001.L2.RetStd.v4.0.9.0.G06049092626.hdf',
                           '%s/AIRS.2003.01.03.002.L2.RetStd.v4.0.9.0.G06049092443.hdf' % fakeAirsDataDir]

class localizeTestCase(unittest.TestCase):
    """Test case for localize."""
    
    def testIsLocalUrl(self):
        """Test isLocalUrl() function."""
        
        assert localize.isLocalUrl(testUrl1) == assertRes1
        assert localize.isLocalUrl(testUrl2) == assertRes1
        assert localize.isLocalUrl(assertRes1) == assertRes1
        assert localize.isLocalUrl(testUrl3) is None
        
    def testIsDapUrl(self):
        """Test isDapUrl() function."""
        
        assert localize.isDapUrl(testUrl1) is None
        assert localize.isDapUrl(dapUrl1) == dapUrl2
        assert localize.isDapUrl(dapUrl2) == dapUrl2
        assert localize.isDapUrl(dapUrl3) is None
        assert localize.isDapUrl(dapUrl4) == dapUrl5
        assert localize.isDapUrl(dapUrl5) == dapUrl5
        assert localize.isDapUrl(dapUrl6) is None
        
    def testFilterLocalUrls(self):
        """Test filterLocalUrls() function."""
        

        assert localize.filterLocalUrls(filterList) == ([assertRes1, assertRes1],
            [testUrl3, dapUrl1, dapUrl2, dapUrl3, dapUrl4, dapUrl5, dapUrl6])
        assert localize.filterLocalUrls(filterList2) == ([], filterList2)
        
    def testLocalUrls(self):
        """Test localUrls() function."""
        
        assert localize.localUrls(filterList) == [assertRes1, assertRes1]
        assert localize.localUrls(filterList2) == []
        
    def testLocalUrl(self):
        """Test localUrl() function."""
        
        assert localize.localUrl(filterList) == assertRes1
        self.assertRaises(IndexError, localize.localUrl, filterList2)
        
    def testFilterDapUrls(self):
        """Test filterDapUrls() function."""
        

        assert localize.filterDapUrls(filterList) == ([dapUrl2, dapUrl2, dapUrl5,
            dapUrl5], [testUrl1, testUrl2, testUrl3, dapUrl3, dapUrl6])
        assert localize.filterDapUrls(filterList3) == ([], filterList3)
        
    def testDapUrls(self):
        """Test dapUrls() function."""
        
        assert localize.dapUrls(filterList) == [dapUrl2, dapUrl2, dapUrl5,
            dapUrl5]
        assert localize.dapUrls(filterList3) == []
        
    def testDapUrl(self):
        """Test dapUrl() function."""
        
        assert localize.dapUrl(filterList) == dapUrl2
        self.assertRaises(IndexError, localize.dapUrl, filterList3)
        
    def testLocalizeUrl(self):
        """Test localizeUrl() function."""
        
        #localize to sciflo root using dataset info
        (localPath, resp) = localize.localizeUrl(fileUrl, want=None,
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert os.path.exists(localPath)
        
        #localize same file except it should be found in cache
        (localPath2, resp2) = localize.localizeUrl(fileUrl, want=None,
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath2 == localPath
        assert resp2 is None
        
        #clean out
        shutil.rmtree(scifloRootDir)
        
        #try with want='path'
        localPath = localize.localizeUrl(fileUrl,
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert os.path.exists(localPath)
        
        #localize same file except it should be found in cache
        localPath2 = localize.localizeUrl(fileUrl,
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath2 == localPath
        
        #try localizing local files using different path notations (absolute path,
        #file://hostname/, and file:///)
        localPath3 = localize.localizeUrl(localPath,
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath3 == localPath
        localPath4 = localize.localizeUrl('file://%s%s' % (hostname, localPath),
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath4 == localPath
        localPath5 = localize.localizeUrl('file://%s' % localPath,
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath5 == localPath
        
        #try with dap url
        (localPath, resp) = localize.localizeUrl(dodsUrl, want=None,
                                   datasetInfo=datasetsXmlFile,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath == dodsUrl
        
        #clean out
        shutil.rmtree(scifloRootDir)

    def testLocalizeUrlUser(self):
        """Test localizeUrl() function using user's dataset directory."""
        
        #change directory to temp dir
        cwd = os.getcwd()
        os.chdir(testDir)
        
        #localize to sciflo root using dataset info
        (localPath, resp) = localize.localizeUrl(fileUrl, want=None,
                                   SCIFLO_ROOT=scifloRootDir)
        assert os.path.exists(localPath)
        
        #localize same file except it should be found in cache
        (localPath2, resp2) = localize.localizeUrl(fileUrl, want=None,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath2 == localPath
        assert resp2 is None
        
        #clean out
        os.unlink(localPath)
        
        #try with want='path'
        localPath = localize.localizeUrl(fileUrl,
                                   SCIFLO_ROOT=scifloRootDir)
        assert os.path.exists(localPath)
        
        #localize same file except it should be found in cache
        localPath2 = localize.localizeUrl(fileUrl,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath2 == localPath
        
        #try localizing local files using different path notations (absolute path,
        #file://hostname/, and file:///)
        localPath3 = localize.localizeUrl(localPath,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath3 == localPath
        absPath = os.path.abspath(localPath)
        localPath4 = localize.localizeUrl('file://%s%s' % (hostname, absPath),
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath4 == absPath
        localPath5 = localize.localizeUrl('file://%s' % localPath,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath5 == localPath
        localPath6 = localize.localizeUrl('file://%s' % absPath,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath6 == absPath
        
        #try with dap url
        (localPath, resp) = localize.localizeUrl(dodsUrl, want=None,
                                   SCIFLO_ROOT=scifloRootDir)
        assert localPath == dodsUrl
        
        #cleanup
        os.chdir(cwd)
        shutil.rmtree(testDir)
        
    def testBestUrlSet(self):
        """Test bestUrlSet() function."""
        
        #geo info xml
        geoInfoXml = open(geoInfoXmlFile).read()
        
        #assert best dap urls when local urls don't exist
        assert localize.bestUrlSet(geoInfoXml) == bestUrlsDap
        
        #assert best non-dap urls when local urls don't exist
        assert localize.bestUrlSet(geoInfoXml, dapOkay=False) == bestUrlsNonDap
        
        #overwrite geoInfoXml to include local fake AIRS files
        fakeGeoInfoXml = geoInfoXml.replace('/FAKE_AIRS_DATA_DIR', fakeAirsDataDir)
        
        #assert best dap urls when local urls exist
        assert localize.bestUrlSet(fakeGeoInfoXml) == bestUrlsLocalDap
        
        #assert best non-dap urls when local urls exist
        assert localize.bestUrlSet(fakeGeoInfoXml, dapOkay=False) == bestUrlsLocalNonDap

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    localizeTestSuite = unittest.TestSuite()
    localizeTestSuite.addTest(localizeTestCase("testIsLocalUrl"))
    localizeTestSuite.addTest(localizeTestCase("testIsDapUrl"))
    localizeTestSuite.addTest(localizeTestCase("testFilterLocalUrls"))
    localizeTestSuite.addTest(localizeTestCase("testLocalUrls"))
    localizeTestSuite.addTest(localizeTestCase("testLocalUrl"))
    localizeTestSuite.addTest(localizeTestCase("testFilterDapUrls"))
    localizeTestSuite.addTest(localizeTestCase("testDapUrls"))
    localizeTestSuite.addTest(localizeTestCase("testDapUrl"))
    localizeTestSuite.addTest(localizeTestCase("testLocalizeUrl"))
    #localizeTestSuite.addTest(localizeTestCase("testLocalizeUrlUser"))
    localizeTestSuite.addTest(localizeTestCase("testBestUrlSet"))

    #return
    return localizeTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)


