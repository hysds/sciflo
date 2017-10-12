#-----------------------------------------------------------------------------
# Name:        testSoapClient.py
# Purpose:     Run this script as a user.
#
# Author:      Gerald Manipon
#
# Created:     Tue Aug 09 10:45:11 2005
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
from SOAPpy import WSDL

from sciflo.webservices import *
from sciflo.utils import SCIFLO_NAMESPACE

#port to run soap server on
port = 8888

#fqdn
fqdn = getfqdn()

#directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

#endpoint xml config file
xmlFile = os.path.join(dirName,'endpoint.xml')

#sciflo namespace
sciflonamespace = SCIFLO_NAMESPACE

#echo soap service result format
echoResultFmt = "We are echoing: %s"

#soap arg
soapArg = "Hello World!"

#soap proxy
#proxy1 = WSDL.Proxy("http://localhost:%s/wsdl?%s" % (port,sciflonamespace+'/TestEndpoint'))

#SSL soap proxy
proxy1 = WSDL.Proxy("https://localhost:%s/wsdl?%s" % (port,sciflonamespace+'/TestEndpoint'))

'''
#GSI soap proxy
config = GSISOAP.SOAPConfig(debug = 1)
proxy1 = GSISOAP.SOAPProxy("https://localhost:%s" % port,
	namespace = sciflonamespace+"/TestEndpoint",config = config)
proxy1.set_channel_mode(ioc.GLOBUS_IO_SECURE_CHANNEL_MODE_GSI_WRAP)
proxy1.set_delegation_mode(ioc.GLOBUS_IO_SECURE_DELEGATION_MODE_NONE)
'''

#call echo soap service
result = proxy1.echo(soapArg)

#assert
assert result == echoResultFmt % soapArg
