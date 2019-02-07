#-----------------------------------------------------------------------------
# Name:        bundler.py
# Purpose:     Bundling utilities.
#
# Author:      Gerald Manipon
#
# Created:     Thu Mar 19 14:02:41 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, re, zipfile, tarfile, shutil, sys, types
from tempfile import mkdtemp

from sciflo.utils import makeLocal
    
def bundleFiles(urlList, bundleFile="bundle.tgz", bundleDir=None):
    """Localize any files and create bundle.  Type of bundle is determined by
    extension of bundleFile.  Return the bundleFile upon success.  Otherwise
    None.
    """

    if bundleDir: tempDir = bundleDir
    else: tempDir = mkdtemp()
    curDir = os.getcwd()
    try:
        fileList = makeLocal(urlList, dir=tempDir)
        
        if re.search(r'\.tar$', bundleFile, re.IGNORECASE):
            b = tarfile.open(bundleFile, 'w')
            m = 'add'
        elif re.search(r'\.(?:tar\.gz|tgz)$', bundleFile, re.IGNORECASE):
            b = tarfile.open(bundleFile, 'w:gz')
            m = 'add'
        elif re.search(r'\.(?:tar\.bz2|tbz2)$', bundleFile, re.IGNORECASE):
            b = tarfile.open(bundleFile, 'w:bz2')
            m = 'add'
        elif re.search(r'\.zip$', bundleFile, re.IGNORECASE):
            b = zipfile.ZipFile(bundleFile, 'w')
            m = 'write'
        else: raise RuntimeError("Unknown extension for bundle type: %s" % bundleFile)
        addFile = getattr(b, m)
        os.chdir(tempDir)
        count = 1
        for f in fileList:
            if isinstance(f, (list, tuple)):
                f = bundleFiles(f, 'bundle_%04d.tgz' % count, tempDir)
                count += 1
            try:
                fileToAdd = os.path.basename(f)
                if not os.path.exists(fileToAdd): shutil.copy(f, os.path.join(tempDir, fileToAdd))
                addFile(fileToAdd)
            except Exception as e:
                print("Got exception trying to add %s to bundle: %s.  Skipping." % \
                    (fileToAdd, e), file=sys.stderr)
                continue
        b.close()
    finally:
        os.chdir(curDir)
        if bundleDir is None: shutil.rmtree(tempDir)
    
    return bundleFile

def tgzFiles(urlList, bundleFile="bundle.tgz"):
    return bundleFiles(urlList, bundleFile)

def tarFiles(urlList, bundleFile="bundle.tar"):
    return bundleFiles(urlList, bundleFile)

def tbz2Files(urlList, bundleFile="bundle.tbz2"):
    return bundleFiles(urlList, bundleFile)

def zipFiles(urlList, bundleFile="bundle.zip"):
    return bundleFiles(urlList, bundleFile)
