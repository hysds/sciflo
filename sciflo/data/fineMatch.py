#-----------------------------------------------------------------------------
# Name:        fineMatch.py
# Purpose:     Various fine matchup utilities.
#
# Author:      Gerald Manipon
#
# Created:     Fri Jun 8 17:06:01 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import Numeric as N
import MA
import math, re, types
import netCDF4 as NC
import hdfeos
from ArrayPrinter import array2string
import matplotlib
matplotlib.use('Agg', warn=False)
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as N2
import numpy.ma as M
import os, sys, re, traceback
from SOAPpy.WSDL import Proxy

from sciflo.utils import getEpochFromTimeString, getXmlEtree

MAJOR_AXIS_RADIUS = 6378.137
MINOR_AXIS_RADIUS = 6356.7523142
RADIUS_EARTH = (2 * MAJOR_AXIS_RADIUS + MINOR_AXIS_RADIUS)/3.
DEG2RAD = N.pi/180.

def getDistance(lon1,lat1, lon2, lat2):
    """Return distance in kilometers between a point specified by lon1/lat1 and
    another point or array of points specified by lon2/lat2."""
    
    #detect which array module to use
    typeList = [type(lon1), type(lon2), type(lat1), type(lat2)]
    if MA.MA.MaskedArray in typeList: Num = MA
    else: Num = N
    
    #calculate diffs
    dLat = lat2 - lat1
    dLon = lon2 - lon1
    
    #calculate distance using great circle
    dist = 2. * RADIUS_EARTH * \
        Num.arcsin( Num.sqrt( \
        (Num.sin(dLat * DEG2RAD/2.))**2 \
        + Num.cos(lat2 * DEG2RAD) \
        * Num.cos(lat1 * DEG2RAD) \
        * (Num.sin(dLon * DEG2RAD/2.))**2 \
    ))
    return dist

def fineMatchPointToSwath(coarseMatchDict, pointAggFile, swathFiles, swathName,
                          pointGeolocVarsDict, swathGeolocVarsDict, tolTime=60.0,
                          tolLoc=100.0, timePriority=True, pointUtcOffset=None,
                          swathUtcOffset=None, pointMissingValue=None,
                          swathMissingValue=None, pointObjectidVar='objectid',
                          pointPrematchupFilter=[], swathPrematchupFilter=[],
                          swathIdRegex=None, swathIdTmpl=None,
                          l1bSwathName=None, l1bSwathPrematchupFilter=[],
                          eosWsdl=None):
    """Return matchup dict containing matching swath objectid, point index,
    scan index, time difference, and distance:
    
    multiMatch[i].append([iAirs, iPoint, iScan, timeDiff, locDiff])"""

    import sciflo
    
    #if swathFiles is a single file, set it as a 1-item list
    if isinstance(swathFiles, types.StringTypes): swathFiles = [swathFiles]
    
    #fine matches
    fineMatchDict = {}
    
    #get point objectids sorted
    pointIds = coarseMatchDict.keys(); pointIds.sort()
    print "TOTAL COARSE MATCHUPS:", len(pointIds)
    
    #get AggregatePointData object and empty dict for SwathData objects for
    #caching purposes (reduced I/O); set utc offset and missing value if specified
    if pointUtcOffset is not None: pointGeolocVarsDict['utcOffset'] = pointUtcOffset
    if pointMissingValue is not None: pointGeolocVarsDict['missingValue'] = pointMissingValue
    aggData = AggregatePointData(pointAggFile, pointObjectidVar, **pointGeolocVarsDict)
    swathDataDict = {}
    l1bSwathDataDict = {}

    #get swathid regex
    if swathIdRegex: swathIdRegex = re.compile(swathIdRegex)

    #get EOS proxy
    if eosWsdl is not None: proxy = Proxy(eosWsdl)
    else: proxy = None
    
    #loop over coarse matchups
    for pointId in pointIds:
        print "=" * 80
        print "Running for pointId:", pointId
        print "timePriority:", timePriority
        #loop and get fine matches
        fineMatches = []
        swathNum = 0
        for swathIdx in coarseMatchDict[pointId]:
            print "-" * 80
            #swath file
            swathFile = swathFiles[swathIdx]
            
            #check swath file
            if swathFile == '': continue

            #get objectid
            objectid = None
            l1bSwathFile = None
            if swathIdRegex and None not in (swathIdTmpl, l1bSwathName, proxy):
                objectid = swathIdTmpl
                swathIdMatch = swathIdRegex.search(swathFile)
                if swathIdMatch:
                    for i, group in enumerate(swathIdMatch.groups()):
                        objectid = re.sub('\(\$%d\)' % (i+1), group, objectid)
                    retXml = proxy.findDataById([objectid], 'L1B.AIRS_Rad', 'v5')
                    retElt, nsDict = getXmlEtree(retXml)
                    for url in retElt.xpath('.//_default:url/text()', namespaces=nsDict):
                        if url.startswith('/') and not os.path.exists(url): continue
                        try: l1bSwathFile = sciflo.data.localize.localizeUrl(url)
                        except:
                            print >>sys.stderr, "Got error in localizeUrl: %s" % traceback.format_exc()
                            continue
                        break
            print "objectid is %s" % objectid
            print "l1bSwathFile is %s" % l1bSwathFile
                    
            #check swathDataDict if swathData is already cached
            if swathDataDict.has_key(swathFile):
                swathData = swathDataDict[swathFile]
            else:
                #set utc offset and missing value if specified
                if swathUtcOffset is not None: swathGeolocVarsDict['utcOffset'] = swathUtcOffset
                if swathMissingValue is not None: swathGeolocVarsDict['missingValue'] = swathMissingValue
                swathData = SwathData(swathFile, swathName, **swathGeolocVarsDict)
                swathDataDict[swathFile] = swathData
                
            #check l1bSwathDataDict if l1bSwathData is already cached
            if l1bSwathDataDict.has_key(l1bSwathFile):
                l1bSwathData = l1bSwathDataDict[l1bSwathFile]
            else:
                l1bSwathData = SwathData(l1bSwathFile, l1bSwathName, **swathGeolocVarsDict)
                l1bSwathDataDict[l1bSwathFile] = l1bSwathData
                
            #get fine match
            fineMatch = getFineMatchPointToSwath(pointId, aggData, swathData, tolTime, tolLoc,
                timePriority, pointPrematchupFilter, swathPrematchupFilter,
                l1bSwathData, l1bSwathPrematchupFilter, swathNum=swathNum)
            print "fineMatch result for %s %s #%d: %s" % (pointId, swathFile, swathNum, fineMatch)
            
            #if none was found, skip;  otherwise add to list of
            #fine matches
            if fineMatch is not None:
                matchDataList = [swathIdx]; matchDataList.extend(fineMatch)
                fineMatches.append(matchDataList)
                
            swathNum += 1
        
        #create fineMatch entry for point if matches found
        if len(fineMatches) > 0: fineMatchDict[pointId] = fineMatches

    print "#" * 80
    print "fineMatch:"
    print "Number of fine matches:", len(fineMatchDict)
    #keys = fineMatchDict.keys(); keys.sort()
    #for k in keys: print "%s: %s" % (k, fineMatchDict[k])
    return fineMatchDict

def getFilterMask(data, filterList):
    """Filter data using constraints in filter list and return mask."""
    
    #set default
    mask = None
    
    #loop over and build mask
    for filter in filterList:
        #get varname and build eval string
        varName, filterVal = filter
        if isinstance(filterVal, (types.ListType, types.TupleType)):
            if len(filterVal) != 3:
                raise RuntimeError, "Invalid number of items in filter: %s" % filterVal
            else: evalStr = 'N.logical_%s(varData %s, varData %s)' % \
                   (filterVal[0], filterVal[1], filterVal[2])
        elif isinstance(filterVal, types.StringTypes):
            evalStr = 'varData %s' % filterVal
        else: raise RuntimeError, "Unknown type for filter: %s" % filterVal
        
        #get data and get mask
        varMaskedData = data.container.getArray(varName, data.missingValue)
        varData = varMaskedData.filled()
        thisMask = eval(evalStr)
        if mask is None: mask = thisMask
        else: mask = N.logical_or(mask, thisMask)
        
    return mask

def maskData(mask, dataList):
    """Apply mask to data in list."""
    
    returnDataList = []
    for data in dataList:
        fillVal = data.fill_value()
        newData = MA.masked_where(mask, data, copy=1)
        newData.set_fill_value(fillVal)
        returnDataList.append(newData)
    return returnDataList

def getFineMatchPointToSwath(pointId, pointData, swathData, tolTime=60.0, tolLoc=100.0,
                             timePriority=True, pointPrematchupFilter=[],
                             swathPrematchupFilter=[], l1bSwathData=None,
                             l1bSwathPrematchupFilter=[], swathNum=0):
    """Get best match for point in swath data."""
    
    #from datetime import datetime
    #print datetime.utcfromtimestamp(pointData.timeData[0]), \
    #datetime.utcfromtimestamp(swathData.timeData[0,0])
    #print "got:", pointPrematchupFilter, pointPostmatchupFilter, swathPrematchupFilter, swathPostmatchupFilter
    
    #get point id index and retrieve point's lon/lat/time data
    pointIdx = pointData.objectidData.index(pointId)
    pointLon = pointData.lonData[pointIdx]
    pointLat = pointData.latData[pointIdx]
    pointTime = pointData.timeData[pointIdx]
    
    #get swath data
    swathLon = swathData.lonData
    swathLat = swathData.latData
    swathTime = swathData.timeData

    print "fineMatch pointId %s with swathId %s:" % (pointId, os.path.basename(swathData.file)), \
        pointLon, pointLat, swathLon[0,0], swathLon[0,29], swathLon[44,0], \
        swathLon[44,29], swathLat[0,0], swathLat[0,29], swathLat[44,0], \
        swathLat[44,29]
    #get point and swath prefilter masks
    pointPrematchupMask = getFilterMask(pointData, pointPrematchupFilter)
    swathPrematchupMask = getFilterMask(swathData, swathPrematchupFilter)

    #get l1b swath prefilter mask from airs resolution mask
    if l1bSwathData and l1bSwathPrematchupFilter:
        l1bSwathPrematchupMaskAirs = getFilterMask(l1bSwathData, l1bSwathPrematchupFilter)
        l1bSwathPrematchupMask = N.zeros(swathPrematchupMask.shape, 'i')
        for x in range(l1bSwathPrematchupMask.shape[0]):
            for y in range(l1bSwathPrematchupMask.shape[1]):
                l1bSwathPrematchupMask[x,y] = \
                    N.sometrue(N.ravel(l1bSwathPrematchupMaskAirs[x*3:x*3+3,y*3:y*3+3]))
    else: l1bSwathPrematchupMask = None
    
    #mask point data using prefilter
    if pointPrematchupMask is not None:
        pointLon, pointLat, pointTime = maskData(pointPrematchupMask,
                                                 [pointLon, pointLat, pointTime])
    
    #mask swath data using prefilter
    if swathPrematchupMask is not None:
            swathLon, swathLat, swathTime = maskData(swathPrematchupMask,
                                             [swathLon, swathLat, swathTime])
    
    #mask swath data using l1b prefilter
    if l1bSwathPrematchupMask is not None:
            swathLon, swathLat, swathTime = maskData(l1bSwathPrematchupMask,
                                             [swathLon, swathLat, swathTime])
    
    #get time diff in seconds; get mask of time diffs greater than tolerated
    timeDiffs = MA.fabs(pointTime - swathTime)
    closestTimeIdx = N2.unravel_index(N2.array(timeDiffs.filled()).argmin(), timeDiffs.shape)
    timeDiffData = timeDiffs.filled(1.e20)
    timeDiffMask = timeDiffData > tolTime
    print "timeTolerance:", tolTime
    #print "timdDiffData:", timeDiffData.flat[0:45]
    #print "time diff N.alltrue, N.sometrue:", N.alltrue(timeDiffMask.flat), N.sometrue(timeDiffMask.flat)
    
    #get distances in km; get mask of distances greater than tolerated
    dists = getDistance(pointLon, pointLat, swathLon, swathLat)
    closestIdx = N2.unravel_index(N2.array(dists.filled()).argmin(), dists.shape)
    distsData = dists.filled(1.e20)
    distsMask = distsData > tolLoc
    #print "dist N.alltrue, N.sometrue:", N.alltrue(distsMask.flat), N.sometrue(distsMask.flat)
    print "tolLoc:", tolLoc
    #print "distsData:", array2string(distsData)
    
    '''
    fig = plt.figure()
    fig.clf()
    m = Basemap(projection='cyl', llcrnrlat=-90, urcrnrlat=90, llcrnrlon=-180,
                urcrnrlon=180, resolution='c')
    airsPlot = m.scatter(swathData.lonData.filled().flat, #swathLon.filled().flat,
                         swathData.latData.filled().flat, #swathLat.filled().flat,
                         marker='d', s=1, c="g", edgecolors='none')
    #print "lonData:", swathData.lonData.shape, type(swathData.lonData.filled())
    #print "latData:", swathData.latData.shape, type(swathData.latData.filled())
    #print "timeDiffData:", timeDiffData.shape, type(N2.array(timeDiffData))
    #print "fill_value:", swathData.lonData.fill_value()
    #print "fill_value:", swathData.latData.fill_value()
    #c = m.contourf(N2.array(swathLon.filled(1e21)), N2.array(swathLat.filled(1e21)),
    #               M.masked_where(timeDiffData > 1e19, timeDiffData), 30, cmap=plt.cm.jet, colors=None)
    csPlot = m.scatter([pointLon], [pointLat], c='r', marker='d', s=50, edgecolors='none')
    cs2Plot = m.scatter([swathData.lonData.filled()[closestIdx]],
        [swathData.latData.filled()[closestIdx]], c='b',
        marker='d', s=50, edgecolors='none')
    cs3Plot = m.scatter([swathData.lonData.filled()[closestTimeIdx]],
        [swathData.latData.filled()[closestTimeIdx]], c='c',
        marker='d', s=50, edgecolors='none')
    #plt.colorbar(c, orientation='horizontal')
    m.drawcoastlines()
    m.drawparallels(N.arange(-90., 91., 30.))
    m.drawmeridians(N.arange(-180., 181., 60.))
    plt.title("%s/%s: %d, dist=%s, time=%s" % (pointId, os.path.basename(swathData.file),
                                               N.alltrue(distsMask.flat), dists[closestIdx],
                                               timeDiffs[closestTimeIdx]))
    plotDir = os.path.join('/tmp/gpsairs', pointId)
    if not os.path.isdir(plotDir): os.makedirs(plotDir)
    plotFile = os.path.join(plotDir, 'plot_%d.png' % swathNum)
    fig.savefig(plotFile)
    plt.close(fig)
    '''
    
    print "Closest dist:", dists[closestIdx]
    print "Closest time:", timeDiffs[closestTimeIdx]
    
    #get mask that satisfies both tolLoc and tolTime;
    #mask out time diff and dists data
    totalMask = N.logical_or(timeDiffMask, distsMask)
    N.putmask(timeDiffData, totalMask, 1.e20)
    N.putmask(distsData, totalMask, 1.e20)
    
    #return None if nothing passed
    if N.alltrue(totalMask.flat):
        #print "Returning None because nothing passed."    
        return None
    
    #if time priority, do closest in time
    if timePriority:
        #get scan/point index of smallest distance and get its distance
        minIdx = N.argmin(timeDiffData.flat)
        minScan = minIdx/timeDiffData.shape[1]
        minPoint = minIdx % timeDiffData.shape[1]
    #otherwise closest by distance
    else:
        #get scan/point index of smallest distance and get its distance
        minIdx = N.argmin(distsData.flat)
        minScan = minIdx/distsData.shape[1]
        minPoint = minIdx % distsData.shape[1]
        
    #get values for minimum time diff and distance
    minTimeDiff = timeDiffData[minScan, minPoint]
    minDist = distsData[minScan, minPoint]
    
    return [minPoint, minScan, minTimeDiff, minDist]

class DataError(Exception): pass
class Data(object):
    """Base class for data."""
    
    def __init__(self, file, lon='lon', lat='lat', time='time', utcOffset=None, missingValue=None):
        self.file = file
        self.lon = lon
        self.lat = lat
        self.time = time
        self.utcOffset = utcOffset
        self.missingValue = missingValue
        
        #opendap?
        if self.file.startswith('http') and \
            re.search(r'nph-dods', self.file, re.IGNORECASE):
            
            #if hdf, HdfContainer can already handle this
            if re.search(r'\.hdf', self.file, re.IGNORECASE):
                self.container = HdfContainer(self.file)
            #otherwise use DapContainer
            else:
                self.container = DapContainer(self.file)
            
        #assume local file
        else:
            #hdf or netcdf?
            if re.search(r'\.nc$', self.file, re.IGNORECASE):
                self.container = NetcdfContainer(self.file)
            elif re.search(r'\.hdf', self.file, re.IGNORECASE):
                self.container = HdfContainer(self.file)
            else: raise DataError, \
                "Cannot resolve local data container type: %s" % self.file
        
        #data type
        self.dataType = None
        
        #lon/lat/time data
        self.lonData = None
        self.latData = None
        self.timeData = None
    
class AggregatePointDataError(Exception): pass
class AggregatePointData(Data):
    """Class implementing interface for aggregate point data."""
    
    def __init__(self, pointAggFile, pointObjectidVar, lon='lon', lat='lat', time='time',
                 utcOffset=None, missingValue=None):
        super(AggregatePointData, self).__init__(pointAggFile, lon, lat, time,
                                                 utcOffset, missingValue)
        
        #var name for objectid
        self.objectidVar = pointObjectidVar
        
        #set data type
        self.dataType = 'point'
        self.container.dataType = self.dataType
        
        #get objectid list
        self.objectidData = [''.join(i).strip() for i in self.container.getArray(self.objectidVar).tolist()]
        
        #read in lon/lat/time data
        self.lonData = self.container.getArray(self.lon, self.missingValue)
        self.latData = self.container.getArray(self.lat, self.missingValue)
        self.timeData = self.container.getArray(self.time, self.missingValue)
        
        #add offset
        if self.utcOffset is not None: self.timeData += self.utcOffset

class SwathDataError(Exception): pass
class SwathData(Data):
    """Class implementing interface for swath data."""
    
    def __init__(self, swathFile, swathName, lon='lon', lat='lat', time='time',
                 utcOffset=None, missingValue=None):
        super(SwathData, self).__init__(swathFile, lon, lat, time, utcOffset,
                                        missingValue)
        
        #set data type
        self.dataType = 'swath'
        self.container.dataType = self.dataType
        
        #set swath name in container
        self.swathName = swathName
        self.container.globalSettingsDict['swath'] = self.swathName
        
        #read in lon/lat/time data
        self.lonData = self.container.getArray(self.lon, self.missingValue)
        self.latData = self.container.getArray(self.lat, self.missingValue)
        self.timeData = self.container.getArray(self.time, self.missingValue)
        
        #add offset
        if self.utcOffset is not None: self.timeData += self.utcOffset

class DataContainerError(Exception): pass
class DataContainer(object):
    """Base class implementing a data container interface."""
    
    def __init__(self, file, dataType=None):
        self.file = file
        self.dataType = dataType
        self.globalSettingsDict = {}
        
    def getArray(self, varName, missingValue=None):
        #get array
        data = self._getArray(varName)
        
        #if missing value is defined, return masked array.
        if missingValue is not None:
            return MA.masked_values(data, missingValue, copy=1, savespace=1)
        #otherwise return array
        else: return data
    
    def _getArray(self, varName): raise NotImplementedError, "Implement in subclass."

class NetcdfContainerError(Exception): pass
class NetcdfContainer(DataContainer):
    """Netcdf container class."""
    
    def __init__(self, file):
        super(NetcdfContainer, self).__init__(file)
        
        #open file
        self.ncObj = f = NC.Dataset(self.file)
        
    def _getArray(self, varName): return self.ncObj.variables[varName][:]
    def hasVar(self, varName): return varName in self.ncObj.variables

class HdfContainerError(Exception): pass
class HdfContainer(DataContainer):
    """Hdf container class."""
    
    def __init__(self, file):
        super(HdfContainer, self).__init__(file)
        
    def _getArray(self, varName):
        #swath type?
        if self.dataType == 'swath':
            if self.globalSettingsDict.has_key('swath'):
                try: return hdfeos.swath_field_read(self.file,
                                               self.globalSettingsDict['swath'],
                                               varName)
                except Exception, e:
                    raise HdfContainerError, "Error reading '%s' in %s: %s" % (varName, self.file, str(e))
            else: raise HdfContainerError, "Swath name undefined."
        else: raise NotImplementedError, "Not implemented for data type: %s" % self.dataType

class DapContainerError(Exception): pass
class DapContainer(DataContainer):
    """OPeNDAP container class."""
    
    def __init__(self, file):
        super(DapContainer, self).__init__(file)
