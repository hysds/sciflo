#!/bin/env python

"""
The ipath module provides simple functions to manipulate IPath
(international resource Identifier Path) objects, which are an
extension of the XPath notation and syntax to permanent IRIs.
The general form for an IPath is:

<namespaceBundlePrefix>::<modified_relative_xpath>

For example, using the sfpath 'eos::data/AIRS/RetStd/L2' means:

 - Lookup the bundle of namespaces referred to by the eos prefix.
   (The prefixes thereby defined can be used in the xpath.)
   
 - Also lookup up the IPath ROOT pointed to by that prefix.
 
 - Construct the (absolute) extended IPath from the root and the
   relative path 'data/AIRS/RetStd/L2'.
   
 - Resolve the absolute sfpath and return the XML doc it points to.   

A 'modified XPath' is a slight variation on an XPath.  In the
modified form used in IPath, any tag in the path without a namespace
prefix is implicitly in the default namespace (defined by the eos
namespaceBundlePrefix).  There are no tags in the <null> namespace.

The 'eos' part of the IPath might begin with a full URI which will
be resolved by a scalable permanent name resolution service.
For example, the IPath might be:
  usa:gov:nasa:eos::data/AIRS/RetStd/L2
  
The scalable name resolution service would resolve the URI down to
the eos resolver, which would look up the namespace bundle and the
eos ROOT, and then path below the ROOT into a virtual or real XML
document.  The shorter IPath ('eos::') can serve as an abbreviated
form of theh full IPath since the 'eos' name resolver maintains
'backlinks' pointing to the global IRIs that contain it.   

The combination of IRI/URI notation, using the ':' separator, and
XPath notation, using the '/' separator, is intentional.
The dividing line between the two domains (IRI resolution and
virtual XPath) is indicated by the repeated colon separator ('::').
The lookup semantics in the two domains are quite different.

Mistake??????

"""

class IPath:
    def __init__(ipath):
        self.ipath = ipath
        self.xpath, self.ns, self.xpathRoot = parseIPath(ipath)    

    
def parseIPath(ipath):
    if '::' not in ipath:
        raise 'IPath: Illegal ipath, must contain prefix::<xpath>.'
    prefix, dum, xpath = ipath.split(':')
    nsDict, xpathRoot = iriResolve(prefix)
    return (xpath, nsDict, xpathRoot)

EosNS = 'http://eos.nasa.gov/2007/v1'

NamespaceBundles = {'eos': ({'eos': EosNS, '_': EosNS}, '/eos') }
 
def iriResolve(prefix):
    try:
        return NameSpaceBundles[prefix]
    except:
        raise 'iriResolve: Cannot resolve name %s' % prefix
        



