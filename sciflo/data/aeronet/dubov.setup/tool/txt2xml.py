#!/usr/bin/python

import sys, os
from datetime import datetime
import xml.dom.minidom as minidom
import re

# hack
sys.path.insert(0,"./misc")
import check_field
A = check_field.check("./misc/check_field.txt")

def txt2xml_one(fid, inPath, outPath):
    """ convert one aot file to xml. """

    fout = open(outPath,'w')
    fin = open(inPath,'r')
    
    # line1:
    line = fin.readline()
    # extract long, lat, elev and Locations
    meta = dict([x.split('=') for x in line.rstrip().split(',')][1:5])

    # line2:
    line = fin.readline()

    # line3:
    line = fin.readline()
    # sanity check is done in summarize.py, so commented out here.
    # to add more field in
    #if not(re.match(r"Date.*,Time.*,Julian_Day(,AOT_\d{3,4}){16},Water.*,DATA_TYPE$", line)):
    #    raise IOError, 'wrong line format in ' + fname

    vars = line.rstrip().split(',')
    # mormalized field names using A
    if len(vars) != len(A):
        raise Exception, "number of fields mismatch"
    c = 0
    for i in range(len(vars)):
        a = A[i].copy()
        var = a.pop()
        if vars[i] != var:
            c = c + 1
            print vars[i] + " -> " + var
            vars[i] = var
    if c != 0:
        print str(c) + " field names normalized"

    #for i in range(vars.length):

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

        # extract AOTExt.+-[TC]
        for i in range(20,32):
          var = vars[i]
          # AOTExt.+-[TC] -> AOTExt.+minus[TC]
          var = var.replace("-","minus")
          # seems a bug in original text, so convert "1022" to "1020"
          var = var.replace("1022","1020")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract 870-440AngstromParam.[AOTExt]-Total
        for i in range(32,33):
          var = vars[i]
          # 870-440AngstromParam.[AOTExt]-Total ->
          # 870to440AngstromParam_AOTExtMinusTotal
          var = var.replace("870-440","_870to440")
          var = var.replace(".","")
          var = var.replace("[","_")
          var = var.replace("]","_")
          var = var.replace("-","minus")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract SSA.+-T
        for i in range(33,37):
          var = vars[i]
          # SSA.+-T -> SSA.+minusT
          var = var.replace("-","minus")
          # seems a bug in original text, so convert "1022" to "1020"
          var = var.replace("1022","1020")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract AOTAbsp.+-T
        for i in range(37,41):
          var = vars[i]
          # AOTAbsp.+-T -> AOtAbsp.+minusT
          var = var.replace("-","minus")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract 870-440AngstromParam.[AOTAbsp]
        for i in range(41,42):
          var = vars[i]
          # 870-440AngstromParam.[AOTAbsp] ->
          # 870to440AngstromParam_AOTAbsp_
          var = var.replace("870-440","_870to440")
          var = var.replace(".","")
          var = var.replace("[","_")
          var = var.replace("]","_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract RE.+(.+)
        for i in range(42,50):
          var = vars[i]
          # RE.+(.+) -> RE.+_.+_
          var = var.replace("(","_")
          var = var.replace(")","_")
          # seems a bug in original text, so convert "1022" to "1020"
          var = var.replace("1022","1020")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract ASYM.+-[TFC]
        for i in range(50,62):
          var = vars[i]
          # ASYM.+-[TFC] -> ASYM.+minus[TFC]
          var = var.replace("-","minus")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # skip [62,84]

        # extract Inflection_Point[um]
        for i in range(84,85):
          var = vars[i]
          # Inflection_Point[um] -> Inflection_Point_um_
          var = var.replace("[","_")
          var = var.replace("]","_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract .+-.+
        for i in range(85,97):
          var = vars[i]
          # .+-.+ -> .+minus.+
          var = var.replace("-","Minus")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract .+(.+).+
        for i in range(97,107):
          var = vars[i]
          # .+(.+).+ -> .+_.+_.+
          var = var.replace("(","_")
          var = var.replace(")","_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract .+-.+
        for i in range(107,119):
          var = vars[i]
          # .+-.+ -> .+minus.+
          var = var.replace("-","minus")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # skip [119,120]

        # skip this
        ## extract alm_type
        #for i in range(120,121):
        #  var = vars[i]
        #  val = tmp[i]
        #  if val == "N/A":
        #    val = str(invalid)
        #  print >> fout, "    <"+var+" sqltype=\"int\">"+val+"</"+var+">"

        # extract [121,124]
        for i in range(121,124):
          var = vars[i]
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract alpha440-870
        for i in range(124,125):
          var = vars[i]
          var = var.replace("-","to")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract tau440(measured)
        for i in range(125,126):
          var = vars[i]
          var = var.replace("(","_")
          var = var.replace(")","_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract %sphericity
        for i in range(126,127):
          var = vars[i]
          var = var.replace("%","_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # skip this
        ## extract if_level2_AOD
        #for i in range(127,128):
        #  var = vars[i]
        #  val = tmp[i]
        #  if val == "N/A":
        #    val = str(invalid)
        #  print >> fout, "    <"+var+" sqltype=\"int\">"+val+"</"+var+">"

        # extract scat_angle.+
        for i in range(128,144):
          var = vars[i]
          var = var.replace("(","_")
          var = var.replace(")","_")
          var = var.replace(".","dot")
          var = var.replace(">=","ge")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        # extract albedo.+
        for i in range(144,148):
          var = vars[i]
          var = var.replace("-","_")
          val = tmp[i]
          if val == "N/A":
            val = str(invalid)
          print >> fout, "    <"+var+" sqltype=\"float\">"+val+"</"+var+">"

        print >> fout, "  </record>"

    print >> fout, "</records>"

    fin.close()
    fout.close()

    return


def txt2xml(metaXML, inDir, outDir):

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
        num = x.getElementsByTagName('count')[0].firstChild.data
        #print type(num), int(num.encode('utf-8'))
        if int(num.encode('utf-8')) == 0:
            print "no entry, skip ", fid, fname
            continue
        fname = x.getElementsByTagName('fname')[0].firstChild.data
        inputPath = os.path.join(inDir, fname)
        outputPath = os.path.join(outDir, fname+".xml")
        print "converting", fid, fname
        txt2xml_one(fid, inputPath, outputPath)

    # make sure to clean
    dom.unlink()

    return


def main():

    if (len(sys.argv) != 4):
        sys.stderr.write("Usage: " + sys.argv[0] + " metaXML inDir outDir\n")
        sys.exit(1)

    metaXML, inDir, outDir = sys.argv[1:]

    txt2xml(metaXML, inDir, outDir)

if __name__ == "__main__":
    main()
