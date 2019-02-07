# -----------------------------------------------------------------------------
# Name:        xmlUtilsTest.py
# Purpose:     Unittest for xmlUtils.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jun 09 09:19:36 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import unittest
import os
from tempfile import mkdtemp
import lxml.etree
from io import StringIO

from sciflo.utils import *
from sciflo.utils.xmlIndent import indent

# this dir
thisDir = os.path.dirname(os.path.abspath(__file__))

# default namespace
defaultNamespace = SCIFLO_NAMESPACE

# xsd namespace
xsdNamespace = XSD_NAMESPACE

# xsi namespace
xsiNamespace = XSI_NAMESPACE

# xsl path
scifloXslPath = '/genesis/xsl/sciflo.xsl'

# xsl file
xslFile = os.path.join(thisDir, 'sciflo.xsl')

# sciflo xml file
xmlFile = os.path.join(thisDir, 'testScifloDoc2.xml')

# config file
configFile = os.path.join(thisDir, 'config.xml')

# endpoint xsl
configXslFile = os.path.join(thisDir, 'config2EndpointConfig.xsl')

# root tag
rootTag = 'testRootTag'

# create equal length list of lists
equalLengthList = [[1, 2, 3, 4, 5], ['a', 'b', 'c', 'd', 'e'], [
    'test', 'test2', 'test3', 'test4', 'test5']]

# equal length list heading
equalLengthHeadingTuple = ('heading1', 'heading2',
                           'heading3', 'heading4', 'heading5')

# create unequal length list of lists
unequalLengthList = [[1, 2, 3, 4, [9, 8, 7, 6, 5]], ['a', 'b', 'c', 'd', ['z']], ['test', 'test2', 'test3', 'test4', []],
                     ['asdf', 'qwe', 'ghdfg', 'hthtstf', 'ed4fd']]

# unequal length list heading
unequalLengthHeadingTuple = (
    'heading1', 'heading2', 'heading3', 'heading4', ('heading5', 'subheading'))

# result xml strings to assert against
result1 = '''<?xml version="1.0" ?>
<testRootTag/>'''
result2 = '''<?xml version="1.0" ?>
<?xml-stylesheet type="text/xsl" href="/genesis/xsl/sciflo.xsl"?><testRootTag xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf"/>'''
result3 = '''<Rows xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf">
  <row>
    <heading1 type="xs:int">1</heading1>
    <heading2 type="xs:int">2</heading2>
    <heading3 type="xs:int">3</heading3>
    <heading4 type="xs:int">4</heading4>
    <heading5 type="xs:int">5</heading5>
  </row>
  <row>
    <heading1>a</heading1>
    <heading2>b</heading2>
    <heading3>c</heading3>
    <heading4>d</heading4>
    <heading5>e</heading5>
  </row>
  <row>
    <heading1>test</heading1>
    <heading2>test2</heading2>
    <heading3>test3</heading3>
    <heading4>test4</heading4>
    <heading5>test5</heading5>
  </row>
</Rows>\n'''
result4 = '''<Rows xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf">
  <row>
    <heading1 type="xs:int">1</heading1>
    <heading2 type="xs:int">2</heading2>
    <heading3 type="xs:int">3</heading3>
    <heading4 type="xs:int">4</heading4>
    <heading5>
      <subheading type="xs:int">9</subheading>
      <subheading type="xs:int">8</subheading>
      <subheading type="xs:int">7</subheading>
      <subheading type="xs:int">6</subheading>
      <subheading type="xs:int">5</subheading>
    </heading5>
  </row>
  <row>
    <heading1>a</heading1>
    <heading2>b</heading2>
    <heading3>c</heading3>
    <heading4>d</heading4>
    <heading5>
      <subheading>z</subheading>
    </heading5>
  </row>
  <row>
    <heading1>test</heading1>
    <heading2>test2</heading2>
    <heading3>test3</heading3>
    <heading4>test4</heading4>
    <heading5/>
  </row>
  <row>
    <heading1>asdf</heading1>
    <heading2>qwe</heading2>
    <heading3>ghdfg</heading3>
    <heading4>hthtstf</heading4>
    <heading5>
      <subheading>ed4fd</subheading>
    </heading5>
  </row>
</Rows>\n'''
result5 = '''<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf" xmlns:xf="http://www.w3.org/2002/xforms" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><head><title>nrayRun</title><script type="text/javascript" src="http://sciflo.jpl.nasa.gov/genesis/test/js/formfaces.js"/><xf:model id="scifloXForm"><xf:instance><sf:inputs><sf:gpsOccId xsi:type="xs:string">20030410_2241chm_g39</sf:gpsOccId><sf:flag xsi:type="xs:float">1.5</sf:flag><sf:nstep xsi:type="xs:int">3</sf:nstep><sf:dstep xsi:type="xs:float">0.1</sf:dstep><sf:extrap xsi:type="xs:int">0</sf:extrap><sf:resultsTarFile xsi:type="xs:string">result.tar.gz</sf:resultsTarFile></sf:inputs></xf:instance><xf:submission id="s1" method="post" action="http://sciflo.jpl.nasa.gov/genesis/cgi-bin/test.cgi"/></xf:model></head><body><div class="form"><font color="blue"><p><b>nrayRun</b></p><p>Run nray.</p></font><p><b>Inputs:</b><br/><xf:input ref="/sf:inputs/sf:gpsOccId" model="scifloXForm"><xf:label>gpsOccId (string): </xf:label><xf:hint>                        Please enter a string.
                    </xf:hint></xf:input><br/><xf:input ref="/sf:inputs/sf:flag" model="scifloXForm"><xf:label>flag (string): </xf:label><xf:hint>                        Please enter a string.
                    </xf:hint></xf:input><br/><xf:input ref="/sf:inputs/sf:nstep" model="scifloXForm"><xf:label>nstep (string): </xf:label><xf:hint>                        Please enter a string.
                    </xf:hint></xf:input><br/><xf:input ref="/sf:inputs/sf:dstep" model="scifloXForm"><xf:label>dstep (string): </xf:label><xf:hint>                        Please enter a string.
                    </xf:hint></xf:input><br/><xf:input ref="/sf:inputs/sf:extrap" model="scifloXForm"><xf:label>extrap (string): </xf:label><xf:hint>                        Please enter a string.
                    </xf:hint></xf:input><br/></p><p><b>Outputs:</b><br/><xf:input ref="/sf:inputs/sf:resultsTarFile" model="scifloXForm"><xf:label>resultsTarFile (string): </xf:label><xf:hint>                        Please enter a string.
                    </xf:hint></xf:input><br/></p><xf:submit submission="s1"><xf:label>Submit</xf:label></xf:submit></div></body></html>'''
result6 = '''<?xml version="1.0"?><soapEndpoint xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf" xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><endpointName>http://sciflo.jpl.nasa.gov/2006v1/sf/GridService</endpointName><soapMethodSet><soapMethod><exposedName>addAndExecuteWorkUnit</exposedName><pythonFunction>testGridModule.addAndExecuteWorkUnitTest2</pythonFunction></soapMethod><soapMethod><exposedName>queryWorkUnit</exposedName><pythonFunction>testGridModule.queryWorkUnitTest2</pythonFunction></soapMethod><soapMethod><exposedName>cancelWorkUnit</exposedName><pythonFunction>testGridModule.cancelWorkUnitTest2</pythonFunction></soapMethod><soapMethod><exposedName>workUnitCallback</exposedName><pythonFunction>scifloManagerTest.workUnitCallback</pythonFunction></soapMethod></soapMethodSet></soapEndpoint>'''


class xmlUtilsTestCase(unittest.TestCase):
    """Test case for utils."""

    def testGetMinidomXmlDocument(self):
        """Test getMinidomXmlDocument() function."""

        # get minidom doc
        doc = getMinidomXmlDocument(rootTag)
        assert doc.toxml() == result1

        # get minidom doc with xsl processing instruction
        doc2 = getMinidomXmlDocument(
            rootTag, defaultNamespace, xslPath=scifloXslPath)
        assert doc2.toxml() == result2

    def testList2Xml(self):
        """Test list2Xml() function."""

        # get equal length list xml
        xml = list2Xml(equalLengthList, equalLengthHeadingTuple)
        assert xml == result3

        # get equal length list with list embedded
        # print unequalLengthList,unequalLengthHeadingTuple
        xml2 = list2Xml(unequalLengthList, unequalLengthHeadingTuple)
        assert xml2 == result4

    def testXmlTransform(self):
        """Test XSLT transformation using xml file and xsl file."""

        # get transformed xml
        transformedXml = transformXml(xmlFile, xslFile)

        # assert
        assert transformedXml == result5

    def testXmlTransformStrings(self):
        """Test XSLT transformation using xml string and xsl string."""

        # get strings
        xmlString = open(xmlFile, 'r').read()
        xslString = open(xslFile, 'r').read()

        # get transformed xml
        transformedXml = transformXml(xmlString, xslString)

        # assert
        assert transformedXml == result5

    def testXmlTransformXmlStringXslFile(self):
        """Test XSLT transformation using xml string and xsl file."""

        # get strings
        xmlString = open(xmlFile, 'r').read()

        # get transformed xml
        transformedXml = transformXml(xmlString, xslFile)

        # assert
        assert transformedXml == result5

    def testXmlTransformXmlFileXslString(self):
        """Test XSLT transformation using xml file and xsl string."""

        # get strings
        xslString = open(xslFile, 'r').read()

        # get transformed xml
        transformedXml = transformXml(xmlFile, xslString)

        # assert
        assert transformedXml == result5

    def testConfigToEndpointConfigXmlTransform(self):
        """Test XSLT transformation of sciflo config xml to grid endpoint xml."""

        # get transformed xml
        transformedXml = transformXml(configFile, configXslFile)

        # print transformedXml
        assert transformedXml == result6

    def testXmlIndent(self):
        """Test xml indent function."""

        # unindented xml
        unindentedXml = '<a><b><c>d</c><d>e</d></b><z>test</z></a>'
        assertionXml = '''<?xml version="1.0" encoding="iso-8859-1"?>
<a>
  <b>
    <c>d</c>
    <d>e</d>
  </b>
  <z>test</z>
</a>'''
        # test indent of xml string
        indented = indent(unindentedXml)
        self.assertEqual(indented, assertionXml)

        # test indent of element to string
        elt = lxml.etree.parse(StringIO(unindentedXml)).getroot()
        self.assertEqual(indented, indent(lxml.etree.tostring(elt)))
        elt2 = lxml.etree.XML(unindentedXml)
        self.assertEqual(indented, indent(lxml.etree.tostring(elt2)))

# create testsuite function


def getTestSuite():
    """Creates and returns a test suite."""
    # run tests
    xmlUtilsTestSuite = unittest.TestSuite()
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase("testGetMinidomXmlDocument"))
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase("testList2Xml"))
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase("testXmlTransform"))
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase("testXmlTransformStrings"))
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase(
        "testXmlTransformXmlStringXslFile"))
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase(
        "testXmlTransformXmlFileXslString"))
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase(
        "testConfigToEndpointConfigXmlTransform"))
    xmlUtilsTestSuite.addTest(xmlUtilsTestCase("testXmlIndent"))

    # return
    return xmlUtilsTestSuite


# main
if __name__ == "__main__":

    # get testSuite
    testSuite = getTestSuite()

    # run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
