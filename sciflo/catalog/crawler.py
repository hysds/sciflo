#-----------------------------------------------------------------------------
# Name:        crawler.py
# Purpose:     Sciflo crawler base class and various subclasses.
#
# Author:      Gerald Manipon
#
# Created:     Sun May 08 22:26:03 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
from __future__ import with_statement
import os, re

from spider import *

CRAWLER_SCHEMA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
            elementFormDefault="qualified"
            targetNamespace="http://sciflo.jpl.nasa.gov/2006v1/sf"
            xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf"
            xmlns:py="http://sciflo.jpl.nasa.gov/2006v1/py">
    <xs:element name="crawlerConfig">
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="sf:instrument"/>
                <xs:element ref="sf:level"/>
                <xs:element ref="sf:dataLocations"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="instrument" type="xs:string"/>
    <xs:element name="level" type="xs:string"/>
    <xs:element name="dataLocations">
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="sf:location" minOccurs="1" maxOccurs="999"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="location">
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="sf:protocol" minOccurs="1" maxOccurs="1" />
                <xs:element ref="sf:site" minOccurs="1" maxOccurs="1" />
                <xs:element ref="sf:user" minOccurs="0" maxOccurs="1" />
                <xs:element ref="sf:password" minOccurs="0" maxOccurs="1" />
                <xs:element ref="sf:rootDir" minOccurs="1" maxOccurs="1" />
                <xs:element ref="sf:matchFileRegEx" minOccurs="1" maxOccurs="1" />
                <xs:element ref="sf:objectidTemplate" minOccurs="1" maxOccurs="1" />
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="protocol">
        <xs:simpleType>
            <xs:restriction base="xs:string">
                <xs:enumeration value="HTTP"/>
                <xs:enumeration value="FTP"/>
                <xs:enumeration value="DODS"/>
                <xs:enumeration value="LOCAL"/>
                <xs:enumeration value="FILE"/>
            </xs:restriction>
        </xs:simpleType>
    </xs:element>
    <xs:element name="site" type="xs:string" />
    <xs:element name="user" type="xs:string" />
    <xs:element name="password" type="xs:string" />
    <xs:element name="rootDir" type="xs:string"/>
    <xs:element name="matchFileRegEx" type="xs:string"/>
    <xs:element name="objectidTemplate" type="xs:string"/>
</xs:schema>
"""

class ScifloCrawlerError(Exception):
    """Exception class for ScifloCrawler class."""
    pass

class ScifloCrawler(object):
    """Sciflo crawler base class."""

    def __init__(self, site, user, password, rootDir, matchFileRegEx, objectidTemplate):
        """Constructor."""

        #set attributes
        self._site = site
        self._user = user
        self._password = password
        self._rootDir = rootDir
        self._matchFileRegEx = matchFileRegEx
        self._objectidTemplate = objectidTemplate

        #crawlerDataDict
        self._crawlerDataDict = None

    def _extractObjectid(self, matchObject):
        """Private method that takes in a re.match object and extracts the objectid
        from the objectidTemplate expression.
        """

        #get match groups
        groups = matchObject.groups()

        #loop over all groups and substitute it in the objectidTemplate string.
        objectid = self._objectidTemplate
        groupIndex = 1
        for group in groups:
            objectid = re.sub('\(\$%d\)' % groupIndex, group, objectid)
            groupIndex += 1
        return objectid

    def _getFileList(self):
        """Private method that returns a list of files extracted from the data location.
        NOTE: Implement this method in a subclass.
        """
        pass

    def crawl(self):
        """Go through all files returned from _getFileList() method, match any file that
        matches the regular expression(matchFileRegEx), extract the objectid using the
        objectidTemplate expression, and create a dict entry for it.

        Result is a dict of url lists indexed by objectid.  Set and return it.
        """

        foundFiles = self._getFileList()
        while True:
            try: file = foundFiles.next()
            except StopIteration: break
            #except Exception, e:
            #    print "Got exception: %s\nSkipping." % e
            #    continue
            match = self._matchFileRegEx.search(file)
            if match:
                objectid = self._extractObjectid(match)
                yield (objectid, [file])

class LocalCrawlerError(Exception):
    """Exception class for LocalCrawler class."""
    pass

class LocalCrawler(ScifloCrawler):
	"""ScifloCrawler subclass implementing local file system crawling."""

	def __init__(self, site, user, password, rootDir, matchFileRegEx, objectidTemplate):
		"""Constructor."""
		super(LocalCrawler, self).__init__(site, user, password, rootDir, matchFileRegEx, objectidTemplate)

	def _getFileList(self):
		"""Crawl the local file system.  Create list of files and return.
		"""
		return localCrawlForFiles(self._rootDir)

class FtpCrawlerError(Exception):
    """Exception class for FtpCrawler class."""
    pass

class FtpCrawler(ScifloCrawler):
	"""ScifloCrawler subclass implementing ftp crawling."""

	def __init__(self, site, user, password, rootDir, matchFileRegEx, objectidTemplate):
		"""Constructor."""
		super(FtpCrawler, self).__init__(site, user, password, rootDir, matchFileRegEx, objectidTemplate)

	def _getFileList(self):
		"""Crawl the ftp server's file system.  Create list of files and return.
		"""
		return ftpCrawlForFiles(self._site, self._rootDir, self._user, self._password)

class HttpCrawlerError(Exception):
    """Exception class for HttpCrawler class."""
    pass

class HttpCrawler(ScifloCrawler):
	"""ScifloCrawler subclass implementing http crawling."""

	def __init__(self, site, user, password, rootDir, matchFileRegEx, objectidTemplate):
		"""Constructor."""
		super(HttpCrawler, self).__init__(site, user, password, rootDir, matchFileRegEx, objectidTemplate)

	def _getFileList(self):
		"""Crawl the http server's file system.  Create list of files and return.
		"""
		return httpCrawlForFiles(self._site, self._rootDir, self._user, self._password)

class FileListingCrawlerError(Exception):
    """Exception class for FileListingCrawler class."""
    pass

class FileListingCrawler(ScifloCrawler):
	"""ScifloCrawler subclass implementing file list (in a text file) crawling."""

	def __init__(self, site, user, password, rootDir, matchFileRegEx, objectidTemplate):
		"""Constructor."""
		super(FileListingCrawler, self).__init__(site, user, password, rootDir, matchFileRegEx, objectidTemplate)

	def _getFileList(self):
		"""Crawl the file listing.  Create list of files and return.
		"""

		with open(self._site) as f:
		    for s in f.readlines(): yield s.strip()
