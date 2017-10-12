#!/usr/bin/python
#-----------------------------------------------------------------------------
# Name:        subset.py
# Purpose:     Aeronet txt subset functions.
#
# Author:      Zhangfan Xing
#
# Created:     Mon Aug 14 14:43:21 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, sys
from datetime import datetime
import xml.dom.minidom as minidom


def getDatetime(datetimeString):
    """ given string "yyyy-mm-dd hh:mm:ss", return datetime """

    dString, tString = datetimeString.split(' ')

    y, m, d = [int(x) for x in dString.split('-')]
    hh, mm, ss = [int(x) for x in tString.split(':')]

    return datetime(y, m, d, hh, mm, ss)


def subset_one(dir, fname, var, dt0, dt1):
    """ given an aot fname in dir, return list data
        for var of datetime within [dt0, dt1] (inclusive).
    """

    f = open(os.path.join(dir, fname),'r')

    # line1:
    line = f.readline()

    # line2:
    line = f.readline()

    # line3:
    line = f.readline()
    meta = dict([x.split('=') for x in line.rstrip().split(',')])
    #print meta

    # line4:
    line = f.readline()

    # line5:
    line = f.readline()
    vars = line.rstrip().split(',')
    idx = vars.index(var)

    # rest are data lines
    data = []
    for line in f:

        tmp = line.rstrip().split(',')

        dString, tString = tmp[:2]
        # oddity: order is day, month, year, not year, month, day
        d, m, y = [int(x) for x in dString.split(":")]
        hh, mm, ss = [int(x) for x in tString.split(":")]
        dt = datetime(y, m, d, hh, mm, ss)

        # note: data lines in some aot files are not monotonic in datetime,
        # otherwise no need to go through all lines.
        # For now, must go through all lines.
        if not(dt0 <= dt <= dt1):
            continue

        # be consistent with rdb version (var, dt, lon, lat, fname)
        data.append((tmp[idx], dt, meta["long"], meta["lat"], fname))

    f.close()

    return data


def subset(metaXML, dir, var, dt0, dt1, lon0, lon1, lat0, lat1):
    """ Subset var from data files in dir with help of meta file metaXML. """

    dt0 = getDatetime(dt0)
    dt1 = getDatetime(dt1)

    dom = minidom.parse(metaXML)

    data = []
    for x in dom.getElementsByTagName("file"):
        #fid = x.getElementsByTagName('fid')[0].firstChild.data
        lon = x.getElementsByTagName('lon')[0].firstChild.data
        lat = x.getElementsByTagName('lat')[0].firstChild.data
        fname = x.getElementsByTagName('fname')[0].firstChild.data
        #count = x.getElementsByTagName('count')[0].firstChild.data
        dts = x.getElementsByTagName('minDatetime')[0].firstChild.data
        dte = x.getElementsByTagName('maxDatetime')[0].firstChild.data

        # to datetime from string
        dts = getDatetime(dts)
        dte = getDatetime(dte)

        # to float from string
        lon0, lon1, lon = [float(x) for x in (lon0, lon1, lon)]
        lat0, lat1, lat = [float(x) for x in (lat0, lat1, lat)]

        if dt1 < dts or dt0 > dte:
            #print "-", dts, dte, fname
            continue

        if not(lon0 <= lon <= lon1 and lat0 <= lat <= lat1):
            #print "-", lon, lat, fname
            continue

        #print "found in", fname, dts, dte, lon, lat
        data += subset_one(dir, fname, var, dt0, dt1)
    
    # make sure to clean
    dom.unlink()

    return data


def main():

    if (len(sys.argv) != 10):
        sys.stderr.write("Usage: " + sys.argv[0]
            + " metaXML dir var dt0 dt1 lon0 lon1 lat0 lat1\n")
        sys.exit(1)

    metaXML, dir, var, dt0, dt1, lon0, lon1, lat0, lat1 = sys.argv[1:]

    for x in subset(metaXML, dir, var, dt0, dt1, lon0, lon1, lat0, lat1):
        print x


if __name__ == "__main__":
    main()
