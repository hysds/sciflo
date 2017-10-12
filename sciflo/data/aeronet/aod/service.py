#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        service.py
# Purpose:     Aeronet service functions.
#
# Author:      Zhangfan Xing
#
# Created:     Mon Aug 14 14:42:03 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import sys, os
import MySQLdb as db

from sciflo.utils import SCIFLO_NAMESPACE, XSD_NAMESPACE
from sciflo.data.aeronet.subset import parse, subsetOneSite, DATA_VARS
from sciflo.data.aeronet.misc import PUB_DATA_DIR, PUB_DATA_DIR_URL, writeAsXML, writeToFileAsCSV, RANDOM_TAG

def geoRegionQuery(datasetName, level, version,
    startDatetime, endDatetime, latMin, latMax, lonMin, lonMax,
    responseGroups="Medium",
    dburi="127.0.0.1:8989/aeronet", outDir=None, outDirUrl=None):
    """geoRegionQuery(), returns response in xml."""

    # check datasetName
    if datasetName != "aeronet":
        raise RuntimeError, "%s data unavailable" % (datasetName)

    # check level
    if level == None:
        level = "1.5"

    if level == "1.5":
        metaTable="level15_meta"
        dataTable="level15_data"
    elif level == "2.0" or level == "2":
        metaTable="level20_meta"
        dataTable="level20_data"
    else:
        raise RuntimeError, "aeronet data unavailable for level %s" % (level)

    # output dir and url
    if outDir == None:
        #outDir = (WORKDIR,"./")[WORKDIR==None]
        outDir = PUB_DATA_DIR
    if outDirUrl == None:
        #outDirUrl = ("file://"+WORKDIR,"./")[WORKDIR==None]
        outDirUrl = PUB_DATA_DIR_URL

    # check verion
    # ignored for now

    # setup db conn
    host, port, username, password, dbname = parse(dburi)
    conn = db.connect(host=host, port=port, user=username, passwd=password, db=dbname)
    cursor = conn.cursor()

    # execute query for meta
    query = "SELECT fname, minDatetime, maxDatetime, lat, lon" \
        + " FROM %s" % (metaTable) \
        + " WHERE" \
        + " (lat BETWEEN %s AND %s)" % (latMin, latMax) \
        + " AND" \
        + " (lon BETWEEN %s AND %s)" % (lonMin, lonMax) \
        + " AND (" \
        + " (maxDatetime >= '%s')" %(startDatetime) \
        + " AND" \
        + " (minDatetime <= '%s')" %(endDatetime) \
        + " ) ORDER BY fname"
    cursor.execute(query)
    rows = cursor.fetchall()

    # cleanup db conn
    cursor.close()
    conn.close()
    
    # generate response xml
    xmlText = "<?xml version='1.0' encoding='UTF-8'?>\n"
    xmlText += "<resultSet xmlns='%s' xmlns:sf='%s' xmlns:xs='%s' id='aeronet'>\n" % (SCIFLO_NAMESPACE, SCIFLO_NAMESPACE, XSD_NAMESPACE)
    for x in rows:
        fname = x[0]
        xmlText += "  <result>\n"
        xmlText += "    <objectid>%s</objectid>\n" %(x[0])
        xmlText += "    <starttime>%s</starttime>\n" %(x[1])
        xmlText += "    <endtime>%s</endtime>\n" %(x[2])
        xmlText += "    <lat type='xs:float'>%s</lat>\n" %(x[3])
        xmlText += "    <lon type='xs:float'>%s</lon>\n" %(x[4])
        if responseGroups == 'Small':
            pass
        else:
            # note that it is possible len(dataRows) = 0
            dataRows = subsetOneSite(dburi, metaTable, dataTable, DATA_VARS, fname, startDatetime, endDatetime, latMin, latMax, lonMin, lonMax)
            if responseGroups == 'Large':
                xmlText += writeAsXML(DATA_VARS,dataRows)
            elif responseGroups == 'Medium':
                if len(dataRows) == 0:
                    #xmlText += "    <urls></urls>\n"
                    pass
                else:
                    xmlText += "    <urls>\n"
                    path = os.path.join(outDir,RANDOM_TAG+"."+level+"."+fname)
                    path = os.path.abspath(writeToFileAsCSV(DATA_VARS,dataRows,path))
                    xmlText += "        <url>file://%s</url>\n" % path
                    url = os.path.join(outDirUrl,os.path.basename(path))
                    xmlText += "        <url>%s</url>\n" % url
                    xmlText += "    </urls>\n"
            else:
                raise RuntimeError, "unknown responseGroups %s" % (responseGroups)
        xmlText += "  </result>\n"
    xmlText += "</resultSet>\n"

    return xmlText

def main():
    sys.stderr.write("Usage: not implemented")
    sys.exit(1)

if __name__ == "__main__":
  main()
