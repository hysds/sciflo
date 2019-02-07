#!/usr/bin/env python
# -------------------------------------------------------------------------------------
# Name:        flowcheck.py
# Purpose:     Tests sciflo documents for exceptions and outputs status in xml format.
#
# Author:      Marcus Hammond
#
# Created:     Wed Jun 27 23:26:44 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -------------------------------------------------------------------------------------

import sys
import os
import getopt
import datetime
import tempfile
import shutil
import re
from lxml.etree import Element, SubElement, tostring


def checkflow(path=None, outfile=None):
    if path is None:
        path = os.getcwd()
    if outfile is None:
        outfile = os.path.join(path, 'flowcheck.xml')
    outdir = os.path.dirname(os.path.abspath(outfile))
    #	print '\n finding and running all .sf.xml files in directories rooted at ', path

    # Perform search of 'path' and save all sciflo docs' complete pathways into list named 'y'
    y = []
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            if f == 'sciflo.sf.xml':
                continue
            if f.endswith("sf.xml"):
                y.append(os.path.join(dirpath, f))

    # Create temporary directory
    workdir = tempfile.mkdtemp()
    bin = tempfile.mkdtemp(dir=workdir)
    os.chdir(workdir)

    # Start building XML tree
    root = Element('table')
    header = SubElement(root, 'header')
    columnnames = ['Name', 'Path', 'Time', 'Status', 'Messages']
    columnlabels = ['Flow Name', 'Flow Path', 'Run Time', 'Status', 'Messages']

    for i in range(len(columnlabels)):
        colheader = SubElement(header, columnnames[i])
        colheader.text = columnlabels[i]
    for i in y:

        # Get file name
        array = i.split('/')
        filename = array[-1].split('.')
        name = filename[0]

        # Get time
        t = str(datetime.datetime.utcnow())
    #		print '\n\n' , i

        sflExec = os.path.join(sys.prefix, 'bin', 'sflExec.py')
        cmd = '%s -d -f -o ' % sflExec + bin + '/' + \
            array[-1] + ' ' + i + '> sflExec.log 2>&1'
        retVal = os.system(cmd)
        logContents = open('sflExec.log').read()
        if re.search(r'(Encountered the following errors during execution|\Traceback \(most recent call last\):)', logContents):
            status = 'Exception encountered'
        else:
            status = 'Successful'
        data = [name, i, t, status, logContents]
        row = SubElement(root, name)

        for j in range(len(data)):
            col = SubElement(row, columnnames[j])
            col.text = data[j]

    shutil.rmtree(workdir)

    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    outputf = open(outfile, 'w')
    outputf.write(tostring(root, pretty_print=True))

    return


if __name__ == '__main__':

    opts, args = getopt.getopt(sys.argv[1:], "o:r:")

    # print opts
    # print args

    for o, a in opts:
        if o in ("-o"):
            outFile = a
        if o in ("-r"):
            rootDir = a

    checkflow(rootDir, outFile)
