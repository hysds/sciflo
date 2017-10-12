#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        rest.py
# Purpose:     CGI script to call a SOAP service via a REST URL.
#
# Author:      Brian Wilson
#
# Created:     Fri May 19 16:01:06 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
#

USAGE = """
Call an arbitrary SOAP service (method) via a REST URL.

For example:
rest.py?_service=EOSServices&_method=geoRegionQuery&
datasetName=AIRS&level=L2&version=None&
startDateTime=2003-01-01T00:00:00&endDateTime=2003-01-02T00:00:00&
latMin=-90.&latMax=90.&lonMin=-180.&lonMax=180.&
responseGroups=Medium

Parameters:
  _service: names the WSDL file (interface to services bundle)
  _method:  name the service or method you want to invoke

The remainder of the arguments are the arguments for the service itself.
They must all be present with some value.

"""

import sys, os, socket
import cgi
#import cgitb
#cgitb.enable()
#cgitb.enable(display=0, logdir='/tmp/')
from SOAPpy import WSDL
from sciflo.utils import ScifloConfigParser

Debug = False

#PathToWsdlFiles = "/home/www/sciflo/services/wsdl"
PathToWsdlFiles = "http://%s:%s/wsdl?http://sciflo.jpl.nasa.gov/2006v1/sf" % \
    (socket.getfqdn(), ScifloConfigParser().getParameter('exposerPort'))

def floatOrQuote(s):
    try:
        v = float(s)
        return s
    except:
        if s is None or s == 'None':
            return 'None'
        else:
	    return "'%s'" % s

def quoteArg(s):
    if s is None or s == 'None':
        return 'None'
    else:
        return "'%s'" % s


def call():
    errMsgs = []
    try:
        if Debug:
            form = dict(_service='EOSServices', _method='geoRegionQuery', 
                        datasetName='AIRS', level='L2', version='None',
                        startDateTime='2003-01-01T00:00:00', endDateTime='2003-01-01T01:00:00',
                        latMin='-90.', latMax='90.', lonMin='-180.', lonMax='180.',
                        responseGroups='Medium')
            node = form.get('_node', None)
            service = form.get('_service', None)
            method = form.get('_method', None)
        else:
            form = cgi.FieldStorage()
	    node = form.getfirst('_node', None)
            service = form.getfirst('_service', None)
            method = form.getfirst('_method', None)

        if not service or not method:
            raise Exception('Bad SOAP call: Must specify _service and _method in query: ' + \
                    'e.g., rest.py?_service=EOSServices&_method=geoRegionQuery')

#        wsdl = os.path.join(PathToWsdlFiles, service + '.wsdl')
#        if not os.path.exists(wsdl):
#            raise 'Cannot find WSDL file for a %s service.  Is service name correct?' % service
        wsdl = os.path.join(PathToWsdlFiles, service)

        proxy = WSDL.Proxy(wsdl)
        if not hasattr(proxy, method):
            raise Exception('Services bundle %s does not have %s method' % (service, method))
        params = proxy.methods[method].inparams   # get list of input args in method order

        if Debug:
            args = [floatOrQuote(form.get(param.name, None)) for param in params]
#            args = [quoteArg(form.get(param.name, None)) for param in params]
        else:
            args = [floatOrQuote(form.getfirst(param.name, None)) for param in params]

        call = 'proxy.%s(%s)' % (method, ', '.join(args))
        result = eval(call)
    except Exception, e:
        errMsgs.append(e.message)
        errorResponse(errMsgs, USAGE)
        
    print "Content-Type: text/xml"
    print
    print result


def errorResponse(msgs, usage):
    print "Content-Type: text/plain"
    print
    print usage, '\nError(s):\n', '\n'.join(msgs)
    sys.exit(0)


if __name__ == '__main__':
#    cgi.test()
#    cgi.print_environ()
#    cgi.print_form(form)
#    cgi.print_arguments()

    call()

"""
To modify or debug, first set Debug=True and make call() work.
Then set Debug=False and try a (quoted) query string on the command line.
Then finally install it in cgi-bin and try a REST URL in the browser.
Like:
http://sciflo.jpl.nasa.gov/sciflo/services/rest?
_service=EOSServices&_method=geoRegionQuery&datasetName=AIRS&level=L2&version=None&
startDateTime=2003-01-01T00:00:00&endDateTime=2003-01-01T01:00:00&
latMin=-90.&latMax=90.&lonMin=-180.&lonMax=180.&responseGroups=Medium

"""
