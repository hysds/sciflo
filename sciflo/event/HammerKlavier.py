"""
HammerKlavier.py -- Hammer a server by using multiple threads or processes to
                    submit many simultaneous requests.

(HammerKlavier means 'hammer keyboard')

"""

from processing import Process
from pdict import PersistentDict


def multiProcessTest(n, funcs):
    """Fork N processes and run a testing function in each."""
    if type(funcs) != list: funcs = [funcs] * n
    procs = []
    for f, args in funcs:
        procs.append( Process(target=f, args=args) )
    for p in procs: p.start()
    for p in procs: p.join()


def testPDict(dictName, keyRoot):
    from random import randint
    from time import clock
    abc = keyRoot + 'abcdefghijklmnopqrstuvwxyz'
    val1 = abc * 23
    val2 = abc * 20
    db = PersistentDict(dictName)
    print 'start len db = ', len(db)

    t0 = clock()
    for i in xrange(10000):
        key = abc+'%4.4d' % i
#        print key
        db[key] = val1
    print 'inserts', clock() - t0

    t0 = clock()
    for i in xrange(10000):
        key = abc+'%4.4d' % i
#        print key
        tmp = db[key]
        db[key] = val2
        tmp = db[key]
    print 'newvalues', clock() - t0

    t0 = clock()
    for i in xrange(10000):
        j = randint(0, 10000)
        key = abc+'%4.4d' % j
        try:
	    tmp = db[key]
#            print key
	    del db[key]
#            db.sync()
        except:
            pass
    print 'deletes', clock() - t0

    print 'end len db = ', len(db)
    db.close()


def main():
    multiProcessTest(4, [(testPDict, ['EventStore', 'p1']), (testPDict, ['EventStore', 'p2']),
                         (testPDict, ['EventStore', 'p3']), (testPDict, ['EventStore', 'p4'])])

if __name__ == '__main__':
    main()
