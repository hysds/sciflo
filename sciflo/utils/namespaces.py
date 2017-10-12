#-----------------------------------------------------------------------------
# Name:        namespaces.py
# Purpose:     Set namespace constants.
#
# Author:      Gerald Manipon
#
# Created:     Thu Apr 27 12:08:11 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
#default namespace
SCIFLO_NAMESPACE = 'http://sciflo.jpl.nasa.gov/2006v1/sf'

#xsd namespace
XSD_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'

#xsi namespace
XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'

#sciflo python namespace
PY_NAMESPACE = 'http://sciflo.jpl.nasa.gov/2006v1/py'

#get prefix from namespace dict
def getPrefixForNs(nsDict,ns):
    """Return prefix string for namespace."""
    if nsDict.get('_default',None) == ns: return '_default'
    for pre in nsDict.keys():
        if nsDict[pre] == ns: return pre
    return None
