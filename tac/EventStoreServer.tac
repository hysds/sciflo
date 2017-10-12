"""
Start with:
twistd -y EventStoreServer.tac

"""

if True:
    from sciflo.event.pdict import NamedDicts, PersistentDictFactory
    from twisted.application import internet, service

    namedDict = 'EventStore'
    port = NamedDicts[namedDict]['port']
    application = service.Application("EventStoreServer")
    factory = PersistentDictFactory(namedDict)
    pdictService = internet.TCPServer(port, factory)
    pdictService.setServiceParent(service.IServiceCollection(application))
