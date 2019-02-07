#!/bin/env python
#
# xmlIndent.py -- Indent or pretty print an XML docucment efficiently using a SAX stream parser

import types
import urllib.error
import urllib.parse
import urllib.request
import re
import sys
from io import StringIO
from xml.sax.saxutils import XMLGenerator
import xml.sax
USAGE = """
xmlIndent.py [<document URL>]

If no document URL specified, then reads from stdin.
"""


def info(s): sys.stdout.write('xmlIndent' + ": " + str(s) + "\n")


def warn(s): sys.stderr.write('xmlIndent' + ": " + str(s) + "\n")


def die(s, status=1): warn(s); sys.exit(status)


class Indenter(XMLGenerator):
    """Indent or pretty print an XML document."""

    def __init__(self, indent='  ', newline='\n', out=None, encoding="iso-8859-1"):
        self.indent = indent
        self.newline = newline
        self.indents = [newline]  # stack of indents for the tag levels
        # remember type of last element seen (start, end, characters)
        self.last = 'c'
        XMLGenerator.__init__(self, out, encoding)

    def _write(self, text):
        if isinstance(text, str):
            self._out.write(text)
        else:
            self._out.write(text.encode(self._encoding, _error_handling))

    def startElement(self, name, attrs):
        """Override startElement handler so that it inserts (newline and) indent if appropriate
        and then increments the indent level."""
        if self.last != 'c':
            self._write(self.indents[-1])
        XMLGenerator.startElement(self, name, attrs)
        self.last = 's'
        self.indents.append(self.indents[-1] + self.indent)

    def endElement(self, name):
        """Override endElement handler so that it decrements indent level and inserts (newline and) indent if appropriate."""
        self.indents.pop(-1)
        if self.last != 'c':
            self._write(self.indents[-1])
        XMLGenerator.endElement(self, name)
        self.last = 'e'

    def startElementNS(self, name, qname, attrs):
        """Override startElementNS handler so that it inserts (newline and) indent if appropriate
        and then increments the indent level."""
        if self.last != 'c':
            self._write(self.indents[-1])
        XMLGenerator.startElementNS(self, name, qame, attrs)
        self.last = 's'
        self.indents.append(self.indents[-1] + self.indent)

    def endElementNS(self, name, qname):
        """Override endElementNS handler so that it decrements indent level and inserts (newline and) indent if appropriate."""
        self.indents.pop(-1)
        if self.last != 'c':
            self._write(self.indents[-1])
        XMLGenerator.endElementNS(self, name, qname)
        self.last = 'e'

    def characters(self, content):
        """Override characters handler so that it updates indent (no newline) for leaf tags."""
        XMLGenerator.characters(self, content)
        self.last = 'c'


def getInputStream(xml=None):
    stream = xml
    if xml is None:
        stream = sys.stdin
    elif isinstance(xml, bytes):
        if re.match('\s*<', xml):
            xml = xml.replace('\n', '')
            if not re.match('(?is)\s*<\?xml', xml):
                xml = '<?xml version = "1.0"?>\n' + xml
            # print xml
            stream = StringIO(xml)
        else:
            try:
                stream = urllib.request.urlopen(xml)
            except Exception as e:
                warn("xmlIndent.getInputStream: Cannot open document URL: %s" % url)
                die(e)
    return stream


def indent(xmls, indent='  ', newline='\n', header=True):
    """Indent or pretty print an XML document stream using a SAX parser."""
    ins = getInputStream(xmls)
    outs = StringIO()
    try:
        handler = Indenter(indent, newline, out=outs)
        xml.sax.parse(ins, handler)
    except Exception as e:
        warn("Error encountered while parsing XML document.")
        die(e)
    xmlFragment = outs.getvalue()
    if not header:
        match = re.match('(?is)\s*<\?xml.*?\?>\s*(.*)$', xmlFragment)
        if match:
            xmlFragment = match.group(1)
    return xmlFragment


if __name__ == "__main__":
    from sys import argv, stdout
    if len(argv) < 1:
        print(USAGE)
    me = argv[0]
    try:
        url = argv[1]
    except:
        url = None

    print((indent(url)))
