#-----------------------------------------------------------------------------
# Name:        sqlobjectCatalog.py
# Purpose:     SqlObjectCatalog subclass -- database backend implemented
#              via MySQL, Postgres, SQLite, Firebird, Sybase, MAX DB,
#              MS SQL Server using SQLObject.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 25 12:16:10 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
from sqlobject import *
from sqlobject.sqlbuilder import Delete
import os
import cPickle

from catalog import *
from sciflo.utils import (getXmlEtree, SCIFLO_NAMESPACE, getPrefixForNs,
getListFromUnknownObject)

class Urls(SQLObject):
	objectid = StringCol(alternateID=True,length=128)
	urlList = StringCol()

class SqlObjectCatalogError(Exception):
	"""Exception class for SqlObjectCatalog class."""
	pass

class SqlObjectCatalog(ScifloCatalog):
	"""Subclass of ScifloCatalog that implements the catalog's database
	backend via databases supported by SQLObject."""

	def __init__(self,container):
		super(SqlObjectCatalog,self).__init__(container)
		self._connection = connectionForURI(self._container)
		sqlhub.processConnection = self._connection
		Urls.createTable(ifNotExists = True)

	def update(self,objectid,objectDataList,**kargs):
		"""Update/insert an objectid and its list of data objects into the catalog.
		Return 1 upon success.  Otherwise return None.
		"""
		objectDataList = cPickle.dumps(getListFromUnknownObject(objectDataList))
		try: Urls.byObjectid(objectid).urlList = objectDataList
		except SQLObjectNotFound: Urls(objectid=objectid, urlList=objectDataList)
		except: raise
		return 1

	def query(self,objectid):
		"""Query the catalog by objectid.  Returns a list of data objects that belong
		to the objectid.  Otherwise return None.
		"""
		try: return cPickle.loads(Urls.byObjectid(objectid).urlList)
		except SQLObjectNotFound: return list()
		except: raise

	def remove(self,objectid):
		"""Remove an objectid or list of objectids and its data objects from the catalog.  Return 1
		upon success.  Otherwise return None.
		"""
		#delete record (slow for multiple records)
		#thisRec.destroySelf()

		#delete record (fast...perid)
		#connection.query(connection.sqlrepr(Delete(Urls.sqlmeta.table, \
		#	Urls.q.objectid == 'gps_2')))
		for id in getListFromUnknownObject(objectid):
			try: Urls.byObjectid(id).destroySelf()
			except SQLObjectNotFound: return None
			except: raise
		return 1

	def getAllObjectids(self):
		"""Return a list of all objectids in the catalog."""
		return [i.objectid for i in Urls.select()]

	def removeAll(self):
		"""Remove an objectid or list of objectids and its data objects from the catalog.  Return 1
		upon success.  Otherwise return None.
		"""
		self._connection.query(self._connection.sqlrepr(Delete(Urls.sqlmeta.table,None)))
