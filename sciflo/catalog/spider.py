#-----------------------------------------------------------------------------
# Name:        spider.py
# Purpose:     Various spider/crawler utilities.
#
# Author:      Gerald Manipon
#
# Created:     Wed May 18 13:29:22 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import ftplib
import re
import sys
from urlparse import urljoin

from sciflo.utils.filelist import *

def localCrawlForFiles(rootDir='.'):
    """Walk a directory recursively and return a list of files found."""
    for root, dirs, files in os.walk(rootDir, followlinks=True):
        for file in files: yield os.path.join(root, file)

def ftpCrawlForFiles(site, rootDir, user=None, password=None):
    """Walk a directory on an ftp server recursively and return a list
    of file urls found.
    """

    #parse out server name
    if site.startswith('ftp://'): site = site.replace('ftp://','')

    #parse out port number and site
    port = None
    match = re.search(r'^(.+):(\d+)$', site)
    if match:
        site = match.group(1)
        port = int(match.group(2))

    #get ftp object
    ftp = ftplib.FTP()

    #connect to site
    if port: ftp.connect(site, port)
    else: ftp.connect(site)

    #if no user was specified, login via anonymous (default for login() method)
    if user is None: ftp.login()
    else: ftp.login(user, password)

    #change to root directory on server
    ftp.cwd(rootDir)

    #get list of urls and append site to url
    for url in ftpRecurse(ftp): yield "ftp://%s%s" % (site, url)

NOT_A_DIR_REGEX = re.compile(r'Not a directory', re.IGNORECASE)
NO_SUCH_FILE_DIR_REGEX = re.compile(r'No such file or directory', re.IGNORECASE)
LINK_REGEX = re.compile(r'->')
TOTAL_REGEX = re.compile(r'^total \d+$')

def ftpRecurse(ftp):
    """	Recursively crawl through each directory and call a
        callback function with current data to deal with the data.
    """
    lines = []
    ftp.dir(lines.append)
    parent = ftp.pwd()

    for line in lines:
        try:
            line.strip()
            items = line.split(' ')
            if items[-1] in ('.','..'): continue
            if items[0].startswith('d'):
                try: ftp.cwd(items[-1])
                except ftplib.error_perm:
                    print "Failed to cwd to dir %s.  Skipping." % os.path.join(parent, items[-1])
                    continue
                gen = ftpRecurse(ftp)
                while True:
                    try: yield gen.next()
                    except StopIteration: break
                ftp.cwd(parent)
            elif items[0].startswith('l') and LINK_REGEX.search(items[-2]):
                try:
                    ftp.cwd(items[-3])
                except ftplib.error_perm, e:
                    errorStr = str(e)
                    if NOT_A_DIR_REGEX.search(errorStr):
                        print "Got soft-linked file: %s" % os.path.join(parent, items[-3])
                        yield os.path.join(parent, items[-3])
                        continue
                    elif NO_SUCH_FILE_DIR_REGEX.search(errorStr):
                        print "Source directory for soft link doesn't exist: %s" % errorStr
                        continue
                    else: raise
                gen = ftpRecurse(ftp)
                while True:
                    try: yield gen.next()
                    except StopIteration: break
                ftp.cwd(parent)
            elif items[0].startswith('-'):
                yield os.path.join(parent, items[-1])
            elif TOTAL_REGEX.search(line): continue
            else:
                print "Unknown file type encountered: %s" % line
        except Exception, e:
            print >>sys.stderr, "Encountered exception: %s" % e

def httpCrawlForFiles(site, rootDir, user=None, password=None):
    """Walk a directory on an http server recursively and return a list
    of file urls found.
    """
    rootUrl = urljoin(site, rootDir)
    if user is None or password is None:
        userCreds = None
        #matchedFiles, fetchedFiles, destinationFiles = filelist([rootUrl], quietMode=True,
        #    xmlMode=False)
    else:
        userCreds = UserCredentials().add(rootUrl, UserCredential(user, password, (1, 0, 0)))
        #matchedFiles, fetchedFiles, destinationFiles = filelist([rootUrl], quietMode=True,
        #    xmlMode=False, needCredentials=True, userCredentials=userCreds)
    gen = walk(rootUrl, userCreds)
    while True:
        try:
            root, dirs, files, infos = gen.next()
            for file in files: yield urlparse.urljoin(root + '/', file)
        except StopIteration: break
