# -----------------------------------------------------------------------------
# Name:        security.py
# Purpose:     Various security related classes and functions.
#
# Author:      Gerald Manipon
#
# Created:     Tue Jan 16 09:49:22 2007
# Copyright:   (c) 2007, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import re

import sciflo.utils


class FetchNotAllowedError(Exception):
    pass


class InstallNotAllowedError(Exception):
    pass


def inIpRange(host, spec):
    """Return True if host is in the ip range specification, False otherwise."""
    # extract host octet values
    match = re.search(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)$', host)
    if not match:
        raise RuntimeError("Format error for host ip: %s" % host)
    hostOcts = list(map(int, match.groups()))

    # loop over spec octets and check that host's corresponding octet is included
    specOcts = spec.split('.')
    if len(specOcts) != 4:
        raise RuntimeError("Must have 4 octets in spec: %s" % spec)
    for i in range(0, 4):
        # match all octets
        if specOcts[i] == '*':
            continue

        # match exact octet value
        if re.search(r'^\d+$', specOcts[i]):
            if hostOcts[i] == int(specOcts[i]):
                continue
            else:
                return False

        # match range
        match = re.search(r'^(\d+)-(\d+)$', specOcts[i])
        if match:
            startOct, endOct = list(map(int, match.groups()))
            if startOct >= endOct:
                raise RuntimeError(
                    "Start octet cannot be >= end octet: %s" % specOcts[i])
            if hostOcts[i] < startOct or hostOcts[i] > endOct:
                return False
            else:
                continue

        # raise
        raise RuntimeError("Unknown format for ip range spec: %s" % spec)
    return True


def fetchFromAllowed(netloc):
    """Return True if fetching bundles/files from netloc is allowed.
    Return False otherwise."""
    scp = sciflo.utils.ScifloConfigParser()
    for iprange in re.split(r'\s+', scp.getParameter('allowCodeFetchFrom')):
        if iprange == '':
            continue
        if inIpRange(sciflo.utils.getHostIp(netloc), iprange):
            return True
    return False


def installFromAllowed(netloc):
    """Return True if installation of bundles/files from netloc is allowed.
    Return False otherwise."""
    scp = sciflo.utils.ScifloConfigParser()
    for iprange in re.split(r'\s+', scp.getParameter('allowCodeInstallFrom')):
        if iprange == '':
            continue
        if inIpRange(sciflo.utils.getHostIp(netloc), iprange):
            return True
    return False
