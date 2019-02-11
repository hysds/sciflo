# -----------------------------------------------------------------------------
# Name:        rdbmsStore.py
# Purpose:     RdbmsStore class.
#
# Author:      Gerald Manipon
#
# Created:     Wed May 09 11:01:01 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import sys
import os
import types
import re
import time
try:
    import pickle
    pickle = cPickle
except ImportError:
    import pickle
from sqlalchemy import *
import sqlalchemy.pool as pool

from .store import *
from sciflo.utils import validateDirectory

DB_SAFE_FIELDS_MAP = {
    'index': 'procIndex',
    'call': 'wuCall',
}


def getDbSafeFieldName(field):
    """Return db safe field name."""
    if field in DB_SAFE_FIELDS_MAP:
        return DB_SAFE_FIELDS_MAP[field]
    else:
        return field


def createTable(name, meta, fields):
    """Return new table."""
    dbColumns = [Column('id', Integer, primary_key=True)]
    for field in fields:
        f = getDbSafeFieldName(field)
        if field in ['wuid', 'wuConfigId', 'scifloid']:
            columnType = String
        else:
            columnType = PickleType
        dbColumns.append(Column(f, columnType))
    table = Table(name, meta, *dbColumns)
    table.create()
    return table


class RdbmsStoreError(Exception):
    """Exception class for RdbmsStore class."""
    pass


class RdbmsStore(Store):
    """Store implemented via rdbms database."""

    def __init__(self, name, fieldsList, dbHome, dbName, cleanTable=False):
        """Constructor."""

        # call super()
        super(RdbmsStore, self).__init__(name, fieldsList)

        # set db attributes
        self._dbHome = dbHome
        self._dbName = dbName

        # get db
        if self._dbHome.startswith('mysql://'):
            self._db = create_engine(self._dbHome, pool_size=1, max_overflow=0,
                                     use_threadlocal=False)
        else:
            self._db = create_engine(self._dbHome)
        #self._db.dialect.is_disconnect = lambda e: isinstance(e, exceptions.SQLError)
        self._db.echo = False
        self._dbMetadata = MetaData(self._db)
        try:
            self._table = createTable(
                self._name, self._dbMetadata, self._fieldsList)
        except exceptions.SQLError as e:
            if not re.search(r'already exists', str(e)):
                raise e
            self._table = Table(self._name, self._dbMetadata, autoload=True)
            if cleanTable is True:
                self._table.drop()
                self._table = createTable(
                    self._name, self._dbMetadata, self._fieldsList)
        self._session = create_session()
        self._retryMax = 10
        self._sleepTime = .5

    def _add(self, fieldDataList):
        """Add the fieldData list as a record."""

        insertDict = {}
        for i, field in enumerate(self._fieldsList):
            f = getDbSafeFieldName(field)
            insertDict[f] = fieldDataList[i]
        tries = 0
        while True:
            try:
                self._table.insert(insertDict).execute()
                break
            except:
                if tries > self._retryMax:
                    raise
                tries += 1
                time.sleep(self._sleepTime)

    def _remove(self, id):
        """Remove a record from the store by its id (first field)."""

        tries = 0
        while True:
            try:
                self._table.delete(getattr(self._table.c, getDbSafeFieldName(
                    self._fieldsList[0])) == id).execute()
                break
            except:
                if tries > self._retryMax:
                    raise
                tries += 1
                time.sleep(self._sleepTime)

    def _query(self, queryField, queryValue, returnFieldsList):
        """Return the field values of a field matching.  If no return fields are specified,
        it just returns the value of field.  If a single return field is specified, the
        result is a single value.  If a list of return fields is specified, result is a
        list corresponding to that list.
        """
        tries = 0
        while True:
            try:
                recs = self._table.select(getattr(self._table.c,
                                                  getDbSafeFieldName(queryField)) == queryValue).execute().fetchall()
                break
            except:
                if tries > self._retryMax:
                    raise
                tries += 1
                time.sleep(self._sleepTime)

        returnResultSet = []
        for result in recs:
            returnValsList = []
            for field in returnFieldsList:
                f = getDbSafeFieldName(field)
                val = getattr(result, f)
                returnValsList.append(val)
            returnResultSet.append(returnValsList)
        return returnResultSet

    def _update(self, id, modifyFieldDataDict):
        """Update a record."""

        updateDict = {}
        for field in list(modifyFieldDataDict.keys()):

            # make sure field is in the list
            if not field in self._fieldsList:
                raise RdbmsStoreError(
                    "Cannot update.  Field %s is not in this store." % field)

            # make sure it is not the id (first field)
            if field == self._fieldsList[0]:
                raise RdbmsStoreError(
                    "Cannot update.  The id field, %s, cannot be modified." % field)

            updateDict[getDbSafeFieldName(field)] = modifyFieldDataDict[field]
        tries = 0
        while True:
            try:
                self._table.update(getattr(self._table.c, getDbSafeFieldName(
                    self._fieldsList[0])) == id, updateDict).execute()
                break
            except:
                if tries > self._retryMax:
                    raise
                tries += 1
                time.sleep(self._sleepTime)

    def _queryAllValuesFromFields(self, returnFieldsList):
        """Query all values from a list of fields for all records and return a list."""

        # print "rdbmsStore returnFieldsList:",returnFieldsList, self._name

        # get list of results
        tries = 0
        while True:
            try:
                resultSet = self._table.select().execute().fetchall()
                break
            except:
                if tries > self._retryMax:
                    raise
                tries += 1
                time.sleep(self._sleepTime)

        returnResultSet = []
        for result in resultSet:
            returnValsList = []
            for field in returnFieldsList:
                returnValsList.append(
                    getattr(result, getDbSafeFieldName(field)))
            returnResultSet.append(returnValsList)
        return returnResultSet

    def _queryMultipleFields(self, queryDict, returnFieldsList):
        """Return the field values of fields matching.  If no return fields are specified,
        it just returns the value of fields.  If a single return field is specified, the
        result is a single value.  If a list of return fields is specified, result is a
        list corresponding to that list.
        """

        # create condition dict
        conditionClause = []
        for key, val in list(queryDict.items()):
            conditionClause.append(
                getattr(self._table.c, getDbSafeFieldName(key)) == val)

        # get list of results
        tries = 0
        while True:
            try:
                resultSet = self._table.select(
                    and_(*conditionClause)).execute().fetchall()
                break
            except:
                if tries > self._retryMax:
                    raise
                tries += 1
                time.sleep(self._sleepTime)

        # return result set
        returnResultSet = []

        # loop
        for result in resultSet:
            returnValsList = []
            for field in returnFieldsList:
                returnValsList.append(
                    getattr(result, getDbSafeFieldName(field)))
            returnResultSet.append(returnValsList)
        return returnResultSet

    def drop(self):
        """Drop table."""
        self._table.drop()
