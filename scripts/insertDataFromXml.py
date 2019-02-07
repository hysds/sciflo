#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Name:        updateDbFromXml.py
# Purpose:     Update database using data in xml.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jun 22 09:08:08 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import os
import sys
import getopt
import re
import lxml.etree as etree

import sciflo


def usage():
    """Print usage info."""
    print(("""%s [-l|--location <location>] [-t|--table <table>] [-u|--update] \
[-r|--recordTag <tag>] [-k|--keyTags <tag1,tag2,tag3,...>] [-d|--debug] \
[-h|--help] <xml doc>""" % sys.argv[0]))


def main():

    # get opts
    try:
        opts, args = getopt.getopt(sys.argv[1:], "l:t:r:k:hdu", ["location=", "table=",
                                                                 "recordTag=", "keyTags=", "update", "debug", "help"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    # set defaults
    location = None
    table = None
    recordTag = None
    keyTags = []
    update = False
    debug = False

    # process opts
    for o, a in opts:

        # check if help
        if o in ("-h", "--help"):
            usage()
            sys.exit()

        # check if debug
        if o in ("-d", "--debug"):
            debug = True

        # check if update
        if o in ("-u", "--update"):
            update = True

        # set location
        if o in ("-l", "--location"):
            if location:
                print("""Multiple -l|--location specifications found.\
  Only specify one location.""")
                usage()
                sys.exit(2)
            else:
                location = a

        # set table
        if o in ("-t", "--table"):
            if table:
                print("""Multiple -t|--table specifications found.\
  Only specify one table.""")
                usage()
                sys.exit(2)
            else:
                table = a

        # set recordTag
        if o in ("-r", "--recordTag"):
            if recordTag:
                print("""Multiple -r|--recordTag specifications found.\
  Only specify one recordTag.""")
                usage()
                sys.exit(2)
            else:
                recordTag = a

        # set keyTag
        if o in ("-k", "--keyTags"):
            if keyTags:
                print("""Multiple -k|--keyTags specifications found.\
  Only specify one keyTag.""")
                usage()
                sys.exit(2)
            else:
                keyTags = [i.strip() for i in a.strip().split(',')]

    # make arg was specified
    if len(args) != 1:
        print("Please specify one xml document.")
        usage()
        sys.exit(2)

    # make sure table and location defined
    if table is None or location is None:
        print("Please specify both location and table.")
        usage()
        sys.exit(2)

    # xml doc
    doc = args[0]
    f = open(doc, 'r')
    xml = f.read()
    f.close()

    # insert
    kargs = {'autoKey': False, 'createIfNeeded': True,
             'iterateMode': False, 'forceDelete': False}
    if recordTag:
        kargs['recordTag'] = recordTag
    if keyTags:
        kargs['keyTags'] = keyTags
    if update:
        kargs['updateOnDup'] = True
    etree.clearErrorLog()
    try:
        ret = sciflo.db.insertXml(location, table, xml, **kargs)
    except etree.XMLSyntaxError as e:
        print("Got XMLSyntaxError:")
        print((e.error_log.filter_levels(etree.ErrorLevels.FATAL)))
        print("Please check xml.")
    except sciflo.db.NoIndexedFieldsInXmlError as e:
        print(
            "Couldn't find indexed/keyed fields.  Specify them with -k|--keyTags  option.")
        usage()
        sys.exit(2)
    except Exception as e:
        if re.search(r'duplicate entry', str(e), re.IGNORECASE):
            print(e)
            print("Specify -u|--update option to force update.")
            usage()
            sys.exit(2)
        else:
            raise


if __name__ == '__main__':
    main()
