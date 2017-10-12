#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        exposer.py
# Purpose:     Expose services via soap server.
#
# Author:      Gerald Manipon
#
# Created:     Tue Apr 25 13:01:20 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys
from tempfile import mkstemp, mkdtemp
from socket import getfqdn
from signal import SIGTERM
import glob
import getopt

from sciflo.utils import ScifloConfigParser
from sciflo.webservices import *

def usage():
    """Print usage info."""

    print """%s [-p|--port <port number>] [-x|--xmlDir <endpoint xml directory>] [-w|--wsdlDir <wsdl directory>] \
[-a|--addPath <module search path>] [-s|--serveDir <directory>] [-d|--debug] [-t|--type <threading|forking|twisted>] \
[-e|--executeDir <execution directory>] [-h|--help]""" % sys.argv[0]

def main():

    #get opts
    try:
        opts,args = getopt.getopt(sys.argv[1:], "p:x:w:a:dt:e:h",
                                  ["port=", "xmlDir=", "wsdlDir=",
                                   "addPath=", "serveDir=", "debug", "type=",
                                   "executeDir=", "help"])

    except getopt.GetoptError:
        usage()
        sys.exit(2)

    #print "opts:",opts
    #print "args:",args

    #set default values
    port = 8888
    xmlDirs = []
    wsdlDir = None
    addPaths = []
    debugFlag = 0
    serveFiles = False
    rootDir = None
    threading = True
    executeDir = None

    #flags to prevent multiple specifications of certain options
    portSet = 0
    wsdlDirSet = 0
    serveDirSet = 0
    typeSet = 0
    executeDirSet = 0

    #process opts
    for o,a in opts:

        #check if help
        if o in ("-h","--help"):
            usage()
            sys.exit()

        #check if debug
        if o in ("-d","--debug"): debugFlag = 1

        #check if port
        if o in ("-p","--port"):
            if portSet:
                print "Multiple -p|--port specifications found.  Only specify one port."
                usage()
                sys.exit(2)
            else:
                port = int(a)
                portSet = 1
                
        #check type
        if o in ("-t","--type"):
            if typeSet:
                print "Multiple -t|--type specifications found.  Only specify one type."
                usage()
                sys.exit(2)
            else:
                if a not in ('threading', 'forking', 'twisted'):
                    print "Invalid server type: %s." % a
                    usage()
                    sys.exit(2)
                if a == 'threading': threading = True
                elif a == 'forking': threading = False
                else: threading = None
                typeSet = 1
                
        #check xml directory
        if o in ("-x","--xmlDir"): xmlDirs.append(a)

        #check wsdl directory
        if o in ("-w","--wsdlDir"):
            if wsdlDirSet:
                print "Multiple -w|--wsdlDir specifications found.  Only specify one wsdl output directory."
                usage()
                sys.exit(2)
            else:
                wsdlDir = a
                wsdlDirSet = 1

        #check if add search path
        if o in ("-a","--addPath"): addPaths.append(a)

        #check if serving files
        if o in ("-s","--serveDir"):
            if serveDirSet:
                print "Multiple -s|--serveDir specifications found.  Only specify one root directory to serve."
                usage()
                sys.exit(2)
            else:
                serveFiles = True
                rootDir = a
                serveDirSet = True
        
        #check if chdir to execute directory
        if o in ("-e","--executeDir"):
            if executeDirSet:
                print "Multiple -e|--executeDir specifications found.  Only specify one root directory to execute in."
                usage()
                sys.exit(2)
            else:
                executeDir = a
                executeDirSet = True

    #extend sys.path var to include directories to look for webservices
    if addPaths: sys.path.extend(addPaths)

    #fqdn
    fqdn = getfqdn()

    #get exposerProxyUrl
    exposerProxyUrl = ScifloConfigParser().getParameter('exposerProxyUrl')
    if not exposerProxyUrl: exposerProxyUrl = None

    #instantiate forking soap server
    server = SoapServer(('0.0.0.0',port), debug=debugFlag, rootDir=rootDir, serveFiles=serveFiles,
                        proxyUrl=exposerProxyUrl, threading=threading, executeDir=executeDir)

    #xml endpoint file list
    xmlFiles = []

    #get xml endpoints from xml directories
    for xmlDir in xmlDirs: xmlFiles.extend(glob.glob('%s/*.xml' % xmlDir))

    #loop over wsdlFiles
    for xmlFile in xmlFiles:

        #wsdl file
        basename,ext = os.path.splitext(os.path.basename(xmlFile))

        #if wsdlDir was set, build path to wsdl file
        wsdlFile = None
        if wsdlDir: wsdlFile = os.path.join(wsdlDir, basename+'.wsdl')

        #register an endpoint and create wsdl file if set
        wsdlFile = server.registerEndpoint(xmlFile, wsdlFile)

    #serve
    server.serveForever()

if __name__ == '__main__': main()
