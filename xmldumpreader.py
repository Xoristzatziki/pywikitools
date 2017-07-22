#!/usr/bin/python3

"""
Each XmlEntry object represents a page, as read from an XML source

The MediaWikiXmlHandler can be used for the XML given by Special:Export
as well as for XML dumps.

The XmlDump class reads a (bz2) pages_current XML dump (like the ones offered on
http://dumps.wikimedia.org/) or an XML uncompressed file
(ex. using api: index.php?title=Special:Export)
and offers a generator over
XmlEntry objects which can be used by other bots.

For fastest processing, XmlDump uses the cElementTree library.
"""
#Based on:
# (C) Pywikipedia bot team, 2005-2010
#
# Distributed under the terms of the MIT license.
#
#__version__='$Id: xmlreader.py 9042 2011-03-13 10:14:47Z xqt $'
#
#Changes:
#1. uses only xml.etree.ElementTree (not cElementTree)
#2. opens only bz2 and plain xml
#3. can read file-like objects already opened
#    (for use with downloaded pages as strings)

import os,io
import bz2

from xml.etree.ElementTree import iterparse

def ourUnescape(s):

    if '&' not in s:
        return s
    s = s.replace('&lt;', "<")
    s = s.replace('&gt;', ">")
    s = s.replace('&apos;', "'")
    s = s.replace('&quot;', '"')
    s = s.replace('&amp;', "&") # Must be last
    return s

class XmlEntry:
    """
    Represents a page.
    """
    def __init__(self, title, pageid, ns, text, username, ipedit, timestamp,
                 revisionid, comment, redirect):
        # there are more tags that someone could read.
        self.title = title
        self.pageid = pageid
        self.ns = ns
        self.text = text
        self.username = username.strip()
        self.ipedit = ipedit
        self.timestamp = timestamp
        self.revisionid = revisionid
        self.comment = comment
        self.isredirect = redirect
        self.content = self.text

class XmlHeaderEntry:
    """
    Represents a header entry
    """
    def __init__(self):
        self.sitename = ''
        self.base = ''
        self.generator = ''
        self.case = ''
        self.namespaces = {}

class XmlDump(object):
    """
    Represents an XML dump file. Reads the local file at initialization,
    parses it, and offers access to the resulting XmlEntries via a generator.

    Can be used as context manager.
    Return only the latest revision.
    

    @param filenameorstring: string
        If a file exists with that name:
        Either is a bz2 that endswith .bz2
        Or is an xml file that endswith .xml

        If none of the above is true then is traited as a string contaning xml.
    """
    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        '''Close the opened file descriptor if any.

        '''
        if self.fd:
            self.fd.close()
        return True

    def __init__(self, filenameorstring):
        self.filename = None
        self.astring = None
        self.fd = None
        
        try:
            if os.path.exists(filenameorstring):
                self.filename = filenameorstring
        finally:#if errors found assume that it is a string.
            if self.filename == None:
                self.astring = filenameorstring

    def parse(self):
        """Return a generator that will yield XmlEntry objects"""
        if self.filename:
            if self.filename.endswith('.bz2'):
                source = bz2.open(self.filename)
            else:
                source = open(self.filename)
            self.fd = source
        else:
            source = io.StringIO(self.astring)
        context = iterparse(source, events=("start", "end", "start-ns"))
        self.root = None
        xcounter = 0

        for event, elem in context:
            if event == "start-ns" and elem[0] == "":
                self.uri = elem[1]
                continue
            if event == "start" and self.root is None:
                self.root = elem
                continue
            for rev in self._parse_only_latest(event, elem):
                yield rev
        if self.fd:
            self.fd.close()

    def _headers(self, elem):
        self.title = elem.findtext("{%s}title" % self.uri)
        self.pageid = elem.findtext("{%s}id" % self.uri)
        self.ns = elem.findtext("{%s}ns" % self.uri)
        self.isredirect = elem.findtext("{%s}redirect" % self.uri) is not None


    def _parse_only_latest(self, event, elem):
        """Parser that yields only the latest revision"""
        if event == "end" and elem.tag == "{%s}page" % self.uri:
            #print('in _parse_only_latest')
            self._headers(elem)
            revision = elem.find("{%s}revision" % self.uri)
            revisionid = revision.findtext("{%s}id" % self.uri)
            timestamp = revision.findtext("{%s}timestamp" % self.uri)
            comment = revision.findtext("{%s}comment" % self.uri)
            contributor = revision.find("{%s}contributor" % self.uri)
            ipeditor = contributor.findtext("{%s}ip" % self.uri)
            username = ipeditor or contributor.findtext("{%s}username" % self.uri)
            # could get comment, minor as well
            text = revision.findtext("{%s}text" % self.uri)
            text = ourUnescape(text)
            theentry = XmlEntry(title=self.title,
                            pageid=self.pageid,
                            text=text or '',
                            username=username or '', #username might be deleted
                            ipedit=bool(ipeditor),
                            ns=self.ns,
                            timestamp=timestamp,
                            revisionid=revisionid,
                            comment=comment,
                            redirect=self.isredirect
                           )
            yield theentry
            elem.clear()
            self.root.clear()

    def getSiteInfo(self):
        '''Return SiteInfo.'''
        if self.fd:
            self.fd.close()
        if self.filename:
            if self.filename.endswith('.bz2'):
                source = bz2.open(self.filename)
            else:
                source = open(self.filename)
            self.fd = source
        else:
            source = io.StringIO(self.astring)
        context = iterparse(source, events=("start", "end", "start-ns"))
        self.root = None

        siteinfo = XmlHeaderEntry()
        for event, elem in context:
            if event == "start-ns" and elem[0] == "":
                self.uri = elem[1]
                continue
            if event == "start" and self.root is None:
                self.root = elem
                continue
            if event == "end" and elem.tag == "{%s}siteinfo" % self.uri:
                siteinfo.sitename = elem.findtext("{%s}sitename" % self.uri)
                siteinfo.base = elem.findtext("{%s}base" % self.uri)
                siteinfo.generator = elem.findtext("{%s}generator" % self.uri)
                siteinfo.case = elem.findtext("{%s}case" % self.uri)
                siteinfo.namespaces = {}
                b = elem.find("{%s}namespaces" % self.uri)
                for c in list(b):
                    for d in c.itertext():
                        siteinfo.namespaces[c.get('key')] = d
                elem.clear()
                self.root.clear()
                if '0' not in siteinfo.namespaces:#optional
                    siteinfo.namespaces['0'] = 'main'
                if self.fd:
                    self.fd.close()
                return siteinfo
        return None

    def getMissedPagesidxs(self):
        """Return _idx of missed pages from a string returned by API."""
        missedpages = []
        pagesids = {}
        source = io.StringIO(self.astring)
        context = iterparse(source, events=("start", "end", "start-ns"))
        self.root = None

        for event, elem in context:
            if event == "start-ns" and elem[0] == "":
                self.uri = elem[1]
                continue
            if event == "start" and self.root is None:
                self.root = elem
                continue
            if event == "end" and elem.tag == "pages":
                for c in elem.iterfind("page"):
                    idx = int(c.get('_idx'))
                    if idx < 0:
                        missedpages.append(c.get('title'))
                    else:
                        pagesids[c.get('title')] = idx
                elem.clear()
                self.root.clear()
                return missedpages, pagesids
        return None, None

if __name__ == "__main__":
    #realfile = os.path.realpath(__file__)
    #realfile_dir = os.path.dirname(os.path.abspath(realfile))
    test = XmlDump('/home/ilias/Λήψεις/Προγραμματισμός1/dumps/dn/skwiktionary-latest-pages-meta-current.xml.bz2')
    b = test.parseSiteInfo()
    print(b.sitename)
