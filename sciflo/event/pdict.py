"""
pdict.py -- Implement a (remote) persistent dictionary that is accessed over
            a socket.  The backend dictionary could be dbshelve, BSDDB, or
            even a relational table of (key, blob).

*** The purpose is to have a bullet-proof, separate-process, persistent dictionary
    that is very fast, globally shared by many processes, and can't be harmed by
    process segfaults.
***
"""

from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log

import os, sys, socket
from bsddb3 import dbshelve
import cPickle as pickle
try:
    from UserDict import DictMixin
except ImportError:
    class DictMixin: pass

#retrieve work unit cache dir and file from user configuration
from sciflo.utils import ScifloConfigParser, validateDirectory
scp = ScifloConfigParser()
WorkUnitCacheDir = scp.getParameter("cacheHome")
WorkUnitCacheFile = scp.getParameter("cacheDb")
WorkUnitCachePort = int(scp.getParameter("cachePort"))
WorkUnitCache = os.path.join(WorkUnitCacheDir, WorkUnitCacheFile)
WorkUnitCacheLog = os.path.join(sys.prefix, 'log', '%s.log' %
                                os.path.splitext(WorkUnitCacheFile)[0])

DEBUG = False

# Registry of named (shareable) dictionaries
NamedDicts = {'WorkUnitCache':
                {'dbFile': WorkUnitCache, 'port': WorkUnitCachePort,
                 'logFile': WorkUnitCacheLog},
              'EventStore':
                {'dbFile': '/tmp/EventStore/eventStore.db', 'port': 8002,
                 'logFile': 'eventStoreServer.log'},
              'Test':
                {'dbFile': None, 'port': 8009, 'logFile': '/tmp/Test.log'},
             }

# String constants for client/server protocol across wire
NNL = '\r\n'  # network newline
MsgPrefix = '#!#'
OkMsg = MsgPrefix + 'ok'
NoneMsg = MsgPrefix + 'None'
ErrorMsg = MsgPrefix + 'error: '
EndMsg = MsgPrefix + 'end'
EndToken = EndMsg + NNL

_TestDict = {'foo': 'bar', 'bush': 'sucks', 'fool': 'no money'}


class PersistentDictProtocol(LineReceiver):
    """A twisted server to allow access to a persistent dictionary (e.g. bsddb)
from multiple remote clients.  The line-oriented protocol accepts the commands:

 - ping<NNL>           : see if the server is up on a given port)
 - get<NNL>key<NNL>    : get the string value of a string key)
 - delete<NNL>key<NNL> : delete a key/value pair from the dictionary
 - insert<NNL>key<NNL>val<EndMsg><NNL> : insert a multi-line string value under that key)
 - length<NNL>         : return number of keys in dict (**CURRENTLY BROKEN, returns zero**)

Notes:
 - Keys cannot contain network newlines, NNL = '\r\n'.
 - Values can be multi-line strings (python pickles or XML).
 - Newlines are used to separate parts of the commands so that the cmd can be
   parsed using LineReceiver
    """

    def __init__(self, state='start'):
        self.state = state  # state of FSM = 'start', 'get', 'delete', 'insert', or 'getval'
        self.key = None     # key to insert value under
        self.val = None     # value to insert

    def connectionMade(self):
        if DEBUG: print 'PersistentDict: connection made.'

    def lineReceived(self, line):
        """Simple finite state machine to process the four possible commands.
        """
        dic = self.factory.dict  # get dictionary opened in factory init()
        if DEBUG: print '**', line, '**'
        if self.state == 'start':
            if line == 'ping':
                print 'ping'
                self.sendline(OkMsg)
            elif line == 'length':
                print 'length'
                self.sendline('1')
#                self.sendline( str(len(dic)) )
            elif line in ('get', 'delete', 'insert'):
                if DEBUG: print 'Change state to', line
                self.state = line
        elif self.state == 'get':
            print 'get', line
            val = dic.get(line, NoneMsg)
            self.sendline(val + EndMsg)
            self.state = 'start'
        elif self.state == 'delete':
            print 'delete', line
            if line in dic: del dic[line]
            self.sendline(OkMsg)
            self.state = 'start'
        elif self.state == 'insert':
            print 'insert', line
            self.key = line
            self.val = ''
            self.state = 'getval'
        elif self.state == 'getval':
            if DEBUG: print 'Adding to val:', line
            self.val += line
            if line.endswith(EndMsg):
                val = self.val[:-len(EndMsg)]
                dic[self.key] = val
                if DEBUG: print 'Inserted:'
                if DEBUG: print val
                self.sendline(OkMsg)
                self.state = 'start'

    def sendline(self, line):
        self.transport.write(line + NNL)


class PersistentDictFactoryException(RuntimeError): pass

class PersistentDictFactory(ServerFactory):
    protocol = PersistentDictProtocol

    def __init__(self, dictName, dictRegistry=NamedDicts):
        """Set up for the protocol by opening the named persistent dictionary.
        """
        self.dictName = dictName
        try:
	    self.dbFile   = dictRegistry[dictName]['dbFile']
	    self.port     = dictRegistry[dictName]['port']
            if self.dbFile:
                dbHome = os.path.split(self.dbFile)[0]
                if not os.path.exists(dbHome): os.makedirs(dbHome, 0777)
                self.dbHome = dbHome
                logFile  = dictRegistry[dictName]['logFile']
                if not logFile.startswith('/'): logFile = os.path.join(dbHome, logFile)
                self.logFile = logFile
        except:
            raise PersistentDictFactoryException('Error, no dict of that name: %s' % dictName)
        validateDirectory(os.path.dirname(self.logFile))
        log.startLogging(open(self.logFile, 'w'))
        if dictName == 'Test':
            self.dict = _TestDict
        else:
            self.dict = dbshelve.open(self.dbFile)
            os.chmod(self.dbFile, 0666)


class PersistentDictClientException(RuntimeError): pass

class PersistentDictClient:
    """A simple client to call a persistent dictionary (e.g. bsddb) across a socket.
The client only has four useful methods:  ping, get, delete, insert.
    """
    def __init__(self, dictName, dictRegistry=NamedDicts, pickleVals=False, timeout=3.0, bufsize=4096):
        self.dictName = dictName
        self.pickleVals = pickleVals
        self.timeout = timeout
        self.bufsize = bufsize
        try:
	    self.port = dictRegistry[dictName]['port']
        except:
            raise PersistentDictClientException('Error, no dict of that name: %s' % dictName)
        self.soc = self._openLocalSocket(self.port)
        if not self.ping():
            raise PersistentDictClientException('Error, server for %s on port %s does not return ping' % (dictName, self.port))

    def close(self):
        self.soc.close()
        if DEBUG: print 'PersistentDictClient: Closed socket connection to dictName, port: %s, %d' % (self.dictName, self.port)

    def ping(self):
        """Ping server to ensure it's alive."""
        try:
            return self._sendCmd('ping')
        except:
            return False

    def get(self, key, default=None):
        """Get value of a string key, or default value if missing."""
        soc = self.soc
        cmd = 'get' + NNL + key + NNL
        try:
            soc.sendall(cmd)
        except socket.error, msg:
            soc.close()
            raise PersistentDictClientException('Error, cannot send to socket: %s' % cmd)
        data = ''
        firstTry = True
        while not data.endswith(EndToken):
            try:
                data += soc.recv(self.bufsize)
                if DEBUG: print 'Got data:', data
            except socket.error, msg:
                soc.close()
                raise PersistentDictClientException('Error, no data received from socket, sent: %s' % cmd)
            if data.startswith(NoneMsg) or (firstTry and len(data) == 0): return default
            firstTry = False
        data = data[:-len(EndToken)]
        if self.pickleVals:
            return pickle.loads(data)
        else:
            return data

    def delete(self, key):
        """Delete a key and its value from persistent dict."""
        cmd = 'delete' + NNL + key + NNL
        try:
            return self._sendCmd(cmd)
        except:
            return False
        
    def insert(self, key, val):
        """Insert or change the value of a key."""
        if self.pickleVals: val = pickle.dumps(val)
        cmd = 'insert' + NNL + key + NNL + val + EndToken
        try:
            return self._sendCmd(cmd)
        except:
            return False

    def length(self):
        """Return number of keys in dict."""
        try:
            return int(self._sendCmd('length'))
        except:
            return 0

    def _openLocalSocket(self, port):
        """Open a port on localhost and send a ping command to ensure server is alive."""
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.connect(('127.0.0.1', port))
            soc.settimeout(self.timeout)
        except socket.error, e:
            soc.close()
            print 'PersistentDictClient: Error, cannot connect socket to local port: %s' % port
            raise e
        return soc

    def _sendCmd(self, cmd):
        """Send a command and check for returned 'ok' message."""
        soc = self.soc
        if cmd[-2:] != NNL: cmd += NNL
        try:
            soc.sendall(cmd)
        except socket.error, msg:
            soc.close()
            raise RuntimeError('PersistentDictClient: Error, cannot send to socket: %s' % cmd)
        try:
            data = soc.recv(self.bufsize)
        except socket.error, e:
            soc.close()
            print 'PersistentDictClient: Error, no data received from socket, sent: %s' % cmd
            raise e
        data = data[-len(NNL):]
        if data == OkMsg: data = True
        return data
        

class PersistentDictException(RuntimeError): pass

class PersistentDict(DictMixin):
    """Presents the usual dict interface, accessing a *named*, shared, persistent dictionary,
and hides the (socket) client and (twisted) server classes from view.
    """
    def __init__(self, dictName, pickleVals=False):
        self.dictName = dictName; self.db = None
        self.db = PersistentDictClient(dictName, pickleVals=pickleVals)

    def __del__(self):
        if self.db: self.db.close()

    def __getattr__(self, name):
        """Many methods we can just pass through to the DB object."""
        return getattr(self.db, name)

    # dictionary access methods
    def __len__(self):
        return self.db.length()

    def __getitem__(self, key):
        return self.db.get(key)

    def __setitem__(self, key, val):
        self.db.insert(key, val)

    def __delitem__(self, key):
        self.db.delete(key)

    def keys(self, txn=None):
        raise PersistentDictException('Error, class does not implement keys() method.')

    def items(self, txn=None):
        raise PersistentDictException('Error, class does not implement items() method.')

    def values(self, txn=None):
        raise PersistentDictException('Error, class does not implement values() method.')


def startPersistentDictServer():
    """This code belongs in a twisted tac file (at toplevel)."""
    from pdict import NamedDicts, PersistentDictFactory
    from twisted.application import internet, service

    namedDict = "EventStore"    
    port = NamedDicts[namedDict]['port']
    application = service.Application("pdict")
    factory = PersistentDictFactory(namedDict)
    pdictService = internet.TCPServer(port, factory)
    pdictService.setServiceParent(service.IServiceCollection(application))


def testClientSimple():
    dic = PersistentDict("Test")
    print dic['foo']
    del dic['foo']
    dic['you'] = 'tube'
    print dic['you']
    del dic

def testClient():
    dic = PersistentDict("EventStore")
    print len(dic)
    print dic['foo']
    dic['foo'] = 'bar'
    dic['bush'] = 'sucks'
    dic['fool'] = 'no money'
    print dic['foo']
    del dic['foo']
    dic['you'] = 'tube'
    print dic['you']
    print len(dic)


def main():
    testClient()

if __name__ == '__main__':
    main()
