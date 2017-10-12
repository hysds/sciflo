#-----------------------------------------------------------------------------
# Name:        occultation.py
# Purpose:     Various classes/function for GPS occultation data.
#
# Author:      Gerald Manipon
#
# Created:     Tue Jun 20 09:26:32 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import urllib
import zlib
import gzip
import re
from lxml.etree import Element, SubElement, tostring

#when running from mod_wsgi, long-running instances may give
#'ValueError: Type Byte has already been registered' errors;
#we try to catch them here
try: from numarray.records import array
except ValueError, e:
    if not re.search(r'Type Byte has already been registered', str(e)): raise

from sciflo.utils import getXmlEtree

#GPS metadata sqltype xml
GPS_METADATA_XML = '''<?xml version='1.0' encoding='UTF-8'?>
<metadataMapSet>
	<metadataMap>
		<metadata>objectid</metadata>
		<sqltype>char(30)</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>StartTime</metadata>
		<sqltype>datetime</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>EndTime</metadata>
		<sqltype>datetime</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>Latitude</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>Longitude</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>WestBoundingCoordinate</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>NorthBoundingCoordinate</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>EastBoundingCoordinate</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>SouthBoundingCoordinate</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>Transmitter</metadata>
		<sqltype>char(5)</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>Receiver</metadata>
		<sqltype>char(5)</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>ReferenceTransmitter</metadata>
		<sqltype>char(5)</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>ReferenceReceiver</metadata>
		<sqltype>char(4)</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>LowestAltitude</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>LocalTime</metadata>
		<sqltype>char(8)</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>LinkOrientation</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>AngleToVelocity</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>StartTimeInSecondsFromJ2000</metadata>
		<sqltype>double unsigned</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>TimeForRadiusOfCurvatureFromJ2000</metadata>
		<sqltype>double unsigned</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>RadiusOfCurvature</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CenterOfCurvature</metadata>
		<sqltype>char(100)</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_StartPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_EndPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_MinimumPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_MaximumPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_StartSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_EndSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_MinimumSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>CA_MaximumSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_StartPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_EndPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_MinimumPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_MaximumPhase</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_StartSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_EndSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_MinimumSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
	<metadataMap>
		<metadata>P2_MaximumSNR</metadata>
		<sqltype>double</sqltype>
	</metadataMap>
</metadataMapSet>'''

class L2TextOccultationError(Exception):
	"""Exception class for L2TextOccultation."""
	pass

class L2TextOccultation(object):
	"""Base class for L2TextOccultation classes."""

	def __init__(self,fileOrUrl):
		"""Constructor."""

		self.fileOrUrl = fileOrUrl
		if os.path.isfile(self.fileOrUrl): self.file = fileOrUrl
		else: (self.file,headers) = urllib.urlretrieve(self.fileOrUrl)
		if self.fileOrUrl.endswith('.gz'): f = gzip.GzipFile(self.file,'rb')
		else: f = open(file,'r')
		self.lines = [i.strip() for i in f.readlines()]
		f.close()

		#set headers as list and as dictionary
		self.headerLines = []
		self.dataLines = []
		self.headerDict = {}
		self.headersList = []
		for line in self.lines:
			match = re.search(r'^(.*?)\s* = \s*(.*)$',line)
			if match:
				self.headerLines.append(line)
				header = match.group(1)
				value = match.group(2)
				self.headerDict[header] = value
				self.headersList.append(header)
			else: self.dataLines.append(line)

		#adjust longitude bounds to be -180.<= x <= 180.
		for bc_name in ('WestBoundingCoordinate','EastBoundingCoordinate'):
			bc_val = float(self.headerDict[bc_name])
			if bc_val > 180.: self.headerDict[bc_name] = str(bc_val - 360.)

		#set attributes
		self.objectid = self.headerDict['DataSetID']
		self.secs = float(self.headerDict['StartTimeInSecondsFromJ2000'])
		self.west = float(self.headerDict['WestBoundingCoordinate'])
		self.north = float(self.headerDict['NorthBoundingCoordinate'])
		self.east = float(self.headerDict['EastBoundingCoordinate'])
		self.south = float(self.headerDict['SouthBoundingCoordinate'])
		self.lon = abs((self.west - self.east)/2.) + self.west
		self.lat = abs((self.south - self.north)/2.) + self.south
		self.versionID = self.headerDict['VersionID']
		self.version = self.versionID.replace('.','p')
		self.metadataXml = None
		self.dataRecordsDictById = None
		self.recArrayDictById = None

		#get data type names's
		self.allDataNameList = []
		dataTypeNameStr = self.headerDict['DataTypeName']
		match = re.search(r'{(.*)}',dataTypeNameStr)
		if match:
			dataTypeNameStr2 = match.group(1)
			d = re.sub('\s','',dataTypeNameStr2)
			self.allDataNameList = d.split(',')
			self.occName = self.allDataNameList[0]
			self.modelNameList = self.allDataNameList[1:]
		else: raise L2TextOccultationError, "Cannot parse header 'DataTypeName'."

		#get data type ID's
		self.occId = None
		self.modelIdList = []
		self.allDataIdList = []
		self.allDataNamesDict = {}
		dataTypeIdStr = self.headerDict['DataTypeID']
		match = re.search(r'{(.*)}',dataTypeIdStr)
		if match:
			dataTypeIdStr2 = match.group(1)
			d = re.sub('\s','',dataTypeIdStr2)
			self.allDataIdList = d.split(',')
			length = len(self.allDataIdList)
			self.occId = self.allDataIdList[0]
			self.allDataNamesDict[self.allDataIdList[0]] = self.allDataNameList[0]
			self.modelIdList = self.allDataIdList[1:]
			for i in range(1,length):
				self.allDataNamesDict[self.allDataIdList[i]] = self.allDataNameList[i]
		else: raise L2TextOccultationError, "Cannot parse header 'DataTypeID'."

		#get fields names
		self.fieldNamesDictById = {}
		for i in self.allDataIdList:
			fieldsStr = self.headerDict["Fields(%s)" % i]
			match = re.search(r'{\s*(.*)\s*}',fieldsStr)
			if match:
				d = match.group(1)
				self.fieldNamesDictById[i] = [re.sub(r'"','',j.strip()) for j in d.split(',')]
			else: raise L2TextOccultationError, "Cannot parse header 'Fields(%s)'." % i

	def parseData(self):
		"""Parse data into list and record arrays."""

		#return True if already parse
		if self.dataRecordsDictById and self.recArrayDictById: return True
		else: self.dataRecordsDictById = {}; self.recArrayDictById = {}
		#get data records as list indexed by data type id in to a hash
		for i in self.allDataIdList: self.dataRecordsDictById[i] = []
		for i in self.dataLines:
			match = re.search(r'^(\d+)\s+(.*)$',i)
			if match:
				id,data = match.groups()
				if id == '0': continue #no data available
				self.dataRecordsDictById[id].append(map(float,re.split(r'\s+',data)))
			else: raise L2TextOccultationError, "Encountered error: Unrecognized format in data line:\n%s" % i

		#sort the data records for each data id list
		for i in self.allDataIdList: self.dataRecordsDictById[i].sort()

		#rec array
		for i in self.allDataIdList:
			self.recArrayDictById[i] = array(self.dataRecordsDictById[i],
											 names=self.fieldNamesDictById[i])
		return True

	def getRecArrayById(self, id=None):
		"""Return record array for data specified by id.  By default returns
		record array for occultation id."""

		if id is None: id = self.occId
		if self.recArrayDictById is None: self.parseData()
		return self.recArrayDictById[str(id)]

	def getDataListById(self, id=None):
		"""Return data list for data specified by id.  By default returns
		data list for occultation id."""

		if id is None: id = self.occId
		if self.dataRecordsDictById is None: self.parseData()
		return self.dataRecordsDictById[str(id)]

	def getMetadataXml(self):
		"""Returns metadata header info in xml format."""

		#if already defined
		if self.metadataXml: return self.metadataXml

		#create root element
		metadataMapElt,nsDict = getXmlEtree(GPS_METADATA_XML)
		root = Element('metadata')
		for elt in metadataMapElt.xpath('./metadataMap'):
			dbh = elt.xpath('./metadata')[0].text
			sqltype = elt.xpath('./sqltype')[0].text
			if dbh == 'LocalTime': eltTag = 'ltime'
			else: eltTag = dbh.lower()
			subElt = SubElement(root,eltTag)
			if dbh == 'objectid':
				subElt.text = self.objectid
				sqltype += ' not null unique'
			elif dbh == 'StartTime':
				subElt.text = "%s %s" % (self.headerDict['RangeBeginningDate'],
							             self.headerDict['RangeBeginningTime'])
			elif dbh == 'EndTime':
				subElt.text = "%s %s" % (self.headerDict['RangeEndingDate'],
							             self.headerDict['RangeEndingTime'])
			elif dbh == 'Latitude':
				subElt.text = str(self.lat)
			elif dbh == 'Longitude':
				subElt.text = str(self.lon)
			else:
				subElt.text = self.headerDict[dbh]

			#set sqltype
			subElt.set('sqltype',sqltype)
			root.append(subElt)

		#return xml
		self.metadataXml = tostring(root, pretty_print=True)
		return self.metadataXml

	def __del__(self): urllib.urlcleanup()
