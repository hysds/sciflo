import libxml2
import libxslt
from tempfile import mkstemp

# xml file
file = 'testScifloDoc2.xml'

# xsl stylesheet
xsl = 'sciflo.xsl'

# temp file
(tmpFileHandle, tmpFile) = mkstemp()

styledoc = libxml2.parseFile(xsl)
style = libxslt.parseStylesheetDoc(styledoc)
doc = libxml2.parseFile(file)
result = style.applyStylesheet(doc, None)
style.saveResultToFilename(tmpFile, result, 0)
style.freeStylesheet()
doc.freeDoc()
result.freeDoc()
print(tmpFile)
