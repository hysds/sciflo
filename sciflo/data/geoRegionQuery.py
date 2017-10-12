"""
geoRegionQuery.py - Class and protocol for constructing geoRegionQuery SOAP services.

To create a space/time query service for L2 or L3 data, subclass one of the
contained classes, e.g. TimeQuery or SpaceTimeQuery.  All classes are
constructed from a simple XML metadata block; see queryableDatasets.xml.

"""

import types

class GeoRegionQuery:
    """Base class for geoRegionQuery services.
Inheritor must implement the getGeoRegionInfo and getDataById methods or make
use of specialized implementations in the SpaceTimeOrbitQuery, TimeCadenceQuery,
or TimeSeriesQuery subclasses.
    """
    def __init__(self, datasetInfo, ns={}):
        """Parse XML metadata from the schema queryableDataset and simply save the etree."""
        if isinstance(datasetInfo, types.StringType):
            self._info, self._ns = mkEtree(datasetInfo)
        else:
            self._info = datasetInfo
            self._ns = ns
    
    def info(self, path):
        """"Return the text value of a specified path in the XML info."""
        return xpathText(path, self._info, self._ns)

    def infos(self, path):
        """Return a list of text values from a specified path in the XML info."""
        return getChildList(path, self._info, self._ns)

    def getGeoRegionInfo(self, source, product, level, version, startTime, endTime,
                         latMin, latMax, lonMin, lonMax, responseGroups='Medium'):
        """Given a product specification and a space/time box, look up data objects that
match the query and return geoRegionInfo metadata.  Provided implmentations use a repeating
orbit table to look up space/time or bounding boxes (SpaceTimeOrbitQuery), algorithmically
compute what granules should be available from expected cadence (TimeCadenceQuery), or
subset a time series of data from accumulating files (TimeSeriesQuery).
        """
        pass

    def getDataById(self, objectIds):
        """Given a list of objectIds, return a (python) list of URLs for each objectId."""
        pass
    
    def geoRegionQuery(self, source, product, level, version, startTime, endTime, latMin,
                       latMax, lonMin, lonMax, responseGroups='Medium'):
        """
Given a product specification and a space/time box, look up data objects that
match the query and return geoRegionInfo metadata and optionally URLs.
Typical response groups are:
  'Small' - return objectIds and space/time metadata only
  'Medium' - add URLs
  'Large' - add the data itself for small datasets, or perhaps some data or a data summary.

The default implementation calls getGeoRegionInfo and getDataById.
Used for public geoRegionQuery SOAP service.
    """  
    # default impl
    pass

    def findDataById(self, objectIds):
        """Given an XML list of geoRegionInfo blocks (return from geoRegionQuery), look up URLs
for each objectId and add them to each block.  Used for public findDataById SOAP service.
        """
        pass

        
class TimeCadenceQuery(GeoRegionQuery):
    """GeoRegionQuery class that generates expected filenames at a given time cadence."""
    def __init__(self, datasetInfo):
        self._info, self._ns = mkEtree(datasetInfo)
        pubDirs = self.infos('publishAt/location/data')
        self.hostName = getHostName()
        localDirs = [dir for dir in pubDirs if dir.startswith('file:') and parseUrl(dir)[2] == hostName]
        if len(localDirs) > 0:
            self.localDir = localDirs[0]
        else:
            raise 'TimeCadenceQuery: Error, no registered data found for ' \
                      + '(source, product, level, version) = (%s, %s, %s, %s)' \
                      % (source, product, level, version)
        self.urlRoot = 'file://' + self.hostName + localDir + '/'

        self.fileTemplate = self.info('identification/fileTemplate')
        fileCadence, unit = valWithUnit(self.info('metadata/cadence'))
        if unit is None:
            try: unit = self.info('metadata/cadence/@unit')
            except: raise 'TimeCadenceQuery.getRegionInfo: Error, cadence must have unit.'
        self.timeDelta = cadence2timeDelta(fileCadence, unit)
    
    def getGeoRegionInfo(self, source, product, level, version, startTime, endTime, latMin,
                         latMax, lonMin, lonMax, responseGroups='Medium'):
        """Given a product specification and a time range, look up data objects that match
the query and return geoRegionInfo metadata.  The spatial bounding box is ignored.
        """
        return [self.urlRoot + templateSubst(self.fileTemplate, timeFields(t)) for t in \
                   evenTimeSequence(startTime, endTime, self.timeDelta)]
    
    def getDataById(self, objectIds):
        """Given a list of objectIds, return a (python) list of URLs for each objectId."""
        pass
    

    

# Utils follow.

def mkEtree(s):
    """Make an element tree and also return the extracted namespaces.
    """
    if not s.startswith('<'): s = urlopen(s).read()
    ns = extractNamespaces(s)
    return (XML(s), ns)

def xpathText(xpath, etree, ns):
    children = etree.xpath(xpath, namespaces=ns)
    if children:
        return children[0].text
    else:
        if ':' not in xpath:
            xpath = '_:' + xpath   # try adding default namespace to find tag
            return xpathText(xpath, etree, ns)
        else:
            return None

def getChildVals(keys, etree, ns):
    """Return a dictionary of sub-tag values for a list of input child tags."""
    return dict([(key, xpathText(key, etree, ns)) for key in keys])

def getChildList(xpath, etree, ns):
    """Return a list of values for child tags matching an xpath."""
    return [child.text for child in etree.xpath(xpath, namespaces=ns)]

def getHostName():
    return 'fubar'

    
