#!/usr/bin/python

import os, sys
from datetime import datetime
import re


def summarize_one(dir, fname, level):
    """ summarize one aot file. """

    f = open(os.path.join(dir, fname), 'r')
    
    # line1:
    line = f.readline()
    
    # line2:
    line = f.readline()

    # no longer needed
    ## 20070729, xing, need for level 1.5
    #if level == "1.5":
    #    line = f.readline()
    
    # line3:
    line = f.readline()
    meta = dict([x.split('=') for x in line.rstrip().split(',')])

    # line4:
    line = f.readline()
    
    # line5:
    line = f.readline()
    # sanity check, throw exception if aeronet format changes
    if not(re.match(r"Date.*,Time.*,Julian_Day(,AOT_\d{3,4}){16},Water.*(,%TripletVar_\d{3,4}){16},%WaterError(,\d{3}-\d{3}Angstrom(\(Polar\))?){6},Last_Processing_Date,Solar_Zenith_Angle", line)):
        raise IOError, 'wrong line format in ' + fname

    # no longer needed
    ## 20070729, xing, need for level 1.5
    #if level == "1.5":
    #    line = f.readline()

    # rest are data lines
    dt0 = dt1 = datetime(1, 1, 1)
    count = 0
    for line in f:

        count += 1

        dString, tString, tmp = line.rstrip().split(',', 2)
        d, m, y = [int(x) for x in dString.split(":")]
        hh, mm, ss = [int(x) for x in tString.split(":")]
        dt = datetime(y, m, d, hh, mm, ss)

        # figure out min and max datetime
        if (count == 1):
          dt0 = dt1 = dt
        else:
          if dt < dt0:
            dt0 = dt
          if dt > dt1:
            dt1 = dt
    
    f.close()

    # all items are strings
    return {
        "fname":fname,
        "minDatetime":dt0.isoformat(' '),
        "maxDatetime":dt1.isoformat(' '),
        "lon":meta["long"],
        "lat":meta["lat"],
        "count":str(count),
    }


def summarize(dir, level):
    """ summarize aot files in dir into an xml meta file."""

    # mapping
    var2sql = {
        "fid":{"name":"fid", "type":"int"},
        "fname":{"name":"fname", "type":"char(40) not null unique"},
        "minDatetime":{"name":"minDatetime", "type":"datetime"},
        "maxDatetime":{"name":"maxDatetime", "type":"datetime"},
        "lon":{"name":"lon", "type":"float"},
        "lat":{"name":"lat", "type":"float"},
        "count":{"name":"count", "type":"int"},
        }

    print "<files>"
    fid = 0
    list = os.listdir(dir)
    list.sort() # make sure list is host independent
    for f in list:
        fid += 1
        #if fid > 1:
        #    break
        dict = summarize_one(dir,f,level)
        dict["fid"] = str(fid)
        print "    <file>"
        for x in var2sql.keys():
            tagName = var2sql[x]["name"]
            sqlType = var2sql[x]["type"]
            text = dict[x]
            print "        <"+tagName+" sqltype=\""+sqlType+"\">"+text+"</"+tagName+">"
        print "    </file>"
    print "</files>"


def main():
    """ the main """

    if (len(sys.argv) != 3):
        sys.stderr.write("Usage: " + sys.argv[0] + " dir level\n")
        sys.exit(1)

    dir, level = sys.argv[1:]
    summarize(dir, level)


if __name__ == "__main__":
    main()
