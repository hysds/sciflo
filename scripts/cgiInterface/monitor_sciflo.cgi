#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        monitor_sciflo.cgi
# Purpose:     Monitor the execution of a sciflo.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jul 27 10:56:00 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import cgi
#import cgitb; cgitb.enable()
from string import Template
import os
import sys
import datetime
import time
from xml.dom.minidom import parseString
from lxml.etree import XML
import re
import types
from UserList import UserList
import urllib
import traceback
from urlparse import urlparse, urljoin

import sciflo
from sciflo.utils.sajax1 import (form, sajax_init, sajax_export, sajax_handle_client_request,
sajax_show_javascript)
from sciflo.utils import (getListFromUnknownObject, getNamespacePrefixDict, escapeCharsForCDATA,
sanitizeHtml)
from sciflo.grid.executor import PICKLE_FIELDS, ScifloExecutorError
from sciflo.grid.funcs import CANCELLED_MESSAGE
from cgiUtils import *

CGI_URL_BASE = sciflo.utils.getCgiBaseHref()
HTML_URL_BASE = sciflo.utils.getHtmlBaseHref()
REL_URL = sciflo.utils.getRelativeUrl(CGI_URL_BASE, HTML_URL_BASE)

basicTemplate = form.getfirst('basicTemplate',None)
if basicTemplate is None: import pageTemplate
else: import basicPageTemplate as pageTemplate

JQUERY_URL = os.path.join(REL_URL, 'jquery-ui/js/jquery-1.9.0.js')
JQUERY_UI_URL = os.path.join(REL_URL, 'jquery-ui/js/jquery-ui-1.10.0.custom.js')
JQUERY_CSS_URL = os.path.join(REL_URL, 'jquery-ui/css/smoothness/jquery-ui-1.10.0.custom.css')
D3_URL = os.path.join(REL_URL, 'd3/d3.js')

#config file
configFile = None

#templates
spacesStr = '&nbsp;' * 3

formDataTpl = Template('''
<b>$field</b>:$spaces<font color="blue">$value</font><br/>
<b>type</b>:$spaces<font color="green">$tp</font><br/>''')

monitorScifloTpl = Template('''
<form name="monitorSciflo" method="POST">
<span>Please enter a valid scifloid:$spaces</span>
<span><input name="wuid" type="text" size="72"/></span>
<span><input type="submit" name="Monitor" value="Monitor" /></span>
</span>
</form>
''')

inputsTableTpl = Template('''
<h1><font color="blue">$scifloName</font></h1>
<pre>$scifloDesc</pre><br/>
<div id="scifloInputs">
    <table id="inputsTable">
        <caption>Sciflo Inputs</caption>
        <thead>
            <tr>
                <td id="inputTag">tag</td>
                <td id="inputVal">value</td>
            </tr>
        </thead>
        <tbody>
        $tbodyContent
        </tbody>
    </table>
</div>''')

inputsTableRowTpl = Template('''
        <tr>
            <td id="inputTag">$tag</td>
            <td id="inputVal">$value</td>
        </tr>''')

outputsTableTpl = Template('''
<div id="scifloOutputs">
    <table id="outputsTable">
        <caption>Sciflo Outputs</caption>
        <thead>
            <tr>
                <td id="outputTag">tag</td>
                <td id="outputVal">value</td>
            </tr>
        </thead>
        <tbody>
        $tbodyContent
        </tbody>
    </table>
</div>
<br/>
<div id="annotatedSciflo"><b>Annotated SciFlo:</b>
<a href="$annotatedSciflo" target="_blank">xml</a></div>''')

outputsTableRowTpl = Template('''
        <tr>
            <td id="outputTag">$tag</td>
            <td id="outputVal">$value</td>
        </tr>''')

statusTableTpl = Template('''
<div id="refreshSection">
    <div id="scifloStatus" json="$json" status="$scifloStatus">
    <b>Status of this sciflo is:
    <font style="background-color: $scifloStatusColor">$scifloStatus</font></b>
    </div>
    <br/>
    <!--<b>Refresh time: <div id="refreshTime">$refreshTime</div></b>
    <br/>-->
    <table id="statusTable">
        <caption>Work Unit Monitoring</caption>
        <thead>
            <tr>
                <td id="index">index</td>
                <td id="procId">procId</td>
                <td id="type">type</td>
                <td id="deps">dependencies</td>
                <td id="status">status</td>
                <td id="executionTime">execution time (secs)</td>
                <td id="results">results</td>
            </tr>
        </thead>
        <tbody>
        $tbodyContent
        </tbody>
    </table>
    <div id="colorLegend">$colorLegend</div>
    <br/>
    $cancelSciflo
    <b>Execution time (secs): <div id="executeTime">$executeTime</div></b>
    $execLog
</div>''')

statusRowTpl = Template('''
        <tr>
            <td id="index">$index</td>
            <td id="procId">$procId</td>
            <td id="type">$type</td>
            <td id="deps">$dependencies</td>
            <td id="status" bgcolor="$colorStatus">
                <a href="$executionLog" target="_blank">$wuidStatus</a>
            </td>
            <td id="executionTime">$executionTime</td>
            <td id="results">$resultLnk</td>
        </tr>''')

#status color
statusColorDict = {'waiting': '#FFA000',
                   'ready': '#FFFF00',
                   'staging': '#CCFF00',
                   'working': '#00FF00',
                   'done': '#00CCFF',
                   'exception': '#CC0000',
                   'cancelled': '#990099',
                   'paused': '#CCCC66',
                   'finalizing': '#339966',
                   'cached': '#99FFFF'
                   }

#results section
resultsSectionTpl = Template('''
<div id="resultsSection">
    $resultsContent
</div>''')

#execution log
executionLogLinkTpl = Template('''
<br/><b>Execution log:</b> <a href="$logStr" target="_blank">log</a>''')

def queryMethod(json, keys):
    """Return query results."""
    if isinstance(keys, (types.ListType, types.TupleType)):
        return [json[k] for k in keys]
    elif isinstance(keys, types.StringTypes): return json[keys]
    else: raise RuntimeError("Unknown type: %s" % type(keys))
    
def refresh(jsonUrl):
    """Backend for ajax refresh() call.  Return current status table html
    string."""

    try: return getStatusTable(jsonUrl)
    except: return ''

def printResults(jsonUrl, status):
    """Backend for ajax printResults() call.  Return results section as
    a string."""

    return getResultsSection(jsonUrl, status)

def getResultsSection(jsonUrl, status):
    """Return html string of results section."""

    #get json
    json = sciflo.grid.utils.loadJson(jsonUrl, unpickleKeys=PICKLE_FIELDS)
    
    #if done or cached, print results
    if status in ('done','exception'):

        #if exception, print get error and print
        if status == 'exception':
            res, trace, outputDir = queryMethod(json, ['result', 'exceptionMessage', 'outputDir'])
            if isinstance(res, ScifloExecutorError) and re.search(r'%s' % CANCELLED_MESSAGE, str(res)):
                errorMsg = 'SciFlo execution was cancelled.'
            else:
                #extract Invalid, *Errors, and *Exceptions embedded within soap exceptions
                errMatch = re.search(r'(?:Invalid|.*Error|.*Exception):(.*?)>', str(res), re.S)
                if errMatch: errorMsg = errMatch.group(1)
                else: errorMsg = re.search(r'Exception Value:(.*?)Traceback ', str(res), re.S).group(1)
            errorHtml = '''<div id="annotatedSciflo"><b>Annotated SciFlo: </b><a href="%s" target="_blank">xml</a></div><br/>''' % \
                         os.path.join(outputDir, 'sciflo.sf.xml')
            if trace is None:
                errorHtml += '<font color="red"><b>Error: </b><br/>%s</font><br/><br/>' % escapeCharsForCDATA(errorMsg)
                #errorHtml += '<b>Exception: </b><br/>%s' % escapeCharsForCDATA(str(res))
            else:
                trace = map(str, eval(trace))
                errorHtml += '<font color="red"><b>Error: </b><br/>%s</font><br/><br/>' % escapeCharsForCDATA(errorMsg)
                #errorHtml += '<b>Exception in %s:</b><br/>' % escapeCharsForCDATA(trace[0])
                #errorHtml += '%s<br/>' % escapeCharsForCDATA(trace[2])
            errorHtml = errorHtml.replace('\n','<br/>')
            return resultsSectionTpl.substitute({'resultsContent':errorHtml})

        #get call, result, workdir
        wuid, scifloXml, result, outputDir = queryMethod(json, ['scifloid', 'call', 'result', 'outputDir'])

        #get link to annotated sciflo
        annotatedXmlFile = os.path.join(outputDir, 'sciflo.sf.xml')

        #get ns prefix dict
        nsDict = getNamespacePrefixDict(scifloXml)

        #get lxml elt
        elt = XML(scifloXml)

        #get global outputs via xpath
        outputsRows = []
        outputsElt = elt.xpath('./*/sf:outputs',namespaces=nsDict)
        #loop through and clean out comment elements
        otElts = []
        for i in outputsElt[0]:
            otTag = str(i.tag)
            if otTag == 'None': continue
            otElts.append(i)
        #loop over and get html for results
        resIdx = 0
        for i in otElts:
            outputsRows.append(outputsTableRowTpl.substitute(
                {'tag': re.sub(r'^{.*}','',str(i.tag)),
                 'value': getResultLinkHtml(wuid,result[resIdx], resIdx,
                                                showFilesInline=True,
                                                outputDir=outputDir)}))
            resIdx += 1

        #get table
        return outputsTableTpl.substitute({'tbodyContent': '\n'.join(outputsRows),
                                           'annotatedSciflo': annotatedXmlFile})

    #elif status == 'exception':
    #    resLnkHtml = '<font color="red"><b>sciflo encountered exception.</b></font>'
    elif status == 'cancelled':
        resLnkHtml = '<font color="red"><b>SciFlo execution was cancelled.</b></font>'
    else:
        #resLnkHtml =' <font color="red"><b>NOT IMPLEMENTED: %s.</b></font>' % status
        resLnkHtml = ''

    #handle status
    return resultsSectionTpl.substitute({'resultsContent':resLnkHtml})

def getWorkUnitResultLink(wuid, results, outputDir, outputElt, showFilesInline=False, tracebackMessage=None):
    """Return html string of links to results."""
    
    #if implicit work unit or exception
    if outputElt is None or isinstance(results, Exception):
        return getResultLinkHtml(wuid, results, 0, showFilesInline=showFilesInline,
                                 tracebackMessage=tracebackMessage,
                                 outputDir=outputDir)
    
    #if only one element
    if  len(outputElt.getchildren()) == 1:
        return getResultLinkHtml(wuid, results, 0, showFilesInline=showFilesInline,
                                 tracebackMessage=tracebackMessage,
                                 outputName=outputElt.getchildren()[0].tag,
                                 outputDir=outputDir)
    
    #output elements
    retHtml = ''
    for i, j in enumerate(outputElt.getchildren()):
        retHtml += getResultLinkHtml(wuid, results[i], i, showFilesInline=showFilesInline,
            tracebackMessage=tracebackMessage, outputName=j.tag, outputDir=outputDir)
        retHtml += '<br/>'
    return retHtml

def getStatusTable(jsonUrl):
    """Return html string of status table."""

    #refStarttime
    #refStarttime=time.time()
    
    #get json
    json = sciflo.grid.utils.loadJson(jsonUrl, unpickleKeys=PICKLE_FIELDS)
    scifloid = json['scifloid']

    #query for current status
    curStatus, scifloStarttime, scifloStr, scifloExecLog = \
        queryMethod(json, ['status', 'startTime', 'call', 'executionLog'])
    sflObj = sciflo.grid.doc.Sciflo(scifloStr)
    sflObj.resolve()
    nsDict = sflObj._namespacePrefixDict
    
    #get flow output configs
    flowOutputConfigs = sflObj.getFlowOutputConfigs()
    flowOutputIds = [i.getId() for i in flowOutputConfigs]

    statusInfoList = []
    procIds, procIdWuidMap, workDir = queryMethod(json, ['procIds', 'procIdWuidMap', 'workDir'])
    for i, procId in enumerate(procIds):
        wuid = procIdWuidMap[procId]
        if wuid is not None:
            wuidDir = os.path.join(workDir, wuid)
            wuJsonUrl = os.path.join(wuidDir, 'workunit.json')
            wuidJson = sciflo.grid.utils.loadJson(wuJsonUrl, unpickleKeys=PICKLE_FIELDS)
            typ, status, workerStatus, args, result, tbMessage, execLog, digest, startTime, endTime = \
                queryMethod(wuidJson, ['typ', 'status', 'workerStatus', 'args', 'result',
                                       'tracebackMessage', 'executionLog', 'hex', 'startTime',
                                       'endTime'])
            if workerStatus is None or status == 'cancelled':
                if status == 'sent': workerStatus = 'working'
                else: workerStatus = status
            if status in ('finalizing'): workerStatus = status
        else:
            typ = ''; status = 'waiting'; args = []; result = None
            tracebackMessage = ''; executionLog = ''; digest = None
            startTime = None; endTime = None; workerStatus = 'waiting'
        #f = open('/tmp/error_log', 'a')
        #print >>f, "%s,%s,%s,%s" % (procId, wuid, status, workerStatus)
        statusInfoList.append({'index': i,
                               'type': typ,
                               'status': workerStatus,
                               'wuid': wuid,
                               'wuidDir': wuidDir,
                               'procId': procId,
                               'args': args,
                               'result': result,
                               'tracebackMessage': tbMessage,
                               'executionLog': execLog,
                               'digest': digest,
                               'entryTime': startTime,
                               'finishedTime': endTime})

    #create status table, execution log, and jsonData str
    jsonDataList = []
    statusRows = []
    sortedStatusInfoList = []
    for x in statusInfoList:
      index = x['index']
      sortedStatusInfoList.append((int(index), x))
    sortedStatusInfoList.sort()
    statusInfoList = [x[1] for x in sortedStatusInfoList]
    procIdList = [x['procId'] for x in statusInfoList]
    for statusInfo in statusInfoList:
        
        #get procId for json
        thisprocid = statusInfo['procId']
        
        #get process output elts
        outputElt = None
        if not thisprocid.startswith('implicit_'):
            for i in sflObj._flowProcessesProcess:
                if thisprocid == i.get('id'): outputElt = i.xpath('./sf:outputs', namespaces=nsDict)[0]
            if outputElt is None:
                raise RuntimeError, "Cannot find process %s's output elements in sciflo doc." % thisprocid

        #get wuid
        thiswuid = statusInfo['wuid']

        #set wuid and color
        if thiswuid is None:
            statusInfo['wuidStatus'] = 'waiting'
            statusInfo['colorStatus'] = statusColorDict['waiting']

            #set execution time
            statusInfo['executionTime'] = ''
        else:
            wuidStatus = statusInfo['status']
            statusInfo['wuidStatus'] = wuidStatus
            statusInfo['colorStatus'] = statusColorDict.get(wuidStatus,'#FFFFFF')

            #set execution time
            starttime = statusInfo['entryTime']
            endtime = statusInfo['finishedTime']
            #starttime = statusInfo['entryTime'] #get from schedule store
            #endtime = statusInfo['finishedTime'] #get from schedule store
            if None in (starttime,endtime): statusInfo['executionTime'] = ''
            else: statusInfo['executionTime'] = "%02.3f" % (endtime-starttime)
            
        #add json data
        jsonDataList.append("'%s':'%s'" % (thisprocid,statusInfo['colorStatus']))

        #if finished and there is a global output that depends on this,
        #add global output to json
        if statusInfo['wuidStatus'] in sciflo.grid.finishedStatusList:
            for i in range(len(flowOutputIds)):
                if flowOutputIds[i] == thisprocid:
                    if statusInfo['wuidStatus'] in ['exception','cancelled']: outputColor = 'lightpink'
                    else: outputColor = '#9999CC'
                    outputJson = "'%s':'%s'" % (sflObj.globalOutputs[i],outputColor)
                    if outputJson not in jsonDataList:
                        jsonDataList.append(outputJson)

        #get dependency procids and index
        depProcs = []
        statusInfo['dependencies'] = ''
        #print >>sys.stderr, "statusInfo['args']:", statusInfo['args']
        for arg in statusInfo['args']:
            if isinstance(arg,sciflo.grid.doc.UnresolvedArgument):
                depProcs.append(str(procIdList.index(arg.getId()) + 1))
        if len(depProcs) > 0: statusInfo['dependencies'] = ', '.join(depProcs)

        #if type is sciflo, link status text to status of sciflo
        if statusInfo['type'] == 'sciflo':
            rootBaseUrl = os.path.dirname(os.environ['HTTP_REFERER'])
            statusInfo['wuidStatus'] = '''<a href="%s/monitor_sciflo.cgi?wuid=%s" target="_blank">%s</a>''' % \
            (rootBaseUrl, thiswuid, statusInfo['wuidStatus'])

        #get result link
        if statusInfo['result'] is None:
            if statusInfo['status'] == 'cached':
                #thisreswuid = queryMethod(thiswuid,'digest')
                #thisRes = queryMethod(thisreswuid,'result')
                #thisError = queryMethod(thisreswuid,'tracebackMessage')
                thisreswuid = statusInfo['digest']
                thisRes = statusInfo['result']
                thisError = statusInfo['tracebackMessage']
                statusInfo['resultLnk'] = getWorkUnitResultLink(thiswuid,thisRes,
                                                                statusInfo['wuidDir'],
                                                                outputElt,
                                                                tracebackMessage=thisError)
                #print >>sys.stderr, "#####",thisreswuid, statusInfo['resultLnk']
            else: statusInfo['resultLnk'] = ''
        else:
            statusInfo['resultLnk'] = getWorkUnitResultLink(thiswuid,statusInfo['result'],
                statusInfo['wuidDir'], outputElt, tracebackMessage=statusInfo['tracebackMessage'])

        #fill template
        statusRows.append(statusRowTpl.substitute(statusInfo))

    scifloExecLog = escapeCharsForCDATA(scifloExecLog)
    
    #print cancel link if not yet done
    if curStatus in sciflo.grid.finishedStatusList:
        cancelSciflo = ''
    else:
        cancelSciflo = '''
        <div id="cancelSciflo">To cancel execution:
            <button id="cancel-button" onclick="showCancelDialog();">Cancel</button>
            <div id="cancel-dialog" title="Cancelling Execution" style="display:none;">
                <p>Please wait while the execution of this SciFlo is cancelled...</p>
            </div>
        </div>
        '''

    #return table and json data
    returnTbl = statusTableTpl.substitute({'tbodyContent': '\n'.join(statusRows),
                                           'scifloStatus': curStatus, 'json': jsonUrl,
                                           'scifloStatusColor': statusColorDict[curStatus],
                                           'colorLegend': getColorLegend(),
                                           'cancelSciflo': cancelSciflo,
                                           'execLog': executionLogLinkTpl.substitute({
                                           'logStr': scifloExecLog}),
                                           'executeTime': "%02.3f" % (time.time()-float(scifloStarttime)),
                                           'refreshTime': ''})#"%02.3f" % (time.time()-refStarttime)})
    jsonDataStr = '{' + ','.join(jsonDataList) + '}'
    return returnTbl + '_SPLIT_ON_THIS_' + jsonDataStr

def getColorLegend():
    """Return html string for color legend."""

    legStr = "<div>Work Unit Status/Color Legend:"
    legList = []
    for s in ('waiting','ready','staging','working','finalizing','done','cached',
              'exception','cancelled','paused'):
        legList.append('''<font style="background-color: %s">%s</font>''' % (statusColorDict[s],s))
    legStr += ",".join(legList)
    legStr += "</div>"
    return legStr

def getScifloInputsTable(scifloXml,args):
    """Return inputs table for this sciflo as an html string."""

    #get ns prefix dict
    nsDict = getNamespacePrefixDict(scifloXml)

    #get lxml elt
    elt = XML(scifloXml)

    #get normalized sciflo args
    args = sciflo.grid.normalizeScifloArgs(args)

    #get global inputs via xpath
    inputsRows = []
    inputsElt = elt.xpath('./*/sf:inputs',namespaces=nsDict)[0]
    inElts = [i for i in inputsElt if i.tag is not None]
    if isinstance(args, (types.ListType, types.TupleType)):
        inIdx = 0
        for i in inElts:
            try: arg = args[inIdx]
            except: arg = i.text
            if isinstance(arg, types.StringType) and len(arg) > 240: arg = arg[0:240] + ' ...'
            inputsRows.append(inputsTableRowTpl.substitute(
                {'tag': re.sub(r'^{.*}','',i.tag),'value': sanitizeHtml(arg)}))
            inIdx += 1
    elif isinstance(args, types.DictType):
        for i in inElts:
            arg = args.get(i.tag, i.text)
            if isinstance(arg, types.StringType) and len(arg) > 240: arg = arg[0:240] + ' ...'
            inputsRows.append(inputsTableRowTpl.substitute(
                {'tag': re.sub(r'^{.*}','',i.tag),'value': sanitizeHtml(arg)}))
    else: raise RuntimeError, "Unknown type for args: %s" % type (args)

    #get table
    return inputsTableTpl.substitute({'tbodyContent': '\n'.join(inputsRows),
                                      'scifloName': elt.xpath('./sf:flow',namespaces=nsDict)[0].get('id'),
                                      'scifloDesc': elt.xpath('./*/sf:description/text()',
                                                              namespaces=nsDict)[0]})

def printForm():
    """Just print the form."""
    print monitorScifloTpl.substitute({'spaces':spacesStr})

def handleForm(form):
    """Handle form."""

    #get scifloid and json values
    jsonUrl = sanitizeHtml(form['json'].value)
    json = sciflo.grid.utils.loadJson(jsonUrl, unpickleKeys=PICKLE_FIELDS)
    scifloid = queryMethod(json, 'scifloid')

    #query for current status and type; bomb if not sciflo
    curStatus, outputDir = queryMethod(json, ['status','outputDir'])

    #if curstatus is none, print form with error
    if curStatus is None or outputDir is None:
        print '''<font color="red"><b>Invalid scifloid.</b></font><br/>'''
        printForm()
        return
    
    #print scifloid
    print '<div id="scifloid" style="display:none;">%s</div>' % scifloid
    
    #get sciflo xml
    scifloXml, args = queryMethod(json, ['call', 'args'])
    
    #get svg/png for graph
    graphSvgUrl = os.path.join(outputDir, 'scifloGraph.svg')
    try: svgStr = urllib.urlopen(graphSvgUrl).read()
    except: svgStr = None
    graphPngUrl = os.path.join(outputDir, 'scifloGraph.png')

    #print sciflo arguments
    print getScifloInputsTable(scifloXml, args)
    print '<br/>'
    
    #show graph png
    #print '<b>Execution graph:</b><br/>'
    #print '<img id="pngGraph" src="%s">' % graphPngUrl
    #print '<br/><br/>'
    
    #get status table and json data for svg
    gstCount = 1
    while True:
        try:
            statusTable, jsonDataStr = getStatusTable(jsonUrl).split('_SPLIT_ON_THIS_')
            break
        except: time.sleep(1)
        gstCount += 1
        if gstCount > 5: raise
    
    #print svg
    print '<b>Execution monitoring:</b>'
    print '<div id="jsonDataStr" style="display: none;"><pre>%s</pre></div>' % jsonDataStr
    print '<div id="svgGraph">'
    if svgStr is not None:
        print '''<script type="text/javascript">
            d3.xml("%s", "image/svg+xml", function(xml) {
                $("#svgGraph").append(xml.documentElement);
                initSvg();
            });
        </script>''' % graphSvgUrl
    print '</div>'
    print '<br/>'
    print getColorLegend()
    print '<br/>'
    
    #print initial status table
    print '<div id="updateStatusTable">'
    print statusTable
    print '</div>'
    print '<br/>'

    #print results section, initially empty
    print getResultsSection(jsonUrl, curStatus)

if __name__ == '__main__':
    
    #initiate sajax stuff
    sajax_init()
    sajax_export(refresh,printResults)
    sajax_handle_client_request()

    #print html
    print Template('''
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>$title</title>
        <link href="$JQUERY_CSS_URL" rel="stylesheet">
        <script src="$JQUERY_URL"></script>
        <script src="$JQUERY_UI_URL"></script>
        <script src="$D3_URL"></script>
        <style type="text/css">
            #statusTable {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                border-collapse: collapse;
                width: 100%;
            }

            #statusTable caption {
                font-weight: bold;
            }

            #statusTable thead {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                width: 10%;
                font-weight: bold;
            }

            #statusTable td {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                width: 10%;
            }

            #statusTable tfoot {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                width: 10%;
                font-weight: bold;
            }
            td#index { width: 1%; }
            td#status { width: 1%; }

            #inputsTable {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                border-collapse: collapse;
                width: 100%;
            }

            #inputsTable caption {
                font-weight: bold;
            }

            #inputsTable thead {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                width: 10%;
                font-weight: bold;
            }

            #inputsTable td {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                width: 10%;
            }
            td#inputVal { font-weight: bold; width: 90%; }

            #outputsTable {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                border-collapse: collapse;
                width: 25%;
            }

            #outputsTable caption {
                font-weight: bold;
            }

            #outputsTable thead {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                width: 10%;
                font-weight: bold;
            }

            #outputsTable td {
                border-width: 1px;
                border-spacing: 0px;
                border-style: solid;
                border-color: black;
                width: 10%;
            }
            td#outputVal { font-weight: bold; }
            
            .no-close .ui-dialog-titlebar-close {
                display: none;
            }
        </style>
        $customHead
        <script type="text/javascript">
    ''').substitute(title="Monitor SciFlo",
                    JQUERY_CSS_URL=JQUERY_CSS_URL,
                    JQUERY_URL=JQUERY_URL,
                    JQUERY_UI_URL=JQUERY_UI_URL,
                    D3_URL=D3_URL,
                    customHead=pageTemplate.customHead)
    sajax_show_javascript()
    print Template('''
        
        function getXmlStringFromCDATAString(xmlStr) {
            var nlMatch=/[\\r\\n]*/g;
            xmlStr=xmlStr.replace(nlMatch,'');
            var reMatch=/\[CDATA\[(.*)]]$$/g;
            reMatch.test(xmlStr);
            s=RegExp.$$1;
            return s.replace(/&#62;/g,'>').replace(/&#60;/g,'<').replace(/&#91;/g,'[').replace(/&#93;/g,']')
        }
        
        function initSvg() {
            // zoom in so that SVG fits the width of the browser
            var svg = d3.select("svg");
            var imgWidth = parseFloat(d3.select("#graph0").node().getBBox().width);
            var imgHeight = parseFloat(d3.select("#graph0").node().getBBox().height);
            var divWidth = $$("#svgGraph").width();
            var scale = divWidth/imgWidth;
            if (scale > 2.0) scale = 2.0; // max out scaling factor at 2
            var divHeight = parseInt(imgHeight*scale)
            //console.log(scale + ' ' + imgWidth + ' ' + imgHeight + ' ' + divWidth + ' ' + divHeight);
            d3.select('#svgGraph').style('height', divHeight + 'px');
            svg.attr('width', divWidth + 'px');
            svg.attr('height', divHeight + 'px');
            svg.attr('viewBox', '0 0 ' + divWidth + ' ' + divHeight);
            d3.select("#graph0").attr("transform",
                "translate(4 " + divHeight + ") scale(" + scale + ")");
                
            // start updating
            var jsonDoc=document.getElementById('jsonDataStr');
            updateSvg(jsonDoc.childNodes[0].innerHTML);
        }
        
        function updateSvg(jsonData) {
            // get color data
            var colorData = eval("(" + jsonData + ")");
            
            // get svg node to start updating viz
            var svg = d3.select("svg");
            svg.selectAll("text")
               .data(function() {
                    // connect color data to the appropriate text node
                    var data = [];
                    $$.each(this, function(i, v) {
                        data.push(colorData[$$(v).text()]);
                    });
                    return data;
                })
                .style('font-size', '6pt')
                .style('font-weight', 'bold')
                .each(function(d, i) {
                    // change shape color
                    var shapeElt = d3.select(this.parentNode).select('polygon, ellipse');
                    if (d) shapeElt.style('fill', d);
                    if (d == '#00FF00') {
                        if (shapeElt.node().childNodes.length == 0) {
                            shapeElt.append("animate")
                                    .attr("attributeType", "CSS")
                                    .attr("attributeName", "opacity")
                                    .attr("from", 1)
                                    .attr("to", 0)
                                    .attr("dur", "1s")
                                    .attr("repeatCount", "indefinite");
                        }
                    }else {
                        shapeElt.selectAll("animate").remove();
                    }
                });
            return;
        }
        
        function moldResults(wuid, action) {
            window.open('${MOLD_RESULTS_URL}?action=' + action + '&wuid=' + wuid, action).blur();
            window.focus();
        }
        
        function printResults_cb(newData) {
            try {
                document.getElementById("resultsSection").innerHTML=newData;
                if ($$('#map3d') != null) {
                    //need to reload in order for google earth plugin to load kml output
                    //location.reload(true);
                }
            } catch(e) {}
        }
        
        function refresh_cb(newData) {
            var reScifloStatus=/scifloStatus/g;
            if (reScifloStatus.test(newData)) {
                data = newData.split('_SPLIT_ON_THIS_');
                tblData = data[0];
                jsonData = data[1];
                if (tblData!='') { document.getElementById("updateStatusTable").innerHTML=tblData; }
                if (jsonData!='') { updateSvg(jsonData); }
            }
            setTimeout("refresh()", 300);
        }
        
        function refresh() {
            var scifloStatusElt=document.getElementById("scifloStatus");
            if (scifloStatusElt) {
                var status=scifloStatusElt.getAttribute('status');
                var json=scifloStatusElt.getAttribute('json');
                if (status=='done' || status=='exception' || status=='cached' || status=='cancelled') {
                    x_printResults(json,status,printResults_cb);
                }else {
                    x_refresh(json,refresh_cb);
                }
            }
        }
        
        function cancelExecution() {
            $$.ajax({
                url:  "${CANCEL_URL}",
                data: {scifloid: $$( "#scifloid" ).text() },
                async: false,
                success: function(data, textStatus, jqXHR) {
                    setTimeout(function() {
                        $$( "#cancel-dialog" ).dialog( "close" );
                    }, 5000);
                }
            });
        }
        
        function showCancelDialog() {
            $$( "#cancel-dialog" ).dialog({
                autoOpen: false,
                modal: true,
                width: 600,
                dialogClass: 'no-close',
                open: function(event, ui) {
                    cancelExecution();
                }
            }).dialog( "open" );
        }
        
        $$(refresh);
        </script>
    ''').substitute(MOLD_RESULTS_URL=urljoin(CGI_URL_BASE, 'mold_results.cgi'),
                    CANCEL_URL=urljoin(CGI_URL_BASE, 'cancel_sciflo.cgi'))
    
    # print end of header, start of body, and add accessibility
    print Template("""</head>
        <body>
        <a href="${REQUEST_URI}#main"><img src="$spacer" alt="Follow this link to skip to the main content"
       width="1" height="1" hspace="0" vspace="0" border="0" align="left"></a>
       $customBodyStart
       <noscript>
       <font color="red">
       JavaScript is turned off in your web browser. Turn it on to make this site functional, then refresh the page.
       </font><br><br>
       </noscript>
    """).substitute(REQUEST_URI=sanitizeHtml(os.environ['REQUEST_URI']),
                    spacer=os.path.join(REL_URL, 'portal_images/spacer.gif'),
                    customBodyStart=pageTemplate.customBodyStart)

    #if nothing, print form
    if len(form) == 0 or not form.has_key('json'): printForm()
    else: handleForm(form)

    #print end of html
    print "</body></html>"
