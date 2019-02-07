#-----------------------------------------------------------------------------
# Name:        soap.py
# Purpose:     SOAP service related classes and functions.
#
# Author:      Gerald Manipon
#
# Created:     Fri Jun 03 12:01:00 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
from xml.etree.ElementTree import parse, Element, tostring, SubElement, XMLID
from xml.dom.ext import PrettyPrint
from xml.dom.minidom import parseString
import re
import types
import sys
import os
import time
from inspect import getargspec
from SOAPpy import *
from SOAPpy.Config import Config
from SOAPpy.Server import SOAPServerBase, SOAPRequestHandler
import glob
from socket import getfqdn
from M2Crypto import SSL
from getpass import getuser
from http.server import SimpleHTTPRequestHandler
import posixpath
import mimetypes
import traceback
import urllib.request, urllib.parse, urllib.error
import socketserver
from twisted.web import server, resource, static
from twisted.internet import reactor, defer, threads, ssl
from twisted.python import log as twistedLog
from tempfile import mktemp

from sciflo.utils import *
from sciflo.grid import Sciflo
from sciflo.grid.executor import runSciflo
from sciflo.grid.funcs import forkChildAndRun

#schema xml for endpoint xml documents
ENDPOINT_SCHEMA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
elementFormDefault="qualified"
targetNamespace="http://sciflo.jpl.nasa.gov/2006v1/sf"
xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf">
  <xs:element name="soapEndpoint">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:endpointName"/>
        <xs:element ref="sf:soapMethodSet"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="endpointName" type="xs:string"/>
  <xs:element name="soapMethodSet">
    <xs:complexType>
      <xs:sequence>
        <xs:element maxOccurs="unbounded" ref="sf:soapMethod"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="soapMethod">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:exposedName"/>
        <xs:element ref="sf:pythonFunction"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="exposedName" type="xs:NCName"/>
  <xs:element name="pythonFunction" type="xs:string"/>
</xs:schema>
"""

class SoapEndpointError(Exception):
	"""Exception class for SoapEndpoint class."""
	pass

class SoapEndpoint(object):
    """Class representing a SOAP endpoint.
    """

    def __init__(self,xmlFile,soapPort,rootDir=None):
        """Constructor."""

        #validate xml endpoint file or string and get element root
        validated,validationError = validateXml(xmlFile,ENDPOINT_SCHEMA_XML)
        if validated:
            if  os.path.isfile(xmlFile):
                self._endpointXmlFile = xmlFile
                self._endpointXmlString = None
                root = parse(self._endpointXmlFile).getroot()
            else:
                self._endpointXmlFile = None
                self._endpointXmlString = xmlFile
                root = XMLID(self._endpointXmlString)[0]
        else:
            raise SoapEndpointError("Failed to validate xmlFile %s with ENDPOINT_SCHEMA_XML: %s" % \
                (xmlFile, str(validationError)))

        #set attributes
        self._soapPort = soapPort
        self._rootDir = rootDir

        #get namespace
        match = re.match(r'^\{(.+)\}.+$',root.tag)
        if match: self._namespace = match.group(1)
        else:
            raise SoapEndpointError("Couldn't get default namespace and/or rootTag from endpoint xml: \
                %s" % self._endpointXmlFile)

        #get endpointName
        self._endpointName = root.find('{%s}%s' % (self._namespace,'endpointName')).text

        #set endpointNamespace; if namespace is already fully qualified just use it
        #otherwise create it from default namespace and the endpointName
        match = re.match(r'^\w+://', self._endpointName)
        if match:
            self._endpointNamespace = self._endpointName
            self._endpointName = self._endpointName.split('/')[-1]
        else: self._endpointNamespace = self._namespace + '/' + self._endpointName

        #get list of soapmethods defined in xml
        soapmethodsList = root.findall('*/{%s}%s' % (self._namespace,'soapMethod'))
        #print "Found",len(soapmethodsList)

        #empty list of SoapMethod objects
        self._soapMethodObjects = []

        #loop over each xml element and create a list of SoapMethod objects
        for soapmethodElt in soapmethodsList:

            #get exposed name
            exposedName = soapmethodElt.find('{%s}%s' % (self._namespace,'exposedName')).text

            #get python function
            pythonFunction = soapmethodElt.find('{%s}%s' % (self._namespace,'pythonFunction')).text

            try:
                #create SoapMethod object
                soapmethodObj = SoapMethod(exposedName,pythonFunction,self._rootDir,self._soapPort)

                #append to list
                self._soapMethodObjects.append(soapmethodObj)

            except SoapMethodError as e:
                print("SoapMethodError: %s" % e, file=sys.stderr)
                continue
            except Exception as e:
                raise SoapEndpointError("Encountered an exception creating SoapMethod object: %s" % e)

        #set wsdl string
        self._wsdlString = self._generateWsdlString()

        #append the wsdl() method to expose
        self._soapMethodObjects.append(SoapMethod('wsdl',lambda:self._wsdlString,self._rootDir))

    def getEndpointXmlFile(self):
        """Return path of the endpoint xml file."""
        return self._endpointXmlFile

    def getEndpointXmlString(self):
        """Return the endpoint xml string."""
        return self._endpointXmlString

    def getSoapPort(self):
        """Return the soap port this endpoint will be exposed on."""
        return self._soapPort

    def getNamespace(self):
        """Return the default namespace defined in the endpoint xml file."""
        return self._namespace

    def getEndpointName(self):
        """Return the name of this soap endpoint."""
        return self._endpointName

    def getEndpointNamespace(self):
        """Return the namespace of this soap endpoint."""
        return self._endpointNamespace

    def getSoapMethodObjectsList(self):
        """Return a list of SoapMethod objects."""
        return self._soapMethodObjects

    def getWsdl(self):
        """Return the wsdl string."""
        return self._wsdlString

    def _generateWsdlString(self):
        """Generate the WSDL xml for this SOAP endpoint."""

        #root element
        root = Element('definitions',{'name':self._endpointName,
                                      'targetNamespace':self._endpointNamespace,
                                      'xmlns:tns':self._endpointNamespace,
                                      'xmlns:xs':"http://www.w3.org/2001/XMLSchema",
                                      'xmlns:soap':"http://schemas.xmlsoap.org/wsdl/soap/",
                                      'xmlns':"http://schemas.xmlsoap.org/wsdl/"})

        #create portType
        portType = Element('portType',{'name':self._endpointName+'PortType'})

        #create binding
        binding = Element('binding',{'name':self._endpointName+'Binding',
                                     'type':'tns:'+self._endpointName+'PortType'})
        SubElement(binding,'soap:binding',{'style':"rpc",
                                           'transport':"http://schemas.xmlsoap.org/soap/http"})

        #create service
        service = Element('service',{'name':self._endpointName})
        documentation = SubElement(service,'documentation')
        documentation.text = "SciFlo SOAP methods for %s." % self._endpointName
        port = SubElement(service,'port',{'name':self._endpointName+'Port',
                                          'binding':'tns:'+self._endpointName+'Binding'})
        soapAddress = SubElement(port,'soap:address',{'location': self._soapPort})

        #loop over functions and add message, portType, binding elements
        for soapObject in self._soapMethodObjects:

            #message request
            messageRequest = Element('message',{'name':soapObject.getExposedName()+'Request'})
            root.append(messageRequest)
            args = soapObject.getPythonFunctionArgNames()
            #print "args is",args
            if args is None or len(args) == 0: pass
            else:
                for arg in args:
                    part = SubElement(messageRequest,'part',{'name':arg,
                                                             'type':'xs:string'})

            #message response
            messageResponse = Element('message',{'name':soapObject.getExposedName()+'Response'})
            root.append(messageResponse)
            messageResponsePart = SubElement(messageResponse,'part',{'name':'Result',
                                                                     'type':'xs:string'})

            #operation element in porttype
            operation = Element('operation',{'name':soapObject.getExposedName()})
            portType.append(operation)
            input = SubElement(operation,'input',{'message':'tns:'+soapObject.getExposedName()+'Request'})
            output = SubElement(operation,'output',{'message':'tns:'+soapObject.getExposedName()+'Response'})

            #operation element in binding
            commonHash = {'use':'encoded',
                          'namespace':self._endpointNamespace,
                          'encodingStyle':'http://schemas.xmlsoap.org/soap/encoding/'}
            operationInBinding = Element('operation',{'name':soapObject.getExposedName()})
            binding.append(operationInBinding)
            soapOperation = SubElement(operationInBinding,'soap:operation',{'soapAction':""})
            input2 = SubElement(operationInBinding,'input',{'name':soapObject.getExposedName()+'Request'})
            soapBody = SubElement(input2,'soap:body',commonHash)
            output2 = SubElement(operationInBinding,'output',{'name':soapObject.getExposedName()+'Response'})
            soapBody2 = SubElement(output2,'soap:body',commonHash)

        #append elements to root
        root.append(portType)
        root.append(binding)
        root.append(service)

        #get pretty string
        wsdlString = getPrettyPrintXmlFromDom(parseString(tostring(root)))
        return wsdlString

    def writeWsdlFile(self,file):
        """Generate a WSDL file for this SOAP endpoint."""

        f = open(file,'w')
        f.write(self._wsdlString)
        f.close()
        return file
    
class ScifloFunction(object):
    """Utility class to wrap a sciflo flow into a function."""
    def __init__(self, xml): self.xml = xml
    def __call__(self, *args):
        return forkChildAndRun(None, runSciflo, self.xml, args, publicize=True)

class AsyncFunction(object):
    """Utility class to wrap execution of a soap function in an asynchronous call."""
    def __init__(self, func, rootDir, urlBase):
        self.func = func
        self.rootDir = rootDir
        self.urlBase = urlBase
        if not os.path.isdir(self.rootDir): os.makedirs(self.rootDir)
        self.ubt = UrlBaseTracker(self.rootDir, self.urlBase)
    def __call__(self, *args, **kargs):
        pickleFile = mktemp(suffix="_%d" % os.getpid(), dir=self.rootDir)
        pid = os.fork()
        if pid > 0: return 'scifloAsync:%s' % self.ubt.getUrl(pickleFile)
        os.chdir("/")
        os.setsid()
        os.umask(0)
        pid = os.fork()
        if pid > 0:
            os.waitpid(pid, 0)
            os._exit(0)
        result = self.func(*args, **kargs)
        p = open(pickleFile, 'w')
        pickle.dump(result, p)
        p.close()
        os._exit(0)

def resolveSoapFunction(exposedName, funcOrSflStr, rootDir=None, urlBase=None):
    """Resolve string into a python function."""
    #handle flows to expose
    sfl = None
    xmlDoc = None
    try:
        if funcOrSflStr.startswith('<'): xmlDoc = funcOrSflStr
        elif os.path.exists(funcOrSflStr):
            xmlDoc = open(funcOrSflStr,'r').read()
        else: xmlDoc = urllib.request.urlopen(funcOrSflStr).read()
        sfl = Sciflo(xmlDoc)
    except Exception as e: pass
    if sfl:
        func = ScifloFunction(str(xmlDoc))
        if funcOrSflStr == xmlDoc: funcOrSflStr = sfl.getName() #no xml
        funcOrSflStrArgNames = sfl.globalInputs
        
    #handle functions to expose
    else:
        #async
        async = False
        
        #check if pythonFunction is already a function
        if isinstance(funcOrSflStr,types.FunctionType):
            func = funcOrSflStr
            funcOrSflStr = str(func)
        else:
            #check if async
            matchAsync = re.search(r'^async:(.*)$', funcOrSflStr)
            if matchAsync:
                async = True
                funcOrSflStr = matchAsync.group(1)
            
            #check if internal name is None or empty
            if funcOrSflStr is None or re.match(r'^\s*$',funcOrSflStr):
                raise RuntimeError("Undefined specification for %s." % exposedName)

            #check if we have to import any libraries
            libmatch = re.match(r'^(.+)\.\w+$',funcOrSflStr)
            if libmatch:
                importLib = libmatch.group(1)
                try: exec("import %s" % importLib)
                except Exception as e:
                    raise RuntimeError("Failed to import %s for %s (%s): %s" \
                        % (importLib,funcOrSflStr,exposedName,e))

            #get function
            try: func = eval(funcOrSflStr)
            except Exception as e:
                raise RuntimeError("Failed to eval function %s (%s): %s" \
                    % (funcOrSflStr,exposedName,e))

            #verify function is actually a function
            if isinstance(func,types.FunctionType): pass
            else:
                raise RuntimeError("Failed because pythonFunction %s (%s) is not a function." \
                    % (funcOrSflStr,exposedName))

        #get list of argnames
        try:
            (args,varargs,varkw,defaults) = getargspec(func)
            funcOrSflStrArgNames = args
        except Exception as e:
            raise RuntimeError("Failed to inspect function %s for args (%s): %s" \
                % (funcOrSflStr,exposedName,e))
            
        #wrap if async
        if async and rootDir and urlBase:
            print("Wrapping %s as an AsyncFunction()." % exposedName)
            func = AsyncFunction(func, rootDir, urlBase)
    return (func, funcOrSflStr, funcOrSflStrArgNames)

class SoapMethodError(Exception):
	"""Exception class for SoapMethod class."""
	pass

class SoapMethod(object):
    '''Container class for a SOAP method.'''

    def __init__(self,exposedName,pythonFunction,rootDir=None,urlBase=None):
        """Constructor."""

        #set vars
        self._exposedName = exposedName
        self._rootDir = rootDir
        self._urlBase = urlBase

        #resolve
        try:
            (self._function, self._pythonFunction, self._pythonFunctionArgNames) = \
                resolveSoapFunction(exposedName, pythonFunction, self._rootDir, self._urlBase)
        except Exception as e: raise SoapMethodError(str(e))

    #accessors
    def getExposedName(self):
        """Return the name that this SOAP methods will be exposed as."""
        return self._exposedName

    def getPythonFunctionName(self):
        """Return the name of the underlying python function of this SOAP
        method.
        """
        return self._pythonFunction

    def getFunction(self):
        """Return the underlying function object of this SOAP method."""
        return self._function

    def getPythonFunctionArgNames(self):
        """Return the list of argument names of the underlying function
        object of this SOAP method.
        """
        return self._pythonFunctionArgNames

def callback(arg, handle, identity, context):
    """Callback function for GSI SOAP server."""
    return 1

class ForkingSOAPServer(SOAPServerBase, socketserver.ForkingTCPServer):
    """Forking SOAP server absent from SOAPpy."""
    request_queue_size = 50
    max_children = 50
    def __init__(self, addr = ('localhost', 8000), RequestHandler = SOAPRequestHandler,
                 log = 0, encoding = 'UTF-8', config = Config, namespace = None,
                 ssl_context = None):

        # Test the encoding, raising an exception if it's not known
        if encoding != None: ''.encode(encoding)

        if ssl_context != None and not config.SSLserver:
            raise AttributeError("SSL server not supported by this Python installation")

        self.namespace = namespace
        self.objmap = {}
        self.funcmap = {}
        self.ssl_context = ssl_context
        self.encoding = encoding
        self.config = config
        self.log = log
        self.allow_reuse_address = 1

        socketserver.ForkingTCPServer.__init__(self, addr, RequestHandler)
    
class ScifloSOAPPublisher(resource.Resource):
    """SOAP publisher class for TwistedSOAPServer."""
    isLeaf = True
    encoding = "UTF-8"
    def __init__(self, namespace, requestHandler, config):
        self.namespace = namespace
        self.requestHandler = requestHandler
        self.config = config
        self.funcmap = {}
        resource.Resource.__init__(self)
    
    def registerFunction(self, function, namespace = '', funcName = None, path = ''):
        if not funcName : funcName = function.__name__
        if namespace == '' and path == '': namespace = self.namespace
        if namespace == '' and path != '':
            namespace = path.replace("/", ":")
            if namespace[0] == ":": namespace = namespace[1:]
        if namespace in self.funcmap:
            self.funcmap[namespace][funcName] = function
        else:
            self.funcmap[namespace] = {funcName : function}
            
    def lookupFunction(self, functionName, namespace):
        """Lookup published SOAP function."""
        if namespace in self.funcmap and functionName in self.funcmap[namespace]:
            return self.funcmap[namespace][functionName]
        else: return None
        
    def render_GET(self, request):
        """Handle GET."""
        scheme, netloc, path, params, query, frag = urlparse.urlparse(request.uri)
        if path == '/wsdl' and query != '':
            request.setHeader('content-type', "text/xml")
            return self.funcmap[query]['wsdl']()
        else:
            #get list of all available wsdl namespaces
            allNs = list(self.funcmap.keys())
            wsdlListStr = '<html><head><title>WSDL Directory</title></head><body><list>'
            for thisNs in allNs:
                wsdlListStr += '''<li><a href="/wsdl?%s">%s</a></li>\n''' % (thisNs, os.path.basename(thisNs))
            wsdlListStr += '</list></body></html>'    
            return wsdlListStr

    def render_POST(self, request):
        """Handle a SOAP command."""
        data = request.content.read()

        p, header, body, attrs = parseSOAPRPC(data, 1, 1, 1)

        methodName, args, kwargs, ns = p._name, p._aslist, p._asdict, p._ns

        # deal with changes in SOAPpy 0.11
        if callable(args):
            args = args()
        if callable(kwargs):
            kwargs = kwargs()

        function = self.lookupFunction(methodName, ns)

        if not function:
            self._methodNotFound(request, methodName, ns)
            return server.NOT_DONE_YET
        else:
            if hasattr(function, "useKeywords"):
                keywords = {}
                for k, v in list(kwargs.items()):
                    keywords[str(k)] = v
                #using threads.deferToThread() allows for better connection
                #handling for multiple concurrent requests but performs
                #poorly on computationally intensive concurrent requests
                d = threads.deferToThread(self.runDeferredFunc, function,
                                          methodName, ns, **keywords)
                #using defer.maybeDeferred() allows for better performance
                #on multiple concurrent requests that are computationally
                #intensive but performs poorly on connection handling of
                #multiple concurrent requests
                #d = defer.maybeDeferred(self.runDeferredFunc, function,
                #                        methodName, ns, **keywords)
            else:
                d = threads.deferToThread(self.runDeferredFunc, function,
                                          methodName, ns, *args)
                #d = defer.maybeDeferred(self.runDeferredFunc, function,
                #                        methodName, ns, *args)

        d.addCallback(self._gotResult, request, methodName, ns)
        return server.NOT_DONE_YET
    
    def runDeferredFunc(self, function, methodName, ns, *args, **kargs):
        """Run deferred function."""
        try: return function(*args, **kargs)
        except Exception as e:
            info = sys.exc_info()
            if isinstance(e, faultType):
                fault = e
            else:
                fault = faultType("%s:Server" % NS.ENV_T,
                    "Method %s:%s failed." % (ns, methodName))
                
            if self.config.returnFaultInfo:
                fault._setDetail("".join(traceback.format_exception(
                    info[0], info[1], info[2])))
            elif not hasattr(fault, 'detail'):
                fault._setDetail("%s %s" % (info[0], info[1]))
            return fault

    def _methodNotFound(self, request, methodName, ns):
        response = buildSOAP(faultType("%s:Client" %
            NS.ENV_T, "Method %s:%s not found" % (ns,methodName)),
            encoding=self.encoding, config=self.config)
        self._sendResponse(request, response, status=500)

    def _gotResult(self, result, request, methodName, ns):
        if isinstance(result, faultType):
            response = buildSOAP(result, encoding=self.encoding, config=self.config)
            self._sendResponse(request, response, status=500)
        else:
            if not isinstance(result, voidType):
                result = {"Result": result}
            response = buildSOAP(kw={'%sResponse' % methodName: result},
                                      encoding=self.encoding,
                                      config=self.config)
            self._sendResponse(request, response)

    def _sendResponse(self, request, response, status=200):
        request.setResponseCode(status)

        if self.encoding is not None:
            mimeType = 'text/xml; charset="%s"' % self.encoding
        else:
            mimeType = "text/xml"
        request.setHeader("Content-type", mimeType)
        request.setHeader("Content-length", str(len(response)))
        request.write(response)
        request.finish()

class TwistedSOAPServer(object):
    """Class that implements a Sciflo SOAP Server using the twisted framework."""
    def __init__(self, addr=('localhost', 8000), RequestHandler=SOAPRequestHandler,
                 log=0, encoding='UTF-8', config=Config, namespace=None,
                 ssl_context=None, certfile=None, keyfile=None, rootDir=None,
                 serveFiles=True):
        self.addr = addr
        self.requestHandler = RequestHandler
        self.log = log
        self.encoding = encoding
        self.config = config
        self.namespace = namespace
        self.ssl_context = ssl_context
        self.certfile = certfile
        self.keyfile = keyfile
        self.rootDir = rootDir
        self.serveFiles = serveFiles
        
        if self.log: twistedLog.startLogging(sys.stdout)
        self.publisher = ScifloSOAPPublisher(self.namespace, self.requestHandler,
                                             self.config)
        
    def registerFunction(self, function, namespace='', funcName=None, path=''):
        """Register function."""
        self.publisher.registerFunction(function, namespace, funcName, path)
    
    def handle_request(self):
        """Start reactor."""
        
        #serve static files from root directory
        if self.serveFiles:
            if self.rootDir: root = static.File(self.rootDir)
            else: root = static.File('.')
            root.isLeaf = False
            
            #update mime types
            root.contentTypes.update({
                '.svg': 'image/svg+xml',
                })
            
            #add soap resource
            root.putChild('wsdl', self.publisher)
            root.putChild('', self.publisher)
        
        #no static file serving
        else: root = self.publisher
        
        #create site
        site = server.Site(root)
        
        #start ssl or non ssl
        if self.ssl_context:
            #SOAPpy's WSDL.Proxy() hangs when accessing twisted SOAP server
            #running over SSL because it's using urlopen from urllib instead
            #of urllib2.  To use twisted over ssl, pass in urllib2 file handle
            #to WSDL.Proxy():
            #import urllib2
            #from SOAPpy import WSDL
            #u = urllib2.urlopen('https://localhost:8888/wsdl?foobar')
            #p = WSDL.Proxy(u)
            reactor.listenSSL(self.addr[1], site,
                contextFactory=ssl.DefaultOpenSSLContextFactory(self.keyfile, self.certfile))
        else:
            reactor.listenTCP(self.addr[1], site)
        reactor.run(installSignalHandlers=0)
        
    def server_close(self): pass
    
class SoapServerError(Exception):
	"""Exception class for SoapServer class."""
	pass

class SoapServer(object):
    """Class that implements a Sciflo SOAP Server."""

    def __init__(self, addr=('0.0.0.0', 8888), sslCertFile=None, sslKeyFile=None, log=1,
                 returnFaultInfo=1, debug=0, rootDir=None, serveFiles=True, proxyUrl=None,
                 threading=True, executeDir=None):
        """Constructor."""

        #set attributes
        self._addr = addr
        self._interface = self._addr[0]
        self._port = self._addr[1]
        self._sslCertFile = sslCertFile
        self._sslKeyFile = sslKeyFile
        self._log = log
        self._serveFiles = serveFiles
        self._proxyUrl = proxyUrl

        #get base url
        if self._proxyUrl:
            baseUrl = self._proxyUrl
        else:
            fqdn = getfqdn()
            if self._sslCertFile and self._sslKeyFile and os.path.isfile(self._sslCertFile) \
                and os.path.isfile(self._sslKeyFile):
                baseUrl =  getBaseUrl('SSL', fqdn, self._port)
            else: baseUrl = getBaseUrl('HTTP', fqdn, self._port)

        #validate root dir if defined
        if rootDir:
            if not validateDirectory(rootDir):
                raise SoapServerError("Cannot validate root directory: %s." % rootDir)
            self._rootDir = os.path.abspath(rootDir)
        else: self._rootDir = rootDir

        #global root dir
        globalRootDir = self._rootDir
        
        #validate execute dir if defined
        if executeDir:
            if not validateDirectory(executeDir):
                raise SoapServerError("Cannot validate execute directory: %s." % executeDir)
            self._executeDir = os.path.abspath(executeDir)
            os.chdir(self._executeDir)
        else: self._executeDir = executeDir

        #global serve files var
        globalServeFiles = self._serveFiles

        class ScifloRequestHandlerBase(SimpleHTTPRequestHandler):
            """Class that implements a do_GET() method."""

            def do_GET(self):

                #print 'command        ', self.command
                #print 'path           ', self.path
                #print 'request_version', self.request_version
                #print 'headers'
                #print '   type    ', self.headers.type
                #print '   maintype', self.headers.maintype
                #print '   subtype ', self.headers.subtype
                #print '   params  ', self.headers.plist

                #get path
                path = self.path

                #provide wsdl
                if path.startswith('/wsdl?') or globalServeFiles is False:
                    wsdlFunc = wsdlNamespace = None
                    match = re.search(r'/wsdl\?(.+)$',path)
                    if match: wsdlNamespace = match.group(1)
                    #print self.server.funcmap
                    #print self.server.objmap
                    if wsdlNamespace in self.server.funcmap \
                            and 'wsdl' in self.server.funcmap[wsdlNamespace]:
                        wsdlFunc = self.server.funcmap[wsdlNamespace]['wsdl']

                    if wsdlFunc:
                        self.send_response(200)
                        self.send_header("Content-type", 'text/xml')
                        self.end_headers()
                        response = wsdlFunc(*())
                        self.wfile.write(str(response))
                        return

                    #get list of all available wsdl namespaces
                    allNs = list(self.server.funcmap.keys())
                    wsdlListStr = ''
                    for thisNs in allNs:
                        wsdlListStr += '''<li><a href="wsdl?%s">%s</a></li>\n''' % (thisNs, os.path.basename(thisNs))

                    # return error
                    self.send_response(200)
                    self.send_header("Content-type", 'text/html')
                    self.end_headers()
                    self.wfile.write('''\
        <head>
        <title>Error!</title>
        </head>

        <body>
        <h1>Error accessing SOAP services!</h1>

        <p>
          This server supports HTTP GET requests for the purpose of
          obtaining Web Services Description Language (WSDL) for a specific
          service or for retrieving files.<br><br>

          Either you requested a URL that doesn't conform to the following
          format:<br><br>
          %s/wsdl?{namespace}<br><br>
          e.g. %s/wsdl?http://sciflo.jpl.nasa.gov/2006v1/sf/GenericServices
          <br><br>
          or this
          server does not implement a wsdl method.
        </p>

        <p>
          The following links are the WSDL files to the services available through this server:
        </p>

        <ul>%s</ul>

        </body>''' % (baseUrl, baseUrl, wsdlListStr))
                    return

                #otherwise pass it on to the SimpleHTTPRequestHandler
                else:

                    #save cwd
                    try: savedCwd = os.getcwd()
                    except: savedCwd = None

                    #chdir to rootDir if set
                    if globalRootDir: os.chdir(globalRootDir)

                    SimpleHTTPRequestHandler.do_GET(self)

                    #return to original dir
                    if globalRootDir and savedCwd: os.chdir(savedCwd)

                    return

            def guess_type(self, path):
                """Guess the type of a file.

                Argument is a PATH (a filename).

                Return value is a string of the form type/subtype,
                usable for a MIME Content-type header.

                The default implementation looks the file's extension
                up in the table self.extensions_map, using application/octet-stream
                as a default; however it would be permissible (if
                slow) to look inside the data to make a better guess.

                """

                base, ext = posixpath.splitext(path)
                if ext in self.extensions_map: return self.extensions_map[ext]
                ext = ext.lower()
                if ext in self.extensions_map: return self.extensions_map[ext]
                else: return self.extensions_map['']

            extensions_map = mimetypes.types_map.copy()
            extensions_map.update({
                '': 'application/octet-stream', # Default
                '.py': 'text/plain',
                '.c': 'text/plain',
                '.h': 'text/plain',
                '.xml': 'text/xml',
                '.svg': 'image/svg+xml',
                })

        class ScifloRequestHandler(SOAPRequestHandler,ScifloRequestHandlerBase):
            """Request handler class to use for a non-GSI SOAP server."""

            def date_time_string(self, timestamp=None):
                """Return the current date and time formatted for a message header."""
                if timestamp is None:
                    timestamp = time.time()
                year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
                s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
                        self.weekdayname[wd],
                        day, self.monthname[month], year,
                        hh, mm, ss)
                return s

            def do_GET(self):

                #call our implementation of do_GET()
                return ScifloRequestHandlerBase.do_GET(self)

        #return SOAP Fault info?
        self._retFaultInfo = returnFaultInfo

        #turn on debugging?
        self._debug = debug

        #get config object and specify to return fault info
        self._config = SOAPConfig(returnFaultInfo=self._retFaultInfo,debug=self._debug)

        #verify ssl key/cert files
        self._ctx = None
        if self._sslCertFile and self._sslKeyFile and os.path.isfile(self._sslCertFile) \
        and os.path.isfile(self._sslKeyFile):

            #create SSL context
            self._ctx = SSL.Context()
            self._ctx.load_cert(self._sslCertFile,self._sslKeyFile)
        
        #get threading or forking soap server?
        self._threading = threading
        if self._threading is True: soapServer = ThreadingSOAPServer #from SOAPpy
        elif self._threading is False: soapServer = ForkingSOAPServer #our own
        elif self._threading is None: soapServer = TwistedSOAPServer
        else: raise SoapServerError("Illegal value for threading arg: %s" % self._threading)
        
        #use ssl
        if self._ctx:

            #set server type
            self._type = 'SSL'

            #create SSL SOAP server
            #if twisted, pass in cert/key files and root dir
            if self._threading is None:
                self._server = soapServer(self._addr, RequestHandler=ScifloRequestHandler, log=self._log,
                                          config=self._config, ssl_context=self._ctx, certfile=self._sslCertFile,
                                          keyfile=self._sslKeyFile, rootDir=self._rootDir, serveFiles=self._serveFiles)
            #otherwise pass in ssl_context
            else:
                self._server = soapServer(self._addr, RequestHandler=ScifloRequestHandler, log=self._log,
                                          config=self._config, ssl_context=self._ctx)
        else:

            #set server type
            self._type = 'HTTP'

            #create non-SSL SOAP server
            #if twisted, pass in root dir
            if self._threading is None:
                self._server = soapServer(self._addr, RequestHandler=ScifloRequestHandler, log=self._log,
                                          config=self._config, rootDir=self._rootDir, serveFiles=self._serveFiles)
            else:
                self._server = soapServer(self._addr, RequestHandler=ScifloRequestHandler, log=self._log,
                                          config=self._config)

        #get fqdn
        self._fqdn = getfqdn()

        #get fqdn soap port
        if self._proxyUrl: self._soapPortFqdn = self._proxyUrl
        else: self._soapPortFqdn = getBaseUrl(self._type,self._fqdn,self._port)

    def registerEndpoint(self,endpointFile,wsdlFile=None):
        """Register a SOAP endpoint xml configuration file with this SOAP server.
        If the optional wsdlFile argument is specified, a WSDL file will be written
        corresponding to that path.  Return wsdlFile path if it was specified,
        or the url to the wsdl.
        """

        #result
        result = 1

        #get soap endpoint object
        obj = SoapEndpoint(endpointFile,self._soapPortFqdn, self._rootDir)

        #get endpoint name
        endpointName = obj.getEndpointName()

        #get endpointNamespace
        endpointNamespace = obj.getEndpointNamespace()

        #write wsdl file and set path as result or
        #set url to wsdl as result
        if wsdlFile: result = obj.writeWsdlFile(wsdlFile)
        else: result = os.path.join(self._soapPortFqdn,'wsdl?%s' % endpointNamespace)

        #get list of SOAP method objects
        soapMethodObjList = obj.getSoapMethodObjectsList()

        #loop over SoapMethod objects
        for soapMethodObj in soapMethodObjList:

            #get exposed name
            exposedName = soapMethodObj.getExposedName()

            #get python function name
            pythonFunctionName = soapMethodObj.getPythonFunctionName()

            #get python function
            pythonFunction = soapMethodObj.getFunction()

            #register function
            self._server.registerFunction(pythonFunction,endpointNamespace,exposedName)

            #print to log
            if isinstance(pythonFunction, ScifloFunction):
                self.logMessage("Registered sciflo: %s as soap method %s",pythonFunctionName,exposedName)
            else:
                self.logMessage("Registered function: %s as soap method %s",pythonFunctionName,exposedName)

        #return result
        return result

    def serveForever(self):
        """Start up SOAP server and serve forever."""

        #print startup message
        if self._threading is True: threadingType = 'threading'
        elif self._threading is False: threadingType = 'forking'
        else: threadingType = 'twisted'
        if self._proxyUrl:
            self.logMessage("Started up %s %s SOAP server at %s:%s and proxying as %s." % (threadingType,
                self._type, self._interface, self._port, self._proxyUrl))
        else:
            self.logMessage("Started up %s %s SOAP server at %s:%s." % (threadingType, self._type,
                self._interface, self._port))

        #loop forever if TCPServer type
        if threadingType in ('threading', 'forking'):
            while 1: self.handleRequest()
        #handleRequest() starts loop for twisted
        else: self.handleRequest()

    def handleRequest(self):
        """Handle a single request."""

        try: self._server.handle_request()
        except KeyboardInterrupt:
                self.serverClose()
                raise SystemExit
        except SSL.SSLError:
            etb = traceback.format_exc()
            if 'unexpected eof' in etb: pass
            else: self.logMessage("Got SSLError: %s",etb)

    def serverClose(self):
        """Close server."""

        self.logMessage("Stopped %s SOAP server at %s:%s." % (self._type,
            self._interface, self._port))
        self._server.server_close()

    def logMessage(self, format, *args):
        """Write to message log."""
        if self._threading is None and self._log:
            sys.stderr.write("%s\n" % format % args)
        else:
            sys.stderr.write("%s - - [%s] %s\n" % (getuser(),getDateTimeLogString(),format % args))
