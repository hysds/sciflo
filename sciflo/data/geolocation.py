#-----------------------------------------------------------------------------
# Name:        geolocation.py
# Purpose:     Sciflo Geolocation classes.
#
# Author:      Benyang Tang
#
# Created:     Mon May 16 10:02:12 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import types
import time
import string
import Numeric as N

from sciflo.utils.timeUtils import *

class GeolocationError(Exception):
	"""Exception class for the Geolocation class."""
	pass

class Geolocation(list):
	"""Base class representing a geolocation entity composed of a list
	of value types that are shared amongst different dataset types
	(points, swaths, grids).
	"""

	def __init__(self,sequence):
		"""Constructor.  This takes a list of values which contain the
		geolocation information.  The first value must be the epoch value of
		the starttime and the second value must be that of the endtime.  The
		rest of the values are specified in the subclass implementations.

		e.g. For a PointGeolocation, the list would be [starttime,endtime,lat,lon]
		as it is implemented below.
		"""

		#get starttime (sequence[0]) and endtime (endtime[0]) and make sure
		#they are epoch values, not string;
		#if string, try to convert it
		if not isinstance(sequence[0],types.FloatType):
			sequence[0] = getEpochFromTimeString(sequence[0])
		if not isinstance(sequence[1],types.FloatType):
			sequence[1] = getEpochFromTimeString(sequence[1])

		#make sure the rest of the values are floats
		sequence[2:3] = [float(i) for i in sequence[2:3]]

		#call super()
		super(Geolocation,self).__init__(sequence)

	def getStarttime(self):
		"""Return starttime epoch."""
		return self.__getitem__(0)

	def getEndtime(self):
		"""Return endtime epoch."""
		return self.__getitem__(1)

class GeolocationSetError(Exception):
	"""Exception class for the GeolocationSet class."""
	pass

class GeolocationSet(object):
	"""Base class representing a set of geolocation data.
	"""

	def __init__(self,geolocationClass,geolocationDict={}):
		"""Constructor.  Pass in the Geolocation class and a dictionary of
		(starttime,endtime,geolocVal1,...,geolocValN) lists or list of
		the specified Geolocation objects indexed by objectids.  If no dict
		is passed in, creates an empty object that you can use to incrementally
		build.
		"""

		#set Geolocation class that this set is composed of.
		self._geolocationClass = geolocationClass

		#loop over geoLocationDict and rewrite lists to be Geolocation objects.
		#The type of Geolocation subclass will be implemented in the subclass.
		for objectid in geolocationDict:

			#get item
			geolocobj = geolocationDict[objectid]

			#if already a PointGeolocation object, skip otherwise coerce it and
			#overwrite in dict
			if isinstance(geolocobj,self._geolocationClass): pass
			else: geolocationDict[objectid] = self._geolocationClass(geolocobj)

		#geollocation dict
		self._geoLocationDict = geolocationDict

		#sorted objectid list
		self._objectids = None

		#geolocation arrays
		self._starttimeArray = None
		self._endtimeArray = None

		#set flag that indicates whether or not we need to update the
		#sorted objectids list and the geolocation arrays
		self._updateNeededFlag = 1

		#update the objectid list and geolocation arrays.
		self.update()

	def update(self):
		"""Update the objectid list and geolocation arrays."""

		#resort and get the new starttime and endtime arrays
		self._sortByTimeAndUpdateTimeArrays()

		#create the rest of the arrays
		self._updateOtherArrays()

		#clear the updateNeededFlag
		self._updateNeededFlag = 0

		#return
		return 1

	def _sortByTimeAndUpdateTimeArrays(self):
		"""Private method to sort by objectid then by starttime, set the list of
		objectids, and update the starttime and endtime arrays."""

		#sort objectids by name (Use Python 2.3 style of sorting to be
		#backwards compatible)
		#sortedObjectids = sorted(self._geoLocationDict)
		sortedObjectids = self._geoLocationDict.keys()
		sortedObjectids.sort()


		#turn list of time strings into epoch array for both starttime and endtime
		starttimeList = [self._geoLocationDict[i][0] for i in sortedObjectids]
		starttimeArray = N.array(starttimeList)
		endtimeList = [self._geoLocationDict[i][1] for i in sortedObjectids]
		endtimeArray = N.array(endtimeList)

		#get sorted time index
		sortedTimeIndex = N.argsort(starttimeArray)

		#get starttime sorted by time
		self._starttimeArray = N.take(starttimeArray,sortedTimeIndex)

		#get endtime sorted by time
		self._endtimeArray = N.take(endtimeArray,sortedTimeIndex)

		#get list of objectids in the sorted order and set attribute
		self._objectids = [sortedObjectids[i] for i in sortedTimeIndex]

	def _updateOtherArrays(self):
		"""Update the other arrays.  The rest of this method should be implemented
		in the subclass to loop over the objectids and build the other arrays.
		The following example is building the lat and lon arrays for point data.
		"""

		'''
		#################################
		#Please implement in subclass
		#################################
		#loop over objectidList and populate the temporary geolocation lists
		latList = []
		lonList = []
		for objectid in self._objectids:

			#populate
			latList.append(self._geoLocationDict[objectid][2])
			lonList.append(self._geoLocationDict[objectid][3])

		#set geolocation attributes
		self._latArray = N.array(latList)
		self._lonArray = N.array(lonList)
		'''
		pass

	def addGeolocation(self,objectid,geolocationList):
		"""Add a geolocation object to the set."""

		#create the Geolocation type object
		if isinstance(geolocationList,self._geolocationClass):
			self._geoLocationDict[objectid] = geolocationList
		else:
			self._geoLocationDict[objectid] = self._geolocationClass(geolocationList)

		#set updateNeededFlag
		self._updateNeededFlag = 1

		#return success
		return 1

	def removeGeolocation(self,objectid):
		"""Remove a geolocation object from the set."""

		#remove
		del self._geoLocationDict[objectid]

		#set updateNeededFlag
		self._updateNeededFlag = 1

		#return
		return 1

	def getObjectidList(self):
		"""Return the list of objectids."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._objectids

	def getStarttimeArray(self):
		"""Return the starttime array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._starttimeArray

	def getEndtimeArray(self):
		"""Return the endtime array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._endtimeArray

class PointGeolocationError(Exception):
	"""Exception class for the PointGeolocation class."""
	pass

class PointGeolocation(Geolocation):
	"""Subclass representing a list of values that are to be interpreted
	as (starttime,endtime,lat,lon) geolocation values for an
	instance of a point-like dataset.  All values should be float values.
	"""

	def __init__(self,sequence):
		"""Constructor."""

		#make sure it has 4 items
		#if len(sequence)!=4:
		#	raise PointGeolocationError, "Illegal number of values in list/tuple of geolocation values: %s" % str(sequence)

		#call super()
		super(PointGeolocation,self).__init__(sequence)

	def getLatitude(self):
		"""Return latitude."""
		return self.__getitem__(2)

	def getLongitude(self):
		"""Return longitude."""
		return self.__getitem__(3)

class PointGeolocationSetError(Exception):
	"""Exception class for the PointGeolocationSet class."""
	pass

class PointGeolocationSet(GeolocationSet):
	"""Subclass representing a set of geolocation data for point-like datasets.
	"""

	def __init__(self,geolocationDict={}):
		"""Constructor.  Pass in a dictionary of (startime,endtine,lat,lon) lists or
		list of PointGeolocation objects indexed by objectids.  If nothing is passed
		in, creates an empty object that you can use to incrementally build.
		"""

		#set lat and lon arrays
		self._latArray = None
		self._lonArray = None

		#call super()
		super(PointGeolocationSet,self).__init__(PointGeolocation,geolocationDict)

	def _updateOtherArrays(self):
		"""Update the other arrays, latitude and longitude.
		"""

		#loop over objectidList and populate the temporary geolocation lists
		latList = []
		lonList = []
		for objectid in self._objectids:

			#populate
			latList.append(self._geoLocationDict[objectid][2])
			lonList.append(self._geoLocationDict[objectid][3])

		#set geolocation attributes
		self._latArray = N.array(latList)
		self._lonArray = N.array(lonList)

	def getLatitudeArray(self):
		"""Return the latitude array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._latArray

	def getLongitudeArray(self):
		"""Return the longitude array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._lonArray

class SwathGeolocationError(Exception):
	"""Exception class for the SwathGeolocation class."""
	pass

class SwathGeolocation(Geolocation):
	"""Base class representing a list of values that are to be interpreted
	as (starttime_epoch,endtime_epoch,westbound,eastbound,southbound,northbound)
	geolocation values for an instance of a swath-like dataset.
	All values should be float values or they will be converted.
	"""

	def __init__(self,sequence):
		"""Constructor."""

		#make sure it has 6 items
		#if len(sequence)!=6:
		#	raise SwathGeolocationError, "Illegal number of values in list/tuple of geolocation values: %s" % str(sequence)

		#call super()
		super(SwathGeolocation,self).__init__(sequence)

	def getWestBound(self):
		"""Return west bounding longitude."""
		return self.__getitem__(2)

	def getEastBound(self):
		"""Return east bounding longitude."""
		return self.__getitem__(3)

	def getSouthBound(self):
		"""Return south bounding latitude."""
		return self.__getitem__(4)

	def getNorthBound(self):
		"""Return north bounding latitude."""
		return self.__getitem__(5)

class SwathGeolocationSetError(Exception):
	"""Exception class for the SwathGeolocationSet class."""
	pass

class SwathGeolocationSet(GeolocationSet):
	"""Base class representing a set of geolocation data	for swath-like datasets.
	"""

	def __init__(self,geolocationDict={}):
		"""Constructor.  Pass in a dictionary of (startime,endtine,westbound,eastbound,
		southbound,northbound) lists or SwathGeolocation objects indexed by objectids.
		If nothing is passed in, creates an empty object that you can use to incrementally
		build.
		"""

		#set bounding box  value arrays
		self._westArray = None
		self._eastArray = None
		self._southArray = None
		self._northArray = None

		#call super()
		super(SwathGeolocationSet,self).__init__(SwathGeolocation,geolocationDict)

	def _updateOtherArrays(self):
		"""Update the other arrays: west, east, south, north.
		"""

		#loop over objectidList and populate the temporary geolocation lists
		westList = []
		eastList = []
		southList = []
		northList = []
		for objectid in self._objectids:

			#populate
			westList.append(self._geoLocationDict[objectid][2])
			eastList.append(self._geoLocationDict[objectid][3])
			southList.append(self._geoLocationDict[objectid][4])
			northList.append(self._geoLocationDict[objectid][5])

		#set geolocation attributes
		self._westArray = N.array(westList)
		self._eastArray = N.array(eastList)
		self._southArray = N.array(southList)
		self._northArray = N.array(northList)

	def getWestArray(self):
		"""Return the west bound array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._westArray


	def getEastArray(self):
		"""Return the east bound array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._eastArray


	def getSouthArray(self):
		"""Return the south bound array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._southArray


	def getNorthArray(self):
		"""Return the north bound array."""

		#if updateNeeded, call update first
		if self._updateNeededFlag == 1:

			#call update() first
			self.update()

		#return
		return self._northArray
	
