#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        getConfigVal.py
# Purpose:     Return the config value.
#
# Author:      Gerald Manipon
#
# Created:     Wed Nov 29 18:42:34 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys

from sciflo.utils import ScifloConfigParser

def usage():
    """Print usage info."""
    print(("""%s <config field>""" % sys.argv[0]))

#make sure right number of arguments provided
if len(sys.argv) != 2:
    usage()
    sys.exit(2)

#get sciflo config parser
scp = ScifloConfigParser()

#print
print((scp.getParameter(sys.argv[1])))

