
import sys, os
from bsddb import dbshelve
from .pdict import PersistentDict

def test(filename, mode='direct'):
    from random import randint
    from time import clock
    abc = 'abcdefghijklmnopqrstuvwxyz'
    val1 = abc * 23
    val2 = abc * 20

    t0 = clock()
    if mode == 'remote':
        db = PersistentDict(filename)
    else:
        db = dbshelve.open(filename, flags='c')
        
    for i in range(10000):
        key = abc+'%4.4d' % i
#        print key
        db[key] = val1
    print(('inserts', clock() - t0))

    t0 = clock()
    for i in range(10000):
        key = abc+'%4.4d' % i
#        print key
        tmp = db[key]
        db[key] = val2
        tmp = db[key]
    print(('newvalues', clock() - t0))

    t0 = clock()
    for i in range(10000):
        j = randint(0, 10000)
        key = abc+'%4.4d' % j
        try:
	    tmp = db[key]
#            print key
	    del db[key]
#            db.sync()
        except:
            pass
    print(('deletes', clock() - t0))

    db.close()


def main():
    from sys import argv
    try:
        mode = argv[1]
        filename = argv[2]
    except:
        mode = 'direct'
        filename = '/tmp/testDbshelve.db'
    test(filename, mode)

if __name__ == '__main__':
    main()


