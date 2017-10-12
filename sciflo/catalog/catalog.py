#-----------------------------------------------------------------------------
# Name:        catalog.py
# Purpose:     ScifloCatalog base class.
#
# Author:      Gerald Manipon
#
# Created:     Sun May 08 22:26:03 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import types

from sciflo.utils import *

class ScifloCatalogError(Exception):
	"""Exception class for ScifloCatalog class."""
	pass

class ScifloCatalog(object):
	"""Sciflo catalog base class."""

	def __init__(self,container): self._container = container
	def _createList(self,obj): return getListFromUnknownObject(obj)

	def update(self,objectid,objectDataList,**kargs):
		"""Update/insert an objectid and its list of data objects into the catalog.
		Return 1 upon success.  Otherwise return None.

		NOTE: Implement this method in a subclass.
		"""
		pass

	def query(self,objectid):
		"""Query the catalog by objectid.  Returns a list of data objects that belong
		to the objectid.  Otherwise return None.

		NOTE: Implement this method in a subclass.
		"""
		pass

	def remove(self,objectid):
		"""Remove an objectid or list of objectids and its data objects from the catalog.  Return 1
		upon success.  Otherwise return None.

		NOTE: Implement this method in a subclass.
		"""
		pass

	def getAllObjectids(self):
		"""Return a list of all objectids in the catalog.

		NOTE: Implement this method in a subclass.
		"""
		pass
