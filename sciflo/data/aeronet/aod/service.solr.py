import urllib
import sys, os, json
import md5

from sciflo.utils import SCIFLO_NAMESPACE, XSD_NAMESPACE
#from sciflo.data.aeronet.subset import parse, subsetOneSite, DATA_VARS
#from mySubset import subsetOneSite, DATA_VARS
from sciflo.data.aeronet.misc import PUB_DATA_DIR, PUB_DATA_DIR_URL, writeAsXML, writeToFileAsCSV, RANDOM_TAG

# standard variable names
DATA_VARS = [
'AOT_1640', 'AOT_1020', 'AOT_870', 'AOT_675', 'AOT_667',
'AOT_555', 'AOT_551', 'AOT_532', 'AOT_531', 'AOT_500',
'AOT_490', 'AOT_443', 'AOT_440', 'AOT_412', 'AOT_380',
'AOT_340'
]

def subsetOneSite(uriPrefix, vars, name, level,
        dt0, dt1, lat0, lat1, lon0, lon1):
    """ Subset vars on one site by field fname
        for given time range, lat and lon domain.
    """

    uri = uriPrefix + "/select"

    q = 'name:%s AND level:%s AND datetime:[%s %s] AND lat:[%s %s] AND lon:[%s %s]' % (name,level,dt0,dt1,lat0,lat1,lon0,lon1)
    #print q

    #fl = "name,datetime,lon,lat,%s" % (','.join(vars))
    fl = "name,datetime,lon,lat,*"
    #fl = "*"
    #print fl

    objectId = md5.md5(q).hexdigest()

    offset = 0
    total = 1
    limit = 100

    a = []
    #max = 1000 # do not return more than max entries
    while offset <= total:
        params = urllib.urlencode({'q':q,'fl':fl,'start':offset,'rows':limit,'wt':'json'})
        f = urllib.urlopen(uri, params)
        o = json.load(f)
        #print o
        offset = o['response']['start'] + limit
        total = o['response']['numFound']
        #print offset, total

        #if total > max:
        #    xmlText += "    <error>total %s (>%s) entries found. please try again with smaller query.</error>\n" % (total,max)
        #    break;
        #else:
        #    xmlText += "    <total>%s</total>\n" % total
        for x in o['response']['docs']:
            vals = [x['datetime'],x['lon'],x['lat']]
            for var in vars:
                vals.append(x[var])
            a.append(vals)

    return a

def geoRegionQuery(datasetName, level, version,
    startDatetime, endDatetime, latMin, latMax, lonMin, lonMax,
    responseGroups="Medium",
    uriPrefix=None, outDir=None, outDirUrl=None):
    """geoRegionQuery(), returns response in xml."""

    # check datasetName
    if datasetName != "aeronet":
        raise RuntimeError, "%s data unavailable" % (datasetName)

    # check level
    if level == None:
        level = "lev20"

    if level == "lev20" or level == "2.0" or level == "2":
        level = "lev20"
    elif level == "lev15" or level == "1.5":
        level = "lev15"
    else:
        raise RuntimeError, "aeronet data unavailable for level %s" % (level)

    if uriPrefix == None:
        raise RuntimeError, "endpoint prefix uriPrefix missing"

    # output dir and url
    if outDir == None:
        #outDir = (WORKDIR,"./")[WORKDIR==None]
        outDir = PUB_DATA_DIR
    if outDirUrl == None:
        #outDirUrl = ("file://"+WORKDIR,"./")[WORKDIR==None]
        outDirUrl = PUB_DATA_DIR_URL

    # check verion
    # ignored for now

    uri = uriPrefix + "-summarize/select"

    q = 'level:%s AND maxDatetime:[%s NOW] AND minDatetime:[0000-00-00T00:00:00Z %s] AND lat:[%s %s] AND lon:[%s %s]' % (level,startDatetime,endDatetime,latMin,latMax,lonMin,lonMax)

    fl = "*"

    offset = 0
    total = 1
    limit = 100

    # generate response xml
    xmlText = "<?xml version='1.0' encoding='UTF-8'?>\n"
    xmlText += "<resultSet xmlns='%s' xmlns:sf='%s' xmlns:xs='%s' id='aeronet'>\n" % (SCIFLO_NAMESPACE, SCIFLO_NAMESPACE, XSD_NAMESPACE)

    while offset <= total:
        params = urllib.urlencode({'q':q,'fl':fl,'start':offset,'rows':limit,'wt':'json'})
        f = urllib.urlopen(uri, params)
        o = json.load(f)
        offset = o['response']['start'] + limit
        total = o['response']['numFound']
        #print offset, total

        for x in o['response']['docs']:
            fname = x['name']
            xmlText += "  <result>\n"
            xmlText += "    <objectid>%s</objectid>\n" %(x['name'])
            xmlText += "    <starttime>%s</starttime>\n" %(x['minDatetime'])
            xmlText += "    <endtime>%s</endtime>\n" %(x['maxDatetime'])
            xmlText += "    <lat type='xs:float'>%s</lat>\n" %(x['lat'])
            xmlText += "    <lon type='xs:float'>%s</lon>\n" %(x['lon'])

            if responseGroups == 'Small':
                pass
            else:
                # note that it is possible len(dataRows) = 0
                print fname
                dataRows = subsetOneSite(uriPrefix, DATA_VARS, fname, level, startDatetime, endDatetime, latMin, latMax, lonMin, lonMax)
                #print dataRows
                #dataRows = []
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
