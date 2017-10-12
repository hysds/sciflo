import os, unittest, shutil, SimpleHTTPServer, SocketServer, sys, socket, time
import signal
from tempfile import mkdtemp
from twisted.application import internet, service
from twisted.internet import reactor

from sciflo.grid import (GridServiceConfig, getScheduleConfigFromConfiguration,
ScheduleStoreHandler, getStoreConfigFromConfiguration, WorkUnitStoreHandler,
getRootWorkDirFromConfiguration, loadJson)
from sciflo.webservices import SoapServer
from sciflo.utils.xmlUtils import transformXml, GRID_ENDPOINT_CONFIG_XSL
from sciflo.grid.soapFuncs import submitSciflo_client, cancelSciflo_client
from sciflo.event.pdict import PersistentDict, NamedDicts, PersistentDictFactory
from sciflo.utils import ScifloConfigParser
from sciflo.grid.status import *

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#get config file here
configFile = os.path.join(dirName,'config.xml')

#sciflo template xml file
xmlFile = os.path.join(dirName,'test_all_template.sf.xml')

#sciflo dir
scifloDir = os.path.normpath(sys.prefix)

#ssl cert and key files
serverCertFile = os.path.join(scifloDir,'ssl','hostcert.pem')
serverKeyFile = os.path.join(scifloDir,'ssl','hostkey.pem')

#TestService xml config file
testServiceXmlFile = os.path.join(dirName,'TestService.xml')

#test soap port
testServicePort = 8007

#test soap module
testSoapModuleFile = os.path.join(dirName,'testModule.py')

#grid wsdl and submit name
wsdl = 'http://localhost:8008/wsdl?http://sciflo.jpl.nasa.gov/2006v1/sf/GridService'
submitFuncName = 'submitSciflo'
submitNoCacheFuncName = 'submitSciflo_nocache'
cancelFuncName = 'cancelSciflo'

#cache name
cacheName = "WorkUnitCache"

class scifloServerTestCase(unittest.TestCase):
    """Test case for ScifloManager using the SciFlo server to provide
    soap methods and file serving (staging)."""

    def __init__(self, *args, **kargs):
        "Constructor."

        #get sciflo doc string
        f = open(xmlFile)
        sflStr = f.read(); f.close()
        self.xmlString = sflStr.replace('XXTESTDIRXX', dirName)

        #soap dir
        self.soapDir = mkdtemp()

        #test dir
        self.testDir = os.path.join('/tmp', 'testdir')
        if not os.path.isdir(self.testDir): os.makedirs(self.testDir)

        #call base class constructor
        unittest.TestCase.__init__(self,*args,**kargs)

    def testScifloServer(self):
        """Test ScifloManager class and the soap server's ability to handle
        SOAP requests and HTTP requests."""

        #make sure we are in the right directory
        os.chdir(os.path.join(dirName))

        #get grid service config
        gscObj = GridServiceConfig(configFile)
        gridSoapPort = gscObj.getPort()
        gridProtocol = gscObj.getProtocol()

        #set schedule store config and clean out
        workUnitScheduleConfig = getScheduleConfigFromConfiguration(configFile)
        (dbHome, dbName)=workUnitScheduleConfig.getStoreArgs()
        if os.path.isdir(dbHome):
            shutil.rmtree(dbHome)

        #get bsddb home dir and db file name and clean out
        scheduleHandler = ScheduleStoreHandler(workUnitScheduleConfig)
        storeConfig = getStoreConfigFromConfiguration(configFile)
        (wuDbHome, wuDbName)=storeConfig.getStoreArgs()
        if os.path.isdir(wuDbHome):
            shutil.rmtree(wuDbHome)

        #root work unit work dir and clean out
        rootWorkDir = getRootWorkDirFromConfiguration(configFile)
        if os.path.isdir(rootWorkDir):
            shutil.rmtree(rootWorkDir)
            
        #get cache info and clean out
        scp = ScifloConfigParser(configFile)
        cacheDir = scp.getParameter("cacheHome")
        cacheFile = scp.getParameter("cacheDb")
        cachePort = int(scp.getParameter("cachePort"))
        cache = os.path.join(cacheDir, cacheFile)
        cacheLog = os.path.join(sys.prefix, 'log', '%s.log' %
                                        os.path.splitext(cacheFile)[0])
        NamedDicts[cacheName] = {'dbFile': cache,
                         'port': cachePort,
                         'logFile': cacheLog}
        if os.path.isdir(cacheDir): shutil.rmtree(cacheDir)
        
        #start up cache server
        cachePid = os.fork()
        if not cachePid:
            os.setpgid(0, 0)
            application = service.Application("pdict")
            factory = PersistentDictFactory(cacheName)
            reactor.listenTCP(cachePort, factory)
            reactor.run()
            os._exit(0)

        #start up grid soap server
        pid = os.fork()
        if not pid:
            os.setpgid(0,0)
            while [1]:
                try:
                    #secure
                    if gridProtocol == 'ssl':
                        server = SoapServer(('0.0.0.0', gridSoapPort),
                            serverCertFile, serverKeyFile, returnFaultInfo=1,
                            rootDir=rootWorkDir, threading=None, debug=1)
                    else:
                        server = SoapServer(('0.0.0.0', gridSoapPort),
                            returnFaultInfo=1, rootDir=rootWorkDir,
                            threading=None, debug=1)
                    break
                except Exception, e:
                    print e
                    print "Retrying soap server."
                    time.sleep(1)
            retval = server.registerEndpoint(transformXml(configFile,
                GRID_ENDPOINT_CONFIG_XSL))
            server.serveForever()
            os._exit(0)

        #gridPid
        gridSoapPid = pid

        #soapDir
        soapDir = self.soapDir

        #start up test service soap server
        pid2 = os.fork()
        if not pid2:
            os.setpgid(0,0)
            
            #chdir to soapDir and copy test soap module files there
            os.chdir(soapDir)
            shutil.copy(testSoapModuleFile,soapDir)

            while [1]:
                try:
                    #ssl soap server for test services
                    server = SoapServer(('0.0.0.0', testServicePort),
                        returnFaultInfo=1, debug=1)
                    break
                except Exception, e:
                    print e
                    print "Retrying soap server."
                    time.sleep(1)
            retval = server.registerEndpoint(testServiceXmlFile)
            server.serveForever()
            os._exit(0)

        #testpid
        testSoapPid = pid2

        try:
            #loop until we can hit each server
            for s,p in (('service server', testServicePort),
                ('grid server', gridSoapPort), ('cache server', cachePort)):
                loopLimit = 0
                while True:
                    sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        sc.connect(('localhost',p))
                        sc.close()
                        print "Connected to %s at localhost:%s successfully." % (s,p)
                        break
                    except:
                        print "Waiting for %s at localhost:%s to come up." % (s,p)
                        time.sleep(1)
                    if loopLimit>=30:
                        raise RuntimeError, "%s failed to come up at localhost:%s." % (s,p)
                    loopLimit+=1

            #first submit
            scifloid, jsonFile = submitSciflo_client(wsdl, submitFuncName,
                                                     self.xmlString, {})
            while True:
                try: info = loadJson(jsonFile)
                except IOError, e:
                    print "Got IOError for %s: %s" % (jsonFile, e)
                    time.sleep(1)
                    continue
                if info['status'] in finishedStatusList: break
                time.sleep(5)
            for k in info: print "%s: %s" % (k, info[k])
            
            #second submit(cached)
            scifloid, jsonFile = submitSciflo_client(wsdl, submitFuncName,
                                                     self.xmlString, {})
            while True:
                try: info = loadJson(jsonFile)
                except IOError, e:
                    print "Got IOError for %s: %s" % (jsonFile, e)
                    time.sleep(1)
                    continue
                if info['status'] in finishedStatusList: break
                time.sleep(5)
            for k in info: print "%s: %s" % (k, info[k])
            
            #no look cache submit
            scifloid, jsonFile = submitSciflo_client(wsdl, submitNoCacheFuncName,
                                                     self.xmlString, {})
            while True:
                try: info = loadJson(jsonFile)
                except IOError, e:
                    print "Got IOError for %s: %s" % (jsonFile, e)
                    time.sleep(1)
                    continue
                if info['status'] in finishedStatusList: break
                time.sleep(5)
            for k in info: print "%s: %s" % (k, info[k])
            
            #fourth submit(cached)
            scifloid, jsonFile = submitSciflo_client(wsdl, submitFuncName,
                                                     self.xmlString, {})
            while True:
                try: info = loadJson(jsonFile)
                except IOError, e:
                    print "Got IOError for %s: %s" % (jsonFile, e)
                    time.sleep(1)
                    continue
                if info['status'] in finishedStatusList: break
                time.sleep(5)
            for k in info: print "%s: %s" % (k, info[k])
            
            #fifth submit(non-cached then cancelled)
            scifloid, jsonFile = submitSciflo_client(wsdl, submitNoCacheFuncName,
                                                     self.xmlString, {})
            time.sleep(10)
            print cancelSciflo_client(wsdl, cancelFuncName, scifloid)
            time.sleep(5)
            
        finally:
            #kill grid server
            try:
                os.kill(gridSoapPid, signal.SIGKILL)
                os.waitpid(gridSoapPid, 0)
            except: pass

            #kill test service soap server
            try:
                os.kill(testSoapPid, signal.SIGKILL)
                os.waitpid(testSoapPid, 0)
            except: pass
            
            #kill cache server
            try:
                os.kill(cachePid, signal.SIGKILL)
                os.waitpid(cachePid, 0)
            except: pass
            
            #remove root work directory
            if os.path.isdir(rootWorkDir): shutil.rmtree(rootWorkDir)

            #remove schedule db directory
            if os.path.isdir(dbHome): shutil.rmtree(dbHome)

            #remove workunit db directory
            if os.path.isdir(wuDbHome): shutil.rmtree(wuDbHome)

            #remove soap dir
            if os.path.isdir(soapDir): shutil.rmtree(soapDir)
                
            #remove cache dir
            if os.path.isdir(cacheDir): shutil.rmtree(cacheDir)

            #remove test dir
            if os.path.isdir(self.testDir): shutil.rmtree(self.testDir)

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    scifloServerTestSuite = unittest.TestSuite()
    scifloServerTestSuite.addTest(scifloServerTestCase("testScifloServer"))

    #return
    return scifloServerTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
