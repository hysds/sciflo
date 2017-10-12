#-----------------------------------------------------------------------------
# Name:        storeConfig.py
# Purpose:     Store config class.
#
# Author:      Gerald Manipon
#
# Created:     Tue Jul 19 22:39:35 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------

from storeTypeMapping import StoreTypeMapping

class StoreConfigError(Exception):
    """Exception class for StoreConfig class."""
    pass

class StoreConfig(object):
    """Class representing the configuration for a Store object."""

    def __init__(self, storeType, storeName, storeFieldsList, *args, **kargs):
        """Constructor."""

        #make sure store type exists
        if not storeType in StoreTypeMapping:
            raise StoreConfigError, "Unknown store type %s." % storeType

        #set attributes
        self._storeType = storeType
        self._storeName = storeName
        self._storeFieldsList = storeFieldsList
        self._args = args
        self._kargs = kargs

    def getStoreType(self):
        """Return store type."""
        return self._storeType

    def getStoreName(self):
        """Return store name."""
        return self._storeName

    def getStoreFieldsList(self):
        """Return store fields list."""
        return self._storeFieldsList

    def getStoreArgs(self):
        """Return the store args list."""
        return self._args

    def getStoreKargs(self):
        """Return the store keyword args."""
        return self._kargs

    def getStoreClass(self):
        """Return the store class."""
        return StoreTypeMapping[self._storeType]
