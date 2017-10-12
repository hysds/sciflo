import os, sys, urllib
import numpy as N
from pyhdf.SD import SD, SDC
from pyhdf.HDF import HDF
from pyhdf.VS import VS
from pyhdf.V import V
from pyhdf.error import HDF4Error
from lxml.etree import Element, SubElement, tostring

#TAI = calendar.timegm((1993, 1, 1, 0, 0, 0))
TAI = 725846400

class HdfFile(object):
    """Class implementing HDF file access."""
    
    GEOLOC_FIELDS = ()
    
    TYPE_TABLE = {
           SDC.CHAR:    'CHAR',
           SDC.CHAR8:   'CHAR8',
           SDC.UCHAR8:  'UCHAR8',
           SDC.INT8:    'INT8',
           SDC.UINT8:   'UINT8',
           SDC.INT16:   'INT16',
           SDC.UINT16:  'UINT16',
           SDC.INT32:   'INT32',
           SDC.UINT32:  'UINT32',
           SDC.FLOAT32: 'FLOAT32',
           SDC.FLOAT64: 'FLOAT64'
    }
    
    def __init__(self, file):
        """Constructor."""
        
        self.file = file
        self.hdf = None
        self.vs = None
        self.vdinfo = None
        self.sd = None
        self.v = None
        self.savedVarsDict = None
        self.open()
        self.datasetList = self.sd.datasets().keys()
        self.vdList = [i[0] for i in self.vdinfo]
        #print self.datasetList
        #print self.vdList
        #print type(self.vdinfo)
        #self.close()

    def open(self):
        """Open for reading."""
        
        if self.hdf is None:
            self.hdf = HDF(self.file)
            self.vs = self.hdf.vstart()
            self.vdinfo = self.vs.vdatainfo()
            self.sd = SD(self.file)
            self.v = self.hdf.vgstart()
    
    def close(self):
        """Close hdf file."""
        
        if self.hdf is not None:
            self.vs.end()
            self.hdf.close()
            self.sd.end()
            self.hdf = None
            self.vs = None
            self.vdinfo = None
            self.sd = None
            self.v = None
            
    def getMetadataXml(self):
        """Return metadata xml."""
        
        #create root element
        nsDict = {None: 'http://sciflo.jpl.nasa.gov/sciflo/namespaces/granuleMetadataXML-1.0'}
        rtElt = Element('{%s}file' % nsDict[None], nsmap=nsDict)
        rtElt.set('location', os.path.basename(self.file))
        rtElt.set('type', 'hdf4')
        
        #create group
        vg = self.v.attach(self.v.getid(-1))
        grpElt = SubElement(rtElt, 'group')
        grpElt.set('name', vg._name)
        
        #iterate over datasets
        dimDict = {}
        varDict = {}
        for ds in self.datasetList:
            dimNames, dimSizes, dsType, dsIdx = self.sd.datasets()[ds]
            
            #remove :(groupName) from dims name
            dimNames = [dim.replace(':%s' % vg._name, '') for dim in dimNames]
            
            #add dimension elements to dict
            for i, dim in enumerate(dimNames):
                if dimDict.has_key(dim): continue
                dimDict[dim] = Element('dimension')
                dimDict[dim].set('name', dim)
                dimDict[dim].set('length', str(dimSizes[i]))
            
            #add variable to dict
            varDict[ds] = Element('variable')
            varDict[ds].set('name', ds)
            varDict[ds].set('shape', ' '.join(dimNames))
            varDict[ds].set('type', self.TYPE_TABLE[dsType])
            dsObj = self.sd.select(ds)
            dsAttrs = dsObj.attributes()
            for dsAttr in dsAttrs:
                if dsAttr == '_FillValue': attr = 'fill_value'
                else: attr = dsAttr
                varDict[ds].append(Element('attribute', name=attr, value=str(dsAttrs[dsAttr])))
            
        #add dimensions
        for dim in dimDict: grpElt.append(dimDict[dim])
        
        #add variables
        for variable in varDict: grpElt.append(varDict[variable])
        
        return tostring(rtElt, pretty_print=True)

    def __del__(self): self.close()

def main():
    """Command-line interface."""
    
    if len(sys.argv) != 2:
        print "Usage: sys.argv[0] <hdf file or url>"
        exit(1)
        
    f, f_hdrs = urllib.urlretrieve(sys.argv[1])
    try: print HdfFile(f).getMetadataXml()
    finally: urllib.urlcleanup()