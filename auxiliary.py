#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import hashlib, os, sys, re
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET
import inspect

HASH_BUFFER_SIZE = 65535

sha1 = hashlib.sha1()

version = '0.0.3'

justAQueryingAgentHeaders = {'User-Agent':'Xoristzatziki fishing only boat','version': version}

def myprint(*args):
    if len(args):
        for x in args:
            print(x, end='\t')
        print()
        sys.stdout.flush()

def myprintstay(*args):
    if len(args):
        print('', end = '\r')
        for x in args:
            print(x, end='\t')
        sys.stdout.flush()

def checksha1hash(thefullfilepath, thesha1hash):
    with open(thefullfilepath, 'rb') as f:
        while True:
            dataread = f.read(HASH_BUFFER_SIZE)
            if not dataread:break
            sha1.update(dataread)
    myprint(sha1.hexdigest(), thesha1hash)
    return (sha1.hexdigest() == thesha1hash)

def getnonZtime(whichZtime):
    '''Return a TS in format YYYYMMDDHHMMSS'''
    if 'Z' in whichZtime:
        return whichZtime[:4] + whichZtime[5:7] + whichZtime[8:10] + whichZtime[11:13] + whichZtime[14:16] + whichZtime[17:19]
    else:
        #return as is, not a Z time
        return whichZtime

def getUserInfo(theuser):
    theuser = urllib.parse.quote(theuser)
    url = "https://meta.wikimedia.org/w/index.php?title=Special%3ACentralAuth&target=" + theuser
    #ok, alldata = dnpage(urllib.parse.urlencode(url))
    ok, alldata = dnpage(url)
    if ok:
        root = ET.fromstring(alldata)
        resultfixed = ''
        for onerev in root.iter('body'):
            myprint('onerev', onerev)
            #for sometext in onerev.itertext():
                #myprint('sometext', sometext)
                #if sometext.strip():
                    #resultfixed += '\n' + sometext
            for atable in onerev.iter('table'):
                if atable.get('class') =='wikitable sortable mw-centralauth-wikislist':
                    resultfixed = ET.tostringlist(atable, encoding="unicode", method="html")
                    myprint('\n'.join(resultfixed))
                    return '\n'.join(resultfixed)
                    #for sometext in onerev.itertext():
                        #myprint('sometext', sometext)
                        #if sometext.strip():
                            #resultfixed += '\n' + sometext
            #thetitle = onerev.attrib['title']
            #theTS = onerev.attrib['timestamp']
            #thetype = onerev.attrib['type']
            #self.addifnewer(thetitle, theTS, False)        
            #myprint(onerev.text)
            #resultfixed = onerev
            #resultfixed = '\n'.join(filter(lambda x:  not re.match(r'^\s*$', x), resultfixed))
            #wikitable sortable mw-centralauth-wikislist

            #return resultfixed
    myprint('an error')
    return 'an error'
    

def dnpage(url):
    try:
        req = urllib.request.Request(url, headers = justAQueryingAgentHeaders)
        #print('Trying... ' + url, end = '')
        #sys.stdout.flush()
        with urllib.request.urlopen(req) as response:
            respData = response.read()
        #print(' ...DONE')
        #TODO:is really worth to check for charset=xxxx inside .html?
        pageinUTF8 = respData.decode('utf8')
    except HTTPError as e:
        print('The server couldn\'t fulfill the request.')
        print('Error code: ', e.code)
        return False, [e.code]
    except URLError as e:
        print('We failed to reach a server.')
        print('Reason: ', e.reason)
        return False, [e.code]
    except Exception as e:myprint(inspect.stack()[0][3],e)
        #raise ProcessTheError(inspect.stack()[0][3],e.args)
    return True, pageinUTF8

def dnfile( url, saveas=None):
    #print('Downloading from... ',url, end = '')
    #print('Downloading from... ',url)
    #sys.stdout.flush()
    #print()
    try:
        #fname, headers = urllib.request.urlretrieve(url)
        fname, headers =  urllib.request.urlretrieve(url, reporthook = reporthook)
        if saveas:
            shutil.move(fname,saveas)
        else:
            saveas = fname
        #print(' ...DONE')
        return True, saveas
    except HTTPError as e:
        print('The server couldn\'t fulfill the request.')
        print('Error code: ', e.code)
        return False, [e.code]
    except URLError as e:
        print('We failed to reach a server.')
        print('Reason: ', e.reason)
        return False, [e.code]
    except Exception as e:myprint(inspect.stack()[0][3],e)
        #raise ProcessTheError(inspect.stack()[0][3],e.args)

    

if __name__ == "__main__":
    realfile = os.path.realpath(__file__)
    realfile_dir = os.path.dirname(os.path.abspath(realfile))
    b = checksha1hash('/home/ilias/ziped/apps/dumps/dn/skwiktionary-latest-pages-meta-current.xml.bz2','6241b663874eea6a19256ec5f07232c1a7b9336c')
    print('Files are ' + ('identical' if b else 'different'))
