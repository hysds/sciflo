#-----------------------------------------------------------------------------
# Name:        coarseMatch.py
# Purpose:     Various coarse matchup utilities.
#
# Author:      Benyang Tang
#              Gerald Manipon
#
# Created:     Mon May 16 17:06:01 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import Numeric as N
import math
from Polygon import Polygon
import numpy
import time

from geolocation import *
from sciflo.utils import getEpochFromTimeString

def km2LonLat(tolLoc, lat):
	radiusEarth = 6400
	temp1 = radiusEarth*math.cos(N.pi/180*lat)
	km2dLon = 360.0/(2*temp1*N.pi)
	km2dLat =  360.0/(2*radiusEarth*N.pi)
	return km2dLon, km2dLat

def coarseMatchPointToSwath_orig(pointsGeolocDict, swathsGeolocDict, timeTol,
							locTol):
	"""Wrapper to pointToSwathCoarseMatchup() function to return coarse
	matchup.
	"""
	
	#create PointGeolocationSet object
	pointObj = PointGeolocationSet(pointsGeolocDict)

	#create SwathGeolocationSet object
	swathObj = SwathGeolocationSet(swathsGeolocDict)
	
	#run matchup
	return pointToSwathCoarseMatchup(pointObj,swathObj,timeTol,locTol)

def coarseMatchPointToSwath_Polygon(pointsGeolocDict, swathsGeolocDict, timeTol,
							locTol):
	"""Wrapper to pointToSwathCoarseMatchup() function to return coarse
	matchup.
	"""
	
	#sort objectids
	sortedPointIds = pointsGeolocDict.keys(); sortedPointIds.sort()
	sortedSwathIds = swathsGeolocDict.keys(); sortedSwathIds.sort()
	
	#create swath polygons
	swathPolygons = {}
	for swathId in sortedSwathIds:
		w, e, s, n = swathsGeolocDict[swathId][2:]
		swathPolygons[swathId] = Polygon(((w, s), (e, s), (e, n), (w, n)))
	
	#loop over points
	swathIdList = []
	matchupDict = {}
	for pointId in sortedPointIds:
		#get epochs
		pointStartEpoch = getEpochFromTimeString(pointsGeolocDict[pointId][0])
		pointEndEpoch = getEpochFromTimeString(pointsGeolocDict[pointId][1])
		
		#point lat/lon
		pointLat, pointLon = pointsGeolocDict[pointId][2:]
		
		#turn tolLoc to km
		km2dLon,km2dLat = km2LonLat(locTol, pointLat)
		tolLocLon = locTol*km2dLon
		tolLocLat = locTol*km2dLat
		
		#create point box using tolerances
		w = pointLon - tolLocLon
		if w >= 360.: w = w - 360.
		e = pointLon + tolLocLon
		if e >= 360.: e = e - 360.
		n = pointLat + tolLocLat
		s = pointLat - tolLocLat
		pointPolygon = Polygon(((w, s), (e, s), (n, e), (n, w)))
		
		for swathId in sortedSwathIds:
			#get epochs
			swathStartEpoch = getEpochFromTimeString(swathsGeolocDict[swathId][0]) - timeTol
			swathEndEpoch = getEpochFromTimeString(swathsGeolocDict[swathId][1]) + timeTol
			
			#check time overlap
			if (pointStartEpoch >= swathStartEpoch and pointStartEpoch <= swathEndEpoch) or \
			   (pointEndEpoch >= swathStartEpoch and pointEndEpoch <= swathEndEpoch) or \
			   (pointStartEpoch <= swathStartEpoch and pointEndEpoch >= swathEndEpoch): pass
			else: continue
				
			#check location overlap
			if swathPolygons[swathId].overlaps(pointPolygon):
				if swathId not in swathIdList: swathIdList.append(swathId)
				idx = swathIdList.index(swathId) 
				if matchupDict.has_key(pointId): matchupDict[pointId].append(idx)
				else: matchupDict[pointId] = [idx]
	return (matchupDict, swathIdList)

def coarseMatchPointToSwath_numpy(pointsGeolocDict, swathsGeolocDict, timeTol,
							locTol):
	"""Wrapper to pointToSwathCoarseMatchup() function to return coarse
	matchup.
	"""
	
	print "#" * 80

	#sort objectids
	sortedPointIds = numpy.array(pointsGeolocDict.keys()); sortedPointIds.sort()
	sortedSwathIds = numpy.array(swathsGeolocDict.keys()); sortedSwathIds.sort()
	print "Got %d pointIds" % len(sortedPointIds)
	print "Got %d swathIds" % len(sortedSwathIds)
	print "timeTol:", timeTol
	print "locTol:", locTol
	
	#create lists
	pointTimes = []
	pointBounds = []
	swathTimes = []
	swathBounds = []
	
	#create swath arrays
	for swathId in sortedSwathIds:
		(t1, t2, w, e, s, n) = swathsGeolocDict[swathId]
		t1 = getEpochFromTimeString(t1)
		t2 = getEpochFromTimeString(t2)
		swathTimes.append([t1, t2])
		if w > e: e += 360.
		swathBounds.append([w, e, s, n])
	swathTimes = numpy.array(swathTimes)
	swathBounds = numpy.array(swathBounds)
	
	#create point arrays
	for pointId in sortedPointIds:
		(t1, t2, lat, lon) = pointsGeolocDict[pointId]
		t1 = getEpochFromTimeString(t1) - timeTol
		t2 = getEpochFromTimeString(t2) + timeTol
		pointTimes.append([t1, t2])
		
		#turn tolLoc to km
		km2dLon, km2dLat = km2LonLat(locTol, lat)
		tolLocLon = locTol*km2dLon
		tolLocLat = locTol*km2dLat
		
		#create point box using tolerances
		w = lon - tolLocLon
		e = lon + tolLocLon
		if w > e: e += 360.
		n = lat + tolLocLat
		s = lat - tolLocLat
		pointBounds.append([w, e, s, n])
	pointTimes = numpy.array(pointTimes)
	pointBounds = numpy.array(pointBounds)
	
	#loop over points
	swathIdList = []
	matchupDict = {}
	for pointIdx, pointId in enumerate(sortedPointIds):
		
		print "-" * 80
		print "Finding coarse match for %s" % pointId

		#get time matches
		timeMatch = (
			((pointTimes[pointIdx, 0] >= swathTimes[:, 0]) &
			 (pointTimes[pointIdx, 0] <= swathTimes[:, 1])) |
			((pointTimes[pointIdx, 1] >= swathTimes[:, 0]) &
			 (pointTimes[pointIdx, 1] <= swathTimes[:, 1])) |
			((pointTimes[pointIdx, 0] <= swathTimes[:, 0]) &
			 (pointTimes[pointIdx, 1] >= swathTimes[:, 1]))
		)
		print "timeMatch indices:", numpy.where(timeMatch == True)[0]
		
		#get lon/lat location matches
		lonMatch = (
			((pointBounds[pointIdx, 0] >= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 0] <= swathBounds[:, 1])) |
			((pointBounds[pointIdx, 1] >= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 1] <= swathBounds[:, 1])) |
			((pointBounds[pointIdx, 0] <= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 1] >= swathBounds[:, 1])) |
			((pointBounds[pointIdx, 0]+360. >= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 0]+360. <= swathBounds[:, 1])) |
			((pointBounds[pointIdx, 1]+360. >= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 1]+360. <= swathBounds[:, 1])) |
			((pointBounds[pointIdx, 0]+360. <= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 1]+360. >= swathBounds[:, 1])))
		latMatch = (
			((pointBounds[pointIdx, 2] >= swathBounds[:, 2]) &
				(pointBounds[pointIdx, 2] <= swathBounds[:, 3])) |
			((pointBounds[pointIdx, 3] >= swathBounds[:, 2]) &
				(pointBounds[pointIdx, 3] <= swathBounds[:, 3])) |
			((pointBounds[pointIdx, 2] <= swathBounds[:, 2]) &
				(pointBounds[pointIdx, 3] >= swathBounds[:, 3])))
		locMatch = numpy.logical_and(lonMatch, latMatch)
		print "locMatch indices:", numpy.where(locMatch == True)[0]
		
		#get indexes that matched in time and location
		overallMatch = numpy.logical_and(timeMatch, locMatch)
		overallMatchIdxs = numpy.where(overallMatch == True)[0]
		print "overallMatch indices:", overallMatchIdxs
		matchedIds = sortedSwathIds.take(overallMatchIdxs)
		
		#add matched point/swaths
		if len(overallMatchIdxs) > 0:
			for i, swathId in enumerate(matchedIds):
				if swathId not in swathIdList: swathIdList.append(swathId)
				idx = swathIdList.index(swathId) 
				if matchupDict.has_key(pointId): matchupDict[pointId].append(idx)
				else: matchupDict[pointId] = [idx]
	
	if len(matchupDict) == 0:
		raise RuntimeError("Failed to find coarse matchups.")
	else:
		print "Found %d coarse matchups." % len(matchupDict)

	#return
	return (matchupDict, swathIdList)

def coarseMatchPointToSwath_new(pointsGeolocDict, swathsGeolocDict, timeTol,
							locTol):
	"""Wrapper to pointToSwathCoarseMatchup() function to return coarse
	matchup.
	"""
	
	#sort objectids
	sortedPointIds = pointsGeolocDict.keys(); sortedPointIds.sort()
	sortedSwathIds = swathsGeolocDict.keys(); sortedSwathIds.sort()
	
	#create lists
	pointTimes = []
	pointBounds = []
	swathTimes = []
	swathBounds = []
	
	#create swath arrays
	for swathId in sortedSwathIds:
		(t1, t2, w, e, s, n) = swathsGeolocDict[swathId]
		t1 = getEpochFromTimeString(t1)
		t2 = getEpochFromTimeString(t2)
		swathTimes.append([t1, t2])
		if (e - w) >= 180.:
			eOrig = e; e = w + 360.; w = eOrig
		swathBounds.append([w, e, s, n])
	swathTimes = N.array(swathTimes)
	swathBounds = N.array(swathBounds)
	
	#create point arrays
	for pointId in sortedPointIds:
		(t1, t2, lat, lon) = pointsGeolocDict[pointId][0:4]
		t1 = getEpochFromTimeString(t1) - timeTol
		t2 = getEpochFromTimeString(t2) + timeTol
		pointTimes.append([t1, t2])
		
		#turn tolLoc to km
		km2dLon, km2dLat = km2LonLat(locTol, lat)
		tolLocLon = locTol*km2dLon
		tolLocLat = locTol*km2dLat
		
		#create point box using tolerances
		w = lon - tolLocLon
		e = lon + tolLocLon
		if (e - w) >= 180.:
			eOrig = e; e = w + 360.; w = eOrig
		n = lat + tolLocLat
		s = lat - tolLocLat
		pointBounds.append([w, e, s, n])
	pointTimes = N.array(pointTimes)
	pointBounds = N.array(pointBounds)
	
	#loop over points
	swathIdList = []
	matchupDict = {}
	for pointIdx, pointId in enumerate(sortedPointIds):
		
		#get time matches
		timeMatch = (
			((pointTimes[pointIdx, 0] >= swathTimes[:, 0]) &
			 (pointTimes[pointIdx, 0] <= swathTimes[:, 1])) |
			((pointTimes[pointIdx, 1] >= swathTimes[:, 0]) &
			 (pointTimes[pointIdx, 1] <= swathTimes[:, 1])) |
			((pointTimes[pointIdx, 0] <= swathTimes[:, 0]) &
			 (pointTimes[pointIdx, 1] >= swathTimes[:, 1]))
		)
		
		#get lon/lat location matches
		lonMatch = (
			((pointBounds[pointIdx, 0] >= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 0] <= swathBounds[:, 1])) |
			((pointBounds[pointIdx, 1] >= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 1] <= swathBounds[:, 1])) |
			((pointBounds[pointIdx, 0] <= swathBounds[:, 0]) &
				(pointBounds[pointIdx, 1] >= swathBounds[:, 1])) |
			(N.fabs(pointBounds[pointIdx, 0] - swathBounds[:, 1]) >= 360.) |
			(N.fabs(pointBounds[pointIdx, 1] - swathBounds[:, 0]) >= 360.))
		latMatch = (
			((pointBounds[pointIdx, 2] >= swathBounds[:, 2]) &
				(pointBounds[pointIdx, 2] <= swathBounds[:, 3])) |
			((pointBounds[pointIdx, 3] >= swathBounds[:, 2]) &
				(pointBounds[pointIdx, 3] <= swathBounds[:, 3])) |
			((pointBounds[pointIdx, 2] <= swathBounds[:, 2]) &
				(pointBounds[pointIdx, 3] >= swathBounds[:, 3])))
		locMatch = N.logical_and(lonMatch, latMatch)
		
		#get indexes that matched in time and location
		overallMatch = N.logical_and(timeMatch, locMatch)
		overallMatchIdxs = N.nonzero(overallMatch)
		matchedIds = [sortedSwathIds[i] for i in overallMatchIdxs]
		
		#add matched point/swaths
		if len(overallMatchIdxs) > 0:
			for i, swathId in enumerate(matchedIds):
				if swathId not in swathIdList: swathIdList.append(swathId)
				idx = swathIdList.index(swathId) 
				if matchupDict.has_key(pointId): matchupDict[pointId].append(idx)
				else: matchupDict[pointId] = [idx]
	
	#return
	return (matchupDict, swathIdList)

def coarseMatchPointToSwath(pointsGeolocDict, swathsGeolocDict, timeTol,
							locTol):
	"""Wrapper function."""
	
	#starttime = time.time()
	matchupDict, swathIdList = coarseMatchPointToSwath_numpy(pointsGeolocDict,
		swathsGeolocDict, timeTol, locTol)
	#print "len:", len(matchupDict), len(swathIdList)
	#print "time: %s" % (time.time() - starttime)
	#print matchupDict, swathIdList
	return (matchupDict, swathIdList)

def pointToSwathCoarseMatchup(pointsSetObj,swathsSetObj,
							  timeTolerance,locationTolerance):
	"""Returns a dict of lists where the point-data objectids are the keys and the coarse
	matched swath-data objectids are contained in the corresponding list.

	e.g. pointToSwathMatchupDict={
						'point_objectid_1': ['swath_objectid_1','swath_objectid_43',
						                     'swath_objectid_200'],
						'point_objectid_33' : ['swath_objectid_34',],
						'point_objectid_53' : ['swath_objectid_334','swath_objectid_679'],
						}
	"""

	#get list of point-data and swath data arrays
	pointsIdList = pointsSetObj.getObjectidList()
	pointsStarttimeArray = pointsSetObj.getStarttimeArray()
	pointsEndtimeArray = pointsSetObj.getEndtimeArray()
	pointsLatitudeArray = pointsSetObj.getLatitudeArray()
	pointsLongitudeArray = pointsSetObj.getLongitudeArray()
	swathsIdList = swathsSetObj.getObjectidList()
	swathsStarttimeArray = swathsSetObj.getStarttimeArray()
	swathsEndtimeArray = swathsSetObj.getEndtimeArray()
	swathsWestArray = swathsSetObj.getWestArray()
	swathsEastArray = swathsSetObj.getEastArray()
	swathsSouthArray = swathsSetObj.getSouthArray()
	swathsNorthArray = swathsSetObj.getNorthArray()

	#add time tolerance to swath's starttime and endtime arrays
	swathsStarttimeArray = swathsStarttimeArray-timeTolerance
	swathsEndtimeArray = swathsEndtimeArray+timeTolerance

	#time match
	temp1 = N.nonzero(N.logical_and( pointsStarttimeArray >= swathsStarttimeArray[0],
									pointsEndtimeArray <= swathsEndtimeArray[-1]))

	i1 = temp1[0]
	i2 = temp1[-1]

	#print "temp1",temp1
	#print "swathsIdList",len(swathsIdList)
	#print swathsEndtimeArray[-1]

	timeMatch1 = {}
	jj0 = 0
	for i in range(i1,i2+1):
		jj1 = 0; jj2 = 0; foundStart = 0
		for j in range(jj0,len(swathsIdList)):
			if pointsStarttimeArray[i] >= swathsStarttimeArray[j] \
								 and pointsEndtimeArray[i] <= swathsEndtimeArray[j]:
				if foundStart == 0:
					foundStart = 1
					jj1 = jj0 = j
			else:
				if foundStart == 1:
					jj2 = j - 1
					break

		#print 'i, jj1, jj2 = ', i, jj1, jj2

		if jj2 > jj1:
			timeMatch1[i] = range(jj1,jj2 + 1)

	#print 'number of time matched: %d ' %len(timeMatch1)

	#bounding box match
	coarseMatch = {}
	swathsIdCum = N.zeros((len(swathsIdList),))
	#print "timeMatch1:",timeMatch1
	#print "swathsWestArray",swathsWestArray[-9:-1],len(swathsWestArray)
	for i in timeMatch1.keys():
		#turn tolLoc to km
		km2dLon,km2dLat = km2LonLat(locationTolerance, pointsLatitudeArray[i])
		tolLocLon = locationTolerance*km2dLon
		tolLocLat = locationTolerance*km2dLat

		index1 = timeMatch1[i]
		swathsWestArray2 = N.take(swathsWestArray,index1)
		swathsEastArray2 = N.take(swathsEastArray,index1)
		swathsSouthArray2 = N.take(swathsSouthArray,index1)
		swathsNorthArray2 = N.take(swathsNorthArray,index1)

		temp1 = N.logical_and(pointsLatitudeArray[i] >= swathsSouthArray2-tolLocLat,
							pointsLatitudeArray[i] <= swathsNorthArray2+tolLocLat)

		#need a change to take care of the cyclic lon
		temp2 = N.logical_and(pointsLongitudeArray[i] >= swathsWestArray2-tolLocLon,
							pointsLongitudeArray[i] <= swathsEastArray2+tolLocLon)

		temp3 = N.logical_and(temp1,temp2)
		temp4 = N.nonzero(temp3)
		temp5 = N.take(index1,temp4)
		N.put(swathsIdCum,temp5,1)

		if temp5.shape[0] > 0:
			coarseMatch[i] = temp5

	swathsIdCum1 = N.nonzero(swathsIdCum)
	swathsIdCum2 = [swathsIdList[i] for i in swathsIdCum1]

	#change the matched swaths objectids of the coarseMatch
	allSwathsMatched = N.cumsum(swathsIdCum)-1
	coarseMatch1 = {}
	for i in coarseMatch.keys():
		coarseMatch1[pointsIdList[i]] = N.take(allSwathsMatched, coarseMatch[i])

	#print 'Number of GPS occultations for coarse match = %d' %len(coarseMatch1)
	return coarseMatch1, swathsIdCum2
