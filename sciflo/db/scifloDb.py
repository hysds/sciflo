# -----------------------------------------------------------------------------
# Name:        scifloDb.py
# Purpose:     Various classes/functions for database manipulation.
#
# Author:      Gerald Manipon
#
# Created:     Fri Jun 16 10:05:55 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
from sqlobject import *
from sqlobject.sqlbuilder import *
import re

from sciflo.utils import (getXmlEtree, getDatetimeFromString, xmlList2PyLoD,
                          xmlList2PyLoX, getListFromUnknownObject)


def getPyLoD(xml, recordTag):
    """Wrapper function for retrieving python list of dict from xml."""

    lod = xmlList2PyLoD(xml, recordTag)
    if len(lod) == 0:
        raise RuntimeError("Cannot extract records.  \
Make sure '%s' is the correct recordTag." % recordTag)
    return lod


class NoIndexedFieldsInXmlError(Exception):
    pass


def getIndexedFields(xml, recordTag):
    """Return list of indexed fields from xml.  Specify recordTag
    to specify tag that enumerates each record."""

    root, nsDict = getXmlEtree(xml)
    if root.tag == recordTag:
        recElt = root
    else:
        try:
            recElt = root.xpath('.//_default:%s' %
                                recordTag, namespaces=nsDict)[0]
        except:
            recElt = root.xpath('.//%s' % recordTag)[0]
    retList = []
    for subElt in recElt:
        sqltype = subElt.get('sqltype', 'text')
        if re.search(r'(index|key)', sqltype, re.IGNORECASE):
            retList.append(subElt.tag)
    if len(retList) == 0:
        raise NoIndexedFieldsInXmlError(
            "Unable to find indexed/keyed fields from xml: %s" % xml)
    return retList


def getInsertSql(tableName, xml, recordTag, database='mysql'):
    """Return SQL insert statement string."""
    return sqlrepr(Insert(Table(tableName), getPyLoD(xml, recordTag)), database)


def getUpdateSql(tableName, xml, recordTag, keyTags=[], database='mysql'):
    """Return SQL update statement string."""

    keyTags = getListFromUnknownObject(keyTags)
    t = Table(tableName)
    retStrList = []
    lod = getPyLoD(xml, recordTag)
    if len(keyTags) == 0:
        keyTags = getIndexedFields(xml, recordTag)
    for d in lod:
        whereClause = AND(*[d.get(i) == getattr(t, i) for i in keyTags])
        retStrList.append(sqlrepr(Update(t, d, where=whereClause), database))
    return '\n'.join(retStrList)


def getDeleteSql(tableName, xml, recordTag, keyTags=[], database='mysql'):
    """Return SQL delete statement string."""

    keyTags = getListFromUnknownObject(keyTags)
    t = Table(tableName)
    retStrList = []
    lod = getPyLoD(xml, recordTag)
    if len(keyTags) == 0:
        keyTags = getIndexedFields(xml, recordTag)
    for d in lod:
        whereClause = AND(*[d.get(i) == getattr(t, i) for i in keyTags])
        retStrList.append(sqlrepr(Delete(t, where=whereClause), database))
    return '\n'.join(retStrList)


def getSqlCreateInfo(xml, recordTag):
    """Return list of (column name, sqltype, key) tuples from xml.  Specify recordTag
    to specify tag that enumerates each record."""

    root, nsDict = getXmlEtree(xml)
    if root.tag == recordTag:
        recElt = root
    else:
        try:
            recElt = root.xpath('.//_default:%s' %
                                recordTag, namespaces=nsDict)[0]
        except:
            recElt = root.xpath('.//%s' % recordTag)[0]
    retList = []
    for subElt in recElt:
        retList.append((subElt.tag, subElt.get('sqltype', 'text')))
    return retList


def getCreateSql(tableName, xml, recordTag, autoKey=False):
    """Return SQL create statement string."""

    t = Table(tableName)
    sqlCreateInfoList = getSqlCreateInfo(xml, recordTag)
    retStr = "create table %s (\n" % tableName
    if autoKey:
        retStr += "    id int primary key auto_increment,\n"
    fieldStrList = ["    %s %s" % (field, sqltype)
                    for field, sqltype in sqlCreateInfoList]
    return retStr + ",\n".join(fieldStrList) + ")"


def runSql(location, sql, debug=False):
    """Run sql and return results."""

    connection = connectionForURI(location)
    sqlhub.processConnection = connection
    connection.debug = debug
    return connection.query(sql)


def insertXml(location, tableName, xml, recordTag='record', keyTags=[],
              createIfNeeded=False, database='mysql', autoKey=False,
              updateOnDup=False, iterateMode=False, forceDelete=False,
              debug=False):
    """Insert data formatted as xml into SQL database."""

    connection = connectionForURI(location)
    sqlhub.processConnection = connection
    connection.debug = debug
    if iterateMode:
        xmlRecList = xmlList2PyLoX(xml, recordTag)
    else:
        xmlRecList = [xml]
    for xmlRec in xmlRecList:
        insertSql = getInsertSql(tableName, xmlRec, recordTag, database)
        try:
            if forceDelete:
                connection.query(getDeleteSql(
                    tableName, xmlRec, recordTag, keyTags, database))
            connection.query(insertSql)
        except Exception as e:
            if re.search(r"doesn't exist", str(e), re.IGNORECASE) and createIfNeeded:
                connection.query(getCreateSql(
                    tableName, xmlRec, recordTag, autoKey))
                connection.query(insertSql)
            elif re.search(r'duplicate entry', str(e), re.IGNORECASE) and updateOnDup:
                connection.query(getUpdateSql(tableName, xmlRec, recordTag, keyTags,
                                              database))
            else:
                raise
    return True


def dropTable(location, tableName, debug=False):
    """Drop table."""

    runSql(location, "drop table %s" % tableName, debug)
    return True


class ScifloDbTableError(Exception):
    """Exception class for ScifloDbTable class."""
    pass


class ScifloDbTable(object):
    """Sciflo database table class."""

    def __init__(self, location, xmlSchema):
        """Constructor."""
        self.location = location
        self.connection = connectionForURI(location)
        sqlhub.processConnection = self.connection
        self.schemaElt, self.schemaNsDict = getXmlEtree(xmlSchema)
        self.tableName = self.schemaElt.xpath('./TableName')[0].text
        self.fieldElts = self.schemaElt.xpath('.//Field')
        classDefStrList = ["class %s(SQLObject):" % self.tableName]
        self.keyCol = None
        self.keyColSelectMethodStr = None
        self.fieldInfoDict = {}
        for fieldElt in self.fieldElts:
            id = fieldElt.xpath('./FieldName')[0].text
            typ = fieldElt.xpath('./Type')[0].text
            null = fieldElt.xpath('./Null')[0].text
            key = fieldElt.xpath('./Key')[0].text
            default = fieldElt.xpath('./Default')[0].text

            # get nullable flag
            nullable = None
            if null is None:
                pass
            elif re.search(r'yes', null, re.IGNORECASE):
                nullable = False
            else:
                pass

            # get key spec
            alternateID = None
            unique = None
            if key == '' or re.search(r'mul', key, re.IGNORECASE):
                pass
            elif re.search(r'pri', key, re.IGNORECASE):
                alternateID = True
                nullable = None
                self.keyCol = id
                self.keyColSelectMethodStr = 'by' + id[0].upper() + id[1:]
            elif re.search(r'uni', key, re.IGNORECASE):
                unique = True
            elif re.search(r'yes', key, re.IGNORECASE):
                pass
            else:
                raise ScifloDbTableError("Unknown key: %s" % key)

            # get default
            defaultVal = None
            if default:
                defaultVal = default

            # get column type
            colLen = None
            if typ.startswith('char'):
                colClass = "StringCol"
                matchChar = re.search(r'^char\((\d+)\)$', typ)
                if matchChar:
                    colLen = matchChar.group(1)
            elif typ == 'datetime':
                colClass = "DateTimeCol"
            elif typ.startswith('double'):
                colClass = "FloatCol"
            elif typ == 'time':
                colClass = "StringCol"
            else:
                raise ScifloDbTableError("Unknown column type: %s" % typ)

            # add col string for class
            colStr = "    %s = %s(" % (id, colClass)
            colArgsList = []
            if alternateID == True:
                colArgsList.append("alternateID=True")
            if nullable:
                colArgsList.append("notNone=True")
            if unique == True:
                colArgsList.append("unique=True")
            if colLen is not None:
                colArgsList.append("length=%s" % colLen)
            if defaultVal is not None:
                colArgsList.append("default='%s'" % defaultVal)

            self.fieldInfoDict[id] = {'type': typ,
                                      'alternateID': alternateID,
                                      'nullable': nullable,
                                      'unique': unique,
                                      'colLen': colLen,
                                      'key': key,
                                      'defaultVal': defaultVal
                                      }

            # build col string
            colStr = colStr + ','.join(colArgsList) + ')'

            # append to class def str
            classDefStrList.append(colStr)

        # class def string
        classDefStr = "\n".join(classDefStrList)

        # exec class code and create table
        try:
            exec(classDefStr)
            self.table = eval(self.tableName)
        except ValueError as e:
            if 'is already in the registry' in str(e):
                self.table = classregistry.findClass(self.tableName)
            else:
                raise
        except:
            raise

        self.table._connection.debug = False
        self.table.createTable(ifNotExists=True)

    def update(self, xml):
        """Update record."""

        elt, nsDict = getXmlEtree(xml)
        key = elt.xpath('./%s' % self.keyCol)[0].text
        kwargs = {}
        for thisElt in elt:
            if thisElt.text == key:
                continue
            else:
                if thisElt.tag == 'localtime':
                    fieldName = 'ltime'
                else:
                    fieldName = thisElt.tag
                typ = self.fieldInfoDict[fieldName]['type']
                if typ in ('float', 'double') or \
                        typ.startswith('double'):
                    kwargs[fieldName] = float(thisElt.text)
                elif typ == 'datetime':
                    kwargs[fieldName] = getDatetimeFromString(thisElt.text)
                else:
                    kwargs[fieldName] = thisElt.text
        try:
            res = eval("self.table.%s(key)" % self.keyColSelectMethodStr)
            res.set(**kwargs)
        except SQLObjectNotFound:
            kwargs[self.keyCol] = key
            res = self.table(**kwargs)
        except:
            raise
        return True

    def query(self, id):
        """Query the table by id.  Returns a sqlobject result.  Otherwise return None."""

        try:
            res = eval("self.table.%s(id)" % self.keyColSelectMethodStr)
        except SQLObjectNotFound:
            return None
        except:
            raise
        return res

    def remove(self, id):
        """Remove entry by id.  Return True upon success and False if not present."""

        try:
            eval("self.table.%s(id).destroySelf()" %
                 self.keyColSelectMethodStr)
        except SQLObjectNotFound:
            return False
        except:
            raise
        return True

    def removeAll(self):
        """Clean out table. Return True upon success."""

        self.connection.query(self.connection.sqlrepr(
            Delete(self.table.sqlmeta.table, None)))
        return True

    def dropTable(self):
        """Clean out table. Return True upon success."""

        self.connection.query("drop table %s" % self.table.sqlmeta.table)
        return True
