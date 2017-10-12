#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        soap.cgi
# Purpose:     CGI script to expose SOAP services.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jul 27 13:43:24 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys
import cgi
import cgitb; cgitb.enable()
from SOAPpy import *
import re
import traceback
import sciflo
from sciflo.utils import ScifloConfigParser
from sciflo.webservices import resolveSoapFunction
from inspect import getargspec
from lxml.etree import Element, SubElement, tostring

XML_CONFIG_DIR = os.path.join(sys.prefix,'etc','soap')
sys.path.append(os.path.join(sys.prefix,'scripts','soap'))

def resolveFunction(ns, function):
    """Resolve function."""

    files = os.listdir(XML_CONFIG_DIR)
    func = None
    for i in files:
        try: elt,nsDict = sciflo.utils.getXmlEtree(os.path.join(XML_CONFIG_DIR,i))
        except: continue
        endpointName = elt.xpath('_default:endpointName',namespaces=nsDict)[0]
        if endpointName.text == os.path.basename(ns):
            sm = elt.xpath(".//_default:soapMethod[_default:exposedName = '%s']" % function, namespaces=nsDict)[0]
            pf = sm.getchildren()[1].text
            #resolve
            try: (func, pyFuncStr, args) = resolveSoapFunction(function, pf)
            except: continue
            break
    if func: return func
    else: raise RuntimeError, "Method not found."

def parseSOAPRequest(reqStr):
    """Parse SOAP request."""
    (r, header, body, attrs) = parseSOAPRPC(reqStr, header=1, body=1, attrs=1)
    method = r._name
    args = r._aslist()
    kw = r._asdict()
    ns = r._ns

    #get ordered and named args
    ordered_args = {}
    named_args = {}
    for (k,v) in kw.items():
        if k[0]=="v":
            try:
                i = int(k[1:])
                ordered_args[i] = v
            except ValueError:
                named_args[str(k)] = v
        else:
            named_args[str(k)] = v
    keylist = ordered_args.keys()
    keylist.sort()
    tmp = map(lambda x: ordered_args[x], keylist)
    ordered_args = tmp

    return (ns, method, ordered_args, named_args)

def runSOAPFunction(ns, method, args, kw):
    """Run function and return xml response."""

    # For fault messages
    if ns: nsmethod = "%s:%s" % (ns, method)
    else: nsmethod = method

    #run
    try:
        f = resolveFunction(ns, method)
        fr = apply(f, args, kw)
        if isinstance(fr, voidType):
            resp = buildSOAP(kw = {'%sResponse' % method: fr})
        else:
            resp = buildSOAP(kw = {'%sResponse' % method: {'Result': fr}})
    except:
        info = sys.exc_info()
        resp = buildSOAP(faultType("%s:Client" % NS.ENV_T,
            "Exception encountered",
            "%s : %s %s %s" % (nsmethod, info[0], info[1],
            traceback.format_exc())))
    return resp

def getWSDLDirectory():
    """Return directory of WSDL url's as xml."""

    files = os.listdir(XML_CONFIG_DIR)
    func = None
    retHtml = '''<?xml version="1.0"?>
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
    <head>
    <title>WSDL Directory</title>
    </head>
    <body><h1>WSDL Directory</h1><div id="wsdlDir"><ul>
    '''
    for i in files:
        try: elt,nsDict = sciflo.utils.getXmlEtree(os.path.join(XML_CONFIG_DIR,i))
        except: continue
        endpointName = elt.xpath('_default:endpointName',namespaces=nsDict)[0].text
        endpointNamespace = os.path.join(sciflo.utils.SCIFLO_NAMESPACE, endpointName)
        retHtml += '''<li><a href="?wsdl=%s">%s</a><br/></li>\n''' % (endpointNamespace, endpointName)
    retHtml += '</ul></body></html>'
    return retHtml

def getWSDL(ns):
    """Return WSDL xml."""

    files = os.listdir(XML_CONFIG_DIR)
    endpointName = None
    endpointNamespace = None
    methodInfoList = []
    for i in files:
        try: elt,nsDict = sciflo.utils.getXmlEtree(os.path.join(XML_CONFIG_DIR,i))
        except: continue
        tmpEndpointName = elt.xpath('_default:endpointName',namespaces=nsDict)[0].text
        tmpEndpointNamespace = os.path.join(sciflo.utils.SCIFLO_NAMESPACE, tmpEndpointName)
        if tmpEndpointNamespace == ns:
            endpointName = tmpEndpointName
            endpointNamespace = tmpEndpointNamespace
            smElts = elt.xpath(".//_default:soapMethod", namespaces=nsDict)
            for smElt in smElts:
                exposedName = smElt.xpath("_default:exposedName", namespaces=nsDict)[0].text
                pyFuncStr = smElt.xpath("_default:pythonFunction", namespaces=nsDict)[0].text
                
                #resolve
                try: (func, pyFuncStr, args) = resolveSoapFunction(exposedName, pyFuncStr)
                except: continue
                methodInfoList.append((exposedName, pyFuncStr, args))
            break
    if endpointName is None: raise RuntimeError, "Method not found."
    else: return getWSDLString(endpointName, endpointNamespace, methodInfoList,
                               os.environ['SERVER_NAME'], os.environ['SERVER_PORT'],
                               os.environ['SCRIPT_NAME'], os.environ.get('SSL_PROTOCOL',None))

def getWSDLString(endpointName, endpointNamespace, methodInfoList, serverName,
                  serverPort, scriptName, sslProtocol):
    """Generate WSDL string."""

    #root element
    root = Element('definitions',{'name':endpointName,
                   'targetNamespace':endpointNamespace,
                   'xmlns:tns':endpointNamespace,
                   'xmlns:xs':"http://www.w3.org/2001/XMLSchema",
                   'xmlns:soap':"http://schemas.xmlsoap.org/wsdl/soap/",
                   'xmlns':"http://schemas.xmlsoap.org/wsdl/"})

    #create portType
    portType = Element('portType',{'name':endpointName+'PortType'})

    #create binding
    binding = Element('binding',{'name':endpointName+'Binding',
                                 'type':'tns:'+endpointName+'PortType'})
    SubElement(binding,'soap:binding',{'style':"rpc",
                                       'transport':"http://schemas.xmlsoap.org/soap/http"})

    #create service
    service = Element('service',{'name':endpointName})
    documentation = SubElement(service,'documentation')
    documentation.text = "SOAP methods for %s." % endpointName
    port = SubElement(service,'port',{'name':endpointName+'Port',
                                      'binding':'tns:'+endpointName+'Binding'})
    if sslProtocol:
        location = 'https://%s:%s%s' % (serverName, serverPort, scriptName)
    else:
        location = 'http://%s:%s%s' % (serverName, serverPort, scriptName)
    #use cgiBaseHref if defined
    cgiBaseHref = ScifloConfigParser().getParameter('cgiBaseHref')
    if cgiBaseHref: location = os.path.join(cgiBaseHref, os.path.basename(scriptName))
    soapAddress = SubElement(port,'soap:address',{'location':location})

    #loop over functions and add message, portType, binding elements
    for exposedName, funcStr, args in methodInfoList:

        #message request
        messageRequest = Element('message',{'name':exposedName+'Request'})
        root.append(messageRequest)
        if args is None or len(args) == 0: pass
        else:
            for arg in args:
                part = SubElement(messageRequest,'part',{'name':arg,'type':'xs:string'})

        #message response
        messageResponse = Element('message',{'name':exposedName+'Response'})
        root.append(messageResponse)
        messageResponsePart = SubElement(messageResponse,'part',{'name':'Result',
                                                                 'type':'xs:string'})

        #operation element in porttype
        operation=Element('operation',{'name':exposedName})
        portType.append(operation)
        input=SubElement(operation,'input',{'message':'tns:'+exposedName+'Request'})
        output=SubElement(operation,'output',{'message':'tns:'+exposedName+'Response'})

        #operation element in binding
        commonHash = {'use':'encoded',
                      'namespace':endpointNamespace,
                      'encodingStyle':'http://schemas.xmlsoap.org/soap/encoding/'}
        operationInBinding = Element('operation',{'name':exposedName})
        binding.append(operationInBinding)
        soapOperation = SubElement(operationInBinding,'soap:operation',{'soapAction':""})
        input2 = SubElement(operationInBinding,'input',{'name':exposedName+'Request'})
        soapBody = SubElement(input2,'soap:body',commonHash)
        output2 = SubElement(operationInBinding,'output',{'name':exposedName+'Response'})
        soapBody2 = SubElement(output2,'soap:body',commonHash)

    #append elements to root
    root.append(portType)
    root.append(binding)
    root.append(service)

    #get string
    wsdlString = tostring(root)

    #return
    return wsdlString

def writeResponse(resp, contentType = 'text/xml'):
    """Write response."""

    resp = resp.strip()
    print 'Content-type: %s' % contentType
    print 'Content-length: %s\n' % len(resp)
    print resp

if __name__ == '__main__':

    #parse request
    data = sys.stdin.read().strip()

    if data.startswith('<?xml') and re.search(r'SOAP-ENV', data, re.IGNORECASE):
        (ns, method, args, kw) = parseSOAPRequest(data)

        #run function
        resp = runSOAPFunction(ns, method, args, kw)

        #write response
        writeResponse(resp)
    else:
        #cgi.test()
        plist = map(lambda x: x.strip(), data.split(';'))
        form = cgi.FieldStorage()
        wsdlNs = form.getfirst('wsdl',None)
        if wsdlNs: writeResponse(getWSDL(wsdlNs))
        else: writeResponse(getWSDLDirectory(),'text/html')
