#!/usr/bin/python

import sys, os
from datetime import datetime
import xml.dom.minidom as minidom
import re

def check(path):
    """ convert one aot file to xml. """

    fin = open(path,'r')

    length = 149
    a = []
    for i in range(length):
        a.append(set())
    for line in fin:
        vars = line.rstrip().split(',')
        for i in range(length):
            a[i].add(vars[i])

    fin.close()

    return a


def main():

    if (len(sys.argv) != 2):
        sys.stderr.write("Usage: " + sys.argv[0] + " file\n")
        sys.exit(1)

    file, = sys.argv[1:]

    a = check(file)
    for x in a:
        print x

    normalized = []
    for x in a:
        normalized.append(x.pop())
    print normalized

if __name__ == "__main__":
    main()
