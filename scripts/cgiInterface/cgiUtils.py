import re
import types
import os
from string import Template

from sciflo.utils import isXml, isUrl, escapeCharsForCDATA, getType, getGMapKey


def urlizeEnumerable(obj):
    resList = []
    for i in obj:
        if isinstance(i, (list, tuple)):
            res = urlizeEnumerable(i)
        else:
            if isUrl(i):
                res = '<a href="%s" target="_blank">%s</a>' % (i, i)
            else:
                res = i
        resList.append(res)
    if isinstance(obj, list):
        return resList
    if isinstance(obj, tuple):
        return tuple(resList)
    else:
        raise RuntimeError("Cannot recognize type to urlize: %s" % type(obj))


class LinkHtmlGenerator(object):
    """Holder class to recognize result types and generate appropriate result links."""

    def __init__(self, recognizerFunc, generatorFunc):
        self.rec = recognizerFunc
        self.genFunc = generatorFunc

    def recognized(self, result): return self.rec(result)

    def getLink(self, wuid, result, resultIndex, *args, **kargs):
        return self.genFunc(wuid, result, resultIndex, *args, **kargs)


###############################
# link templates
###############################
# link for xml result(only works for Firefox/Mozilla)
xmlResultLnkTpl = Template('''<a href="$result" target="_blank">xml</a>''')

# link for exceptions
exceptionLnkTpl = Template(
    '''<a href="$result" target="_blank"><font color="red">exception</font></a>''')

# generic result
genericResultLnkTpl = Template(
    '''<a href="$result" target="_blank">$link</a>''')

# url/link result
linkResultLnkTpl = Template('[<a href="$result" target="_blank">download</a>]')

# bundle result
bundleResultLnkTpl = Template(
    '''[<a id="$wuid-result-$resIndex-bundle" href="#" onclick="moldResults('$wuid-result-$resIndex', 'bundle'); return false;">download</a>]''')

# kml result
kmlResultLnkTpl = Template('''
<script src="http://google.com/jsapi?key=${gmapKey}"></script>
<script>
    google.load("earth", "1");
    var ge = null;
    function init() {
        google.earth.createInstance("map3d_${wuid}", initCallback, failureCallback);
    }
    function finished(obj) {
        if (!obj) {
            alert('bad or NULL kml');
            return;
        }
        ge.getFeatures().appendChild(obj);        
    }
    function initCallback(object) {
        ge = object;
        ge.getWindow().setVisibility(true);
        
        //turn on nav control
        var navControl = ge.getNavigationControl();
        navControl.setVisibility(ge.VISIBILITY_SHOW);
        
        //load kml
        google.earth.fetchKml(ge, '${result}', finished);
    }
    function failureCallback(object) {
        alert("Failed to load Google Earth plugin.");
    }
    dojo.addOnLoad(init);
</script>
<div id='map3d_container_${wuid}' style='border: 1px solid silver; height: 600px; width: 800px;'>
    <div id='map3d_${wuid}' style='height: 100%;'></div>
</div><div id='map3d'/><br>''')

# link for results that are too large
largeResultLnk = '''<a href="#" onclick="Ext.Msg.alert('Result size exceeded', 'This result is too large to stream.  Please download using the corresponding download link below in the Sciflo Outputs section after the flow has been executed.'); return false;">xml</a>'''

############################################
# recognizer functions
############################################


def isGeneric(obj): return True


def isException(obj): return isinstance(obj, Exception)


def isNonXmlOrUrlString(obj):
    if isinstance(obj, str) and not isXml(obj) and not isUrl(obj):
        return True
    else:
        return False


def isUrlList(obj):
    # detect if list of urls exists
    urlCount = 0
    if isinstance(obj, (list, tuple)):
        for res in obj:
            if isUrl(res) or os.path.exists(str(res)):
                urlCount += 1
        if urlCount >= 2:
            return True
    return False


def isKml(obj):
    if isinstance(obj, str):
        if isUrl(obj) and obj.endswith('.kml'):
            return True
        elif isXml(obj) and re.search(r'<kml', obj):
            return True
    return False

############################################
# link result generator functions
############################################


def getXmlLink(wuid, result, resultIndex, *args, **kargs):
    # get output dir
    outputDir = kargs.get('outputDir', None)

    if outputDir:
        return xmlResultLnkTpl.substitute({
            'result': os.path.join(outputDir, 'workunit_result-%d.txt' % resultIndex)
        })
    return 'xml'


def getExceptionLink(wuid, result, resultIndex, tracebackMessage=None, **kargs):
    # get output dir
    outputDir = kargs.get('outputDir', None)

    if outputDir:
        return exceptionLnkTpl.substitute({
            'result': os.path.join(outputDir, 'workunit_result-%d.txt' % resultIndex)
        })
    return 'exception'


def getStringLink(wuid, result, resultIndex, *args, **kargs):
    # get output dir
    outputDir = kargs.get('outputDir', None)

    if outputDir:
        return genericResultLnkTpl.substitute({
            'result': os.path.join(outputDir, 'workunit_result-%d.txt' % resultIndex),
            'link': 'str'
        })
    return 'link'


def getGenericLink(wuid, result, resultIndex, *args, **kargs):
    # get output dir
    outputDir = kargs.get('outputDir', None)

    # if xml
    if isXml(result):
        return getXmlLink(wuid, result, resultIndex, *args, **kargs)
    # if exception
    elif isException(result):
        return getExceptionLink(wuid, result, resultIndex, *args, **kargs)
    # non xml/url string
    elif isNonXmlOrUrlString(result):
        return getStringLink(wuid, result, resultIndex, *args, **kargs)
    # anything else
    else:
        if outputDir:
            return genericResultLnkTpl.substitute({
                'result': os.path.join(outputDir, 'workunit_result-%d.txt' % resultIndex),
                'link': getType(result)
            })
        return 'link'


def getUrlLink(wuid, result, resultIndex, showFilesInline=False, **kargs):
    resLnkHtml = linkResultLnkTpl.substitute({'result': result})

    # show files inline
    if showFilesInline:
        ext = os.path.splitext(result)[1]
        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.swf'):
            if ext == '.swf':
                resLnkHtml = '''
                <p>Flash movie:<br><br>
                    <object width="800" height="600">
                    <param name="movie" value="%s">
                <embed width="800" height="600" src="%s"></embed></object><br>''' % (result, result)
            else:
                resLnkHtml = '<img src="%s"/>' % result
    return resLnkHtml


def getKmlLink(wuid, result, resultIndex, showFilesInline=False, **kargs):
    resLnkHtml = ''

    # show files inline
    if showFilesInline:
        ext = os.path.splitext(result)[1]
        if ext == '.kml':
            resLnkHtml = kmlResultLnkTpl.substitute({'wuid': wuid,
                                                     'gmapKey': getGMapKey(),
                                                     'result': result})
    return resLnkHtml


def getBundleLink(wuid, result, resultIndex, *args, **kargs):
    return bundleResultLnkTpl.substitute({'wuid': wuid, 'resIndex': resultIndex})


recList = [
    (isGeneric, getGenericLink),
    (isUrl, getUrlLink),
    (isUrlList, getBundleLink),
    (isKml, getKmlLink),
]

# get linkGenerators
linkGenerators = [LinkHtmlGenerator(i[0], i[1]) for i in recList]


def getResultLinkHtml(wuid, result, resultIndex, *args, **kargs):
    """Return html string for a result."""

    # get output tag name
    outputName = None
    if 'outputName' in kargs:
        outputName = kargs['outputName']

    # get type
    resType = getType(result)

    # if SOAPpy.Types.*ArrayType, coerce to list (hack)
    if re.search(r'soappy\.types\..*arrayType', resType, re.IGNORECASE):
        result = result._aslist()

    resLnkHtml = ''
    if outputName is not None:
        resLnkHtml = '%s: ' % outputName

    # loop over linkGenerators and harvest result links
    for lg in linkGenerators:
        if lg.recognized(result):
            resLnkHtml += lg.getLink(wuid, result,
                                     resultIndex, *args, **kargs) + ' '

    return resLnkHtml
