#-----------------------------------------------------------------------------
# Name:        librarian.py
# Purpose:     Sciflo librarian base class.
#
# Author:      Gerald Manipon
#
# Created:     Sun May 08 22:26:03 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
from xml.etree.ElementTree import ElementTree, XMLID
import urllib
import time

from crawler import *
from catalog import *
from sciflo.utils import *

class ScifloLibrarianError(Exception):
	"""Exception class for ScifloLibrarian class."""
	pass

class ScifloLibrarian(object):
	"""Sciflo librarian base class."""

	def __init__(self,xmlConfigFile,catalogObject=None):
		"""Constructor."""

		#validate xml config file and set
		if self.__validateXmlConfigFile(xmlConfigFile,CRAWLER_SCHEMA_XML): self._xmlConfigFile = xmlConfigFile
		else: raise ScifloCrawlerError, "Couldn't validate xmlConfigFile %s." % xmlConfigFile

		#parse xml
		self._docString = urllib.urlopen(self._xmlConfigFile).read()
		self._doc,self._docIds = XMLID(self._docString)

		#get instrument
		self._instrument = self._doc.find("{%s}instrument" % SCIFLO_NAMESPACE).text

		#get level
		self._level = self._doc.find("{%s}level" % SCIFLO_NAMESPACE).text

		#data locations
		self._locationNodes = self._doc.findall("{%s}dataLocations/{%s}location" % (SCIFLO_NAMESPACE,
																				  SCIFLO_NAMESPACE))

		#loop over locationNodes and build a list of dicts and a list
		#of crawlers for each
		self._dataLocationsDictList = []
		self._dataLocationCrawlers = []
		locationAttributes = ['protocol','site','user','password',
								  'rootDir','matchFileRegEx','objectidTemplate']
		for locationNode in self._locationNodes:
			locationDict = {}
			for attribute in locationAttributes:
				attrNode = locationNode.find("{%s}%s" % (SCIFLO_NAMESPACE,attribute))
				if attrNode is None: locationDict[attribute] = None
				else: locationDict[attribute] = attrNode.text
			self._dataLocationsDictList.append(locationDict)

			#get attributes
			protocol = locationDict['protocol']
			site = locationDict['site']
			user = locationDict['user']
			password = locationDict['password']
			rootDir = locationDict['rootDir']
			matchFileRegEx = re.compile(locationDict['matchFileRegEx'])
			objectidTemplate = locationDict['objectidTemplate']

			#create crawler object
			if protocol == 'HTTP':
				self._dataLocationCrawlers.append(HttpCrawler(site,user,password,rootDir,
															  matchFileRegEx,objectidTemplate))
			elif protocol == 'FTP':
				self._dataLocationCrawlers.append(FtpCrawler(site,user,password,rootDir,
															  matchFileRegEx,objectidTemplate))
			elif protocol == 'DODS':
				self._dataLocationCrawlers.append(DodsCrawler(site,user,password,rootDir,
															  matchFileRegEx,objectidTemplate))
			elif protocol == 'LOCAL':
				self._dataLocationCrawlers.append(LocalCrawler(site,user,password,rootDir,
															  matchFileRegEx,objectidTemplate))
			elif protocol == 'FILE':
				self._dataLocationCrawlers.append(FileListingCrawler(site,user,password,rootDir,
															  matchFileRegEx,objectidTemplate))
			else:
				raise ScifloLibrarianError, "Cannot resolve crawler subclass for protocol %s." % protocol

		#this class needs a ScifloCatalog type object.
		self._catalogObj = catalogObject

	def __validateXmlConfigFile(self,xmlConfigFile,schemaXml):
		"""Private method to validate xml crawler config file against the crawler schema.  Returns 1
		upon success and None otherwise.
		"""

		validated,validationError=validateXml(xmlConfigFile,schemaXml)
		if validated: return 1
		else: return None

	def getInstrument(self):
		"""Return the instrument id of the data."""
		return self._instrument

	def getLevel(self):
		"""Return the data level of the data."""
		return self._level

	def getCatalog(self):
		"""Return the ScifloCatalog object that this librarian is using."""
		return self._catalogObj

	def setCatalog(self,catalogObject):
		"""Set the ScifloCatalog object that this librarian will use."""
		self._catalogObj=catalogObject

	def crawlAndCatalog(self, page=False):
		"""Loop over the crawler objects and crawl for data.  Update the catalog each time."""

		for crawler in self._dataLocationCrawlers:
			crawlerInfo = crawler.crawl()
			addedObjectids = self.catalog(crawlerInfo, page=page)
		return 1

	def catalog(self, crawlerInfo, page=False):
		"""Add the harvested catalog info to the catalog via the catalog object.  Updates
		existing objectid's by prepending the results to the existing list or inserts
		new objectids and their url list.  Returns list of objectids upon success.
		Otherwise None.  Uses generator.
		"""

		#make sure that the catalog is a ScifloCatalog type;
		#otherwise raise error before we even crawl.
		if not isinstance(self._catalogObj,ScifloCatalog):
			raise ScifloLibrarianError, "Catalog is not of type ScifloCatalog.  Please create a ScifloCatalog object\
			and call the setCatalog() method."

		objectidList = []
		while True:
			try: objectid,crawlerUrlList = crawlerInfo.next()
			except StopIteration: break

			#get current url list from catalog
			currentUrlList = self._catalogObj.query(objectid)

			#if there is a list of urls currently in catalog
			if currentUrlList is not None:
				newCurrentUrlList = []

				#loop currentUrlList and remove it if it exists in crawlerUrlList
				for currentUrl in currentUrlList:
					if currentUrl not in crawlerUrlList:
						newCurrentUrlList.append(currentUrl)

				#append the existing list (minus duplicates in new list) to the end of the new list
				crawlerUrlList.extend(newCurrentUrlList)

			#update catalog with new list
			self._catalogObj.update(objectid,crawlerUrlList,page=page)
			objectidList.append(objectid)

		#return
		return objectidList

