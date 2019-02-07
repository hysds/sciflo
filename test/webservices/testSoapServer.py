# -----------------------------------------------------------------------------
# Name:        testSoapServer.py
# Purpose:     Run this script as the admin user.
#
# Author:      Gerald Manipon
#
# Created:     Tue Aug 09 10:44:16 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------

import unittest
import os
from tempfile import mkstemp, mkdtemp
from socket import getfqdn
from signal import SIGTERM
#from pyGlobus import GSISOAP, ioc
#from pyGlobus.io import AuthData, TCPIOAttr
from threading import *

from sciflo.webservices import *
from sciflo.utils import SCIFLO_NAMESPACE

# port to run soap server on
port = 8888

# fqdn
fqdn = getfqdn()

# directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

# endpoint xml config file
xmlFile = os.path.join(dirName, 'endpoint.xml')

# sciflo namespace
sciflonamespace = SCIFLO_NAMESPACE

# echo soap service result format
echoResultFmt = "We are echoing: %s"

# sciflo dir
scifloDir = os.path.normpath(sys.prefix)

# ssl cert and key files
certFile = os.path.join(scifloDir, 'ssl', 'hostcert.pem')
keyFile = os.path.join(scifloDir, 'ssl', 'hostkey.pem')

# instantiate HTTP soap server
# server = SoapServer(('0.0.0.0',port))#,returnFaultInfo = 1,debug = 1)

# instantiate SSL soap server
server = SoapServer(('0.0.0.0', port), certFile, keyFile)

# instantiate GSI soap server
#server = SoapServer(('0.0.0.0',port),useGSI = 1)

# get temporary directory
wsdlDir = mkdtemp()
wsdlFile = os.path.join(wsdlDir, 'TestEndpoint.wsdl')

# register an endpoint and create wsdl file
wsdlFile = server.registerEndpoint(xmlFile)  # ,wsdlFile)
# print "wsdlFile is",wsdlFile

# server.handleRequest()
server.serveForever()
