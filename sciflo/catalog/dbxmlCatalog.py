#-----------------------------------------------------------------------------
# Name:        dbxmlCatalog.py
# Purpose:     DbxmlCatalog subclass -- database backend implemented via
#              dbxml.
#
# Author:      Gerald Manipon
#
# Created:     Sun May 08 22:57:48 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
from xml.dom.minidom import getDOMImplementation, parseString
from xml.etree.ElementTree import ElementTree, XMLID

from catalog import *
from scifloDbxml import *
from sciflo.utils import XSI_NAMESPACE

class DbxmlCatalogError(Exception):
	"""Exception class for DbxmlCatalog class."""
	pass

class DbxmlCatalog(ScifloCatalog):
	"""Subclass of ScifloCatalog that implements the catalog's database
	backend via Sleepycat's BSD DB and DBXML."""

	def __init__(self,container,schemaUrl=None,rootTag='catalogEntry',
				 objectidTag='objectid',objectDataSetTag='objectDataSet',
				 objectDataTag='objectData',indexSpec='node-element-equality-string',
				 xsiNamespace=XSI_NAMESPACE):
		"""Constructor."""

		super(DbxmlCatalog,self).__init__(container)

		#set attributes
		self._dbxmlFile = self._container
		self._dbDir = os.path.dirname(self._dbxmlFile)
		self._xmldbObj = ScifloXmlDb(self._dbxmlFile)
		self._rootTag = rootTag
		self._objectidTag = objectidTag
		self._objectDataSetTag = objectDataSetTag
		self._objectDataTag = objectDataTag
		self._indexSpec = indexSpec
		self._schemaUrl = schemaUrl
		self._xsiNamespace = xsiNamespace

		#add index on objectid
		self._xmldbObj.addIndex(objectidTag, self._indexSpec)

	def __getXml(self,objectid,obj):
		"""Private method to return the xml for the objectid and its
		data objects for insertion into the dbxml database backend.
		"""

		try: objectDataList = self._createList(obj)
		except Exception, e: raise DbxmlCatalogError, str(e)

		#create root element
		implementation = getDOMImplementation()
		xmlDoc = implementation.createDocument(None,None,None)
		rootElem = xmlDoc.createElement(self._rootTag)
		xmlDoc.appendChild(rootElem)

		#create xsi namespace attribute
		xsi = xmlDoc.createAttribute('xmlns:xsi')
		xsi.value = self._xsiNamespace
		rootElem.setAttributeNode(xsi)

		#create xsi namespace schema location attribute if it was set
		if self._schemaUrl:
			xsd = xmlDoc.createAttribute('xsi:noNamespaceSchemaLocation')
			xsd.value = self._schemaUrl
			rootElem.setAttributeNode(xsd)

		#create objectid child and append to xml doc
		objectidNode = xmlDoc.createElement(self._objectidTag)
		objectidNode.appendChild(xmlDoc.createTextNode(objectid))
		rootElem.appendChild(objectidNode)

		#create objectDataSet child and append to xml doc
		objectDataSetNode = xmlDoc.createElement(self._objectDataSetTag)
		rootElem.appendChild(objectDataSetNode)

		#loop over data objects and add to xml doc
		for objectData in objectDataList:

			#create objectData element and attach to objectDataSet node
			objectDataNode = xmlDoc.createElement(self._objectDataTag)
			objectDataNode.appendChild(xmlDoc.createTextNode(objectData))
			objectDataSetNode.appendChild(objectDataNode)

		#get string and return
		xmlString = xmlDoc.toxml()
		return xmlString

	def __getObjectDataListFromXml(self,xml):
		"""Private method to return a list of data objects from the given xml string.
		"""

		#parse xml
		doc,xmlids = XMLID(xml)

		#objectData xpath
		xpathExpr = "%s/%s" % (self._objectDataSetTag,self._objectDataTag)

		#get objectData nodes
		objNodes = doc.findall(xpathExpr)

		#create list of data objects
		objectDataList = [objNode.text for objNode in objNodes]

		#return list
		return objectDataList

	def update(self,objectid,objectDataList,**kargs):
		"""Update/insert an objectid and its list of data objects into the catalog.
		Return 1 upon success.  Otherwise return None.
		"""

		xml = self.__getXml(objectid,objectDataList)
		try: retVal = self._xmldbObj.insertDocument(objectid,xml)
		except Exception, e:
			self._xmldbObj.removeDocument(objectid)
			retVal = self._xmldbObj.insertDocument(objectid,xml)
		return retVal

	def query(self,objectid):
		"""Query the catalog by objectid.  Returns a list of data objects that belong
		to the objectid.  Otherwise return None.
		"""

		resultXmlList = self._xmldbObj.queryDocumentIndex(objectid)
		if len(resultXmlList) == 0: return list()
		return self.__getObjectDataListFromXml(resultXmlList[0])

	def remove(self,objectid):
		"""Remove an objectid or list of objectids and its data objects from the catalog.  Return 1
		upon success.  Otherwise return None.
		"""
		return self._xmldbObj.removeDocument(objectid)


	def getAllObjectids(self):
		"""Return a tuple of all objectids in the catalog."""
		return self._xmldbObj.queryDocumentIndex(returnNodeNamesFlag=1)
