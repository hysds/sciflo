#-----------------------------------------------------------------------------
# Name:        soapTest.py
# Purpose:     Unittest for soap.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jun 02 15:37:07 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import unittest
import os
from tempfile import mkstemp, mkdtemp
from socket import getfqdn
from signal import SIGTERM
#from pyGlobus import GSISOAP, ioc
#from pyGlobus.io import AuthData, TCPIOAttr
from threading import *
import traceback
import shutil
import urllib.request, urllib.parse, urllib.error
import sys

from sciflo.webservices import *
from sciflo.utils import SCIFLO_NAMESPACE

#port to run soap server on
port = 8011

#port to run ssl soap server on
sslPort = 8012

#prot to run gsi soap server on
#gsiPort = 6854

#fqdn
fqdn = getfqdn()

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#endpoint xml config template
templateFile = os.path.join(dirName,'endpoint.xml')

#endpoint xml config file
xmlFile = os.path.join(dirName,'final_endpoint2.xml')

#sciflo doc
sflFile = os.path.join(dirName, 'testScifloDoc.xml')

#test html file
testHtmlFile = os.path.join(dirName,'index.html')

#sciflo namespace
sciflonamespace = SCIFLO_NAMESPACE

#echo soap service result format
echoResultFmt = "We are echoing: %s"

#html results

#sciflo dir
scifloDir = os.path.normpath(sys.prefix)

#ssl cert and key files
certFile = os.path.join(scifloDir,'ssl','hostcert.pem')
keyFile = os.path.join(scifloDir,'ssl','hostkey.pem')

'''
#gsi root dir
gsiRootDir = '/tmp/gsiRootDir'

class testGSIServer(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.__threads = []
        self._serverException = None
        self._serverTraceback = ""

    def run(self):

        try:

            #create directory to serve files
            if os.path.isdir(gsiRootDir):
                shutil.rmtree(gsiRootDir)
            os.makedirs(gsiRootDir)

            #instantiate soap server
            server = SoapServer(('0.0.0.0',gsiPort),certFile,keyFile,useGSI = 1,
                rootDir = gsiRootDir)

            #get temporary directory
            wsdlDir = mkdtemp()
            wsdlFile = os.path.join(wsdlDir,'TestEndpoint.wsdl')

            #register an endpoint and create wsdl file
            wsdlFile = server.registerEndpoint(xmlFile,wsdlFile)
            #print "wsdlFile is",wsdlFile

            server.handleRequest()
            self.doJoins()
            server.serverClose()

            #cleanup
            shutil.rmtree(gsiRootDir)

        except Exception, e:
            self._serverException = e

            #get traceback info
            etype = sys.exc_info()[0]
            evalue = sys.exc_info()[1]
            etb = traceback.extract_tb(sys.exc_info()[2])

            #create error message
            emessage = "Exception Type: %s\n" % str(etype)
            emessage+="Exception Value: %s\n" % str(evalue)
            emessage+="Traceback:\n%s\n" % '\n'.join(map(str,etb))

            self._serverTraceback = emessage

    def doJoins(self):
        for thr in self.__threads:
            thr.join()

    def insertClientThread(self, thread):
        self.__threads.insert(0,thread)

class testGSIClient(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._clientException = None
        self._clientTraceback = ""

    def run(self):

        try:
            #soap arg
            soapArg = "Hello World!"

            #soap proxy
            config = GSISOAP.SOAPConfig(debug = 1)
            proxy1 = GSISOAP.SOAPProxy("https://%s:%s" % (getfqdn(), gsiPort),
                             namespace = sciflonamespace+"/TestEndpoint",config = config)
            proxy1.set_channel_mode(ioc.GLOBUS_IO_SECURE_CHANNEL_MODE_GSI_WRAP)
            proxy1.set_delegation_mode(ioc.GLOBUS_IO_SECURE_DELEGATION_MODE_NONE)

            #call echo soap service
            result = proxy1.echo(soapArg)

            #assert
            assert result == echoResultFmt % soapArg

            #copy some files to serve out
            shutil.copy(xmlFile,gsiRootDir)
            shutil.copy(testHtmlFile,gsiRootDir)

            #THIS HAS BEEN UNCOMMENTED UNTIL THERE IS A GSI-aware urllib.urlopen
            #function to read data from a GSI server.  Otherwise this test will
            #hang.
            #get xml contents via server and and file itself and assert
            xmlUrl = 'https://%s:%s/endpoint.xml' % (getfqdn(), gsiPort)
            xmlContentsViaServer = urllib.urlopen(xmlUrl).read()
            xmlContents = open(xmlFile,'r').read()
            assert xmlContentsViaServer == xmlContents

            #get html contents via server and and file itself and assert
            htmlUrl = 'https://%s:%s/index.html' % (getfqdn(), gsiPort)
            htmlContentsViaServer = urllib.urlopen(htmlUrl).read()
            htmlContents = open(testHtmlFile,'r').read()
            assert htmlContentsViaServer == htmlContents
        except Exception, e:
            self._clientException = e

            #get traceback info
            etype = sys.exc_info()[0]
            evalue = sys.exc_info()[1]
            etb = traceback.extract_tb(sys.exc_info()[2])

            #create error message
            emessage = "Exception Type: %s\n" % str(etype)
            emessage+="Exception Value: %s\n" % str(evalue)
            emessage+="Traceback:\n%s\n" % '\n'.join(map(str,etb))

            self._clientTraceback = emessage
    '''

class soapTestCase(unittest.TestCase):
    """Test case for soap."""

    def setUp(self):
        """Setup."""

        #vars
        self.pid = None
        self.rootDir = None
        self.wsdlFile = None
        
        #write endpoint file
        open(xmlFile, 'w').write("%s\n" % open(templateFile, 'r').\
        read().replace('TEST_SCIFLO_DOC_URL', sflFile))

    def testSoapEndpointInstantiation(self):
        """Test instantiating a SoapEndpoint object  with GET method.  Since
        the SoapEndpoint class instantiates SoapMethod objects, we are implicitly
        testing that class.
        """

        #soapport
        soapport = 'http://%s:8888' % fqdn

        #get soap endpoint object
        obj = SoapEndpoint(xmlFile,soapport)

        #assert the results of accessor methods
        assert obj.getEndpointXmlFile()==xmlFile
        assert obj.getSoapPort()==soapport
        assert obj.getNamespace()==sciflonamespace
        assert obj.getEndpointName()=='TestEndpoint'
        assert obj.getEndpointNamespace()==sciflonamespace+'/TestEndpoint'

        #get list of SOAP method objects
        list = obj.getSoapMethodObjectsList()

        #write wsdl file
        handle,self.wsdlFile = mkstemp()
        #print wsdlFile
        wsdl = obj.writeWsdlFile(self.wsdlFile)

    def testSoapServer(self):
        """Test SoapServer class with GET method."""

        #create directory to serve files
        self.rootDir = mkdtemp()

        #instantiate soap server
        server = SoapServer(('0.0.0.0',port),rootDir = self.rootDir)

        #register endpoint
        wsdlUrl = server.registerEndpoint(xmlFile)
        #print "wsdlUrl:",wsdlUrl

        #fork a server
        self.pid = os.fork()
        if self.pid!=0:

            #soap arg
            soapArg = "Hello World!"

            #soap proxy
            proxy1 = WSDL.Proxy(wsdlUrl)

            #call echo soap service
            result = proxy1.echo(soapArg)

            #assert
            assert result == echoResultFmt % soapArg

            #copy some files to serve out
            shutil.copy(xmlFile,self.rootDir)
            shutil.copy(testHtmlFile,self.rootDir)

            #get xml contents via server and and file itself and assert
            xmlUrl = 'http://%s:%s/final_endpoint2.xml' % (getfqdn(), port)
            xmlContentsViaServer = urllib.request.urlopen(xmlUrl).read()
            xmlContents = open(xmlFile,'r').read()
            assert xmlContentsViaServer == xmlContents

            #get html contents via server and and file itself and assert
            htmlUrl = 'http://%s:%s/index.html' % (getfqdn(), port)
            htmlContentsViaServer = urllib.request.urlopen(htmlUrl).read()
            htmlContents = open(testHtmlFile,'r').read()
            assert htmlContentsViaServer == htmlContents

        else:
            server.serveForever()

    def testSslSoapServer(self):
        """Test SoapServer class over SSL with GET method."""

        #create directory to serve files
        self.rootDir = mkdtemp()

        #instantiate soap server
        server = SoapServer(('0.0.0.0',sslPort),certFile,keyFile,rootDir = self.rootDir)

        #register an endpoint and get wsdl url
        wsdlUrl = server.registerEndpoint(xmlFile)

        #fork a server
        self.pid = os.fork()
        if self.pid!=0:

            #soap arg
            soapArg = "Hello World!"

            #soap proxy
            proxy1 = WSDL.Proxy(wsdlUrl)

            #call echo soap service
            result = proxy1.echo(soapArg)

            #assert
            assert result == echoResultFmt % soapArg

            #copy some files to serve out
            shutil.copy(xmlFile,self.rootDir)
            shutil.copy(testHtmlFile,self.rootDir)

            #get xml contents via server and and file itself and assert
            xmlUrl = 'https://%s:%s/final_endpoint2.xml' % (getfqdn(), sslPort)
            xmlContentsViaServer = urllib.request.urlopen(xmlUrl).read()
            xmlContents = open(xmlFile,'r').read()
            assert xmlContentsViaServer == xmlContents

            #get html contents via server and and file itself and assert
            htmlUrl = 'https://%s:%s/index.html' % (getfqdn(), sslPort)
            htmlContentsViaServer = urllib.request.urlopen(htmlUrl).read()
            htmlContents = open(testHtmlFile,'r').read()
            assert htmlContentsViaServer == htmlContents

        else:
            server.serveForever()

    '''
    def testGSISoapServer(self):
        """Test GSI SoapServer class."""

        global server
        server = testGSIServer()
        server.start()

    def testGSISoapServerClient(self):
        client = testGSIClient()
        server.insertClientThread(client)
        client.start()
        server.join()

        #get server exception
        serverError = server._serverException
        if serverError is not None:
            print "TRACEBACK INFO:", server._serverTraceback
            raise serverError

        #get client exception
        clientError = client._clientException
        if clientError is not None:
            print "TRACEBACK INFO:", client._clientTraceback
            raise clientError
    '''
    def tearDown(self):
        """Cleanup."""

        #kill server process
        if self.pid: os.kill(self.pid,SIGTERM)

        #cleanup rootDir
        if self.rootDir: shutil.rmtree(self.rootDir)

        #cleanup wsdlfile
        if self.wsdlFile: os.unlink(self.wsdlFile)
        
        #cleanup xmlFile
        if os.path.exists(xmlFile): os.unlink(xmlFile)

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    soapTestSuite = unittest.TestSuite()
    soapTestSuite.addTest(soapTestCase("testSoapEndpointInstantiation"))
    soapTestSuite.addTest(soapTestCase("testSoapServer"))
    #soapTestSuite.addTest(soapTestCase("testSslSoapServer"))
    #soapTestSuite.addTest(soapTestCase("testGSISoapServer"))
    #soapTestSuite.addTest(soapTestCase("testGSISoapServerClient"))

    #return
    return soapTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)


