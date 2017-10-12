#-----------------------------------------------------------------------------
# Name:        hdfeosSubsetter.py
# Purpose:     Class that subsets HDFEOS variables via OPeNDAP or local
#              read using pyhdfeos.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 05 09:50:49 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import urllib
import re

import hdfeos

from subsetter import *

class HdfeosFileVariableSubsetterError(Exception):
	"""Exception class for the HdfeosFileVariableSubsetter class."""
	pass

class HdfeosFileVariableSubsetter(DataFileVariableSubsetter):
	"""Subclass of DataFileVariableSubsetter that subsets variables from
	HDFEOS files locally or over OPeNDAP.
	"""

	def __init__(self,fileUrl,swath,varList,outputFile,excludeFlag=None,
				 mandatory=['Latitude','Longitude','Time']):
		"""Constructor."""

		#set swath name attribute
		self._swath = swath

		#super call
		super(HdfeosFileVariableSubsetter,self).__init__(fileUrl,varList,outputFile,
														 excludeFlag,mandatory)

	def subset(self):
		"""Subset the variables out to the output file.  Return 1 upon
		success.  Otherwise raise error.
		"""

		#validate the lists via super()
		super(HdfeosFileVariableSubsetter,self).subset()

		#determine if the url is DODS url or just a location to the file
		if self._fileUrl.startswith('http') and re.search(r'dods',self._fileUrl,re.IGNORECASE):
			self.dodsFlag = 1
			file = self._fileUrl
		#get file via urlretrieve
		else: (file,headers) = urllib.urlretrieve(self._fileUrl)

		#get list of all data fields in the data file
		allfields = hdfeos.swath_data_fields(file,self._swath)

		#get list of all geolocation fields in the data file
		geofields = hdfeos.swath_geo_fields(file,self._swath)
		#print geofields

		#get attributes(not implemented in dapeos so we'll skip this)
		#attrs = hdfeos.hdfeos.swath_attrs(file,self._swath)
		#print attrs

		#loop over the mandatory fields (geo fields)
		geoFieldsData = {}
		geoFieldsDimlist = {}
		for geofield in self._mandatoryList:

			#check that it is in the geo fields of this file
			if geofield not in geofields:
				raise HdfeosFileVariableSubsetterError, "%s not in geolocation fields."

			#get data
			geoFieldsData[geofield] = hdfeos.swath_field_read(file,self._swath,geofield)

			#get dimlist
			geoFieldsDimlist[geofield] = tuple(hdfeos.swath_field_dimlist(file,self._swath,geofield))

		#loop over the all the data fields
		dataFieldsToAdd = []
		dataFieldsData = {}
		dataFieldsDimlist = {}
		for datafield in allfields:

			#if the excludeFlag was set
			if self._excludeFlag:

				#if it is in the list, skip it
				if datafield in self._varList: continue

			#if the excludeFlag was not set
			else:

				#if it is not in the list, skip it
				if datafield not in self._varList: continue

			#add to data field list
			dataFieldsToAdd.append(datafield)

			#add data
			dataFieldsData[datafield] = hdfeos.swath_field_read(file,self._swath,datafield)

			#add dimlist
			dataFieldsDimlist[datafield] = tuple(hdfeos.swath_field_dimlist(file,self._swath,datafield))

		#create the output file
		hdfeos.hdfeos.swath_create_file(self._outputFile)

		#add the swath to output file
		hdfeos.hdfeos.swath_add(self._outputFile,self._swath)

		#add attributes
		#hdfeos.hdfeos.swath_add_attrs(self._outputFile,self._swath,attrs)

		#loop over geo fields and add them
		for geofield in self._mandatoryList:

			#add geo field
			hdfeos.hdfeos.swath_add_geo_field(self._outputFile,
											  self._swath,geofield,
											  geoFieldsDimlist[geofield],
											  geoFieldsData[geofield])

		#loop over data fields and add them
		for datafield in dataFieldsToAdd:

			#add data field
			hdfeos.hdfeos.swath_add_data_field(self._outputFile,
											  self._swath,datafield,
											  dataFieldsDimlist[datafield],
											  dataFieldsData[datafield])

		#close file
		hdfeos.hdfeos.close_all()

		#cleanup
		urllib.urlcleanup()

		#return
		return 1

	def __del__(self):
		"""Destructor."""
		
		#validate the lists via super()
		super(HdfeosFileVariableSubsetter,self).__del__()

		#cleanup temp files
		urllib.urlcleanup()
