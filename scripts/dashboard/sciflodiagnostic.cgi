#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        sciflodiagnostic.cgi
# Purpose:     Display flowcheck results.
#
# Author:      Marcus Hammond
#              Gerald Manipon
#
# Created:     Wed Jun 27 23:26:44 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-------------------------------------------------------------------------------------
import cgi
import cgitb; cgitb.enable()
import os, sys, urllib, tempfile
from string import Template
import elementtree.ElementTree as ET

import sciflo
from cgiUtils import *
import pageTemplate

CGI_URL_BASE = sciflo.utils.getCgiBaseHref()
HTML_URL_BASE = sciflo.utils.getHtmlBaseHref()
REL_URL = sciflo.utils.getRelativeUrl(CGI_URL_BASE, HTML_URL_BASE)

ADDITIONAL_HEAD = '''
<style type="text/css">
/********** Outer Window ***************/
.dojoFloatingPane {
  /* essential css */
  position: relative;
  overflow: visible;
  /*Popup at click point
  left: -350px;
  top: -200px;*/
  z-index: 10;
  /* styling css */
  border: 1px solid;
  border-color: ThreeDHighlight ThreeDShadow ThreeDShadow ThreeDHighlight;
  background-color: ThreeDFace;
}
/********** Title Bar ****************/
.dojoFloatingPaneTitleBar {
  vertical-align: top;
  margin: 2px 2px 2px 2px;
  z-index: 10;
  background-color: #7596c6;
  cursor: default;
  overflow: hidden;
  border-color: ThreeDHighlight ThreeDShadow ThreeDShadow ThreeDHighlight;
  vertical-align: middle;
}
.dojoFloatingPaneTitleText {
  float: left;
  padding: 2px 4px 2px 2px;
  white-space: nowrap;
  color: CaptionText;
  font: small-caption;
}
.dojoTitleBarIcon {
  float: left;
  height: 22px;
  width: 22px;
  vertical-align: middle;
  margin-right: 5px;
  margin-left: 5px;
}
.dojoFloatingPaneActions{
  float: right;
  position: absolute;
  right: 2px;
  top: 2px;
  vertical-align: middle;
}
.dojoFloatingPaneActionItem {
  vertical-align: middle;
  margin-right: 1px;
  height: 22px;
  width: 22px;
}
.dojoFloatingPaneTitleBarIcon {
  /* essential css */
  float: left;
  /* styling css */
  margin-left: 2px;
  margin-right: 4px;
  height: 22px;
}
/* minimize/maximize icons are specified by CSS only */
.dojoFloatingPaneMinimizeIcon, .dojoFloatingPaneMaximizeIcon, .dojoFloatingPaneRestoreIcon, .dojoFloatingPaneCloseIcon {
  vertical-align: middle;
  height: 22px;
  width: 22px;
  float: right;
}
.dojoFloatingPaneMinimizeIcon {
  background-image: url(images/floatingPaneMinimize.gif);
}
.dojoFloatingPaneMaximizeIcon {
  background-image: url(images/floatingPaneMaximize.gif);
}
.dojoFloatingPaneRestoreIcon {
  background-image: url(images/floatingPaneRestore.gif);
}
.dojoFloatingPaneCloseIcon {
  background-image: url(images/floatingPaneClose.gif);
}
/* bar at bottom of window that holds resize handle */
.dojoFloatingPaneResizebar {
  z-index: 10;
  height: 13px;
  background-color: ThreeDFace;
}
/************* Client Area ***************/
.dojoFloatingPaneClient {
  width: 800px;
  position: relative;
  z-index: 10;
  border: 1px solid;
  border-color: ThreeDShadow ThreeDHighlight ThreeDHighlight ThreeDShadow;
  margin: 2px;
  background-color: white;
  padding: 8px;
  font-family: Verdana, Helvetica, Garamond, sans-serif;
  font-size: 12px;
  overflow: visible;
}
</style>
<script type="text/javascript">
  dojo.require("dojo.widget.FloatingPane");
</script>
'''

DIALOG_DIV_TMPL = Template('''
<span dojoType="FloatingPane" title="$id" id="${idUnique}" layoutAlign="client"
style="background-color: white; padding: 5px; display: inline;" hasShadow="true"
displayMinimizeAction="true" windowState="minimized"><pre>$content</pre></span><a href="#"
onclick="dojo.widget.byId('$idUnique').show(); return false;">$id</a>''')

#DIALOG_DIV_TMPL = Template('''
#<span dojoType="dialog" id="$idUnique" bgColor="black" bgOpacity="0.5" toggle="fade"
#toggleDuration="250" followScroll="false" closeOnBackgroundClick="true"
#style="display: inline;"><span dojoType="FloatingPane" title="$id" id="${idUnique}Pane"
#layoutAlign="client" style="background-color: white; padding: 5px; display: inline;"
#hasShadow="true" templateCssString="%s"><span
#style="font-style: normal; font-weight: normal;"><pre>$content</pre></span></span></span><a href="#"
#onclick="dojo.widget.byId('$idUnique').show(); return false;">$id</a>''' % FLOATING_PANE_CSS)

if __name__ == "__main__":
    
    print "Content-Type: text/html\n\n"
    print pageTemplate.pageTemplateHeadStart.substitute(title='Flow Status',
                                                        additionalHead=ADDITIONAL_HEAD)
    print pageTemplate.pageTemplateHeadEnd.substitute(additionalHead='',
                                                  bodyOnload='')
    
    form = cgi.FieldStorage()
    
    #run live?
    runLive = form.getfirst("live", None)
    if runLive is not None: runLive = True
    else: runLive = False
    
    #get flows dir
    flowsRootDir = os.path.join(sys.prefix, 'share', 'sciflo', 'web', 'flows')
    flowsDir = form.getfirst('flowsDir', None)
    
    #run flowcheck.sh live and wait for results
    if runLive:
        if flowsDir is None:
            print "<center><h1>Run Live</h1></center>"
            print '<font color="red"><b>No flows directory specified.</b></font>'
            print pageTemplate.pageTemplateFoot.substitute()
            raise SystemExit
        else:
            Path = tempfile.mktemp(suffix=".xml")
            flowcheckScript = os.path.join(sys.prefix, 'bin', 'flowcheck.sh')
            os.system('SCIFLO_DIR=%s %s %s %s > /dev/null 2>&1' % (sys.prefix,
                flowcheckScript, Path, os.path.join(flowsRootDir, flowsDir)))
            print "<center><h1>Live Run</h1></center>"
    #otherwise use precomputed results
    else:
        #get path to flowcheck xml
        Path = form.getfirst("Path", '/tmp/flowcheck.xml')
        print "<center><h1>Flow Status</h1></center>"
    
    # Check to see if path is local or remote
    
    if Path.startswith('http'):
        u = urllib.urlopen(Path)
        data = u.read()
        (fd, ftemp) = tempfile.mkstemp()
        open(ftemp, 'r+b').write(data)
        tree = ET.ElementTree()
        tree.parse(ftemp)
        root = tree.getroot()
        os.remove(ftemp)
    else:
        xmlfilepath = Path
        tree = ET.ElementTree()
        tree.parse(xmlfilepath)
        root = tree.getroot()
    #------------------------------------------------------------------------
    print '<body text="Black"><table border="1px">'
    
    for y, i in enumerate(root):
        print '<tr>'
        success = False
        if y == 0:
            for j in i[:4]: print '<td width="200"><b>' + j.text + '</b></td>'
            continue
        'Name','Path','Time','Status','Messages'
        nameElt, pathElt, timeElt, statusElt, messageElt = i
        if statusElt.text == 'Successful': color = 'green'
        else: color = 'red'
        status = DIALOG_DIV_TMPL.substitute(content=messageElt.text,
                                            id=nameElt.text,
                                            idUnique=nameElt.text + str(y))
        print '<td width="200">%s</td>' % status
        print '<td width="200">%s</td>' % pathElt.text
        print '<td width="200">%s</td>' % timeElt.text
        print '<td width="200" bgcolor="%s">%s</td>' % (color, statusElt.text)
        print '</tr>'
    print '</table>'
    if flowsDir is not None:
        print '<br/>'
        print '<a href="?live=1&flowsDir=%s">Run Live</a>' % flowsDir
        print '<br/>'
    print '</body>'
    
    print pageTemplate.pageTemplateFoot.substitute()
    
    #cleanup
    if runLive: os.unlink(Path)
