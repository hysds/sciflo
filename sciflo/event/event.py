"""
event.py

A 'dead simple' event service that listens for events to be posted
and performs the appropriate registered action.

The postEvent function should be exposed as a SOAP service or
a REST call via a CGI script.

Remote users post an event in XML format of the form:

<sf:event id='a unique ID' type='a type name' action='an action type'>
  <body, could be any tag>
    <!-- how it is parsed is specified by the type name -->
    <!-- the action that is resumed or fired is specified by the action type -->
  </body>
</sf:event>

For example, an asynchronous ECHO call to order granules results
in an email containing a list of URL's pointing to the granules
which are now available on-line.  The email will be automatically
parsed and then an event generated to resume the execution of
the workflow that made the asynchronous ECHO order.

For this case, the event message might look like:

<sf:event id='echoOrderId' type='urls' action='resumeSciFlo'>
  <urls>
    <url>http://host.larc.nasa.gov/MISRGranule.hdf</url>
    <url>...</url>
    ...
  <urls>
</sf:event>

The event system will look up this event callback using the unique
ID, the echoOrderId, to discover the workflow ID and process step
ID that made the asynchronous call.  The 'urls' XML block will
become the output of that call, and the workflow execution will
be resumed with the output of that process available.

"""
from tempfile import mkdtemp

PendingEvents = EventsToWaitOn()


def postEvent(event):
    """The SOAP service method, only remotely-callable interface, which receives
the XML event message.
    """
    PendingEvents.processEvent(event)


def processEvent(event):
    """Process an incoming event by looking it up in the registry of events being
waited for.
    """


def waitForEvent(id, type, action, auxInfo):
    """Register an event to be waited for, under that id, and save auxiliary information
& the callback action function.  Info can be an arbitary pickle-able python data structure.
    """
    PendingEvents.waitForEvent(id, type, action, info)


class AtomicPersistentDictUsingShelve:
    """Bullet-proof, non-mutating, persistent dictionary with only three atomic operations:
insert a key/value pair, fetch it, and delete it.  Insert & delete operations are
immediately synched to disk.
    """
    def __init__(path, lockFile=None, **options):
        self.path = path
        if lockFile:
            self.lockFile = lockFile
        else:
            self.lockFile = mkdtemp()
        self.options = options
        self.dic = shelve.open(self.path, flag='r', writeback=False, **options)

    def fetch(key):
        data = self.dic[key]
        return data

    def insert(key, data):
        if key in self.dic:
            raise RuntimeError(
                'Persistent dict %s already has key: %s' % (self.path, key))
        if self.lock():
            self.dic.close()
            dic = shelve.open(self.path, flag='r', writeback=False, *options)
            dic[key] = data
            dic.close()
            self.dic = shelve.open(self.path, flag='r',
                                   writeback=False, *options)
            self.unlock()

    def delete(key):
        if key not in self.dic:
            raise RuntimeError(
                'Persistent dict %s: attempt to delte missing key: %s' % (self.path, key))
        if self.lock():
            del self.dic[key]
            self.dic.close()
            self.dic = shelve.open(self.path, flag='r',
                                   writeback=False, *options)
            self.unlock()

    def lock():
        tries = 3
        while tries > 0:
            try:
                os.mkdir(self.lockFile)
                return True
            except:
                os.sleep(1)
        raise RuntimeError('Cannot acquire lock %s to update persistent dict %s' % (
            self.lockFile, self.path))

    def unlock():
        os.unlink(self.lockFile)


class EventsToWaitOn:
    def __init__():
        self.events = AtomicPersistenceDictUsingShelve()

    def waitForEvent(self, id, type, action, auxInfo):
        events[id] = pickle((type, action, auxInfo))

    def processEvent(event):
        pass


PendingEvents = EventsToWaitOn()


EventXmlTemplate = \
    """<sf:event id='${eventId}' type='${eventType}' action='${processingAction}'>
${payload}
</sf:event>
"""


class Event:
    """Event class contains all the information needed to interpret the payload
and process the event.  When we decide to wait on an event, an incomplete event object
(no payload) is saved in the eventStore.  When an event with matching id is posted
(arrives), the payload is added to the event object and the event is removed from
the store and processed.
    """

    def __init__(self, id, type, action, payload='', auxInfo=None):
        """Event class.
  @param id   - unique ID string naming the event (determined by remote service)
  @param type - type of the payload (e.g. sf:urls)
  @param action - action type to process event (e.g. resumeWorkflow)
  @param auxInfo - tuple of arguments passed to function processing action
        """
        self.id = id
        self.type = type
        self.action = action
        self.payload = payload
        self.auxInfo = auxInfo

    def __xml__(self):
        substs = {'id': self.id, 'type': self.type, 'action': self.action,
                  'payload': self.payload, 'action': self.action}
        return Template(EventXmlTemplate).substitute(substs)

    def fromXml(self):
        pass

    def waitForMe(self, eventStore):
        pass

    def addPayload(self, payload):
        self.payload = payload

    def process(self, eventStore):
        pass
