#-----------------------------------------------------------------------------
# Name:        sqlalchemyCatalog.py
# Purpose:     SqlAlchemyCatalog subclass -- database backend implemented
#              via MySQL, Postgres, SQLite, Firebird, Sybase, MAX DB,
#              MS SQL Server using SQLAlchemy.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 25 12:16:10 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
from sqlalchemy import *
from sqlalchemy.orm import clear_mappers, mapper, create_session
import os, cPickle, time

from catalog import *
from sciflo.utils import (getXmlEtree, SCIFLO_NAMESPACE, getPrefixForNs,
getListFromUnknownObject)

class Urls(object): pass

class SqlAlchemyCatalogError(Exception):
    """Exception class for SqlAlchemyCatalog class."""
    pass

class SqlAlchemyCatalog(ScifloCatalog):
    """Subclass of ScifloCatalog that implements the catalog's database
    backend via databases supported by SQLAlchemy."""

    def __init__(self,container):
        super(SqlAlchemyCatalog,self).__init__(container)
        self.db = create_engine(container)
        self.db.echo = False
        self.metadata = MetaData(self.db)
        try:
            self.urlTable = Table('urls', self.metadata,
                                   Column('id', Integer, primary_key = True),
                                   Column('objectid', String(128), unique = True, nullable = False),
                                   Column('url_list', Text()))
            self.urlTable.create()
        except Exception:
            self.urlTable = Table('urls', self.metadata, autoload = True)
        clear_mappers()
        self.urlMapper = mapper(Urls, self.urlTable)
        self.session = create_session()
        #hack for sqlalchemy API change
        if not hasattr(self.session, 'add'): self.session.add = self.session.save
        self.saveCount = 0
        self.triggerFlush = 100
        self.waitingObjectids = {}

    def update(self,objectid,objectDataList,page=False):
        """Update/insert an objectid and its list of data objects into the catalog.
        Return 1 upon success.  Otherwise return None.  If page is True, saved
        records will be committed to the database in pages.
        """
        #check if objectid is already waiting for flush
        if objectid in self.waitingObjectids:
            self.session.flush()
            self.waitingObjectids = {}
        self.waitingObjectids[objectid] = True
        objectDataList = cPickle.dumps(getListFromUnknownObject(objectDataList))
        recs = self.session.query(Urls).filter_by(objectid=objectid).all()
        if len(recs)==0:
            newRec = Urls()
            newRec.objectid = objectid; newRec.url_list = objectDataList
            self.session.add(newRec)
        elif len(recs) == 1:
            recs[0].url_list = objectDataList
        else:
            raise RuntimeError, "Unknown number of records %d." % len(recs)
        self.saveCount += 1
        if page is True:
            if (self.saveCount % self.triggerFlush) == 0:
                self.session.flush()
                self.waitingObjectids = {}
        else:
            self.session.flush()
            self.waitingObjectids = {}
        return 1

    def query(self,objectid):
        """Query the catalog by objectid.  Returns a list of data objects that belong
        to the objectid.  Otherwise return None.
        """
        att = 1
        while True:
            try:
                recs = self.session.query(Urls).filter_by(objectid=objectid).all()
                break
            except:
                if att >= 3: raise
            time.sleep(att*2)
            att += 1
        if len(recs) == 0: return list()
        else: return cPickle.loads(recs[0].url_list)

    def remove(self,objectid):
        """Remove an objectid or list of objectids and its data objects from the catalog.  Return 1
        upon success.  Otherwise return None.
        """
        for id in getListFromUnknownObject(objectid):
            self.session.query(Urls).filter(\
                self.urlTable.c.objectid==objectid).delete()
            self.session.flush()
        return 1

    def getAllObjectids(self):
        """Return a list of all objectids in the catalog."""
        return [i.objectid for i in self.session.query(Urls).all()]

    def removeAll(self):
        """Remove an objectid or list of objectids and its data objects from the catalog.  Return 1
        upon success.  Otherwise return None.
        """
        self.urlTable.drop(); self.urlTable.create()
        return 1
    
    def __del__(self):
        """Destructor.  Call flush prior to going out of scope."""
        self.session.flush()
