#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        get_sciflos.cgi
# Purpose:     Display sciflo listing and allow users to execute or view xml.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jul 27 10:54:49 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys
import cgi
#import cgitb; cgitb.enable()
import re
import traceback
from lxml.etree import Element, SubElement, tostring
import sciflo
import pageTemplate
from urlparse import urlparse, urljoin
from sciflo.utils import getHtmlBaseHref, getCgiBaseHref, getRelativeUrl

CGI_URL_BASE = getCgiBaseHref()
HTML_URL_BASE = getHtmlBaseHref()
REL_URL = getRelativeUrl(CGI_URL_BASE, HTML_URL_BASE)

SCIFLO_DOCS_ROOT_DIR = os.path.join(sys.prefix, 'share', 'sciflo', 'web', 'flows')
SCIFLO_DOCS_ROOT_URL = urljoin(sciflo.utils.getHtmlBaseHref(), 'flows')
SUBMIT_CGI_URL_BASE = 'submit_sciflo.cgi?scifloStr='

def getScifloDirectoryListing(docDir):
    """Return listing of sciflo url's as xml."""

    scifloDocsDir = os.path.join(SCIFLO_DOCS_ROOT_DIR, docDir)
    scifloDocsUrl = os.path.join(SCIFLO_DOCS_ROOT_URL, docDir)
    files = os.listdir(scifloDocsDir); files.sort()
    retHtml = ''
    subdirHtml = ''
    for i in files:
        scifloFile = os.path.join(scifloDocsDir,i)
        if os.path.isdir(scifloFile) and os.access(scifloFile, 5) and \
            not i.startswith('.'):
            subdirFiles = os.listdir(scifloFile); subdirFiles.sort()
            subSfFound = False
            for j in subdirFiles:
                if j.endswith('sf.xml'): subSfFound = True
            if subSfFound:
                subdirHtml += '''<table border="0" width="100%%">
                <tr><td width="90%%">
                    <table border="0">
                        <tr>
                            <td align="left">&#149;<b>Subdirectory
                            <a href="get_sciflos.cgi?dir=%s">
                            <font color="green">%s</b></font></a>
                            </td>
                        </tr></table></td></tr></table>''' % (os.path.join(docDir,i), i)
            continue
        if not scifloFile.endswith('sf.xml'): continue
        scifloUrl = os.path.join(scifloDocsUrl,i)
        try: elt,nsDict = sciflo.utils.getXmlEtree(scifloFile)
        except: continue
        
        #get metadata on sciflo doc
        id = elt.xpath('./sf:flow', namespaces=nsDict)[0].get('id')
        titleNodes = elt.xpath('./sf:flow/sf:title', namespaces=nsDict)
        if len(titleNodes) == 1: title = titleNodes[0].text
        else: title = id
        iconNodes = elt.xpath('./sf:flow/sf:icon', namespaces=nsDict)
        if len(iconNodes) == 1: icon = iconNodes[0].text
        else: icon = os.path.join(REL_URL, 'portal_images/esip.gif')
        desc = elt.xpath('./sf:flow/sf:description', namespaces=nsDict)[0].text
        if desc is None or re.search(r'^\s*$', desc): desc = 'No description defined in sciflo.'
        #set html for sciflo
        retHtml += '''<table border="0" width="100%%">
        <tr>
            <td width="90%%">
                <table border="0">
                    <tr>
                        <td align="left">
                            &#149;<b><font color="blue">%s</b></font>
                            [<a href="%s">xml</a>] [<a href="%s&reset=hard">execute</a>]
                        </td>
                    </tr>
                    <tr>
                        <td align="left">
                            %s
                        </td>
                    </tr>
                </table>
            </td>
            <td width="10%%" align="right" valign="bottom">
                <a href="%s"><img alt="%s" src="%s" width="70" height="60" border="0"></a>
            </td>
        </tr>
        </table>
        <!--
        [<a href="%s&reset=soft">soft reset</a>]
        [<a href="%s&reset=hard">hard reset</a>]-->
        <br/>\n''' % \
                 (title, scifloUrl, SUBMIT_CGI_URL_BASE + scifloUrl, desc,
                  SUBMIT_CGI_URL_BASE + scifloUrl, title, icon, 
                  SUBMIT_CGI_URL_BASE + scifloUrl, SUBMIT_CGI_URL_BASE + scifloUrl)
    ret = '''<a id="main" name="main"></a><center><h1>SciFlo Document Listing</h1><div id="scifloDir"></center>'''
    return ret + subdirHtml + retHtml

def writeResponse(resp, contentType = 'text/html'):
    """Write response."""

    resp = resp.strip()
    #print html
    html = pageTemplate.pageTemplateHead.substitute(title='SciFlo Document Listing',
                                                   additionalHead='',
                                                   bodyOnload='')
    resp = resp.strip()
    html += resp
    html += pageTemplate.pageTemplateFoot.substitute()
    fullStr = "Content-type: %s\nContent-length: %s\n\n%s" % (contentType, len(html), html)
    print fullStr

if __name__=='__main__':
    form = cgi.FieldStorage()
    dir = form.getfirst('dir','')
    writeResponse(getScifloDirectoryListing(dir),'text/html')
