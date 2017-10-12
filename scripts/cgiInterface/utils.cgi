#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        utils.cgi
# Purpose:     Various utilities.
#
# Author:      Gerald Manipon
#
# Created:     Thu Feb 12 11:10:57 2009
# Copyright:   (c) 2009, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, sys, re, types, cgi, cjson, urllib2

#turn on script debugging in browser
#import cgitb; cgitb.enable()

from sciflo.utils import getXmlEtree

def printJson(obj):
    """Jsonify obj and print."""
    print "Content-Type: text/plain\n\n%s" % cjson.encode(obj)

def testComboBoxData(form):
    """Return test ComboBox data for dojo."""
    printJson([["Alaska", "AL"], ["California", "CA"], ["Hawaii", "HI"]])
    
def getVarData(form):
    """Return variable data from data xml."""
    
    dataUrl = form.getfirst('dataUrl', None)
    if dataUrl is None: raise RuntimeError("dataUrl unspecified.")
    elt, nsDict = getXmlEtree(dataUrl)
    ret = []
    #process each group
    for i in elt.xpath('.//_default:group', namespaces=nsDict):
        group = i.get('name', None)
        if group is None: continue
        
        #get dimensions dict
        dims = {}
        for j in i.xpath('.//_default:dimension', namespaces=nsDict):
            dim = j.get('name', None)
            if dim is None: continue
            dims[dim] = [j.get('hide', 'false'), j.get('length')]
        
        #get attributes dict
        attrs = {}
        for j in i.xpath('.//_default:attribute', namespaces=nsDict):
            attr = j.get('name', None)
            if attr is None: continue
            attrs[attr] = j.get('value')
        
        #get variables dict
        variables = {}
        for j in i.xpath('.//_default:variable', namespaces=nsDict):
            var = j.get('name', None)
            if var is None: continue
            shape = j.get('shape')
            variables[var] = shape.split()
        ret.append([group, dims, attrs, variables])
        
    return ret

def getVarData4CB(form):
    """Return variable data from data xml for combobox."""
    printJson(getVarData(form))

if __name__ == '__main__':

    #get form
    form = cgi.FieldStorage()
    func = form.getfirst('func', None)
    if func is None: raise RuntimeError("No function specified.")

    #dispatch to function
    if func == 'testComboBoxData': testComboBoxData(form)
    elif func == 'getVarData4CB': getVarData4CB(form)
    else: raise RuntimeError("Unknown function %s." % func)
