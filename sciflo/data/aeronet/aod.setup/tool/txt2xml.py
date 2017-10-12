#!/usr/bin/python

import sys, os
from datetime import datetime
import xml.dom.minidom as minidom
import re

def txt2xml_one(level, fid, inPath, outPath):
    """ convert one aot file to xml. """

    fout = open(outPath,'w')
    fin = open(inPath,'r')
    
    # line1:
    line = fin.readline()
    
    # line2:
    line = fin.readline()

    # no longer needed
    ## 20070729, xing, need for level 1.5
    #if level == "1.5":
    #    line = fin.readline()
    
    # line3:
    line = fin.readline()
    meta = dict([x.split('=') for x in line.rstrip().split(',')])
    
    # line4:
    line = fin.readline()
    
    # line5:
    line = fin.readline()
    vars = line.rstrip().split(',')
    #print vars
    # the following has been done in summarize.py, so commented out here.
    ## sanity check, throw exception if aeronet format changes
    #if not(re.match(r"Date.*,Time.*,Julian_Day(,AOT_\d{3,4}){16},Water.*(,%TripletVar_\d{3,4}){16},%WaterError(,\d{3}-\d{3}Angstrom(\(Polar\))?){6},Last_Processing_Date,Solar_Zenith_Angle", line)):
    #    raise IOError, 'wrong line format in ' + inPath

    # no longer needed
    ## 20070729, xing, need for level 1.5
    #if level == "1.5":
    #    line = fin.readline()

    invalid = 999999

    # rest are data lines
    print >> fout, "<records>"

    count = 0
    for line in fin:

        count += 1
        #if count > 10:
        #  break

        print >> fout, "  <record>"
        print >> fout, "    <fid sqltype=\"int\">"+fid+"</fid>"

        tmp = line.rstrip().split(',')

        # figure out datetime from date and time
        dString, tString = tmp[0:2]
        # oddity: order is day, month, year, not year, month, day
        d, m, y = [int(x) for x in dString.split(":")]
        hh, mm, ss = [int(x) for x in tString.split(":")]
        dt = datetime(y, m, d, hh, mm, ss)
        print >> fout, "    <dt sqltype=\"datetime\">"+dt.isoformat(" ")+"</dt>"

        # extract all aot_* vars
        for i in range(3,19):
          if tmp[i] == "N/A":
            tmp[i] = str(invalid)
          print >> fout, "    <"+vars[i]+" sqltype=\"float\">"+tmp[i]+"</"+vars[i]+">"
		# extract Water(cm)
        for i in range(19,20):
          var = vars[i]
          # Water(cm) -> Water_cm
          var = var.replace("(","_")
          var = var.replace(")","")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

		# extract all %TripletVar_*
        for i in range(20,36):
          var = vars[i]
          # %TripletVar_* -> Percent_TripletVar_*
          var = var.replace("%","Percent_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

		# extract %WaterError
        for i in range(36,37):
          var = vars[i]
          # %WaterError -> Percent_Error
          var = var.replace("%","Percent_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

		# extract all *Angstrom
        for i in range(37,43):
          var = vars[i]
          # *Angstrom -> Angstrom_*
          var = var.replace("Angstrom","")
          var = var.replace("","Angstrom_",1)
          var = var.replace("-","_")
          var = var.replace("(","_")
          var = var.replace(")","")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

		# extract Last_Processing_Date
        for i in range(43,44):
          var = vars[i]
          val = tmp[i]
          #if val == "N/A":
          #  val = str(invalid)
          d, m, y = [int(x) for x in val.split("/")]
          dt = datetime(y, m, d, 0, 0, 0)
          print >> fout, "    <"+var+" sqltype=\"datetime\">"+dt.isoformat(" ")+"</"+var+">"

		# extract Solar_Zenith_Angle
        for i in range(44,45):
          var = vars[i]
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # todo: extract all other vars

        print >> fout, "  </record>"

    print >> fout, "</records>"

    fin.close()
    fout.close()

    return


def txt2xml(level, metaXML, inDir, outDir):

    #print metaXML

    #metaXML = "./meta.xml"
    #f = open(metaXML)
    dom = minidom.parse(metaXML)
    #dom = minidom.parseString(f.read())

    count = 0
    for x in dom.getElementsByTagName("file"):
        count += 1
        #if count > 3:
        #    break
        fid = x.getElementsByTagName('fid')[0].firstChild.data
        fname = x.getElementsByTagName('fname')[0].firstChild.data
        inputPath = os.path.join(inDir, fname)
        outputPath = os.path.join(outDir, fname+".xml")
        print "converting", fid, fname
        txt2xml_one(level, fid, inputPath, outputPath)

    # make sure to clean
    dom.unlink()

    return


def main():

    if (len(sys.argv) != 5):
        sys.stderr.write("Usage: " + sys.argv[0] + " level metaXML inDir outDir\n")
        sys.exit(1)

    level, metaXML, inDir, outDir = sys.argv[1:]

    txt2xml(level, metaXML, inDir, outDir)

if __name__ == "__main__":
    main()
