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
import sys
import re

#sys.path.insert(0,'/home/mlissa1/xing/pymodule')
#print sys.path

import aod
import dubov
import man

# normalize datetime string to iso format, e.g.,
# 2008-05-19 18:00:00 => 2008-05-19T18:00:00Z
# just a simple hack to give enduser a break.
# however such an enforcement had better be done at upper level.
DT_PATTERN = re.compile(r'(\d{4}-\d{2}-\d{2}).(\d{2}:\d{2}:\d{2}).?')
def normalizeDatetime(dtString):
    m = DT_PATTERN.match(dtString)
    if not m:
        raise IOError, 'unexpected format in datetime ' + dtString
    #print m.group(1) + "T" + m.group(2) + "Z"
    return m.group(1) + "T" + m.group(2) + "Z"

def geoRegionQuery(datasetName, level, version,
    startDatetime, endDatetime, latMin, latMax, lonMin, lonMax,
    responseGroups="Medium",
    dburiPrefix="root:sciflo@127.0.0.1:8989", outDir=None, outDirUrl=None):
    """geoRegionQuery(), returns response in xml."""

    # check datasetName
    if datasetName != "aeronet":
        raise RuntimeError, "%s data unavailable" % (datasetName)

    if responseGroups.find("MAN") != -1:
        startDatetime = normalizeDatetime(startDatetime)
        endDatetime = normalizeDatetime(endDatetime)
        return man.service.geoRegionQuery(datasetName, level, version,
                startDatetime, endDatetime, latMin, latMax, lonMin, lonMax,
                responseGroups.split(',')[0],
                uri="http://guppy.jpl.nasa.gov:8080/aeronet-man/select",
                outDir=outDir, outDirUrl=outDirUrl)

    if responseGroups.find("Particles") != -1:
        dburi = dburiPrefix + "/dubovdb"
        #dburi="root:sciflo@127.0.0.1:8979/dubovdb"
        return dubov.service.geoRegionQuery(datasetName, level, version,
                startDatetime, endDatetime, latMin, latMax, lonMin, lonMax,
                responseGroups.split(',')[0],
                dburi, outDir, outDirUrl)

    dburi = dburiPrefix + "/aeronetdb"
    return aod.service.geoRegionQuery(datasetName, level, version,
                startDatetime, endDatetime, latMin, latMax, lonMin, lonMax,
                responseGroups,
                dburi, outDir, outDirUrl)


def main():

    if (len(sys.argv) == 12):
        datasetName, level, version, dt0, dt1, lat0, lat1, lon0, lon1, responseGroups, dburiPrefix = sys.argv[1:]
        print geoRegionQuery(datasetName, level, version, dt0, dt1, lat0, lat1, lon0, lon1, responseGroups, dburiPrefix=dburiPrefix, outDir=None, outDirUrl=None)
        sys.exit(0)

    if (len(sys.argv) == 14):
        datasetName, level, version, dt0, dt1, lat0, lat1, lon0, lon1, responseGroups, dburiPrefix, outDir, outDirUrl = sys.argv[1:]
        print geoRegionQuery(datasetName, level, version, dt0, dt1, lat0, lat1, lon0, lon1, responseGroups, dburiPrefix=dburiPrefix, outDir=outDir, outDirUrl=outDirUrl)
        sys.exit(0)

    sys.stderr.write("Usage: " + sys.argv[0] + " datasetName level version dt0 dt1 lat0 lat1 lon0 lon1 responseGroups dburiPrefix outDir outDirUrl\n")
    sys.exit(1)


if __name__ == "__main__":
  main()
