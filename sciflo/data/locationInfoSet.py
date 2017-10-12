#-----------------------------------------------------------------------------
# Name:        locationInfoSet.py
# Purpose:     Routines to extract & manipulate geolocation (XML) metadata
#              returned by GeoRegionQuery (SOAP) services.
#
# Author:      Brian Wilson
#              Gerald Manipon
#
# Created:     Mon Aug 06 09:19:36 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import re, types, bisect, socket
from urllib import urlopen
from lxml.etree import XML
from datetime import datetime, timedelta
import time
import Numeric as N
import matplotlib
matplotlib.use('Agg', warn=False)
import matplotlib.pylab as M
try:
   from matplotlib.toolkits.basemap import Basemap
except:
   from mpl_toolkits.basemap import Basemap

from sciflo.utils import getXmlEtree

DefaultNamespaces = '''xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"'''

class GeoInfo:
    """Geolocation info (metadata) for a granule, with URLs.
    """
    def __init__(self, info, ns={}):
        if isinstance(info, types.StringType): info, ns = mkEtree(info)
        self.objectId  = xpathText('_:objectid', info, ns)
        self.startTime = xpathText('_:starttime', info, ns)
        self.endTime   = xpathText('_:endtime', info, ns)
        self.latMin = floatOrNone(xpathText('_:latMin', info, ns))
        self.latMax = floatOrNone(xpathText('_:latMax', info, ns))
        self.lonMin = floatOrNone(xpathText('_:lonMin', info, ns))
        self.lonMax = floatOrNone(xpathText('_:lonMax', info, ns))
        self.urls = getUrls(info, ns)

    def __xml__(self):
        xml =  '<geoInfo %s>\n' % DefaultNamespaces
        xml += '  <objectid>%s</objectid>\n' % self.objectId
        xml += '  <starttime>%s</starttime>\n' % self.startTime
        xml += '  <endtime>%s</endtime>\n' % self.endTime
        if self.lonMin: xml += '  <lonMin type="float">%f</lonMin>\n' % self.lonMin
        if self.lonMax: xml += '  <lonMax type="float">%f</lonMax>\n' % self.lonMax
        if self.latMin: xml += '  <latMin type="float">%f</latMin>\n' % self.latMin
        if self.latMax: xml += '  <latMax type="float">%f</latMax>\n' % self.latMax
        if self.urls is not None and len(self.urls) >= 1:
            if len(self.urls) == 1:
                xml += '  <url>%s</url>\n' % self.urls[0]
            else:
                xml += '  <urls>\n'
                for url in self.urls:
                    xml += '    <url>%s</url>\n' % url
                xml += '  </urls>\n'
        xml += '</geoInfo>\n'
        return xml

    def __repr__(self):
        return self.__xml__()


def floatOrNone(s):
    try:
        return float(s)
    except:
        return None
    
def getUrls(objloc, ns):
    """Return a list of URL's in geolocation infoset (could be list of one URL or empty list).
    """
    if objloc.xpath('_:urls', namespaces=ns):
        return getChildList('_:urls/_:url', objloc, ns)
    url = xpathText('_:url', objloc, ns)
    if url:
        return [url]
    else:
        return []
    
def minLonSpan(lonMin, lonMax):
    if abs(lonMax - lonMin) > 180.:
        if abs(lonMax - 360 - lonMin) < 180:
            return (lonMin, lonMax - 360.)
        if abs(lonMax - lonMin - 360.) < 180.:
            return (lonMin + 360., lonMax)
        raise 'minLonSpan: Cannot minimize longitude span for: %f, %f' % (lonMin, lonMax)
    else:
        return lonMin, lonMax

def longitudeBetween(lon, lonMin, lonMax):
    """Determine if a given longitude is inside a longitude range, dealing properly
with the normalization issue.
    """
    if lonMin < 0.:  # lon range specified in [-180, 180) normalization
        if lon > 180.: lon -= 360.
    else:            # lon range specified in [0, 360) normalization
        if lon < 0.: lon += 360.
    return (lon >= lonMin and lon <= lonMax)


def mkInfoset(infoset, ns={}):
    """Convert a geolocation infoset (XML) into a list of GeoInfo objects.
    """
    if isinstance(infoset, types.ListType): return infoset
    if isinstance(infoset, types.StringType): infoset, ns = mkEtree(infoset)
    return [GeoInfo(elem, ns) for elem in infoset]

def getStartTimes(infoset):
    """Extract list of start times from geolocationInfoset."""
    return [mkDatetime(item.startTime) for item in mkInfoset(infoset)]

def timeSubset(startTime, endTime, infoset, ns={}):
    """Subset a geolocation infoset (XML) by time, returning a new (XML) infoset.
    """
    if isinstance(startTime, types.StringType): startTime = mkDatetime(startTime)
    if isinstance(endTime, types.StringType):   endTime = mkDatetime(endTime)
    if isinstance(infoset, types.StringType): infoset, ns = mkEtree(infoset)
    xmls = '<geoInfos>\n'
    for elem in infoset:
        geoInfo = GeoInfo(elem, ns)
        if mkDatetime(geoInfo.startTime) < endTime and \
           mkDatetime(geoInfo.endTime) > startTime:
            xmls += xml(geoInfo)
    xmls += '</geoInfos>\n'
    return xmls

def mkDatetime(datetimeStr):
    """Make a datetime object from a date/time string YYYY-MM-DD HH:MM:SS"""
    if len(datetimeStr) < 11: datetimeStr += 'T00:00:00'
    if datetimeStr[10] != 'T': datetimeStr = datetimeStr[0:10] + 'T' + datetimeStr[11:]
    if datetimeStr[-1] == 'Z': datetimeStr = datetimeStr[:-1]
    m = re.search(r'^(.*?)\.\d+$', datetimeStr)
    if m: datetimeStr = m.group(1)

    return datetime.fromtimestamp( time.mktime(
               time.strptime(datetimeStr, '%Y-%m-%dT%H:%M:%S')))

def datetime2sec(dt):
    """Convert a datetime object to a time object (float sec. past epoch)."""
    return time.mktime(dt.timetuple())

def sec2datetime(sec):
    """Convert float sec. past epoch  to a datetime object."""
    return datetime.utcfromtimestamp(sec)

def datetime2ymd(dt):
    if isinstance(dt, types.StringType):
        t = dt
    else:
        t = dt.isoformat()
    return (int(t[0:4]), int(t[5:7]), int(t[8:10]))

def daysInPeriod(startTime, endTime):
    if isinstance(startTime, types.StringType): startTime = mkDatetime(startTime)
    if isinstance(endTime, types.StringType):   endTime = mkDatetime(endTime)
    delta = timedelta(1)
    t = startTime
    while t < endTime:
        t0 = t
        t = t + delta
        yield (t0, t)

def geoGridCellIndex(lat, lon, latMin, latMax, latRes, lonMin, lonMax, lonRes, reverseLat=False):
    """Lookup cell in a GeoGrid that a (lat, lon) point falls into.
Returns row/col indices (ilat, ilon).
    """
    lats = mkStrided1DGrid(latMin, latMax, latRes, inclusive=True)
    ilat = bisect.bisect_left(lats, lat)
    lons = mkStrided1DGrid(lonMin, lonMax, lonRes, inclusive=True)
    ilon = bisect.bisect_left(lons, lon)
    if reverseLat:
        return (len(lats) - ilat, ilon)
    else:
        return (ilat, ilon)

def mkStrided1DGrid(min, max, stride, inclusive=False, dtype='f'):
    if inclusive:
        return N.arange(min, max+stride, stride, dtype)
    else:
        return N.arange(min, max, stride, dtype)

def mkCentered1DGrid(min, max, stride, inclusive=False):
    return N.arange(min, max, stride) + stride/2.


def geoImageMap(latMin, latMax, latRes, lonMin, lonMax, lonRes, grid, itemFn,
                imageFile='gridImage.png', imageWidth=640, imageHeight=480):
    """Create an HTML image map for a 2D GeoGridded dataset.
Each lat/lon cell is a hot spot, pointing to the output of itemFn(grid[ilat][ilon])
    """
    imageFile = geoGridImage(latMin, latMax, latRes, lonMin, lonMax, lonRes,
                             imageFile, imageWidth, imageHeight)
    tmpl = \
'''<img src="${imageFile}" usemap="#${imageFile}_map" border="0">
<map name="${imageFile}_map"
  <area shape="rect" coords="trx, try, blx, bly" href="hist1.png">
</map>
'''
    pass

def geoGridImage(latMin, latMax, latRes, lonMin, lonMax, lonRes,
                 imageFile='gridImage.png', imageWidth=640, imageHeight=480, dpi=100):
    width = float(imageWidth)/dpi; height = float(imageHeight)/dpi
    f = M.figure(figsize=(width,height)).add_axes([0.,0.,1.,1.])  # map fills figure
    m = Basemap(lonMin, latMin, lonMax, latMax, projection='cyl',
                lon_0=(lonMin+lonMax)/2)
    m.drawcoastlines()
    m.drawmeridians(mkStrided1DGrid(lonMin, lonMax, lonRes), labels=[0,0,0,0], linestyle='-')
    m.drawparallels(mkStrided1DGrid(latMin, latMax, latRes), labels=[0,0,0,0], linestyle='-')
    M.savefig(imageFile, dpi=dpi)
    return imageFile

# XML utils follow.

def pyListOfTables2xml(ts, listTags=('<list %s>' % DefaultNamespaces, ''),
                       tableTags=('<table>', '<row>', '<col>'),
                       itemTags=('<item>', '</item>'), indent=''):
    out = emitOpenTag(listTags[0], indent); indent = '\n' + indent + '  '
    tblTags = list(tableTags)
    for t in ts:
        nRows = len(t); nCols = len(t[0])
        tblTag = tblTags[0][:-1] + ' nRows="%d" nCols="%d"' % (nRows, nCols) + '>'
        out += emitOpenTag(listTags[1]+tblTag, indent); indent += '  '
        for row in t:
            out += emitOpenTag(tblTags[1], indent)
            for col in row:
                out += emitOpenTag(tblTags[2]) + emitOpenTag(itemTags[0])
                out += str(col)
                out += emitCloseTag(itemTags[1]) + emitCloseTag(tblTags[2])
            out += emitCloseTag(tblTags[1], indent)
        indent = indent[:-2]; out += emitCloseTag(tblTags[0]+listTags[1], indent)
    indent = indent[:-2]; out +=  emitCloseTag(listTags[0], indent)
    return out

def emitOpenTag(tag, indent=''):
    if tag == '': return ''
    if tag[0] == '<' and tag[-1] == '>':
        return indent + tag
    else:
        return tag

def emitCloseTag(tag, indent=''):
    if tag == '': return ''
    if tag[0] == '<' and tag[-1] == '>':
        if tag[1] != '/':
            tag = tag[1:tag.find(' ')]
            return indent + '</' + tag + '>'
    return tag

def pyListOfTables2html(ts):
    return '<html>\n  <body>' + \
           listOfTables2xml(ts, listTags=('<ol>', '<li>'),
                            tableTags=('<table>', '<tr>', '<th>'),
                            itemTags=('<a href="', '"/>'), indent='\n    ') + \
           '\n  </body>\n<html>\n'

def textOrChildText(elem):
    try:
        return elem[0].text
    except:
        try:
            return elem.text
        except:
            return None

def listOfTables2listOfCells(lot, i, j, xpath=None, cellExtract=textOrChildText):
    if isinstance(lot, types.ListType):
        return [cellExtract(elem[i][j]) for elem in lot]
    elif isinstance(lot, types.StringType):  # assume xml
        etree, ns = mkEtree(lot)
#        return [cellExtract(elem[i][j]) for elem in etree]
        listTag = prefixTag(etree.tag, ns)
        tableTag = prefixTag(etree[0].tag, ns)
        rowTag = prefixTag(etree[0][0].tag, ns)
        colTag = prefixTag(etree[0][0][0].tag, ns)
        xp = '/%s/%s/%s[%d]/%s[%d]/%s' % (listTag, tableTag, rowTag, i, colTag, j, xpath)
        return [cellExtract(cell) for cell in etree.xpath(xp, namespaces=ns)]

def listOfTables2listOfGridVals(lot, xpath=None, itemExtract=textOrChildText):
    if isinstance(lot, types.ListType):
        return [elem for elem in lot]
    elif isinstance(lot, types.StringType):  # assume xml
        etree, ns = mkEtree(lot)
        return [[[floatOrMissing(itemExtract(col.xpath(xpath, namespaces=ns))) for col in row]
                 for row in elem] for elem in etree]

def floatOrMissing(val, missingValue=-9999.):
    try: return float(val)
    except: return missingValue
    
def prefixTag(qname, namespaces):
    """Convert a qualified name '{ns}tag' to 'prefix:tag' form using a namespace dictionary."""
    i = qname.index('}')
    ns = qname[1:i]; tag = qname[i+1:]
    for prefix, namespace in namespaces.iteritems():
        if ns == namespace: return prefix + ':' + tag
    raise 'prefixTag: Namespace {%s}%s not found in dictionary %s.' % (ns, tag, str(namespaces))
    

def xml(obj):
    """Master function to generate XML representation for any object, like str().
    """
    if isinstance(obj, types.StringType): return obj
    if hasattr(obj, '__xml__'): return obj.__xml__()
    if isinstance(obj, types.DictType): return dict2xml(obj)
    if isinstance(obj, types.ListType):
        if isinstance(obj[0], types.TupleType) or isinstance(obj[0], types.ListType):
            return listOfTuple2xml(obj)
        elif hasattr(obj[0], '__xml__'):
            return '<list>\n' + '\n'.join(map(xml, obj)) + '\n</list>\n'
    raise 'Object %s does not define __xml__ method' % str(obj)

def dict2xml(d):
    items = ['<'+tag+'>' + str(val) + '</'+tag+'>' for tag, val in d.iteritems()]
    return ''.join(items)
        
def listOfTuple2xml(lot):
    items = ['<'+item[0]+'>' + str(item[1]) + '</'+item[0]+'>' for item in lot]
    return ''.join(items)
        
def mkEtree(s):
    """Make an element tree and also return the extracted namespaces.
    """
    et, ns = getXmlEtree(s)
    if not ns.has_key('_'): ns['_'] = ns['_default']
    return (et, ns)

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

NS = '{http://sciflo.jpl.nasa.gov/2006v1/sf}'  # SciFlo namespace

def ns(xpath, ns=NS):
    """Add default namespace to an XPath (to all tags without prefixes)"""
    sep = ':'
    if ns[0] == '{': sep = ''

    def addNSIfNone(tag, ns, sep=sep):
        if tag == '' or tag == '.' or '{' in tag or ':' in tag:
            return tag
        else:
            return ns + sep + tag

    return ''.join( [addNSIfNone(elt.tag) for elt in xpath] )


def xmlList2text(xml, tags=None, want='text', ns=NS):
    def wantTag(tag, tags):
        """We want the tag if text like it is in the tags list, or we want every tag if the tags
list is empty.
        """
        if tags is None: return True
        for t in tags:
            if t in tag:
                return True
        return False

    def simpleTag(tag):
        """Simplify tag by discarding namespace if it is a qualified name, {ns}tag."""
        if '}' in tag: return tag[tag.find('}')+1:]

    data = []
    for i, item in enumerate(XML(xml)):
        if i == 0:
            data.append( [simpleTag(elt.tag) for elt in item if wantTag(elt.tag, tags)] )
        data.append( [elt.text for elt in item if wantTag(elt.tag, tags)] )
    if want == 'list':
        return data
    elif want == 'text':
        data = map(' '.join, data)
    elif want == 'cvs':
        data = map(', '.join, data)
    if len(data) > 0: data[0] = '#' + data[0]   # make column headers a comment line
    return '\n'.join(data)


def getFirstUrlFromMeta(aeroInfo, ns=NS):
    """Find first URL in XML return from GeoRegionQuery."""
    url = None
    urlTag = XML(aeroInfo).find(ns+'result/' + ns+'urls/' + ns+'url')
    if urlTag is not None: url = urlTag.text
    return url


def floatOrDate(s):
    """Try to convert a string to a float value, or a datetime value, else return string."""
    try: return float(s)
    except:
        try: return mkDatetime(s)
        except: return s

def mkTime(datetimeStr):
    """Make a time object (float sec. past epoch) from a date/time string YYYY-MM-DD HH:MM:SS"""
    return time.mktime( time.strptime(datetimeStr, '%Y-%m-%d %H:%M:%S') )

if __name__ == '__main__':
    startTime = '2001-01-01 00:00:00'
    endTime =   '2001-01-03 00:00:00'
    latMin = -30.
    latMax =  10.
    lonMin =   0.
    lonMax =  30.
    lat = -20.
    lon = 10.
    latRes = 1.; lonRes = 1.

    geoGridImage(latMin, latMax, latRes, lonMin, lonMax, lonRes,
                 imageFile='gridImage.png')

