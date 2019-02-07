#-----------------------------------------------------------------------------
# Name:        store.py
# Purpose:     Store class.
#
# Author:      Gerald Manipon
#
# Created:     Tue Jun 28 07:25:35 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------

from sciflo.utils import getListFromUnknownObject

class StoreError(Exception):
    """Exception class for Store class."""
    pass

class Store(object):
    """Store base class."""

    def __init__(self, name, fieldsList):
        """Constructor."""

        #set store name
        self._name = name

        #set store fields
        #We assume the first field is the unique id for this record.
        #Generation of this id is handled outside of this class.
        self._fieldsList = fieldsList

        #create store(db) here with the fields indicated
        self._dbHandle = None

    def _add(self, fieldDataList):
        """Implement the adding of a record in this method."""
        pass

    def _remove(self, id):
        """Implement the removal of a record by id in this method."""
        pass

    def _query(self, queryField, queryVal, returnFieldsList):
        """Implement the querying of a record in this method."""
        pass

    def _queryAllValuesFromFields(self, fieldList):
        """Implement the querying of all values from a list of fields
        of all records in this method."""
        pass

    def _queryMultipleFields(self, queryDict, returnFieldsList):
        """Implement the querying of records by checking multiple fields."""
        pass

    def add(self, *args, **kargs):
        """Add a record to the store populating its fields.  Return 1 upon success."""

        #create record's field data with empty values
        fieldDataList = []
        for f in range(len(self._fieldsList)): fieldDataList.append(None)

        #loop over args first
        argIndex=0
        for arg in args:

            #populate fieldData
            fieldDataList[argIndex] = arg

            #increment
            argIndex += 1

        #populate fields from keyword
        for k in list(kargs.keys()):

            #get index
            fieldIndex = self._fieldsList.index(k)

            #populate field
            fieldDataList[fieldIndex] = kargs[k]

        #add data to store
        self._add(fieldDataList)

        #return
        return 1

    def remove(self, id):
        """Remove a record from the store based on the id field (first field).
        Return 1 upon success.
        """

        self._remove(id)
        return 1

    def query(self, queryField, queryValue, returnField=None, getFieldsListFlag=None):
        """Return a list of result sets of the specified field values of records
        matching the query value.  If no return fields are specified, it just
        returns the result set list of value of the query field.  If the optional
        getFieldsListFlag flag is set, will return a tuple (resultSetList, returnFieldsList).
        """

        #return columns
        if returnField is None: returnFieldsList = [queryField]
        else: returnFieldsList = getListFromUnknownObject(returnField)

        #get result set
        resultSetList = self._query(queryField, queryValue, returnFieldsList)

        #return final list of field names and the result set
        if getFieldsListFlag: return (resultSetList, returnFieldsList)
        else: return resultSetList

    def queryMultipleFields(self, queryDict, returnField=None, getFieldsListFlag=None):
        """Return a list of result sets of the specified field values of records
        matching the query values.  If no return fields are specified, it just
        returns the result set list of value of the query fields.  If the optional
        getFieldsListFlag flag is set, will return a tuple (resultSetList, returnFieldsList).
        """

        #return columns
        if returnField is None: returnFieldsList = list(queryDict.keys())
        else: returnFieldsList = getListFromUnknownObject(returnField)

        #get result set
        resultSetList = self._queryMultipleFields(queryDict, returnFieldsList)

        #return final list of field names and the result set
        if getFieldsListFlag: return (resultSetList, returnFieldsList)
        else: return resultSetList

    def queryUnique(self, queryField, queryValue, returnField=None):
        """Verify that a query value is unique and return the fields."""

        #query
        (resultSet,returnedFields) = self.query(queryField, queryValue, returnField, getFieldsListFlag=1)

        #check if unique
        if len(resultSet) == 1:
            if len(returnedFields) == 1: return resultSet[0][0]
            else: return resultSet[0]
        elif len(resultSet)==0: return None
        else:
            raise StoreError("More than 1 result found for unique query: %s %s %s" \
            % (queryField, queryValue, returnedFields))

    def update(self, id, modifyFieldDataDict):
        """Modify the field data for the matching record id.  Return 1 upon success.
        The id cannot be modified.
        """

        #resultSet = self.queryUnique(self._fieldsList[0], id)
        #if resultSet is None:
        #    raise StoreError, "Field value %s for field %s doesn't exist in store." % (id,self._fieldsList[0])
        self._update(id, modifyFieldDataDict)
        return 1

    def getAllIds(self):
        """Return a list of ids (first column vals)."""

        #get id field
        idField = self._fieldsList[0]

        #get result set
        resultSet = self._queryAllValuesFromFields([idField])

        #print "resultSet in store:",resultSet

        #return list
        return [i[0] for i in resultSet]

    def printStore(self):
        """Print out the entire database."""

        #get result set
        resultSet = self._queryAllValuesFromFields(self._fieldsList)

        #separator
        sep = "#################################################################"
        sep2 = "-----------------------------------------------------------------"
        sep3 = "================================================================="

        #print info
        print(sep)
        print(("Name: %s" % self._name))
        print(("Fields:", self._fieldsList))
        print(sep3)

        #loop over and print
        for result in resultSet:

            print(result)
            print(sep2)

        print(sep)
