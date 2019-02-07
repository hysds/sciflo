#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        sflExec.py
# Purpose:     Execute sciflo.
#
# Author:      Gerald Manipon
#
# Created:     Fri Apr 21 18:42:34 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys
import getopt
import types
import pwd
import lxml.etree
import shutil
import curses
import traceback
from io import StringIO
from tempfile import mktemp
import lxml.etree
import _curses
from getpass import getuser

import sciflo

def usage():
    """Print usage info."""

    print(("""%s [-c|--configFile <config file>] [-i|--init] [-o|--outputDir <output dir>]\
[-s|--status] [-f|--force] [-d|--debug] [--nocache] [-t|--timeout <seconds>]\
[-a|--args <input1=val1,input2=val2,...>] [-v|--verbose] [-h|--help] <sciflo doc>""" % sys.argv[0]))

def main():

    #get opts
    try:
        opts,args = getopt.getopt(sys.argv[1:],"c:o:sdhifva:t:",
                                ["configFile=","outputDir=","status","debug","help",
                                 "init","force","verbose","nocache","args=",
                                 "timeout="])

    except getopt.GetoptError:
        usage()
        sys.exit(2)

    #set defaults
    configFile = None
    outputDir = None
    showStatus = False
    debug = False
    doInit = False
    force = False
    verbose = False
    nocache = False
    argsMod = None
    timeout = None

    #flags to prevent multiple specifications of options
    configFileSet = False
    outputDirSet = False
    argsSet = False
    timeoutSet = False

    #process opts
    for o,a in opts:

        #check if help
        if o in ("-h","--help"):
            usage()
            sys.exit()

        #check if show status
        if o in ("-s","--status"):
            showStatus = True

        #check if force removal
        if o in ("-f","--force"):
            force = True

        #check if debug
        if o in ("-d","--debug"):
            debug = True
            
        #check if nocache
        if o in ("--nocache"):
            nocache = True

        #check if do init
        if o in ("-i","--init"):
            doInit = True
            
        #check if verbose
        if o in ("-v","--verbose"):
            verbose = True

        #set config file
        if o in ("-c","--configFile"):
            if configFileSet:
                print("""Multiple -c|--configFile specifications found.\
  Only specify one config file.""")
                usage()
                sys.exit(2)
            else:
                configFile = os.path.abspath(a)
                assert(os.path.isfile(configFile) == True)
                configFileSet = True

        #set output dir
        if o in ("-o","--outputDir"):
            if outputDirSet:
                print("""Multiple -o|--outputDir specifications found.\
  Only specify one output dir.""")
                usage()
                sys.exit(2)
            else:
                origOutputDir = a
                outputDir = os.path.abspath(a)
                outputDirSet = True
                
        #set args
        if o in ("-a","--args"):
            if argsSet:
                print("""Multiple -a|--args specifications found.\
  Only specify one args option.""")
                usage()
                sys.exit(2)
            else:
                argsMod = a
                argsSet = True

        #set worker timeout
        if o in ("-t","--timeout"):
            if timeoutSet:
                print("""Multiple -t|--timeout specifications found.\
  Only specify one timeout option.""")
                usage()
                sys.exit(2)
            else:
                timeout = int(a)
                timeoutSet = True

    #if init, make sure nothing else was specified
    if doInit:
        if True in (showStatus, debug, outputDirSet, len(args) != 0):
            print("Cannot other options or sciflo doc with -i|--init option.")
            usage()
            sys.exit(2)
        userScifloConfig = sciflo.utils.getUserScifloConfig(configFile)
        print(("Your sciflo configuration directory has been initialized: %s" % \
            os.path.dirname(userScifloConfig)))
        sys.exit(0)

    #if showStatus, do debug mode since stderr and stdout won't be put to the screen
    #in local mode (cannot capture stderr/stdout) of forked work units
    #if showStatus: debug = True

    #make arg was specified
    if len(args) != 1:
        print("Please specify one sciflo document.")
        usage()
        sys.exit(2)

    #make sure output dir was specified and doesn't exist
    if outputDir is None:
        print("Please specify output directory.")
        usage()
        sys.exit(2)
    if os.path.isdir(outputDir):
        if force: shutil.rmtree(outputDir)
        else:
            print("Output dir already exists.  Please remove or specify -f|--force.")
            usage()
            sys.exit(2)

    #sciflo doc
    doc = args[0]
    f = open(doc,'r')
    xml = f.read()
    f.close()
    
    #modify global args
    argsDict = {}
    if argsMod is not None:
        argsList = argsMod.split(',')
        for argsItem in argsList:
            key, val = argsItem.split('=')
            argsDict[key] = val
    
    #get results and ScifloManager
    #(results, m) = sciflo.grid.sflExec(getuser(), xml, argsDict, outDir=outputDir,
    #                                   scifloid=None, config=configFile,
    #                                   localExecutionMode=True, debug=debug,
    #                                   showStatus=showStatus, verbose=verbose,
    #                                   returnScifloManager=True, noLookCache=nocache)
    results = sciflo.grid.executor.runSciflo(xml, argsDict, timeout=timeout,
                                             outputDir=outputDir, configDict={'isLocal': True})
    '''
    #get url base tracker
    ubtObj = m._urlBaseTrackerObj
    
    #results
    resultsStrList = []

    #get execution log
    resultsStrList.append("Execution log at: %s" % m.accumulatedExecutionLogFile)

    #sciflo doc with results
    relFinalSflFile = m.annotatedScifloXmlFile
    finalSflFile = os.path.join(outputDir, os.path.basename(doc))
    os.symlink(relFinalSflFile, finalSflFile)
    resultsStrList.append("Final sciflo doc (with results) at: %s" % finalSflFile)
    if isinstance(results,Exception): resultsStrList.append(str(results))
    return (results, resultsStrList)
    '''
    return (results, "Done.")

def restoreScreen():
    """Function to restore screen."""
    curses.nocbreak(); curses.echo(); curses.endwin()

if __name__ == '__main__':
    tracebackStrIO = StringIO()
    results = Exception("Preset exception.")
    resStrList = None
    try:
        results, resStrList = main()
    finally:
        try:
            restoreScreen()
        except: pass
        if sys.exc_info()[0] is not None and sys.exc_info()[0] != _curses.error:
            traceback.print_exc(file = tracebackStrIO)
            print((tracebackStrIO.getvalue()))
    #if resStrList: print '\n'.join(resStrList)
    print(("Results:", results))
    if isinstance(results, Exception): sys.exit(1)
    sys.exit(0)
