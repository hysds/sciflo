import urllib
import sys, os, json
import md5

from sciflo.utils import SCIFLO_NAMESPACE, XSD_NAMESPACE
from sciflo.data.aeronet.subset import parse, subsetOneSite, DATA_VARS
from sciflo.data.aeronet.misc import PUB_DATA_DIR, PUB_DATA_DIR_URL, RANDOM_TAG

def geoRegionQuery(datasetName, level, version,
    startDatetime, endDatetime, latMin, latMax, lonMin, lonMax,
    responseGroups="Medium",
    uri=None, outDir=None, outDirUrl=None):
    """geoRegionQuery(), returns response in xml."""

    # check datasetName
    if datasetName != "aeronet":
        raise RuntimeError, "%s data unavailable" % (datasetName)

    # check level
    if level == None:
        level = "lev10"

    if level == "1.0":
        level = "lev10"
    elif level == "1.5":
        level = "lev15"
    else:
        raise RuntimeError, "aeronet data unavailable for level %s" % (level)

    if uri == None:
        raise RuntimeError, "endpoint uri missing"

    # output dir and url
    if outDir == None:
        #outDir = (WORKDIR,"./")[WORKDIR==None]
        outDir = PUB_DATA_DIR
    if outDirUrl == None:
        #outDirUrl = ("file://"+WORKDIR,"./")[WORKDIR==None]
        outDirUrl = PUB_DATA_DIR_URL

    q = 'level:%s AND datetime:[%s %s] AND lat:[%s %s] AND lon:[%s %s]' % (level,startDatetime,endDatetime,latMin,latMax,lonMin,lonMax)
    fl = "datetime,lon,lat,name,*"

    objectId = md5.md5(q).hexdigest()

    offset = 0
    total = 1
    limit = 100

    xmlText = "<?xml version='1.0' encoding='UTF-8'?>\n"
    xmlText += "<resultSet xmlns='%s' xmlns:sf='%s' xmlns:xs='%s' id='aeronet'>\n" % (SCIFLO_NAMESPACE, SCIFLO_NAMESPACE, XSD_NAMESPACE)

    xmlText += "  <result>\n"
    xmlText += "    <objectid>%s</objectid>\n" %(objectId)
    xmlText += "    <level>%s</level>\n" %(level)
    xmlText += "    <starttime>%s</starttime>\n" %(startDatetime)
    xmlText += "    <endtime>%s</endtime>\n" %(endDatetime)
    xmlText += "    <lonMin type='xs:float'>%s</lonMin>\n" %(lonMin)
    xmlText += "    <lonMax type='xs:float'>%s</lonMax>\n" %(lonMax)
    xmlText += "    <latMin type='xs:float'>%s</latMin>\n" %(latMin)
    xmlText += "    <latMax type='xs:float'>%s</latMax>\n" %(latMax)

    headerWritten = False
    out = None

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

        if headerWritten == False:
            xmlText += "    <total>%s</total>\n" % total

        if responseGroups == "Small":
            break;

        for x in o['response']['docs']:

            if responseGroups == "Medium":
                vars,vals = extract(x)
                if headerWritten == False:
                    path = os.path.join(outDir,RANDOM_TAG+".man."+level)
                    out = open(path,'w+b') # file will be truncated
                    os.chmod(path,0666)
                    url = os.path.join(outDirUrl,os.path.basename(path))
                    out.write('#')
                    out.write(','.join(vars)+'\n')
                    xmlText += "    <urls>\n"
                    xmlText += "        <url>file://%s</url>\n" % path
                    xmlText += "        <url>%s</url>\n" % url
                    xmlText += "    </urls>\n"
                    headerWritten = True
                out.write(','.join(vals)+'\n')

            if responseGroups == "Large":
                vars,vals = extract(x)
                if headerWritten == False:
                    xmlText += "    <dataSet>\n"
                    headerWritten = True
                xmlText += "      <data>\n"
                for i in range(len(vars)):
                    xmlText += "        <%s>%s</%s>\n" % (vars[i], vals[i], vars[i])
                xmlText += "      </data>\n"

    if responseGroups == 'Medium':
        if out != None:
            out.close()
    if responseGroups == 'Large':
        if total != 0:
            xmlText += "    </dataSet>\n"

    xmlText += "  </result>\n"
    xmlText += "</resultSet>\n"

    return xmlText

def extract(x):
    # remove fields not needed
    del x['id']
    del x['longitude']
    del x['latitude']
    del x['level']
    del x['timestamp']

    # save these needing a re-order
    name = x['name']; del x['name']
    datetime = x['datetime']; del x['datetime']
    lon = x['lon']; del x['lon']
    lat = x['lat']; del x['lat']

    # generate ordered keys and respective values
    keys = x.keys()
    keys.sort()
    values = [x[key] for key in keys]
    keys.insert(0,'datetime')
    values.insert(0,datetime)
    keys.insert(1,'lon')
    values.insert(1,str(lon))
    keys.insert(2,'lat')
    values.insert(2,str(lat))
    keys.append('name')
    values.append(name)

    return [keys,values]

def main():

    datasetName = "aeronet"
    level = "1.5"
    version = "ignored"

    #startDatetime = "2008-05-10T00:00:00Z"
    startDatetime = "2008-05-19T18:00:00Z"
    #startDatetime = "2008-05-20T00:00:00Z"
    endDatetime = "2008-05-20T23:59:59Z"
    lonMin = -180; lonMax = 180; latMin = -80; latMax = 80

    responseGroups = "Small"
    responseGroups = "Medium"
    #responseGroups = "Large"

    uri = "http://guppy.jpl.nasa.gov:8080/aeronet-man/select"

    outDir = "./"
    outDirUrl = "file://data/"

    grq = geoRegionQuery(datasetName, level, version, startDatetime, endDatetime, latMin, latMax, lonMin, lonMax, responseGroups, uri=uri, outDir=outDir, outDirUrl=outDirUrl)

    print grq
    #sys.stderr.write("Usage: not implemented")
    #sys.exit(1)

if __name__ == "__main__":
  main()
