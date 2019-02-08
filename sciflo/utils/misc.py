# -----------------------------------------------------------------------------
# Name:        misc.py
# Purpose:     Miscellaneous utilities.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 19 14:02:41 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import types
import os
import urllib.parse
import re
import urllib.request
import urllib.parse
import urllib.error
import shutil
import pwd
import lxml.etree
import traceback
import sys
import socket
import zipfile
import tarfile
import hashlib
import cgi
from io import StringIO
from collections import UserList
from PIL import Image
from string import Template
from tempfile import gettempdir, mktemp
import pickle as pickle
from subprocess import *
from random import Random, randrange

import sciflo
from .namespaces import SCIFLO_NAMESPACE, XSD_NAMESPACE, PY_NAMESPACE
from sciflo.utils.xmlIndent import indent
from .security import (FetchNotAllowedError, InstallNotAllowedError, fetchFromAllowed,
                       installFromAllowed)

# uid
UID = pwd.getpwuid(os.getuid())[0]


def getThreadSafeRandomObject(jumpahead=19594):
    """Return a thread safe random object."""

    rndm = Random()
    rndm.seed(randrange(jumpahead))
    return rndm


def getTempfileName(suffix=None, dir=None):
    """Return a tempfile name making sure it is unique."""

    rndm = getThreadSafeRandomObject()
    tmpBase = str(rndm.randrange(1, 32768))
    if suffix:
        tmpBase += suffix
    if dir:
        return mktemp(tmpBase, UID, dir)
    else:
        return mktemp(tmpBase, UID)


def echo(s):
    """Return the string passed in."""
    return "We are echoing: %s" % s


def getListFromUnknownObject(obj):
    """Return a list from the unknown object.  If it is a list, just return it.
    If it is a tuple or set, coerce it.  If it is a string, create a single item
    list.  If None, then an empty list.
    """

    # if this is a list return it already.
    if isinstance(obj, list):
        return obj
    # if tuple or set, make list
    elif isinstance(obj, tuple) or isinstance(obj, set) or \
            isinstance(obj, UserList):
        return list(obj)
    # if it is None, return an empty list
    elif obj is None:
        return []
    # if it needs to be eval'd, do it
    elif isinstance(obj, str) and obj.startswith('[') and \
            obj.endswith(']'):
        return eval(obj.replace('\r', ''))
    # otherwise create a single item list
    else:
        return [obj]


def getDictFromUnknownObject(obj):
    """Return a dict from the unknown object.  If it is a dict, just return it.
    """

    # if this is a dict return it already.
    if isinstance(obj, dict):
        return obj
    # if it is None, return an empty dict
    elif obj is None:
        return {}
    # if it needs to be eval'd, do it
    elif isinstance(obj, str) and obj.startswith('{') and \
            obj.endswith('}'):
        return eval(obj.replace('\r', ''))
    # otherwise try to call dict() on it
    else:
        return dict(obj)


def validateDirectory(dir, mode=0o755, noExceptionRaise=False):
    """Validate that a directory can be written to by the current process and return 1.
    Otherwise, try to create it.  If successful, return 1.  Otherwise return None.
    """

    if os.path.isdir(dir):
        if os.access(dir, 7):
            return 1
        else:
            return None
    else:
        try:
            os.makedirs(dir, mode)
            os.chmod(dir, mode)
        except:
            if noExceptionRaise:
                pass
            else:
                raise
        return 1


def getHostIp(host=None):
    """Return host ip address.  If no host is passed, returns the ip address of current host."""
    try:
        if host is None:
            host = socket.gethostname()
        return socket.gethostbyname(host)
    except Exception as e:
        print(("Got exception resolving ip address for host %s: %s" % (host, e)))
        return ''


def extractZipfile(file, dir=".", verbose=False):
    """Extract zipfile contents to directory.  Return list of names in the zip archive upon success."""
    z = zipfile.ZipFile(file)
    namelist = z.namelist()
    dirlist = [x for x in namelist if x.endswith('/')]
    filelist = [x for x in namelist if not x.endswith('/')]
    pushd = os.getcwd()
    if not os.path.isdir(dir):
        os.mkdir(dir)
    os.chdir(dir)
    # create directory structure
    dirlist.sort()
    for dirs in dirlist:
        dirs = dirs.split('/')
        prefix = ''
        for dir in dirs:
            dirname = os.path.join(prefix, dir)
            if dir and not os.path.isdir(dirname):
                os.mkdir(dirname)
            prefix = dirname
    # extract files
    for fn in filelist:
        try:
            fnDir = os.path.dirname(fn)
            if fnDir not in ['', '.'] and not os.path.isdir(fnDir):
                os.makedirs(fnDir)
            z.extract(fn)
        finally:
            if verbose:
                print(fn)
    os.chdir(pushd)
    return namelist


def extractTarfile(file, dir=".", verbose=False):
    """Function to extract tarfile to directory."""
    t = tarfile.open(file)
    if not os.path.isdir(dir):
        os.mkdir(dir)
    namelist = t.getnames()
    for n in namelist:
        try:
            t.extract(n, dir)
        finally:
            if verbose:
                print(n)
    return namelist


def isBundle(bundleFile, returnCmd=False):
    """Return True if bundle file is detected.  False otherwise.
    If returnCmd flag is True, returns cmd string instead upon success."""

    if bundleFile is None or not isinstance(bundleFile, str) or \
            not os.path.exists(bundleFile):
        return False
    if tarfile.is_tarfile(bundleFile):
        if returnCmd:
            return extractTarfile
        else:
            return True
    elif zipfile.is_zipfile(bundleFile):
        if returnCmd:
            return extractZipfile
        else:
            return True
    else:
        return False


def isPythonPackageInstaller(namelist):
    """Return the directory path containing the setup.py file, False otherwise."""
    for n in namelist:
        match = re.search(r'^(.*?)/setup\.py$', n)
        if match:
            return match.group(1)
    return False


def unpackBundle(bundleFile, dir=None, forceError=False, loc=None):
    """General function to unpack bundle files: '.tar', '.tar.gz', '.tgz',
    '.zip', '.tar.bz2', or '.tbz2'.  If a setup.py file is detected, then
    this is assumed to be a python package to install to the user's public
    sciflo site-packages directory.  If loc is defined, then installation
    of python packages will occur only if it is allowed per the 'allowCodeInstallFrom'
    configuration.  Return True upon success.
    """

    cmd = isBundle(bundleFile, returnCmd=True)
    if dir:
        curDir = os.getcwd()
    else:
        curDir = None
    if cmd:
        try:
            if dir:
                os.chdir(dir)
            namelist = cmd(bundleFile)

            # install if this is a python package
            packageDir = isPythonPackageInstaller(namelist)
            if packageDir:
                if loc is not None and not installFromAllowed(loc):
                    raise FetchNotAllowedError("Install from %s not allowed.  Modify the 'allowCodeInstallFrom' entry \
in your sciflo configuration." % loc)
                # special directories
                userPubPackageDir = getUserPubPackagesDir()
                md5dir = os.path.join(userPubPackageDir, 'MD5SUMS')
                if not os.path.isdir(md5dir):
                    os.makedirs(md5dir)

                # get md5sum and check if it is already here
                bundleMd5 = hashlib.md5(open(bundleFile).read()).hexdigest()
                md5file = os.path.join(md5dir, bundleMd5)
                if not os.path.exists(md5file):
                    # create install script
                    os.chdir(packageDir)
                    installScriptFile = './sflInstall.sh'
                    installScript = open(installScriptFile, 'w')
                    installCmdList = ["python setup.py install", "--install-purelib=%s" % userPubPackageDir,
                                      "--install-platlib=%s" % userPubPackageDir]
                    installScript.write('''#!/bin/sh\n%s\nif [ "$?" -eq "0" ]; then echo $? > SFL_INSTALL_SUCCESS; fi'''
                                        % ' '.join(installCmdList))
                    installScript.close()
                    os.chmod(installScriptFile, 0o755)

                    # run install script
                    p = Popen(installScriptFile, shell=True, env=os.environ)
                    try:
                        sts = p.wait()  # wait for child to terminate and get status
                    except Exception as e:
                        pass

                    # check if install failed
                    if not os.path.exists('SFL_INSTALL_SUCCESS'):
                        raise RuntimeError(
                            "Failed to install %s." % packageDir)

                    # write to package db
                    open(md5file, 'w').write("%s\n" % packageDir)

                    # cleanup
                    os.chdir('..')
                    shutil.rmtree(packageDir)

                else:
                    print(
                        ("Package %s already installed and is the latest version." % packageDir))
        finally:
            if dir:
                os.chdir(curDir)
        return True
    if forceError:
        raise RuntimeError(
            "Matched no unpack command for bundle: %s" % bundleFile)
    else:
        return False


def copyToDir(fileList, destDir, unpackBundles=False):
    """Generic function to stage a list of files/dirs to the specified directory.
    Generalized to handle urls.  If unpackBundles is set, will look for any
    '.tar', '.tar.gz', '.tgz', '.zip', '.tar.bz2', or '.tbz2' and unpack them."""

    # validate destination directory
    if not validateDirectory(destDir, noExceptionRaise=True):
        raise RuntimeError("Couldn't create/validate directory %s." % destDir)

    # loop over files/dirs and download
    for item in fileList:
        loc = None
        match = re.search(r'^\w+://', item)
        if match:
            (scheme, netloc, path, params, query,
             frag) = urllib.parse.urlparse(item)
            if netloc.find(':'):
                loc = netloc.split(':')[0]
            else:
                loc = netloc
            if not fetchFromAllowed(loc):
                raise FetchNotAllowedError("Fetch from %s not allowed.  Modify the 'allowCodeFetchFrom' entry \
in your sciflo configuration." % loc)

            try:
                # get urllib filehandle
                f = urllib.request.urlopen(item)
                actualUrl = f.geturl()

                # check for any sneaky redirects
                (scheme2, netloc2, path2, params2, query2,
                 frag2) = urllib.parse.urlparse(actualUrl)
                if netloc2.find(':'):
                    loc2 = netloc2.split(':')[0]
                else:
                    loc2 = netloc2
                if loc != loc2:
                    raise RuntimeError(
                        "Redirection was detected for url %s." % item)
                f.close()

                # localize
                dest = sciflo.data.localize.localizeUrl(item, destDir)
            except Exception as e:
                print(("Got exception trying to retrieve url %s to %s: %s" %
                       (item, destDir, e)))
                continue
        else:
            dest = os.path.join(destDir, os.path.basename(item))
            if os.path.isdir(item):
                shutil.copytree(item, dest)
            else:
                shutil.copy(item, dest)
        if unpackBundles:
            unpackBundle(dest, dir=destDir, loc=loc)


def resolvePath(file, pathEnviron):
    """Resolve a file using the passed in path environment or list of paths."""

    (dir, basename) = os.path.split(file)
    if dir:
        return file

    # determine if pathEnviron is a list of paths or a path env i.e. .:/bin:/usr/bin
    if isinstance(pathEnviron, list) or \
            isinstance(pathEnviron, tuple):
          pathDirs = pathEnviron
    else:
        pathDirs = pathEnviron.split(':')

    # loop over and find
    for pathDir in pathDirs:
        filePath = os.path.join(pathDir, basename)
        if os.path.exists(filePath):
            return filePath

    # if nothing came up, raise error
    raise RuntimeError(
        "Couldn't resolve file %s to a path using %s." % (file, pathEnviron))


def pidIsRunning(pid):
    """Check that a pid is currently running by checking for it in the process
    table.  Return 1 if it is.  Return 0 otherwise.
    """

    try:
        os.kill(pid, 0)
        return 1
    except OSError as e:
        return 0


def getBaseUrl(serverType, serverFqdn, serverPort):
    """Return the base url of the a server based on the protocol and port
    it is running on."""

    # dict mapping SOAP server type to protocol
    type2ProtoDict = {'GSI': 'https',
                      'gsi': 'https',
                      'SSL': 'https',
                      'ssl': 'https',
                      'HTTP': 'http',
                      'http': 'http'
                      }

    # make sure we recognize the server type
    if serverType not in type2ProtoDict:
        raise RuntimeError("Server type %s not recognized." % serverType)

    # get protocol from server type
    serverProtocol = type2ProtoDict[serverType]

    return serverProtocol + '://' + serverFqdn + ':%s' % str(serverPort)


class UrlBaseTrackerError(Exception):
    """Exception class for UrlBaseTracker."""
    pass


class UrlBaseTracker(object):
    """Class that encapsulates the mapping between local dir/files under a
    server root directory and the url of those dir/files."""

    def __init__(self, rootDir, urlBase):
        """Constructor."""

        # set root directory
        self._rootDir = os.path.abspath(rootDir)

        # set urlBase
        if urlBase.endswith('/'):
            self._urlBase = re.sub(r'/$', '', urlBase)
        else:
            self._urlBase = urlBase

    def getUrl(self, path, returnFileUrl=False):
        """Construct the url for the local path and return it."""

        # get abspath
        absPath = os.path.abspath(path)

        # make sure path starts with rootDir
        if not absPath.startswith(self._rootDir):
            if returnFileUrl:
                return 'file://%s%s' % (socket.getfqdn(), absPath)
            else:
                return absPath

        # replace
        return absPath.replace(self._rootDir, self._urlBase)

    def getLocalPath(self, url, returnFileUrl=False):
        """Construct the local path for the url and return it."""

        if os.path.exists(url):
            alreadyLocal = True
        else:
            if not url.startswith(self._urlBase):
                raise UrlBaseTrackerError("Url %s not under url base %s." %
                                          (url, self._urlBase))
            alreadyLocal = False
        retUrl = url.replace(self._urlBase, self._rootDir)
        if returnFileUrl:
            return 'file://%s%s' % (socket.getfqdn(), retUrl)
        else:
            return retUrl


class LocalizingFunctionWrapper(object):
    """Function wrapper class."""

    def __init__(self, func):
        self.__name__ = str(func)
        self._func = func
        self._args = []
        self._kargs = {}

    def __call__(self, *args, **kargs):
        self._args = args
        self._kargs = kargs
        return self._func(*self._args, **self._kargs)


class FileConversionFunction(LocalizingFunctionWrapper):
    pass


class FileAggregationFunction(LocalizingFunctionWrapper):
    pass


def runCommandLine(cmd):
    """Run command line not caring about capturing stdout/stderr."""

    try:
        retcode = call(cmd, shell=True)
    except OSError as e:
        if re.search(r'No child processes', str(e), re.IGNORECASE):
            retcode = 0
        else:
            raise RuntimeError("Execution failed for %s: %s" % (cmd, str(e)))
    if retcode < 0:
        raise RuntimeError(
            "Execution failed for %s: Child was terminated by signal %d" % (cmd, -retcode))
    return True


def convertImage(inputFile, outputFile, format=None, convert=None,
                 forcePortrait=True, options={}):
    """Convert image file from one format to another.  Return True upon success."""

    # if ps, detect if landscape
    rotate = None
    if forcePortrait and os.path.splitext(inputFile)[1] == '.ps':
        f = open(inputFile)
        fileContents = f.read()
        f.close()
        match = re.search(r'Orientation:\s*landscape',
                          fileContents, re.IGNORECASE)
        if match:
            rotate = -90
    try:
        im = Image.open(inputFile)
        if rotate:
            im = im.rotate(rotate)
        if convert and im.mode != convert:
            im.draft(convert, im.size)
            im = im.convert(convert)
        if format:
            im.save(*(outputFile, format), **options)
        else:
            im.save(*(outputFile,), **options)
    except IOError:
        #print >>sys.stderr, "Error using PIL to convert image: %s" % traceback.format_exc()
        #print >>sys.stderr, "Trying convert."
        # try using convert
        if rotate:
            cmd = "convert -rotate %s -crop 0x0 -size 1280x1024 %s %s" % (
                abs(rotate), inputFile, outputFile)
        else:
            cmd = "convert -crop 0x0 -size 1280x1024 %s %s" % (
                inputFile, outputFile)
        runCommandLine(cmd)
    return True


def convertToPng(inputFile, outputFile=None):
    """Convert image to png file."""

    # if output file not specified, create png file with same file base.
    if outputFile is None:
        outputFile = os.path.splitext(inputFile)[0]+'.png'
    convertImage(inputFile, outputFile)
    return outputFile


def convertToJpeg(inputFile, outputFile=None):
    """Convert image to jpeg file."""

    # if output file not specified, create jpg file with same file base.
    if outputFile is None:
        outputFile = os.path.splitext(inputFile)[0]+'.jpg'
    convertImage(inputFile, outputFile)
    return outputFile


def getFlashMovie(imageFiles, outputFile=None):
    """Convert images into a flash movie."""

    if outputFile is None:
        outputFile = os.path.basename(getTempfileName(suffix='.swf'))
    pngFiles = []
    for imageFile in imageFiles:
        if imageFile.endswith('.png'):
            pngFile = imageFile
        else:
            pngFile = convertToPng(imageFile)
        pngFiles.append(pngFile)
    movieFile = outputFile + '.tmp1.swf'
    output = runCommandLine(
        'png2swf -o %s -X 700 -Y 500 -j 100 %s' % (movieFile, ' '.join(pngFiles)))
    movieFile2 = outputFile + '.tmp2.swf'
    output = runCommandLine('swfcombine -o %s -X 700 -Y 500 %s viewport=%s' %
                            (movieFile2, os.path.join(sys.prefix, 'share', 'swftools', 'swfs',
                                                      'default_viewer.swf'), movieFile))
    output = runCommandLine('swfcombine -o %s -X 700 -Y 500 %s loader=%s movie=%s' %
                            (outputFile, os.path.join(sys.prefix, 'share', 'swftools', 'swfs',
                                                      'PreLoaderTemplate.swf'),
                             os.path.join(
                                 sys.prefix, 'share', 'swftools', 'swfs', 'default_loader.swf'),
                             movieFile2))
    return outputFile


def linkFile(src, dest):
    """Link src file to destination.  Return True upon success."""

    if os.path.isdir(dest):
        dest = os.path.abspath(os.path.join(dest, os.path.basename(src)))
    try:
        os.link(src, dest)
    except:
        try:
            os.symlink(src, dest)
        except:
            try:
                shutil.copy(src, dest)
            except shutil.Error as e:
                if re.search(r'are the same file', str(e), re.IGNORECASE):
                    pass
                else:
                    raise
    return True


# default conversions
DEFAULT_CONVERSION_FUNCTIONS = '''
      <op from="sf:xmlListOfDicts" to="sf:pythonDictOfLists">sciflo.utils.getListDictFromXml</op>
      <op from="sf:xmlListOfLists" to="sf:pythonDictOfLists">sciflo.utils.xmlLoL2PyDoL</op>
      <op from="sf:pythonDictOfLists" to="sf:xmlList">sciflo.utils.pyDoL2XmlList</op>
      <op from="sf:list" to="sf:xmlList">sciflo.utils.iter2Xml</op>
      <op from="*:*" to="sf:bundleFile">sciflo.utils.bundleFiles</op>
      <op from="*:*" to="sf:tgzFile">sciflo.utils.tgzFiles</op>
      <op from="*:*" to="sf:tarFile">sciflo.utils.tarFiles</op>
      <op from="*:*" to="sf:tbz2File">sciflo.utils.tbz2Files</op>
      <op from="*:*" to="sf:zipFile">sciflo.utils.zipFiles</op>
      <op from="*:*" to="xs:string">str</op>
      <op from="*:*" to="xs:float">float</op>
      <op from="*:*" to="xs:double">float</op>
      <op from="*:*" to="xs:decimal">float</op>
      <op from="*:*" to="xs:dateTime" />
      <op from="*:*" to="xs:date" />
      <op from="*:*" to="xs:timeInstant" />
      <op from="*:*" to="xs:time" />
      <op from="*:*" to="xs:int">int</op>
      <op from="*:*" to="xs:integer">int</op>
      <op from="*:*" to="xs:boolean">sciflo.utils.smart_bool</op>
      <op from="*:*" to="xs:base64">base64.decodestr</op>
      <op from="*:*" to="xs:base64Binary">base64.decodestr</op>
      <op from="*:*" to="sf:string">str</op>
      <op from="*:*" to="sf:float">float</op>
      <op from="*:*" to="sf:double">float</op>
      <op from="*:*" to="sf:decimal">float</op>
      <op from="*:*" to="sf:dateTime" />
      <op from="*:*" to="sf:date" />
      <op from="*:*" to="sf:timeInstant" />
      <op from="*:*" to="sf:time" />
      <op from="*:*" to="sf:int">int</op>
      <op from="*:*" to="sf:integer">int</op>
      <op from="*:*" to="sf:boolean">bool</op>
      <op from="*:*" to="sf:base64">base64.decodestr</op>
      <op from="*:*" to="sf:base64Binary">base64.decodestr</op>
      <op from="*:*" to="sf:list">sciflo.utils.getListFromUnknownObject</op>
      <op from="*:*" to="py:list">sciflo.utils.getListFromUnknownObject</op>
      <op from="*:*" to="sf:dict">sciflo.utils.getDictFromUnknownObject</op>
      <op from="*:*" to="py:dict">sciflo.utils.getDictFromUnknownObject</op>
      <op from="*:*" to="sf:pklFile">sciflo.utils.writePickleFile</op>
      <op from="*:*" to="sf:txtFile">sciflo.utils.writeTextFile</op>
      <op from="*:*" to="sf:pngFile">sciflo.utils.FileConversionFunction(sciflo.utils.convertToPng)</op>
      <op from="*:*" to="sf:localUrlsListNoDods">sciflo.utils.makeLocalNoDods</op>
      <op from="*:*" to="sf:localUrlsList">sciflo.utils.makeLocal</op>
      <op from="*:*" to="sf:localFile">sciflo.utils.makeLocal</op>
      <op from="*:*" to="sf:localFiles">sciflo.utils.makeLocal</op>
      <op from="*:*" to="sf:localFileNoDods">sciflo.utils.makeLocalNoDods</op>
      <op from="*:*" to="sf:localFilesNoDods">sciflo.utils.makeLocalNoDods</op>
      <op from="*:*" to="sf:xmlFile">sciflo.utils.writeXmlFile</op>
      <op from="*:*" to="sf:swfFile">sciflo.utils.FileAggregationFunction(sciflo.utils.getFlashMovie)</op>'''

# implicit conversions
IMPLICIT_CONVERSIONS = ('sf:localUrlsListNoDods', 'sf:localUrlsList',
                        'sf:localFile', 'sf:localFiles', 'sf:localFileNoDods',
                        'sf:localFilesNoDods')


def getUserInfo():
    """Return tuple of (username, home directory, user's sciflo config directory, and
    sciflo config file).  If user sciflo directory does not exist, create it.  If
    config file doesn't exist, generate default file.
    """

    userInfo = pwd.getpwuid(os.getuid())
    userName = userInfo[0]
    homeDir = userInfo[5]
    userScifloDir = os.path.join(homeDir, '.sciflo')
    if not os.path.isdir(userScifloDir):
        os.makedirs(userScifloDir, 0o755)
    convFuncDir = os.path.join(userScifloDir, 'conversionFunctions')
    if not os.path.isdir(convFuncDir):
        os.makedirs(convFuncDir, 0o755)
    userPackagesDir = os.path.join(userScifloDir, 'site-packages')
    if not os.path.isdir(userPackagesDir):
        os.makedirs(userPackagesDir, 0o755)
    pubPackagesDir = os.path.join(userPackagesDir, 'pub')
    if not os.path.isdir(pubPackagesDir):
        os.makedirs(pubPackagesDir, 0o755)
    pvtPackagesDir = os.path.join(userPackagesDir, 'pvt')
    if not os.path.isdir(pvtPackagesDir):
        os.makedirs(pvtPackagesDir, 0o755)
    datasetsDir = os.path.join(userScifloDir, 'datasets')
    if not os.path.isdir(datasetsDir):
        os.makedirs(datasetsDir, 0o755)
    userConfigFile = os.path.join(userScifloDir, 'myconfig.xml')
    if not os.path.isfile(userConfigFile):
        t = Template('''<?xml version="1.0"?>
<myConfig xmlns="${sflNs}"
          xmlns:sf="${sflNs}"
          xmlns:xs="${xsdNs}"
          xmlns:py="${pyNs}">
    <sflWorkDir>${sflWorkDir}</sflWorkDir>
    <sflExecDir>${sflExecDir}</sflExecDir>
    <cachePort>${cachePort}</cachePort>
    <hostCert>${hostCert}</hostCert>
    <hostKey>${hostKey}</hostKey>
    <sflProtocol>${sflProtocol}</sflProtocol>
    <sflPort>${sflPort}</sflPort>
    <sflProxyUrl>${sflProxyUrl}</sflProxyUrl>
    <baseUrl>${baseUrl}</baseUrl>
    <exposerProtocol>${exposerProtocol}</exposerProtocol>
    <exposerPort>${exposerPort}</exposerPort>
    <exposerProxyUrl>${exposerProxyUrl}</exposerProxyUrl>
    <dbPort>${dbPort}</dbPort>
    <dbUser>${dbUser}</dbUser>
    <dbPassword>${dbPassword}</dbPassword>
    <allowCodeFetchFrom>${allowCodeFetchFrom}</allowCodeFetchFrom>
    <allowCodeInstallFrom>${allowCodeInstallFrom}</allowCodeInstallFrom>
    <htmlBaseHref>${htmlBaseHref}</htmlBaseHref>
    <cgiBaseHref>${cgiBaseHref}</cgiBaseHref>
    <gmapKey>${gmapKey}</gmapKey>
    <workUnitTimeout>${timeout}</workUnitTimeout>
    <conversionOperators>${defConvElts}
    </conversionOperators>
</myConfig>''')
        f = open(userConfigFile, 'w')
        f.write(t.substitute(sflNs=SCIFLO_NAMESPACE, xsdNs=XSD_NAMESPACE, pyNs=PY_NAMESPACE,
                             sflWorkDir=os.path.join(
                                 gettempdir(), 'scifloWork-%s' % userName),
                             sflExecDir=os.path.join(userScifloDir, 'exec'), cachePort='8001',
                             hostCert=os.path.join(
                                 sys.prefix, 'ssl', 'hostcert.pem'),
                             hostKey=os.path.join(
                                 sys.prefix, 'ssl', 'hostkey.pem'),
                             sflProtocol='http', sflPort='9999', sflProxyUrl='',
                             exposerProtocol='http', exposerPort='8888', exposerProxyUrl='',
                             dbPort='8989', dbUser='myUsername', dbPassword='myPassword',
                             allowCodeFetchFrom='127.0.0.1 ' + getHostIp(),
                             allowCodeInstallFrom='127.0.0.1 ' + getHostIp(),
                             defConvElts=DEFAULT_CONVERSION_FUNCTIONS,
                             baseUrl='', htmlBaseHref='', cgiBaseHref='',
                             gmapKey='', timeout='86400'))
        f.close()
    return (userName, homeDir, userScifloDir, userConfigFile)


def getUserConversionFunctionsDir():
    """Return path to user's conversion function dir."""
    return os.path.join(getUserInfo()[2], 'conversionFunctions')


def getUserPackagesDir():
    """Return path to user's site-packages dir."""
    return os.path.join(getUserInfo()[2], 'site-packages')


def getUserPubPackagesDir():
    """Return path to user's public site-packages dir."""
    return os.path.join(getUserPackagesDir(), 'pub')


def getUserPvtPackagesDir():
    """Return path to user's private site-packages dir."""
    return os.path.join(getUserPackagesDir(), 'pvt')


def getUserDatasetsDir():
    """Return path to user's datasets dir."""
    return os.path.join(getUserInfo()[2], 'datasets')


SCIFLO_CONFIG_XML_TEMPLATE = Template('''<?xml version="1.0"?>
<scifloConfig xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf"
              xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <workUnitRootWorkDir>${workDir}</workUnitRootWorkDir>
  <workUnitStoreType>${wuStoreType}</workUnitStoreType>
  <workUnitStoreHome>${wuStoreHome}</workUnitStoreHome>
  <workUnitStoreName>workUnits</workUnitStoreName>
  <workUnitStoreDb>workUnits.db</workUnitStoreDb>
  <workUnitTimeout>${timeout}</workUnitTimeout>
  <cacheHome>${cacheHome}</cacheHome>
  <cacheName>workUnitCache</cacheName>
  <cacheDb>workUnitCache.db</cacheDb>
  <cachePort>${cachePort}</cachePort>
  <scheduleStoreType>${schedStoreType}</scheduleStoreType>
  <scheduleStoreHome>${schedStoreHome}</scheduleStoreHome>
  <scheduleStoreName>schedule</scheduleStoreName>
  <scheduleStoreDb>schedule.db</scheduleStoreDb>
  <hostCert>${hostCert}</hostCert>
  <hostKey>${hostKey}</hostKey>
  <gridProtocol>${gridProtocol}</gridProtocol>
  <gridPort>${gridPort}</gridPort>
  <gridProxyUrl>${gridProxyUrl}</gridProxyUrl>
  <gridNamespace>http://sciflo.jpl.nasa.gov/2006v1/sf/GridService</gridNamespace>
  <baseUrl>${baseUrl}</baseUrl>
  <exposerProtocol>${exposerProtocol}</exposerProtocol>
  <exposerPort>${exposerPort}</exposerPort>
  <exposerProxyUrl>${exposerProxyUrl}</exposerProxyUrl>
  <dbPort>${dbPort}</dbPort>
  <dbUser>${dbUser}</dbUser>
  <dbPassword>${dbPassword}</dbPassword>
  <allowCodeFetchFrom>${allowCodeFetchFrom}</allowCodeFetchFrom>
  <allowCodeInstallFrom>${allowCodeInstallFrom}</allowCodeInstallFrom>
  <htmlBaseHref>${htmlBaseHref}</htmlBaseHref>
  <cgiBaseHref>${cgiBaseHref}</cgiBaseHref>
  <gmapKey>${gmapKey}</gmapKey>
  <addWorkUnitMethod>
    <exposedName>addAndExecuteWorkUnit</exposedName>
    <pythonFunction>sciflo.grid.addAndExecuteWorkUnit</pythonFunction>
  </addWorkUnitMethod>
  <queryWorkUnitMethod>
    <exposedName>queryWorkUnit</exposedName>
    <pythonFunction>sciflo.grid.queryWorkUnit</pythonFunction>
  </queryWorkUnitMethod>
  <cancelWorkUnitMethod>
    <exposedName>cancelWorkUnit</exposedName>
    <pythonFunction>sciflo.grid.cancelWorkUnit</pythonFunction>
  </cancelWorkUnitMethod>
  <callbackMethod>
    <exposedName>workUnitCallback</exposedName>
    <pythonFunction>sciflo.grid.workUnitCallback</pythonFunction>
  </callbackMethod>
  <submitScifloMethod>
    <exposedName>submitSciflo</exposedName>
    <pythonFunction>sciflo.grid.soapFuncs.submitSciflo_server</pythonFunction>
  </submitScifloMethod>
  <submitScifloNoCacheMethod>
    <exposedName>submitSciflo_nocache</exposedName>
    <pythonFunction>sciflo.grid.soapFuncs.submitSciflo_server_nocache</pythonFunction>
  </submitScifloNoCacheMethod>
  <cancelScifloMethod>
    <exposedName>cancelSciflo</exposedName>
    <pythonFunction>sciflo.grid.soapFuncs.cancelSciflo_server</pythonFunction>
  </cancelScifloMethod>
</scifloConfig>
''')


def getUserScifloConfig(userConfigFile=None, globalConfigFile=None):
    """Return path to user's sciflo config."""

    # get user info
    userName, homeDir, userScifloDir, userConfig = getUserInfo()
    if userConfigFile is None:
        userConfigFile = userConfig
    userScifloConfigFile = os.path.join(userScifloDir, '.scifloConfig.xml')

    # get workdir and exec dir from user config files
    ucfElt, ucfNs = sciflo.utils.getXmlEtree(userConfigFile)
    workDir = ucfElt.xpath('.//_default:sflWorkDir', namespaces=ucfNs)[0].text
    execDir = ucfElt.xpath('.//_default:sflExecDir', namespaces=ucfNs)[0].text
    if re.search(r'^\w*?://.*$', execDir):
        workUnitStoreType = scheduleStoreType = 'rdbms'
        workUnitStoreHome = scheduleStoreHome = execDir
    else:
        workUnitStoreType = scheduleStoreType = 'bsddb'
        workUnitStoreHome = os.path.join(execDir, 'workUnitStoreHome')
        scheduleStoreHome = os.path.join(execDir, 'scheduleStoreHome')
    cacheHome = os.path.join(execDir, 'workUnitCache')
    cachePort = ucfElt.xpath('.//_default:cachePort', namespaces=ucfNs)[0].text
    hostCert = ucfElt.xpath('.//_default:hostCert', namespaces=ucfNs)[0].text
    hostKey = ucfElt.xpath('.//_default:hostKey', namespaces=ucfNs)[0].text
    gridProtocol = ucfElt.xpath(
        './/_default:sflProtocol', namespaces=ucfNs)[0].text
    gridPort = ucfElt.xpath('.//_default:sflPort', namespaces=ucfNs)[0].text
    gridProxyUrlNodes = ucfElt.xpath(
        './/_default:sflProxyUrl', namespaces=ucfNs)
    if len(gridProxyUrlNodes) == 0:
        gridProxyUrl = ''
    else:
        gridProxyUrl = gridProxyUrlNodes[0].text
    baseUrl = ucfElt.xpath('.//_default:baseUrl', namespaces=ucfNs)[0].text
    if baseUrl is None:
        baseUrl = ''
    exposerProtocol = ucfElt.xpath(
        './/_default:exposerProtocol', namespaces=ucfNs)[0].text
    exposerPort = ucfElt.xpath(
        './/_default:exposerPort', namespaces=ucfNs)[0].text
    exposerProxyUrlNodes = ucfElt.xpath(
        './/_default:exposerProxyUrl', namespaces=ucfNs)
    if len(exposerProxyUrlNodes) == 0:
        exposerProxyUrl = ''
    else:
        exposerProxyUrl = exposerProxyUrlNodes[0].text
    dbPort = ucfElt.xpath('.//_default:dbPort', namespaces=ucfNs)[0].text
    dbUser = ucfElt.xpath('.//_default:dbUser', namespaces=ucfNs)[0].text
    dbPassword = ucfElt.xpath('.//_default:dbPassword',
                              namespaces=ucfNs)[0].text
    allowCodeFetchFrom = ucfElt.xpath(
        './/_default:allowCodeFetchFrom', namespaces=ucfNs)[0].text
    allowCodeInstallFrom = ucfElt.xpath(
        './/_default:allowCodeInstallFrom', namespaces=ucfNs)[0].text
    htmlBaseHrefNodes = ucfElt.xpath(
        './/_default:htmlBaseHref', namespaces=ucfNs)
    if len(htmlBaseHrefNodes) == 0:
        htmlBaseHref = ''
    else:
        htmlBaseHref = htmlBaseHrefNodes[0].text
    cgiBaseHrefNodes = ucfElt.xpath(
        './/_default:cgiBaseHref', namespaces=ucfNs)
    if len(cgiBaseHrefNodes) == 0:
        cgiBaseHref = ''
    else:
        cgiBaseHref = cgiBaseHrefNodes[0].text
    gmapKeyNodes = ucfElt.xpath('.//_default:gmapKey', namespaces=ucfNs)
    if len(gmapKeyNodes) == 0:
        gmapKey = ''
    else:
        gmapKey = gmapKeyNodes[0].text
    timeout = ucfElt.xpath('.//_default:workUnitTimeout',
                           namespaces=ucfNs)[0].text
    if timeout is None:
        timeout = 86400

    # get config string
    if globalConfigFile is None:
        configStr = SCIFLO_CONFIG_XML_TEMPLATE.substitute(workDir=workDir,
                                                          wuStoreType=workUnitStoreType, schedStoreType=scheduleStoreType,
                                                          wuStoreHome=workUnitStoreHome, schedStoreHome=scheduleStoreHome,
                                                          cacheHome=cacheHome, cachePort=cachePort, gridProtocol=gridProtocol,
                                                          gridPort=gridPort, gridProxyUrl=gridProxyUrl, baseUrl=baseUrl,
                                                          exposerProtocol=exposerProtocol, exposerPort=exposerPort,
                                                          exposerProxyUrl=exposerProxyUrl, dbPort=dbPort, dbUser=dbUser,
                                                          dbPassword=dbPassword, allowCodeFetchFrom=allowCodeFetchFrom,
                                                          allowCodeInstallFrom=allowCodeInstallFrom, htmlBaseHref=htmlBaseHref,
                                                          cgiBaseHref=cgiBaseHref, hostCert=hostCert, hostKey=hostKey,
                                                          gmapKey=gmapKey, timeout=timeout)
    else:
        gcfElt, gcfNs = sciflo.utils.getXmlEtree(globalConfigFile)
        gcfElt.xpath('.//_default:workUnitRootWorkDir',
                     namespaces=gcfNs)[0].text = workDir
        gcfElt.xpath('.//_default:workUnitStoreType',
                     namespaces=gcfNs)[0].text = workUnitStoreType
        gcfElt.xpath('.//_default:scheduleStoreType',
                     namespaces=gcfNs)[0].text = scheduleStoreType
        gcfElt.xpath('.//_default:workUnitStoreHome',
                     namespaces=gcfNs)[0].text = workUnitStoreHome
        gcfElt.xpath('.//_default:scheduleStoreHome',
                     namespaces=gcfNs)[0].text = scheduleStoreHome
        gcfElt.xpath('.//_default:workUnitTimeout',
                     namespaces=gcfNs)[0].text = timeout
        gcfElt.xpath('.//_default:cacheHome',
                     namespaces=gcfNs)[0].text = cacheHome
        gcfElt.xpath('.//_default:cachePort',
                     namespaces=gcfNs)[0].text = cachePort
        gcfElt.xpath('.//_default:hostCert',
                     namespaces=gcfNs)[0].text = hostCert
        gcfElt.xpath('.//_default:hostKey', namespaces=gcfNs)[0].text = hostKey
        gcfElt.xpath('.//_default:gridProtocol',
                     namespaces=gcfNs)[0].text = gridProtocol
        gcfElt.xpath('.//_default:gridPort',
                     namespaces=gcfNs)[0].text = gridPort
        gcfElt.xpath('.//_default:gridProxyUrl',
                     namespaces=gcfNs)[0].text = gridProxyUrl
        gcfElt.xpath('.//_default:baseUrl', namespaces=gcfNs)[0].text = baseUrl
        gcfElt.xpath('.//_default:exposerProtocol',
                     namespaces=gcfNs)[0].text = exposerProtocol
        gcfElt.xpath('.//_default:exposerPort',
                     namespaces=gcfNs)[0].text = exposerPort
        gcfElt.xpath('.//_default:exposerProxyUrl',
                     namespaces=gcfNs)[0].text = exposerProxyUrl
        gcfElt.xpath('.//_default:dbPort', namespaces=gcfNs)[0].text = dbPort
        gcfElt.xpath('.//_default:dbUser', namespaces=gcfNs)[0].text = dbUser
        gcfElt.xpath('.//_default:dbPassword',
                     namespaces=gcfNs)[0].text = dbPassword
        gcfElt.xpath('.//_default:allowCodeFetchFrom',
                     namespaces=gcfNs)[0].text = allowCodeFetchFrom
        gcfElt.xpath('.//_default:allowCodeInstallFrom',
                     namespaces=gcfNs)[0].text = allowCodeInstallFrom
        gcfElt.xpath('.//_default:htmlBaseHref',
                     namespaces=gcfNs)[0].text = htmlBaseHref
        gcfElt.xpath('.//_default:cgiBaseHref',
                     namespaces=gcfNs)[0].text = cgiBaseHref
        gcfElt.xpath('.//_default:gmapKey', namespaces=gcfNs)[0].text = gmapKey
        configStr = indent(lxml.etree.tostring(gcfElt, encoding='unicode'))

    # write config file if it doesn't exist, otherwise check if it needs to be updated
    if not os.path.exists(userScifloConfigFile) or open(userScifloConfigFile, 'r').read() != configStr:
        f = open(userScifloConfigFile, 'w')
        f.write(configStr)
        f.close()
    return userScifloConfigFile


def writePickleFile(obj, outputFile=None):
    """Write object to pickle file."""

    # if output file not specified, get random name
    if outputFile is None:
        outputFile = os.path.abspath(
            os.path.basename(getTempfileName(suffix='.pkl')))
    f = open(outputFile, 'wb')
    pickle.dump(obj, f)
    f.close()
    return outputFile


def writeTextFile(obj, outputFile=None):
    """Write object in string representation to text file."""

    # if output file not specified, get random name
    if outputFile is None:
        outputFile = os.path.abspath(
            os.path.basename(getTempfileName(suffix='.txt')))
    f = open(outputFile, 'w')
    f.write(str(obj))
    f.close()
    return outputFile


def findFile(filename, rootDir):
    """Find a file in rootDirectory and return first match.  Otherwise return None."""
    for root, dirs, files in os.walk(rootDir, followlinks=True):
        for file in files:
            if file == filename:
                return os.path.join(root, file)
    return None


def findFileRegEx(expr, rootDir):
    """Find a file in rootDirectory using regex and return first match.
    Otherwise return None."""
    for root, dirs, files in os.walk(rootDir, followlinks=True):
        for file in files:
            if re.search(r'%s' % expr, file):
                return os.path.join(root, file)
    return None


def findInWorkDir(filename):
    """Find a file name in user's work directory."""
    return findFile(filename, sciflo.grid.getRootWorkDirFromConfiguration())


def getType(obj):
    # get result type
    resMatch = re.search(r"<(?:type|class) '(.+)'>", str(type(obj)))
    if resMatch:
        resType = resMatch.group(1)
    else:
        raise RuntimeError("Unable to recognize type: %s" % type(obj))

    # if instance get class name
    if resType == 'instance':
        return str(obj.__class__)
    else:
        return resType


def getFile(item, dir=None):
    """Download file and rewrite path to be local.  Return rewritten path."""

    if dir is None:
        dir = '.'
    if isinstance(item, str) and item.startswith('/'):
        if os.path.exists(item):
            return item
        else:
            return None
    return sciflo.data.localize.localizeUrl(item, dir=dir)


def isDODS(url):
    """Detect whether or not the url is a OPeNDAP url.  Return boolean."""

    if not url.startswith('http'):
        return False
    if '/nph-dods/' in url:
        return True
    try:
        ddsStr = urllib.request.urlopen(url+'.dds').read(9)
        if re.search(r'^Dataset\s*{', ddsStr):
            return True
    except Exception as e:
        pass  # print e
    return False


def makeUrlLocal(url, noDODSFlag, dir=None):
    """Return url to local path.  If DODS, return path unless noDODSFlag is set."""

    if noDODSFlag and isDODS(url):
        return None
    elif isDODS(url):
        return url
    else:
        return getFile(url, dir)


def filterLocal(urlsElt):
    """Helper function to filter elements for local files."""

    urlsToCheck = []
    for urlElt in urlsElt:
        url = urlElt.text
        if url.startswith('/') and os.path.exists(url):
            urlsToCheck = [urlElt]
            break
        urlsToCheck.append(urlElt)
    return urlsToCheck


def makeLocal(urlArg, noDODSFlag=False, dir=None):
    """Download all files locally and rewrite urls.  Return as list.  If noDODSFlag
    is True and the only available url, otherwise empty string is given."""

    # if SOAPpy.Types.*ArrayType, coerce to list (hack)
    if re.search(r'soappy\.types\..*arrayType', getType(urlArg), re.IGNORECASE):
        urlArg = urlArg._aslist()

    retList = []
    if isinstance(urlArg, (list, tuple)):
        for url in urlArg:
            urlToAdd = ''
            if isinstance(url, (list, tuple)):
                localUrl = makeLocal(url, noDODSFlag, dir)
            else:
                localUrl = makeUrlLocal(url, noDODSFlag, dir)
            if localUrl is None:
                pass
            else:
                urlToAdd = localUrl
            retList.append(urlToAdd)
        return retList
    if isinstance(urlArg, str) and not urlArg.startswith('<'):
        localUrl = makeUrlLocal(urlArg, noDODSFlag, dir)
        if localUrl is None:
            return ''
        else:
            return localUrl
    locsDoc, locsNs = sciflo.utils.getXmlEtree(urlArg)
    urlsElts = locsDoc.xpath('.//_default:urls', namespaces=locsNs)
    if len(urlsElts) > 1:
        for urlsElt in urlsElts:
            urlToAdd = ''
            for urlElt in filterLocal(urlsElt):
                localUrl = makeUrlLocal(urlElt.text, noDODSFlag, dir)
                if localUrl is None:
                    pass
                else:
                    urlToAdd = localUrl
                    break
            retList.append(urlToAdd)
        return retList
    elif len(urlsElts) == 1:
        url = makeUrlLocal(urlsElts[0].xpath(
            '_default:url', locsNs)[0].text, noDODSFlag, dir)
        if url is None:
            return ''
        else:
            return url
    else:
        urlElts = locsDoc.xpath('.//_default:url', namespaces=locsNs)
        if len(urlElts) > 1:
            for urlElt in filterLocal(urlElts):
                urlToAdd = ''
                localUrl = makeUrlLocal(urlElt.text, noDODSFlag, dir)
                if localUrl is None:
                    pass
                else:
                    urlToAdd = localUrl
                    break
                retList.append(urlToAdd)
            return retList
        elif len(urlElts) == 1:
            url = makeUrlLocal(urlElts[0].text, noDODSFlag, dir)
            if url is None:
                return ''
            else:
                return url
        else:
            raise RuntimeError("Cannot parse urls from xml:\n%s" % urlArg)


def makeLocalNoDods(urlArg, dir=None): return makeLocal(urlArg, True, dir)


def runDot(dot, outputFile=None, outputType=None):
    """Run dot command and return output file.  If outputType is not specified,
    it is determined from output file extensions.  If outputFile is None, then
    contents of output file is returned instead of the path (Used for retrieving
    SVG)."""

    otTypes = ['ps', 'svg', 'svgz', 'fig', 'mif', 'hpgl', 'pcl', 'png', 'jpg',
               'gif', 'imap', 'ismap', 'cmap', 'cmapx']
    headers = None
    tmpFlag = False
    returnContentsFlag = False
    if outputFile is None:
        outputFile = getTempfileName(suffix='.svg')
        returnContentsFlag = True
    try:
        dotFile, headers = urlllib.urlretrieve(dot)
    except:
        if re.search('}\s*$', dot):
            tmpFlag = True
            dotFile = getTempfileName(suffix='.dot')
            open(dotFile, 'w').write("%s\n" % dot)
        else:
            raise
    if outputType is None:
        ext = os.path.splitext(outputFile)[1][1:]
        if ext in otTypes:
            outputType = ext
        else:
            raise RuntimeError("Unknown extension %s." % ext)
    runCommandLine("dot -T%s -o %s %s" % (ext, outputFile, dotFile))
    if headers:
        urllib.request.urlcleanup()
    try:
        if tmpFlag:
            os.unlink(dotFile)
    except:
        pass
    contents = open(outputFile).read().replace(' encoding="UTF-8"', '')
    with open(outputFile, 'w') as f:
        f.write(contents)
    if returnContentsFlag:
        contents = open(outputFile).read()
        os.unlink(outputFile)
        return contents
    return outputFile


def getRelativeUrl(source, target):
    """Return relative url of target path from source path."""
    su = urllib.parse.urlparse(source)
    tu = urllib.parse.urlparse(target)
    junk = tu[3:]

    # scheme (http) or netloc (www.heise.de) are different
    # return absolut path of target
    if su[0] != tu[0] or su[1] != tu[1]:
        return target
    su = re.split("/", su[2])
    tu = re.split("/", tu[2])
    su.reverse()
    tu.reverse()

    # remove parts which are equal   (['a', 'b'] ['a', 'c'] --> ['c'])
    while len(su) > 0 and len(tu) > 0 and su[-1] == tu[-1]:
        su.pop()
        lastPop = tu.pop()

    # Special case: link to itself (http://foo/a http://foo/a -> a)
    if len(su) == 0 and len(tu) == 0:
        tu.append(lastPop)

    # Special case: (http://foo/a/ http://foo/a -> ../a)
    if len(su) == 1 and su[0] == "" and len(tu) == 0:
        su.append(lastPop)
        tu.append(lastPop)

    tu.reverse()
    relativeUrl = ['..' for i in range(len(su)-1)]
    relUrl = "/".join(relativeUrl + tu)
    relUrl = urllib.parse.urlunparse(
        ["", "", relUrl, junk[0], junk[1], junk[2]])
    return relUrl


def sanitizeHtml(value):
    if value is None:
        return None
    return cgi.escape(value, True)


def smart_bool(s):
    if s is True or s is False:
        return s
    s = str(s).strip().lower()
    return not s in ['false', '0', '']
