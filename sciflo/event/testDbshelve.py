
import sys
import os
from bsddb import dbshelve


def test(filename):
    from random import randint
    from time import clock
    abc = 'abcdefghijklmnopqrstuvwxyz'
    val1 = abc * 23
    val2 = abc * 20

    t0 = clock()
    db = dbshelve.open(filename, flags='c')
    for i in range(10000):
        key = abc+'%4.4d' % i
#        print key
        db[key] = val1
    print((clock() - t0))

    t0 = clock()
    for i in range(10000):
        key = abc+'%4.4d' % i
#        print key
        tmp = db[key]
        db[key] = val2
        tmp = db[key]
    print((clock() - t0))

    t0 = clock()
    for i in range(10000):
        j = randint(0, 10000)
        key = abc+'%4.4d' % j
        try:
            tmp = db[key]
            print(key)
            del db[key]
#            db.sync()
        except:
            pass
    print((clock() - t0))

#    db.close()


def main():
    from sys import argv
    try:
        filename = argv[1]
    except:
        filename = '/tmp/testDbshelve'
    test(filename)


if __name__ == '__main__':
    main()
