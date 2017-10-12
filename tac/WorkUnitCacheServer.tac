"""
Start with:
twistd -y WorkUnitCacheServer.tac

"""

if True:
    from sciflo.event.pdict import NamedDicts, PersistentDictFactory
    from twisted.application import internet, service

    namedDict = 'WorkUnitCache'
    port = NamedDicts[namedDict]['port']
    application = service.Application("WorkUnitCacheServer")
    factory = PersistentDictFactory(namedDict)
    pdictService = internet.TCPServer(port, factory)
    pdictService.setServiceParent(service.IServiceCollection(application))
