# -----------------------------------------------------------------------------
# Name:        xmlSchemaValidationTest.py
# Purpose:     Unittest for utils.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jun 02 15:37:07 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import unittest
import os
from tempfile import mkdtemp
from lxml.etree import XMLSchemaParseError, XMLSyntaxError

from sciflo.utils import *

# directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

# crawler schema
schemaFile = os.path.join(dirName, 'test.xsd')

# bad crawler schema
badschemaFile = os.path.join(dirName, 'test_bad.xsd')

# crawler schema not well-formed
unwellformedSchemaFile = os.path.join(dirName, 'test_notwellformed.xsd')

# crawler xml config file
xmlFile = os.path.join(dirName, 'test.xml')

# bad crawler xml config file
badxmlFile = os.path.join(dirName, 'test_bad.xml')

# crawler xml schema file not well formed
unwellformedxmlFile = os.path.join(dirName, 'test_notwellformed.xml')

# crawler xml as string
crawlerSchemaXml = open(schemaFile, 'r').read()

# xml as string
xmlString = open(xmlFile, 'r').read()


class utilsTestCase(unittest.TestCase):
    """Test case for utils."""

    def testValidateXmlFileWithSchemaFile(self):
        """Test validating xml file with schema file."""

        # validate
        retVal, error = validateXml(xmlFile, schemaFile)
        self.assertEqual(retVal, True)

    def testValidateXmlFileWithSchemaFileBadXml(self):
        """Test validating bad xml file with schema file."""

        # validate bad xml
        retVal, error = validateXml(badxmlFile, schemaFile)
        self.assertEqual(isinstance(error, XmlValidationError), True)

    def testValidateXmlFileWithSchemaFileBadXsd(self):
        """Test validating xml file with bad schema file."""

        # validate bad xsd
        retVal, error = validateXml(xmlFile, badschemaFile)
        self.assertEqual(isinstance(error, XMLSchemaParseError), True)

    def testValidateXmlFileWithSchemaFileNotWellFormedXsd(self):
        """Test validating xml file with schema file not well-formed."""

        # validate bad xsd
        retVal, error = validateXml(xmlFile, unwellformedSchemaFile)
        self.assertEqual(isinstance(error, XMLSyntaxError), True)

    def testValidateXmlFileWithSchemaFileNotWellFormedXml(self):
        """Test validating xml file not well-formed with schema file."""

        # validate bad xsd
        retVal, error = validateXml(unwellformedxmlFile, schemaFile)
        self.assertEqual(isinstance(error, XMLSyntaxError), True)

    def testValidateXmlFileWithSchemaXml(self):
        """Test validating xml file with schema xml."""

        # validate bad xsd
        retVal, error = validateXml(xmlFile, crawlerSchemaXml)
        self.assertEqual(retVal, True)

    def testValidateXmlWithSchemaFile(self):
        """Test validating xml with schema file."""

        # validate bad xsd
        retVal, error = validateXml(xmlString, schemaFile)
        self.assertEqual(retVal, True)

    def testValidateXmlWithSchemaXml(self):
        """Test validating xml with schema xml."""

        # validate bad xsd
        retVal, error = validateXml(xmlString, crawlerSchemaXml)
        self.assertEqual(retVal, True)

# create testsuite function


def getTestSuite():
    """Creates and returns a test suite."""
    # run tests
    utilsTestSuite = unittest.TestSuite()
    utilsTestSuite.addTest(utilsTestCase("testValidateXmlFileWithSchemaFile"))
    utilsTestSuite.addTest(utilsTestCase(
        "testValidateXmlFileWithSchemaFileBadXml"))
    utilsTestSuite.addTest(utilsTestCase(
        "testValidateXmlFileWithSchemaFileBadXsd"))
    utilsTestSuite.addTest(utilsTestCase(
        "testValidateXmlFileWithSchemaFileNotWellFormedXsd"))
    utilsTestSuite.addTest(utilsTestCase(
        "testValidateXmlFileWithSchemaFileNotWellFormedXml"))
    utilsTestSuite.addTest(utilsTestCase("testValidateXmlFileWithSchemaXml"))
    utilsTestSuite.addTest(utilsTestCase("testValidateXmlWithSchemaFile"))
    utilsTestSuite.addTest(utilsTestCase("testValidateXmlWithSchemaXml"))

    # return
    return utilsTestSuite


# main
if __name__ == "__main__":

    # get testSuite
    testSuite = getTestSuite()

    # run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
