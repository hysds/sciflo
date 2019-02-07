# -----------------------------------------------------------------------------
# Name:        bsddbStore.py
# Purpose:     BsddbStore class.
#
# Author:      Gerald Manipon
#
# Created:     Tue Jun 28 07:25:35 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import os
import types
import re
import time
try:
    import pickle
    pickle = cPickle
except ImportError:
    import pickle
from bsddb3 import db

from .store import *
from . import dbtablesCDB
from sciflo.utils import validateDirectory


class BsddbStoreError(Exception):
    """Exception class for BsddbStore class."""
    pass


class BsddbStore(Store):
    """Store implemented via BSDDB database & tables."""

    def __init__(self, name, fieldsList, dbHome, dbName):
        """Constructor."""

        # call super()
        super(BsddbStore, self).__init__(name, fieldsList)

        # set db attributes
        self._dbHome = dbHome
        self._dbName = dbName

        # make sure dbHome directory exists
        if not validateDirectory(self._dbHome):
            raise BsddbStoreError("Couldn't create dbHome directory: %s."
                                  % self._dbHome)

        # create flag
        if os.path.isfile(os.path.join(self._dbHome, self._dbName)):
            createFlag = 0
        else:
            createFlag = 1

        # get db
        self._dbHandle = dbtablesCDB.bsdTableDB(
            self._dbName, dbhome=self._dbHome, create=createFlag)  # , dbflags=db.DB_INIT_CDB)

        # create table with columns if it doesn't exist
        if self._name not in self._dbHandle.ListTables():
            try:
                self._dbHandle.CreateTable(self._name, self._fieldsList)
            except dbtablesCDB.TableAlreadyExists:
                pass

    def __del__(self): self.close()

    def close(self):
        """Close db then dbenv to release all locks."""
        try:
            self._dbHandle.db.close()
        except:
            pass
        try:
            self._dbHandle.env.close()
        except:
            pass

    def _add(self, fieldDataList):
        """Add the fieldData list as a record."""

        # create record data dict to insert
        recDict = {}
        fieldIndex = 0
        for field in self._fieldsList:
            pStr = pickle.dumps(fieldDataList[fieldIndex], 1)
            recDict[field] = pStr
            fieldIndex += 1
        self._dbHandle.Insert(self._name, recDict)

    def _remove(self, id):
        """Remove a record from the store by its id (first field)."""

        idField = self._fieldsList[0]
        self._dbHandle.Delete(self._name, conditions={
                              idField: lambda x: pickle.loads(x) == id})

    def _query(self, queryField, queryValue, returnFieldsList):
        """Return the field values of a field matching.  If no return fields are specified,
        it just returns the value of field.  If a single return field is specified, the
        result is a single value.  If a list of return fields is specified, result is a
        list corresponding to that list.
        """

        # get list of results
        tries = 0
        while True:
            try:
                resultSet = self._dbHandle.Select(self._name, returnFieldsList,
                                                  conditions={queryField: lambda x: pickle.loads(x) == queryValue})
                break
            except Exception as e:
                if re.search(r'Locker does not exist', str(e), re.IGNORECASE):
                    if tries < 5:
                        tries += 1
                    else:
                        raise
                else:
                    raise
            time.sleep(1)
        returnResultSet = []
        for result in resultSet:
            returnValsList = []
            for field in returnFieldsList:
                if result[field] is None:
                    val = None
                else:
                    val = pickle.loads(result[field])
                returnValsList.append(val)
            returnResultSet.append(returnValsList)
        return returnResultSet

    def _update(self, id, modifyFieldDataDict):
        """Update a record."""

        # create record data dict to insert
        mappings = {}
        for field in list(modifyFieldDataDict.keys()):

            # make sure field is in the list
            if not field in self._fieldsList:
                raise BsddbStoreError(
                    "Cannot update.  Field %s is not in this store." % field)

            # make sure it is not the id (first field)
            if field == self._fieldsList[0]:
                raise BsddbStoreError(
                    "Cannot update.  The id field, %s, cannot be modified." % field)

            # pickle
            pStr = pickle.dumps(modifyFieldDataDict[field], 1)

            # create lambda to pickle value
            def pickleFunc(x): return pStr

            # add to mappings
            mappings[field] = pickleFunc

        # modify
        self._dbHandle.Modify(self._name, conditions={self._fieldsList[0]: lambda x: pickle.loads(x) == id},
                              mappings=mappings)

    def _queryAllValuesFromFields(self, returnFieldsList):
        """Query all values from a list of fields for all records and return a list."""

        # print "bsddbStore returnFieldsList:",returnFieldsList, self._name

        # get list of results
        resultSet = self._dbHandle.Select(self._name, returnFieldsList,
                                          conditions={self._fieldsList[0]: lambda x: 1})
        returnResultSet = []
        for result in resultSet:
            returnValsList = []
            for field in returnFieldsList:
                returnValsList.append(pickle.loads(result[field]))
            returnResultSet.append(returnValsList)
        return returnResultSet

    def _queryMultipleFields(self, queryDict, returnFieldsList):
        """Return the field values of fields matching.  If no return fields are specified,
        it just returns the value of fields.  If a single return field is specified, the
        result is a single value.  If a list of return fields is specified, result is a
        list corresponding to that list.
        """

        # create condition dict
        conditionDict = {}
        for key, val in list(queryDict.items()):
            conditionDict[key] = lambda x: pickle.loads(x) == val

        # get list of results
        resultSet = self._dbHandle.Select(self._name, returnFieldsList,
                                          conditions=conditionDict)

        # return result set
        returnResultSet = []

        # loop
        for result in resultSet:
            returnValsList = []
            for field in returnFieldsList:
                returnValsList.append(pickle.loads(result[field]))
            returnResultSet.append(returnValsList)
        return returnResultSet
