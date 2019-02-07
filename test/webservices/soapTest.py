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
from signal import SIGTERM, SIGKILL
from threading import *
import traceback
import sys

from sciflo.webservices import *
from sciflo.utils import SCIFLO_NAMESPACE

#port to run soap server on
port = 8019

#port to run ssl soap server on
sslPort = 8010

#fqdn
fqdn = getfqdn()

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#endpoint xml config template
templateFile = os.path.join(dirName,'endpoint.xml')

#endpoint xml config file
xmlFile = os.path.join(dirName,'final_endpoint.xml')

#sciflo doc
sflFile = os.path.join(dirName, 'testScifloDoc.xml')

#sciflo namespace
sciflonamespace = SCIFLO_NAMESPACE

#echo soap service result format
echoResultFmt = "We are echoing: %s"

#sciflo dir
scifloDir = os.path.normpath(sys.prefix)

#ssl cert and key files
certFile = os.path.join(scifloDir,'ssl','hostcert.pem')
keyFile = os.path.join(scifloDir,'ssl','hostkey.pem')


class soapTestCase(unittest.TestCase):
    """Test case for soap."""
    
    def setUp(self):
        """Setup."""

        #write endpoint file
        open(xmlFile, 'w').write("%s\n" % open(templateFile, 'r').\
        read().replace('TEST_SCIFLO_DOC_URL', sflFile))

    def testSoapEndpointInstantiation(self):
        """Test instantiating a SoapEndpoint object.  Since the SoapEndpoint
        class instantiates SoapMethod objects, we are implicitly testing that
        class.
        """

        #soapport
        soapport = 'http://%s:8889' % fqdn

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
        handle,wsdlFile = mkstemp()
        #print wsdlFile
        wsdl = obj.writeWsdlFile(wsdlFile)

        #remove wsdlFile
        os.unlink(wsdlFile)

    def testSoapServer(self):
        """Test SoapServer class."""

        #instantiate soap server
        server = SoapServer(('0.0.0.0',port))

        #get temporary directory
        wsdlDir = mkdtemp()
        wsdlFile = os.path.join(wsdlDir,'TestEndpoint.wsdl')

        #register an endpoint and create wsdl file
        wsdlFile = server.registerEndpoint(xmlFile,wsdlFile)
        #print "wsdlFile is",wsdlFile

        #fork a server
        self.pid = os.fork()
        if self.pid!=0:

            #soap arg
            soapArg = "Hello World!"

            #soap proxy
            proxy1 = SOAPProxy("http://%s:%s/" % (getfqdn(), port),
                             namespace = sciflonamespace+"/TestEndpoint")

            #call echo soap service
            result = proxy1.echo(soapArg)

            #assert
            assert result == echoResultFmt % soapArg

            #soap proxy from wsdl file
            proxy2 = WSDL.Proxy(wsdlFile)

            #call echo soap service
            result2 = proxy2.echo(soapArg)

            #assert
            assert result2 == echoResultFmt % soapArg

            #soap proxy from wsdl url
            wsdlUrl = 'http://%s:%s/wsdl?%s/%s' % (getfqdn(),port,sciflonamespace,'TestEndpoint')
            proxy3 = WSDL.Proxy(wsdlUrl)

            #call echo soap service
            result3 = proxy3.echo(soapArg)
            print(result3)

            #assert
            result3 == echoResultFmt % soapArg
            
            #test exposed sciflo call
            assert proxy3.echoSciflo("What is this?") == \
                ['What is this? = Hello World\n', 'What is this? = Hello World\n from echo2.']
            return 0

        else:
            server.serveForever()

        #cleanup wsdl
        os.unlink(wsdlFile)
        os.rmdir(wsdlDir)

        #kill server process
        os.kill(self.pid,SIGTERM)

    def testSslSoapServer(self):
        """Test SoapServer class over SSL."""

        #instantiate soap server
        server = SoapServer(('0.0.0.0',sslPort),certFile,keyFile)

        #get temporary directory
        wsdlDir = mkdtemp()
        wsdlFile = os.path.join(wsdlDir,'TestEndpoint.wsdl')

        #register an endpoint and create wsdl file
        wsdlFile = server.registerEndpoint(xmlFile,wsdlFile)
        #print "wsdlFile is",wsdlFile

        #fork a server
        self.sslPid = os.fork()
        if self.sslPid!=0:

            #soap arg
            soapArg = "Hello World!"

            #soap proxy
            proxy1 = SOAPProxy("https://%s:%s/" % (getfqdn(), sslPort),
                             namespace = sciflonamespace+"/TestEndpoint")

            #call echo soap service
            result = proxy1.echo(soapArg)

            #assert
            assert result == echoResultFmt % soapArg

            #soap proxy from wsdl file
            proxy2 = WSDL.Proxy(wsdlFile)

            #call echo soap service
            result2 = proxy2.echo(soapArg)

            #assert
            result2 == echoResultFmt % soapArg

            #soap proxy from wsdl url
            wsdlUrl = 'https://%s:%s/wsdl?%s/%s' % (getfqdn(),sslPort,sciflonamespace,'TestEndpoint')
            proxy3 = WSDL.Proxy(wsdlUrl)

            #call echo soap service
            result3 = proxy3.echo(soapArg)

            #assert
            result3 == echoResultFmt % soapArg
            
            #test exposed sciflo call
            assert proxy3.echoSciflo("What is this?") == \
                ['What is this? = Hello World\n', 'What is this? = Hello World\n from echo2.']

        else:
            server.serveForever()

        #cleanup wsdl
        os.unlink(wsdlFile)
        os.rmdir(wsdlDir)

        #kill server process
        os.kill(self.sslPid,SIGTERM)

    def tearDown(self):
        """Cleanup."""

        #cleanup xmlFile
        if os.path.exists(xmlFile): os.unlink(xmlFile)
        
        #kill servers
        try:
            os.kill(self.pid, SIGKILL)
            os.waitpid(self.pid, 0)
        except: pass

        #kill test service soap server
        try:
            os.kill(self.sslPid, SIGKILL)
            os.waitpid(self.sslPid, 0)
        except: pass
    
#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    soapTestSuite = unittest.TestSuite()
    soapTestSuite.addTest(soapTestCase("testSoapEndpointInstantiation"))
    soapTestSuite.addTest(soapTestCase("testSoapServer"))

    #return
    return soapTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite = getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)


