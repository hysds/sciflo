#!/usr/bin/python
#-----------------------------------------------------------------------------
# Name:        subset.py
# Purpose:     Subset command line tool for aeronet data.
#
# Author:      Zhangfan Xing
#
# Created:     Mon Aug 14 11:15:37 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import sys
import getopt

def main():
    """ a wrapper to subset aeronet data via rdb or txt """

    usage = "Usage: %s [-h|--help] --mode (rdb|txt) [--dbURI dbURI] [--metaTable metaTable] [--dataTable dataTable] [--metaXML metaXML] [--dataDir dataDir] --varName varName dt0 dt1 lon0 lon1 lat0 lat1" % (sys.argv[0])

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help", "mode=", "dbURI=","metaTable=", "dataTable=", "metaXML=", "dataDir=", "varName="])
    except getopt.GetoptError:
        sys.stderr.write(usage+"\n")
        sys.exit(1)

    mode = None
    dbURI = "localhost/test"
    metaTable = "aeronet_meta"
    dataTable = "aeronet_data"
    metaXML = "./meta.txt"
    dataDir = "./AOT"
    varName = None
    for o, a in opts:
        if o in ("-h", "--help"):
            sys.stderr.write(usage+"\n")
            sys.exit(1)
        if o == "--mode":
            mode = a
        if o == "--dbURI":
            dbURI = a
        if o == "--metaTable":
            metaTable = a
        if o == "--dataTable":
            dataTable = a
        if o == "--metaXML":
            metaXML = a
        if o == "--dataDir":
            dataDir = a
        if o == "--varName":
            varName = a

    if not(mode) or not(varName) or len(args) != 6:
        sys.stderr.write(usage+"\n")
        sys.exit(2)


    dt0, dt1, lon0, lon1, lat0, lat1 = args

    if mode == "rdb":
        from rdb.subset import subset
        for x in subset(dbURI, metaTable, dataTable,
            varName, dt0, dt1, lon0, lon1, lat0, lat1):
            print x
    else: # assume mode 'txt'
        from txt.subset import subset
        for x in subset(metaXML, dataDir,
            varName, dt0, dt1, lon0, lon1, lat0, lat1):
            print x


if __name__ == "__main__":
  main()
