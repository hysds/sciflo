#-----------------------------------------------------------------------------
# Name:        localize.py
# Purpose:     The localize module acts as a 'chokepoint' for the movement
#              of data within the SciFlo dataflow network.  Files are
#              automatically retrieved via ftp, http, or DAP URLs and cached on
#              nodes at pre-determined locations.  Thus, 'replicas' of known
#              (recognized) datasets can be cached in the network and discovered
#              by crawlers on multiple nodes.  A recognizable data granule (file),
#              if it is replicated on a node, will always be located in a
#              pre-determined directory structure.  File names are 'recognized'
#              using regular expressions.
#
#              The toplevel interface is the 'localizeUrls' function.  It takes
#              a list of URLs (or a list of list of URLs) and localizes each object.
#              If there are multiple available URLs for that object, then any
#              of them might be used to 'fetch' the file; the choice of which
#              one to use is dictated by policy, performance, and server failures.
#            
#              If the file is already local, it is not fetched.  However, if it
#              is recognized it may be 'moved' to the pre-determined directory.
#              Thus, calling localize is one way to 'recognize' a file and get
#              its local pre-determined path.  The cache directories might be
#              served by ftp, http, and DAP servers, so a particular path is
#              remotely accessible via multiple URL protocols.
#            
#              The output of localizeUrls is a list of URLs, or a list of list
#              of URLs, where each object is pointed to via multiple protocols.
#              The URLs have been 're-written' to point to the fetched replicas
#              of the objects.  By sorting the multiple protocols in a specific
#              order, the system can prefer one protocol over another.  The
#              usual protocol order is: file:, dap:, ftp:, http:.
#
# Author:      Brian Wilson
#              Gerald Manipon
#
# Created:     Mon Aug 06 09:19:36 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, sys, types, urllib, urlparse, socket, re, ftplib, shutil, time
import paramiko, urllib2, requests
from lxml.etree import XML
from twisted.python import lockfile
from tempfile import gettempdir
from netrc import netrc

from sciflo.data import Recognizer
from sciflo.utils import validateDirectory, getUserInfo
from sciflo.data.locationInfoSet import mkInfoset


requests.packages.urllib3.disable_warnings()

FTP_CACHE = {}
SFTP_CACHE = {}

NO_SUCH_FILE_RE = re.compile(r'No such file or directory:')

### Not fully implemented yet.

def hostName():
###    return socket.gethostbyaddr(socket.gethostname())[1][0]
    return socket.getfqdn()

LocalHost = hostName()
DapServerHints = ['/dap/', '/nph-dods/']


def localizeUrls(urls, dir='.', want='path', datasetInfo=None, SCIFLO_ROOT=None):
    """Fetch a list of URLS by calling the localize function.
The list can be in any of several formats:
 - an XML list (as a string),
 - a python list (as a string),
 - a text list with one URL per line,
 - an actual python list of strings
    """
    if isinstance(urls, types.StringType):
        if urls.startswith('<'):     # xml list
            urlList = [item.text for item in XML(urls)]
        elif urls.startswith('['):   # py list as string
            urlList = eval(urls)
        else:                        # assume string is one URL per line
            urlList = [line.strip() for line in urls.split('\n')]
    elif isinstance(urls, types.ListType):
        urlList = urls
    else:
        raise 'fetchFiles: Error, input URL list must be a string or python list.'
    return [localizeUrl(url, dir, want, datasetInfo, SCIFLO_ROOT) for url in urlList]

def atomicRename(src, dest, xfrDir):
    """Atomic rename of file."""
    
    os.rename(src, dest)
    att = 1
    while True:
        try:
            shutil.rmtree(xfrDir)
            break
        except:
            if att >= 3: raise
        time.sleep(5)
        att += 1
    return True

def localizeUrl(url, dir='.', want='path', datasetInfo=None, SCIFLO_ROOT=None, debug=True,
                use_urllib2=False):
    """First version.  To be replaced by better localizeUrl() function that recognizes data products.
Returns local path, or DAP URL left alone, or retrieves ftp/http URL and returns path to local copy.
    """
    if url is None or url.lower().find('none') > 0:
        print 'localizeUrl: None URL encountered, skipping.'
        return url
    path = isLocalUrl(url)
    dap = isDapUrl(url)
    if path:
        response = (path, None)
    elif dap:
        response = (dap, None)
    else:
        #try to recognize
        recognizer = Recognizer(datasetInfo, SCIFLO_ROOT)
        localFile = recognizer.getPublishPath(url)
        if localFile is not None:
            localFile = isLocalUrl(localFile)
        
        #if not recognized, generate path
        scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
        if localFile is None:
            fileName = os.path.split(path)[1]
            localFile = os.path.join(dir, os.path.split(path)[1])

        #acquire lock; sleep if another process has locked this download
        lockFile = os.path.join(gettempdir(), ".%s.lock" % os.path.basename(localFile))
        lock = lockfile.FilesystemLock(lockFile)
        while True:
            gotLock = False
            try: gotLock = lock.lock()
            except Exception, e:
                print >>sys.stderr, 'localizeUrl: Error getting lock for %s: %s' % (url, str(e))
            if gotLock: break
            time.sleep(5)

        try:
            #if doesn't exist, retrieve it
            if not os.path.exists(localFile):
            
                #get local temp file
                localDir = os.path.dirname(localFile)
                dlDir = os.path.join(localDir, ".xfr_%s" % os.path.basename(localFile))
                localTempFile = os.path.join(dlDir, os.path.basename(localFile))

                #create dirs if needed
                validateDirectory(localDir, mode=02775, noExceptionRaise=True)

                #create dirs if needed
                validateDirectory(dlDir, mode=02775, noExceptionRaise=True)
            
                if debug: print >>sys.stderr, 'localizeUrl: Fetching %s to %s' % (url, localFile)

                if scheme == 'ftp':
                    if FTP_CACHE.has_key(netloc): ftp = FTP_CACHE[netloc]
                    else:
                        ftp = ftplib.FTP()
                        ftp.connect(netloc)
                        n = netrc()
                        auths = n.authenticators(netloc)
                        if auths is not None: ftp.login(auths[0], auths[2])
                        else: ftp.login()
                        FTP_CACHE[netloc] = ftp
                    try: ftp.retrbinary('RETR %s' % path, open(localTempFile, 'wb').write)
                    except Exception, e:
                        if re.search(r'421 Disconnecting', str(e)):
                            ftp = ftplib.FTP()
                            ftp.connect(netloc)
                            n = netrc()
                            auths = n.authenticators(netloc)
                            if auths is not None: ftp.login(auths[0], auths[2])
                            else: ftp.login()
                            FTP_CACHE[netloc] = ftp
                            ftp.retrbinary('RETR %s' % path, open(localTempFile, 'wb').write)
                        else: raise
                    atomicRename(localTempFile, localFile, dlDir)
                    response = (localFile, None)
                elif scheme == 'file':
                    if SFTP_CACHE.has_key(netloc): sftp, transport = SFTP_CACHE[netloc]
                    else:
                        userInfo = getUserInfo()
                        transport = paramiko.Transport((netloc, 22))
                        pkeyFile = os.path.join(userInfo[1], '.ssh', 'id_rsa')
                        if not os.path.exists(pkeyFile):
                            raise RuntimeError("Cannot retrieve %s via sftp.  Please generate a private key file with: ssh-keygen -t rsa" % url)
                        pkey = paramiko.RSAKey.from_private_key_file(pkeyFile)
                        transport.connect(username=userInfo[0], pkey=pkey)
                        sftp = paramiko.SFTPClient.from_transport(transport)
                        SFTP_CACHE[netloc] = (sftp, transport)
                    try: sftp.get(path, localTempFile)
                    except Exception, e:
                        userInfo = getUserInfo()
                        transport = paramiko.Transport((netloc, 22))
                        pkeyFile = os.path.join(userInfo[1], '.ssh', 'id_rsa')
                        if not os.path.exists(pkeyFile):
                            raise RuntimeError("Cannot retrieve %s via sftp.  Please generate a private key file with: ssh-keygen -t rsa" % url)
                        pkey = paramiko.RSAKey.from_private_key_file(pkeyFile)
                        transport.connect(username=userInfo[0], pkey=pkey)
                        sftp = paramiko.SFTPClient.from_transport(transport)
                        SFTP_CACHE[netloc] = (sftp, transport)
                        sftp.get(path, localTempFile)
                    #finally:
                    #    sftp.close()
                    #    transport.close()
                    atomicRename(localTempFile, localFile, dlDir)
                    response = (localFile, None)
                else:
                    if use_urllib2:
                        try:
                            localFh = open(localTempFile, 'wb')
                            urlFh = urllib2.urlopen(url)
                            localFh.write(urlFh.read())
                            response = urlFh.info()
                        except Exception, e:
                            print >>sys.stderr, 'localizeUrl: failed to urlretrieve %s to %s: %s' % (url, localTempFile, str(e))
                            raise
                        finally:
                            #close file handles
                            try: localFh.close()
                            except: pass
                            try: urlFh.close()
                            except: pass
                    else:
                        response = requests.request('GET', url, verify=False, stream=True)
                        if response.status_code != 200:
                            print "Got status code %d trying to read %s" % (response.status_code, url)
                            print "Content:\n%s" % response.text
                            print >>sys.stderr, 'localizeUrl: failed to urlretrieve(requests) %s to %s: %s' % (url, localTempFile, response.text)
                        response.raise_for_status()
                        with open(localTempFile, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=1024):
                                if chunk: # filter out keep-alive new chunks
                                    f.write(chunk)
                                    f.flush()
                    atomicRename(localTempFile, localFile, dlDir)
                    response = (localFile, response)
            else:
                if debug: print >>sys.stderr, 'localizeUrl: %s already cached at %s' % (url, localFile)
                response = (localFile, None)
        finally: lock.unlock()
    if want == 'path':
        return response[0]
    else:
        return response

def bestUrlSet(infoset, dapOkay=True, bestHost=None, matchRegex=None, localPathOkay=True):
    """For each object in the geolocation infoset, choose the best URL."""
    geoInfos = mkInfoset(infoset)
#    print >>sys.stderr, geoInfos
    nUrlsIn = len(geoInfos)
    urls = [bestUrl(geoInfo.objectId, geoInfo.urls, dapOkay=dapOkay, bestHost=bestHost,
                    matchRegex=matchRegex, localPathOkay=localPathOkay) for geoInfo in geoInfos]
    nMissingUrlsOut = len([url for url in urls if url is None])
    if nMissingUrlsOut > 0:
        print >>sys.stderr, 'bestUrlSet: Warning, no good URL found for', \
              '%d out of %d total objects' % (nMissingUrlsOut, nUrlsIn)
    return urls

def bestUrlSetNoLocal(infoset, dapOkay=True, bestHost=None, matchRegex=None):
    return bestUrlSet(infoset, dapOkay, bestHost, matchRegex, localPathOkay=False)


def bestUrl(objectId, urls, dapOkay=True, bestHost=None, matchRegex=None, localPathOkay=True):
    return closestUrl(objectId, bestUrls(objectId, urls, dapOkay=dapOkay,
                      matchRegex=matchRegex, localPathOkay=localPathOkay), bestHost=bestHost)

def bestUrls(objectId, urls, dapOkay=True, bestHost=None, matchRegex=None, localPathOkay=True):
    """Choose the 'best' URL from a list of candidates.  Local URLs are preferred to remote
URLs, with DAP having priority over ftp/http.  If there are several candidates in a category,
the 'closest' (network distance) URL is chosen.
    """
#    print 'bestUrls: candidate Urls:', urls
    if matchRegex:
        matcher = re.compile(matchRegex)
        filteredUrls = [url for url in urls if matcher.search(url)]
        if len(filteredUrls) == 0:
            url = bestUrl(objectId, urls, dapOkay=dapOkay, bestHost=bestHost, matchRegex=None)
            print >>sys.stderr, 'bestUrls: Warning, matchRegex filtered out all URLs', \
                'for objectId %s, otherwise bestUrl is %s' % (objectId, url)
        urls = filteredUrls

    goodUrls, rest = filterLocalUrls(urls)
    goodUrls = filter(os.path.exists, goodUrls)  # throw away local paths that don't exist
#    print 'bestUrls: localUrls:', goodUrls
    if len(goodUrls) and localPathOkay > 0:
        return goodUrls
    goodUrls, rest = filterDapUrls(rest)
#    print 'bestUrls: dapUrls:', goodUrls
    if dapOkay:
        if len(goodUrls) > 0:
            return goodUrls
#    print 'bestUrls: rest of Urls:', rest
    return [url for url in rest if url is not None and url != 'None']


def isLocalUrl(url, localHost=LocalHost):
    """If URL is file: URL on this host, or a local path, return the simple path, else return None."""
    if url.startswith('/'):
        path = url
    elif url.startswith('file://'+localHost) or url.startswith('file:///'):
        url = url[7:]
        path =  url[url.index('/'):]
    elif os.path.exists(url):
        path = os.path.abspath(url)
    else:
        path = None
    return path
    
def filterLocalUrls(urls, localHost=LocalHost):
    """Separate list of URLs into two lists: the local paths, and the rest."""
    return filterSplitList(urls, predicate=lambda s: isLocalUrl(s, localHost=localHost))

def localUrls(urls):
    """Return local URLs in the list."""
    return filterLocalUrls(urls)[0]

def localUrl(urls, i=0):
    """Return the first local URL, by default, or the ith."""
    return localUrls(urls)[i]

def isDapUrl(url, dapServerHints=DapServerHints):
    urll = url.lower()
    if urll.startswith('dap:'):
        url = url[4:]
    elif urll.startswith('http:') and anyInString(dapServerHints, urll):
        pass
    else:
        url = None
    return url
    
def filterDapUrls(urls, dapServerHints=DapServerHints):
    """Separate list of URLs into two lists: the local paths, and the rest."""
    return filterSplitList(urls, predicate=lambda s: isDapUrl(s, dapServerHints=dapServerHints))
    
def dapUrls(urls):
    return filterDapUrls(urls)[0]

def dapUrl(urls, bestHost=None):
    return dapUrls(urls)[0]

def closestUrl(objectId, urls, bestHost=None):
    """Placeholder for counting network hops."""
    if len(urls) > 0:
        # for now, return last of sorted URLs, which should be latest version of unique data object
        urls.sort(key=url2fileName)
        return urls[-1]
    else:
        print >>sys.stderr, 'bestUrl: Warning, No good URL found for objectId %s, returning None' % objectId
        return None

def url2fileName(url):
    """Extract file name from URL."""
    path = urlparse.urlparse(url)[2]
    return os.path.split(path)[1]
    
def filterSplitList(lis, predicate):
    """Separate a list of items into two lists based on a predicate.
The predicate should return a possibly modified item to indicate success or None.
    """
    list1 = []; list2 = []
    for item in lis:
        item2 = predicate(item)
        if item2 is not None:
            list1.append(item2)
        else:
            list2.append(item)
    return list1, list2

def anyInString(keys, s):
    for key in keys:
        if s.find(key) >= 0:
            return True
    return False


def main():
    try:
        urlsFile = sys.argv[1]
        urls = open(urlsFile, 'r').read().strip()
    except:
        urls = sys.stdin.read().strip()
    return localizeUrls(urls)


if __name__ == '__main__':
    localFiles = main()
    for f in localFiles: print f
