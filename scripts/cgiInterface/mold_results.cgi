#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        mold_results.cgi
# Purpose:     Mold results.
#
# Author:      Gerald Manipon
#
# Created:     Wed Mar 28 07:56:00 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, sys, cgi, shutil, types, re
#import cgitb; cgitb.enable()
from tempfile import mkdtemp

import sciflo
from sciflo.grid.executor import PICKLE_FIELDS
from sciflo.utils.sajax1 import (form, sajax_init, sajax_export, sajax_handle_client_request,
sajax_show_javascript)
from sciflo.utils import UrlBaseTracker, getHtmlBaseHref

#base hrefs
HTML_BASE_HREF = getHtmlBaseHref()
DATA_BASE_HREF = HTML_BASE_HREF.replace('/web/', '/data/')

#file limit
fileLimit = 30

#config file
configFile = None

#SCIFLOID regex
SCIFLOID_RE = re.compile(r'^scifloid')

def queryMethod(json, keys):
    """Return query results."""
    if isinstance(keys, (types.ListType, types.TupleType)):
        return [json[k] for k in keys]
    elif isinstance(keys, types.StringTypes): return json[keys]
    else: raise RuntimeError("Unknown type: %s" % type(keys))

DATA_MATCH = re.compile(r'^(.*/data)(/.*)$')

def urlize(fileList):
    """Return HTTP accessible url of files."""

    urlList = []
    for file in fileList:
        if os.path.exists(file):
            dataMatch = DATA_MATCH.search(file)
            if dataMatch:
                ubt = UrlBaseTracker(dataMatch.group(1), DATA_BASE_HREF)
                file = ubt.getUrl(file)
        urlList.append(file)
    return urlList
            
def sendBundle(wuidStr):
    """Get results from wuid, bundle, and send."""

    #split wuid and result index
    (wuid, resultIdx) = wuidStr.split('-result-')
    if SCIFLOID_RE.search(wuid): jsonPath = '/%s/sciflo.json' % wuid
    else: jsonPath = '/%s/workunit.json' % wuid
    jsonUrl = sciflo.utils.ScifloConfigParser().getParameter('baseUrl') + jsonPath
    json = sciflo.grid.utils.loadJson(jsonUrl, unpickleKeys=PICKLE_FIELDS)
    resultIdx = int(resultIdx)
    
    #get result
    result = queryMethod(json, 'result')
    if resultIdx > 0: result = result[resultIdx]
    
    #create bundle, read in, cleanup, and send
    tempDir = mkdtemp()
    bundleFile = os.path.join(tempDir, 'bundle.tgz')
    result = [i for i in result if i is not None]
    if len(result) > fileLimit:
        message = "Exceeded %d file limit.  Download manually by running the following script:\n\n#!/bin/sh\n" % fileLimit
        message += "\n".join(["wget %s" % i for i in urlize(result)])
        sys.stdout.write('Content-type: text/plain\n' + \
                         'Content-length: %s\n\n' % len(message) + \
                         message)
    else:
        sciflo.utils.bundleFiles(result, bundleFile)
        bundleBits = open(bundleFile, 'rb').read()
        shutil.rmtree(tempDir)
        sys.stdout.write('Content-type: application/x-gzip\n' + \
                         'Content-length: %s\n' % len(bundleBits) + \
                         'Content-disposition: inline; filename=bundle.tgz\n\n' + \
                         bundleBits)
    
actionDict = {
    'bundle': sendBundle,
}

if __name__ == '__main__':
    form = cgi.FieldStorage()
    
    #get wuid
    if not form.has_key('wuid'): raise RuntimeError, "No work unit id specified."
    wuid = form.getfirst('wuid')
    
    #get action
    if not form.has_key('action'): raise RuntimeError, "No action specified."
    action = form.getfirst('action')
    
    #perform action
    actionDict[action](wuid)
