#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Name:        cancel_sciflo.cgi
# Purpose:     Cancel the execution of a sciflo.
#
# Author:      Gerald Manipon
#
# Created:     Tue Sep 15 10:56:00 2009
# Copyright:   (c) 2009, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import cgi
#import cgitb; cgitb.enable()
from string import Template
import os
import sys

import sciflo
from sciflo.utils.sajax1 import form
from sciflo.utils import sanitizeHtml
from cgiUtils import *

CGI_URL_BASE = sciflo.utils.getCgiBaseHref()
HTML_URL_BASE = sciflo.utils.getHtmlBaseHref()
REL_URL = sciflo.utils.getRelativeUrl(CGI_URL_BASE, HTML_URL_BASE)

basicTemplate = form.getfirst('basicTemplate', None)
if basicTemplate is None:
    import pageTemplate
else:
    import basicPageTemplate as pageTemplate

# config file
configFile = None

# templates
spacesStr = '&nbsp;' * 3

cancelScifloTpl = Template('''
<form name="cancelSciflo" method="POST">
<span>Please enter a valid scifloid:$spaces</span>
<span><input name="wuid" type="text" size="72"/></span>
<span><input type="submit" name="Cancel" value="Cancel" /></span>
</span>
</form>
''')


def printForm():
    """Just print the form."""
    print cancelScifloTpl.substitute({'spaces': spacesStr})


def handleForm(form):
    """Handle form."""

    # get scifloid and json values
    scifloid = sanitizeHtml(form['scifloid'].value)

    # cancel
    gsc = sciflo.grid.GridServiceConfig()
    gridBaseUrl = gsc.getGridProxyUrl()
    if not gridBaseUrl:
        gridBaseUrl = gsc.getGridBaseUrl()
    wsdl = '%s/wsdl?http://sciflo.jpl.nasa.gov/2006v1/sf/GridService' % gridBaseUrl
    try:
        sciflo.grid.soapFuncs.cancelSciflo_client(
            wsdl, 'cancelSciflo', scifloid)
    except Exception, e:
        print "Content-Type: text/html\n\n"
        print '<font color="red">SciFlo Execution server is down.  Unable to cancel sciflo.</font>'
        return

    print "<b>scifloid %s was cancelled.</b>" % scifloid


if __name__ == '__main__':

    print pageTemplate.pageTemplateHead.substitute(title='Cancel SciFlo',
                                                   additionalHead='',
                                                   bodyOnload='')

    # if nothing, print form
    if len(form) == 0 or not form.has_key('scifloid'):
        printForm()
    else:
        handleForm(form)

    # print end of html
    print pageTemplate.pageTemplateFoot.substitute()
