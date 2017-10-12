
if True:
    from sciflo.event.pdict import NamedDicts, PersistentDictFactory
    from twisted.application import internet, service

    namedDict = "WorkUnitCache"    
    filename = NamedDicts[namedDict]["dbFile"]
    port = NamedDicts[namedDict]["port"]
    application = service.Application("pdict")
    factory = PersistentDictFactory(namedDict)
    pdictService = internet.TCPServer(port, factory)
    pdictService.setServiceParent(service.IServiceCollection(application))
