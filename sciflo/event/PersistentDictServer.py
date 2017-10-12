
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.application import internet, service


class PersistentDictProtocol(LineReceiver):
    """A twisted server to allow access to a persistent dictionary (e.g. bsddb)
from multiple remote clients.  The protocol accepts a four commands:

 - ping\n (see if the server is up on a given port)
 - get\nkey\n (get the string value of a string key)
 - delete\nkey\n (delete a key/value pair from the dictionary
 - insert\nkey\nval\n\n (insert a multi-line string value under that key)

    """
    OkMsg = '#!ok'
    NoneMsg = '#!None'
    ErrorMsg = '#!error: '

    Pdict = {'foo': 'bar', 'bush': 'sucks', 'fool': 'no money'}

    def __init__(self, state='start'):
        self.state = state  # 'start', 'get', 'delete', 'insert', or 'getval'
        self.key = None     # key to insert value under
        self.val = None     # value to insert

    def lineReceived(self, line):
        """Simple state machine to process the four possible commands."""
        if self.state == 'start':
            if line == 'ping':
                self.sendline(OkMsg)
            elif line in ('get', 'delete', 'insert'):
                self.state = line
        elif self.state == 'get':
            val = Pdict.get(line, NoneMsg)
            self.sendline(val)
        elif self.state == 'delete':
            if line in Pdict: del Pdict[line]
            self.sendline(OkMsg)
        elif self.state == 'insert':
            self.key = line
            self.val = ''
            self.state = 'getval'
        elif self.state == 'getval':
            if line != '':
                self.val += line
            else:
                Pdict[self.key] = self.val
                self.state = 'start'
                self.sendline(OkMsg)


class PersistentDictFactory(Factory):
    protocol = PersistentDictProtocol


#def tac():
if True:
    application = service.Application("pdict")
    pdictService = internet.TCPServer(8007, PersistentDictFactory())
    pdictService.setServiceParent(application)


#if __name__ == '__main__':
#    tac()




