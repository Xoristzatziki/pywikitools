#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017


#TODO:check if I check the sha1

import inspect #remove in production?

#import datetime

import os, re, sys
#import bz2
import time
import io

#because we may want to move to 2nd disk and os.rename copies instead of move
import shutil

from itertools import islice

import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError


#TODO?: is it worth write a simpler conf rw?
import json

if __name__ == "__main__":
    #print('==:',__name__)
    import xmldumpreader
    import auxiliary
    import db
    from wikitools import wiki, page, api, user
else:
    #print('else:',__name__)
    from . import auxiliary
    from . import db
    from . import xmldumpreader
    #from . import wikitools.api as api
    from .wikitools import wiki, page, api, user#wikitools as mangledwiki
#    from mangledwiki import wiki
#    from mangledwiki import page
#    from mangledwiki import api
#    from mangledwiki import user

myprint = auxiliary.myprint
myprintstay = auxiliary.myprintstay

checksha1hash = auxiliary.checksha1hash
getnonZtime = auxiliary.getnonZtime
#def donotcheck(*args):return True
#checksha1hash = donotcheck try

version = '0.0.3'
#ASSUME dir is inside a path named: 'v' + current version number
subversion = os.path.basename(os.path.abspath(os.path.join(os.path.split(os.path.realpath(__file__))[0], '..')))[2:]


justAQueryingAgentHeaders = {'User-Agent':'Xoristzatziki@elwiktionary fishing only boat','version': subversion + '/' + version}
WEBPAGEOFDUMPS = 'https://dumps.wikimedia.your.org/'
INDEXPAGEOFDUMPS = 'https://dumps.wikimedia.your.org/backup-index.html'
PMCFILESTRING = '-pages-meta-current.xml'
LPMCFILESTRING = '-latest' + PMCFILESTRING

MAX_LE_OR_RC = 500
MAX_PAGES_IN_CHUNK = 50
MAX_LAG = 4
MAX_SPECIALEXPORT_TRIES = 3

def removeif(filefullname):
    if os.path.exists(filefullname):
        os.remove(filefullname)

def reporthook(blocknum, blocksize, totalsize):
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r%5.1f%% %*d / %d" % (
            percent, len(str(totalsize)), readsofar, totalsize)
        sys.stderr.write(s)
        if readsofar >= totalsize: # near the end
            sys.stderr.write("\n")
    else: # total size is unknown
        sys.stderr.write("read %d\n" % (readsofar,))

def projectFromdbPath(dbpath):
    dumpspath, dbname = os.path.split(dbpath)
    return dbname.split('-',1)[0]

def pathFromdbPath(dbpath):
    dumpspath, dbname = os.path.split(dbpath)
    return dumpspath



class Changed:
    def __init__(self):
        self.title = ''
        self.d = False
        self.TS = ''

##################################################################################################################################################################
class Updater:#TODO: Update db siteinfo after each chunk of lemma updates
    #assuming always a "latest" name convention is used not the numbered dumps
    API_ERROR_NONE = 0
    API_ERROR_DN = 1
    API_ERROR_TAGINXML = 2
    def __init__(self, project, dumpspath):
        self.project = project
        self.dumpspath = os.path.abspath(dumpspath)
        self.dbfile = os.path.join(self.dumpspath, project + LPMCFILESTRING + '.db')
        self.txtfile = os.path.join(self.dumpspath, project + LPMCFILESTRING + '.txt')
        self.jsonfile = os.path.join(self.dumpspath, 'dn', project + '-log.json')
        self.bz2file = os.path.join(self.dumpspath, 'dn', project + LPMCFILESTRING + '.bz2')
        self.bz2link = urllib.parse.urljoin(WEBPAGEOFDUMPS, project + '/latest/' + project + LPMCFILESTRING + '.bz2')
        self.tsfile = self.bz2file + '.TS'
        self.sha1file = self.bz2file + '.sha1'
        #myprint('self.jsonfile:', self.jsonfile)
        siteinfo = None
        self.siteurl = ''
        self.apiurl =  ''
        self.dataTS = ''
        self.dumpTS = ''
        self.continueTS = ''
        self.fillselfSiteInfo()
        self.uptoTS = ''
        self.lastrcTS = ''

        self.changes = {}
        self.APIerror = self.API_ERROR_NONE
        self.unchanged = {}

    def fillselfSiteInfo(self):
        if os.path.exists(self.dbfile):
            with db.DB(self.dbfile) as tmpdb:
                ok, siteinfo = tmpdb.getSiteInfo()
                self.siteurl = siteinfo['asiteurl']
                self.apiurl = self.siteurl + 'w/api.php'
                self.dataTS = siteinfo['atimestamp']
                self.dumpTS = siteinfo['adumpTS']
                #self.continueTS = siteinfo['atimestamp']
                #myprint('self.siteurl 0',self.siteurl, len(siteinfo),siteinfo[0])#, siteinfo[1],siteifno[2])
                #for b in siteinfo:
                    #myprint(b)
                #myprint('-----')
                return True
        return False

    def checksmth(self,a):
        with db.DB(self.dbfile) as tmpdb:
            print(tmpdb.getLemmaContent(a))

    def downloadLatestDump(self):
        removeif(self.tsfile)
        removeif(self.sha1file)
        thesha1, theTS = self.getSHA1Values()
        ok  = dnfile(self.bz2link,self.bz2file)
        if ok:
            with open(self.tsfile, 'wt') as ftxt:
                ftxt.write(theTS)
            with open(self.sha1file, 'wt') as ftxt:
                ftxt.write(thesha1)
        return ok

    def newerDumpExists(self):
        '''Check if a newer dump exists.'''
        if self.dumpTS == '':
            print('No dumpTS, newerDumpExists will be True')
            return True
        thesha1, theTS = self.getSHA1Values()
        if theTS != '':
            print('theTS > self.dumpTS', (theTS > self.dumpTS))
            return (theTS > self.dumpTS)
        else:
            return False

    def getSHA1Values(self):
        thesha1 = ''
        theTS = ''
        thesha1sumslink = self.bz2link[:-len(PMCFILESTRING + '.bz2')] + '-sha1sums.txt '
        ok, thetext = dnpage(thesha1sumslink)
        if ok:
            thematch = re.search('(?P<SHA1>.{40}) ' + self.project + '-(?P<TS>[0-9]{8})' + PMCFILESTRING, thetext)
            if thematch:
                thesha1 = thematch.group('SHA1')
                theTS = thematch.group('TS')
            else:
                thematch = re.search('(?P<SHA1>.{40}) ' + self.project + '-(?P<TS>[0-9]{8})-',thetext)
                if thematch:
                    theTS = thematch.group('TS')
        return thesha1, theTS


##########################3*************************************************************************#########
    def getChanges(self):
        print('getChanges from:',self.dataTS)
        with wiki.Wiki(url = self.siteurl) as mywiki:
            try:
                #Get recent edits and new titles.
                #print('get')
                urldata = { 'action':'query',
                'list':'recentchanges',
                'rcprop':'title|timestamp|loginfo',
                'rctype':'log|edit|new',
                'rcdir':'newer',
                'rcstart':self.dataTS,
                #'continue':self.dummycontinue,
                'rclimit':MAX_LE_OR_RC,
                'maxlag':MAX_LAG
                }
                therequest = api.APIRequest(mywiki, urldata)
                #thedict = {}
                #print(therequest)
                for req in therequest.queryGen():
                    #if self.fnrefresh:
                        #myprint('got some data', str(len(self.changes)))
                        #self.fnrefresh('rcpages:' + str(len(self.changes)))
                    #print(req)
                    for title in req['query']['recentchanges']:
                        #print('a query')
                        if title['type'] == 'new' or title['type'] == 'edit':
                            self.addifnewer (title['title'], title['timestamp'])
                        if title['type'] == 'log':
                            if  title['logaction'] == 'delete':
                                self.addifnewer (title['title'], title['timestamp'], True)
                            if title['logaction'] == 'move':
                                self.addifnewer (title['logparams']['target_title'], title['timestamp'])
                                if 'suppressredirect' in title['logparams']:
                                    self.addifnewer (title['logparams']['target_title'], title['timestamp'], True)
                                else:
                                    self.addifnewer (title['title'], title['timestamp'])
                    myprintstay('rcpages:', str(len(self.changes)))
                    self.jsondump()
                #print (thedict)
                #for b in sorted(self.changes, key=lambda x: thedict[x]['timestamp']):
                    #print( thedict[b]['timestamp'], b)
            except Exception as e:
                print(e)
                raise e
        print('Exiting getChanges')
        return True

    def getLatestDumpAndTitles(self, forcedownload = False, usedownloaded = False):
        if forcedownload or self.newerDumpExists():
            oldexisted = os.path.exists(self.dbfile)
            if not self.MoveToBackup():
                myprint('Could not move to backup')
                return False
            if usedownloaded and os.path.exists(self.bz2file):
                ok = True
            else:
                ok = self.downloadLatestDump()
            if not ok:
                myprint('Could not get Latest Dump')
                return False
            ok = InitiateLocalFiles(self.bz2file, self.dbfile, self.txtfile)
            if not ok:
                myprint('Could not Initiate Local Files.')
                if oldexisted:
                    self.MoveFromBackup()
                return False
            ok = self.fillFilesFrombz2()
            if not ok:
                myprint('Could fill Local Files From bz2.')
                if oldexisted:
                    self.MoveFromBackup()
                return False
            else:
                self.DeleteBackup()
                pass
        removeif(self.tsfile)
        removeif(self.sha1file)
        self.fillselfSiteInfo()
        myprint('filled site info')
        if self.jsonread():
            myprint('got changes from json file.', len(self.changes))
        else:
            self.getChanges()
            myprint('got changes', len(self.changes))
        self.getAndUpdateTheContent()
        myprint('updated content')

    def fillFilesFrombz2(self):
        try:
            myprint('reading bz2 and writing txts...')
            listForDB = []
            theTS = ''
            with open(self.bz2file + '.TS', 'rt') as ftxt:
                theTS = ftxt.read().strip()
            with open(self.bz2file + '.sha1', 'rt') as ftxt:
                thesha1 = ftxt.read().strip()
            if len(thesha1) == 40:
                ok = checksha1hash(self.bz2file, thesha1)
                if not ok:
                    myprint('sha1 do not match.')
                    return False
            with open(self.txtfile, 'wt') as ftxt:
                with xmldumpreader.XmlDump(self.bz2file) as myDump:
                    #print('reading from bz2 file...')
                    for entry in myDump.parse():
                        #print(entry.isredirect)
                        #listForDB.append((entry.title, entry.ns, str(ftxt.tell()), str(len(entry.text)),entry.timestamp))
                        #print((entry.title, entry.ns, 1 if entry.isredirect else 0, ftxt.tell(), len(entry.text),entry.timestamp))
                        listForDB.append((entry.title, int(entry.ns), 1 if entry.isredirect else 0, ftxt.tell(), len(entry.text), entry.timestamp))
                        ftxt.write(entry.text + '\n')
                    dsiteinfo = myDump.getSiteInfo()
                    siteurl = urllib.parse.urljoin(dsiteinfo.base,'/')
                    sitenses = '\n'.join((key + '#' + dsiteinfo.namespaces[key]) for key in sorted(dsiteinfo.namespaces, key=int))
            myprint('                  writing texts ...DONE')
            #myprint('filling db, siteurl, sitenses...', siteurl, sitenses)
            ok = False
            with db.DB(self.dbfile) as tmpdb:
                ok = tmpdb.fillemptydb(listForDB, theTS, siteurl, sitenses)
            if not ok:
                print( 'db not filled')
                return ok
            print( 'The 2 files created')
            print('deleting bz2...')
            os.remove(self.bz2file)
            #with open(TSfullname, 'wt') as ftxt:
                #ftxt.write(theTS)
            print('bz2 deleted')
            print('DONE creating files from bz2')
            return True
        except Exception as e:
            myprint(inspect.stack()[0][3],'Problem.')
            raise

    def updatefromjsontest(self):
        ok = self.jsonread()
        if ok:
            xcounter = len(self.changes)
            dictlen = xcounter
            while True:
                if len(self.changes) == 0:
                    break
                for title in list(islice([l for l in sorted(self.changes,key=self.changes.get)],MAX_PAGES_IN_CHUNK)):
                    myprint(self.changes[title], title)
                    del self.changes[title]
                    xcounter -= 1
            print(dictlen, xcounter)

    def updatefromjson(self):
        ok = self.jsonread()
        if ok:
            myprint('getAndUpdateTheContent', 'from updatefromjson')
            self.getAndUpdateTheContent()

    def jsonread(self):
        if os.path.exists(self.jsonfile):
            loggedchanges = {}
            self.changes = {}
            with open(self.jsonfile, 'rt', encoding ='utf_8') as f:
                loggedchanges = json.load(f)
            for key in loggedchanges:
                #print("---",key,"#", type(loggedchanges[key]),"#", loggedchanges[key])
                self.changes[key] = loggedchanges[key]
            return True
        return False

    def updateSiteInfoInDb(self, mywiki, localdb):
        #print('in updateSiteInfoInDb')
        #print(localdb)
        nses = {}
        for key, val in mywiki.namespaces.items():
            #print(key, val, val['*'] )
            nses[key] = val['*']
        nses[0] = 'main'
        #print(nses)
        sitenses = '\n'.join((str(key) + '#' + nses[key]) for key in sorted(nses, key=int))
        #print(sitenses)
        #print('===========updating sitenses and localdb ts ===================')
        #localdb.updateSiteInfo3(sitenses)
        localdb.updateSiteInfo2(sitenses)
        myprint(' siteinfo updated.')

    def getAndUpdateTheContent(self):
        previouscounter = 0
        if len(self.changes) == 0:
            myprint('no changes found')
            return True
        try:
            with db.DB(self.dbfile) as localdb:
                myprint('1. remaining changed pages:',len(self.changes),'  ')
                #myprint('deleting any if exists')
                #myprint(self.changes.keys())
                #print(self.changes)
                removelist = [key for key in self.changes if self.changes[key]['isdel']]
                #print("len(removelist)",len(removelist))
                if len(removelist):
                    print(removelist[0])
                    ok = localdb.deleteWithTransaction(removelist)
                #myprint('deleting deletes finished.')
                self.changes = {key:self.changes[key] for key in self.changes if not self.changes[key]['isdel']}
                #for key in removelist:
                    #print(self.changes[key])
                    #localdb.deleteLemma(key)
                    #print('isdel 3', key)
                    #del self.changes[key]
                    #print('isdel 4', key)
                    #myprint('remaining changed pages:',len(self.changes),'  ')

                myprint('2. remaining changed pages after deletes:',len(self.changes),'  ')
                with wiki.Wiki(url = self.siteurl) as mywiki:
                    print('updating using self.changes')
                    while True:
                        myprint('remaining changed pages in loop:',len(self.changes),'  ')
                        #starttiming = datetime.datetime.now()
                        if len(self.changes) == 0:
                            myprint(inspect.stack()[0][3],'No (more) titles in self.changes.')

                            #return True
                            break
                        if len(self.changes) == previouscounter:
                            myprint(inspect.stack()[0][3],'WARNING! No changes done!!! Stop.')
                            #return False
                            break
                        previouscounter = len(self.changes)
                        #print('previouscounter',previouscounter)
                        #print(sorted(self.changes, key=lambda x: self.changes[x]['timestamp']))
                        #print([l for l in sorted(self.changes.iteritems(), key=lambda (x, y): y['timestamp']) ])
                        listoftitlestoget = list(islice([l for l in sorted(self.changes, key=lambda x: self.changes[x]['timestamp'])], MAX_PAGES_IN_CHUNK))
                        #print("requesting ", len(listoftitlestoget))
                        #myprint('UpdateChangedLemmas, getting next chunk...')
                        #print('===============listoftitlestoget',listoftitlestoget)
                        urldata = { 'action':'query',
                        'titles':'|'.join(listoftitlestoget),
                        'prop':'revisions|info',
                        'rvprop':'content|timestamp'
                        }
                        #print('mywiki, urldata',mywiki, urldata)
                        therequest = api.APIRequest(mywiki, urldata)
                        #print('therequest check')
                        fullreq = therequest.querySimple()
                        #stoptime1 = datetime.datetime.now()
                        if fullreq:
                            req = fullreq['query']
                            #print('got one req')
                            #print(req)
                            if 'normalized' in req:
                                #myprint('has normalized')
                                print('has normalized')
                                for normalised in req['normalized']:
                                    listname = normalised['from']
                                    newname = normalised['to']
                                    self.changes[newname] = self.changes[listname]
                                    del self.changes[listname]
                                    listoftitlestoget.pop(listname)
                                    listoftitlestoget.append(newname)
                            #myprint('after normalized')
                            #print(req)
                            #allids = [x for x in req['pages']]
                            #for anything in req['pages'][x] for x in req['pages']
                            #lala = {}
                            #for x in req['pages']:
                                #print('x',x)
                                #print(req['pages'][x])
                                #lala.append(req['pages'][x])
                            #print('lala',lala)
                            #print({x:req['pages'][x] for x in req['pages']})
                            requestpages = {x:req['pages'][x] for x in req['pages']}
                            #print("in request ", len(requestpages))
                            #TODO: check if title can be zero
                            #deletedids = [x for x in req['pages'] if int(x) < 0]
                            deletedtitles = [requestpages[x]['title'] for x in requestpages if int(x) < 0]
                            requestpages = {x:requestpages[x] for x in requestpages if int(x) > 0}
                            #print('len(deletedtitles)', len(deletedtitles),deletedtitles)
                            if len(deletedtitles):
                                ok = localdb.deleteWithTransaction(deletedtitles)
                                for pagetitle in deletedtitles:
                                    del self.changes[pagetitle]
                            remainingtitles = tuple(requestpages[x]['title'] for x in requestpages)
                            #print('remainingtitles',remainingtitles)
                            existingentries = localdb.getLemmasInList(remainingtitles)
                            #print('existingentries',len(existingentries))#,existingentries)
                            newlemmas = {}
                            oldlemmas = {}
                            for pageid in requestpages:
                                if requestpages[pageid]['title'] in existingentries:
                                    #print("requestpages[pageid]['title']",requestpages[pageid]['title'])
                                    #print("existingentries[requestpages[pageid]]",existingentries[requestpages[pageid]['title']])
                                    #print("requestpages[pageid]",requestpages[pageid])
                                    #oldlemmas[requestpages[pageid]['title']] = {'old':existingentries[requestpages[pageid]['title']],
                                                #'new':requestpages[pageid]}
                                    oldlemmas[pageid] = requestpages[pageid]
                                else:
                                    #print("requestpages[pageid]['title']  NOT",requestpages[pageid]['title'])
                                    newlemmas[pageid] = requestpages[pageid]
                            print('len(oldlemmas)',len(oldlemmas),'len(newlemmas)',len(newlemmas))
                            #print('len(oldlemmas)',oldlemmas)
                            #print('len(newlemmas)',newlemmas)

                            #for pagetitle in oldlemmas:
                                #print('updating old', len(oldlemmas))
                                #print('==============PAGE ================',pagetitle )
                                #print('new dict',oldlemmas[pagetitle]['new'])
                                #print('old dict',oldlemmas[pagetitle]['old'])
                                #print(oldlemmas[pagetitle]['new']['ns'])
                                #print(1 if 'redirect' in oldlemmas[pagetitle]['new'] else 0)
                                #print(oldlemmas[pagetitle]['new']['revisions'][0]['timestamp'])
                                #print(oldlemmas[pagetitle]['new']['revisions'][0]['*'])
                                #print(oldlemmas[pagetitle]['old']['lstart'])
                                #print(oldlemmas[pagetitle]['old']['lcharlen'])
                                #print('=============-----------------------============')
                                #newentrywitholddata = db.DBRow(title = pagetitle,
                                                    #ns = oldlemmas[pagetitle]['new']['ns'],
                                                    #isredirect = 1 if 'redirect' in oldlemmas[pagetitle]['new'] else 0,
                                                    #timestamp = oldlemmas[pagetitle]['new']['revisions'][0]['timestamp'],
                                                    #content = oldlemmas[pagetitle]['new']['revisions'][0]['*'],#rest are dummy values
                                                    #start = oldlemmas[pagetitle]['old']['lstart'],
                                                    #charlen = oldlemmas[pagetitle]['old']['lcharlen']
                                                    #)
                                #print('newentry',newentry)
                                #ok = localdb.updateExistingLemma(newentrywitholddata)
                                #print('updated lemma:',pagetitle)
                                #del self.changes[pagetitle]
                                #listoftitlestoget.remove(pagetitle)
                            if len(oldlemmas):
                                #print('updating old', len(oldlemmas))
                                localdb.updateExistingLemmas(oldlemmas)
                                for pageidtxt in oldlemmas:
                                    del self.changes[oldlemmas[pageidtxt]['title']]
                                    listoftitlestoget.remove(oldlemmas[pageidtxt]['title'])
                            #print('updating old    END', len(oldlemmas))
                            if len(newlemmas):
                                #print('appending new', len(newlemmas))
                                localdb.appendWithTransaction(newlemmas)
                                for pageidtxt in newlemmas:
                                    del self.changes[newlemmas[pageidtxt]['title']]
                                    listoftitlestoget.remove(newlemmas[pageidtxt]['title'])
                            #print('appending new         END', len(newlemmas))
                            #for pageidtxt in newlemmas:
                                #apage = newlemmas[pageidtxt]
                                #newentry = db.DBRow(title = apage['title'],
                                #                    ns = apage['ns'],
                                #                    isredirect = 1 if 'redirect' in apage else 0,
                                 #                   timestamp = apage['revisions'][0]['timestamp'],
                                 #                   content = apage['revisions'][0]['*'],#rest are dummy values
                                 #                   start = 0,
                                 #                   charlen = 0
                                 #                   )
                                #print('newentry',newentry)
                                #ok = localdb.appendLemma(newentry)
                                #print('updated lemma:',apage['title'])
                                #del self.changes[apage['title']]
                                #listoftitlestoget.remove(apage['title'])

                            self.jsondump()
                        #stoptime2 = datetime.datetime.now()
                        #print( stoptime2 - stoptime1, stoptime1 - starttiming)
                    #out of break
                    print('out of break')
                    self.updateSiteInfoInDb( mywiki, localdb)
        except Exceptions as e:
            myprint(inspect.stack()[0][3],e)
            raise e
        #just in case
        self.jsondump()
        print('exiting update content')

    def addifnewer(self, thetitle, theTS, isdel=False):
        if self.changes.get(thetitle) != None:
            if self.changes[thetitle]['timestamp'] > theTS:
                return
        self.changes[thetitle] = {'isdel' : isdel,
            'timestamp' : theTS
            }

    def jsondump(self):
        try:
            if len(self.changes):
                with open(self.jsonfile, 'w', encoding ='utf_8') as f:
                    json.dump(self.changes, f, ensure_ascii=False)
            else:
                if os.path.exists(self.jsonfile):
                    os.remove(self.jsonfile)
            return True
        except Exception as e:
            myprint(inspect.stack()[0][3],'Exception Problem.')
            #return False
            raise e

    def MoveToBackup(self):
        #myprint('moving 2 files to backup')
        try:
            backuppath = os.path.join(self.dumpspath, 'backup')
            #myprint('backuppath 1. moving 2 files to backup',backuppath)
            if not os.path.exists(backuppath):
                #myprint('backuppath 2. moving 2 files to backup',backuppath)
                os.mkdir(backuppath)
            else:
                #myprint('backuppath 3. moving 2 files to backup')
                if not os.path.isdir(backuppath):
                    #myprint('backuppath 4. moving 2 files to backup')
                    return False
            if not os.path.exists(self.dbfile):
                return True
            #myprint('backuppath 5. moving 2 files to backup')
            if os.path.exists(self.dbfile):
                removeif(os.path.join(self.dumpspath,'backup', os.path.basename(self.dbfile)))
                dontcare = shutil.move(self.dbfile, backuppath)
                print('db moved to b')
            if os.path.exists(self.txtfile):
                print('trying to move txt to b')
                removeif(os.path.join(self.dumpspath,'backup', os.path.basename(self.txtfile)))
                dontcare = shutil.move(self.txtfile, backuppath)
            return True
        except Exception as e:
            return False

    def MoveFromBackup(self):
        myprint('moving 2 files back from backup')
        try:
            backuppath = os.path.join(self.dumpspath, 'backup')
            bdbfullname = os.path.join(backuppath, project+ LPMCFILESTRING + '.db')
            btxtfullname = os.path.join(backuppath, project+ LPMCFILESTRING + '.txt')

            dontcare = shutil.move(bdbfullname, dumpspath)
            dontcare = shutil.move(btxtfullname, dumpspath)
            return True
        except Exception as e:
            return False

    def DeleteBackup(self):
        myprint('deleting 2 files from backup.')
        try:
            backuppath = os.path.join(self.dumpspath, 'backup')
            bdbfullname = os.path.join(backuppath, project+ LPMCFILESTRING + '.db')
            btxtfullname = os.path.join(backuppath, project+ LPMCFILESTRING + '.txt')
            removeif(bdbfullname)
            removeif(btxtfullname)
            return True
        except Exception as e:
            return False

##################################################################################################################################################################

def InitiateLocalFiles(bz2fullname, dbfullname, txtfullname, deleteoldfiles = False):
    '''Create the empty .db and .txt files.'''
    #myprint('dbfullname, txtfullname',dbfullname, txtfullname)
    if os.path.exists(dbfullname) or os.path.exists(txtfullname):
        if not deleteoldfiles:
            myprint(inspect.stack()[0][3],'At least one of the 2 files exists and deleteold=False')
            return False
        else:
            if os.path.exists(dbfullname):
                try:os.remove(dbfullname)
                except Exception as e:
                    myprint('could not remove ' + dbfullname, inspect.stack()[0][3])
                    return False
            if os.path.exists(txtfullname):
                try:os.remove(txtfullname)
                except Exception as e:
                    myprint('could not remove ' + txtfullname, inspect.stack()[0][3])
                    return False
    #dump dir is clear
    try:
        with db.DB(dbfullname) as tmpdb:
            tmpdb.createAnEmptyDB()
        open(txtfullname, 'a').close()
        #the 2 files have been inititated
        return True
    except Exception as e:
        myprint('could not create empty db or empty txt file', inspect.stack()[0][3])
        return False



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

def donothing(*args):
    try:
        with wiki.Wiki('https://el.wiktionary.org/') as mywiki:
            print(mywiki)
            p = page.Page(mywiki, title='go')
            print(p)
            urldata = { 'action':'query',
            'list':'recentchanges',
            'rcprop':'title|timestamp|loginfo',
            'rctype':'log|edit|new',
            'rcdir':'newer',
            'rcstart':'20170703230000',
            #'continue':self.dummycontinue,
            #'rclimit':MAX_LE_OR_RC,
            'maxlag':MAX_LAG
            }
            therequest = api.APIRequest(mywiki, urldata)
            #thedict = {}
            print(therequest)
            u = user.User(mywiki,'')
            print(u)
            print(u.getContributions())
    except Exception as e:
        raise e

if __name__ == "__main__":
    realfile = os.path.realpath(__file__)
    realfile_dir = os.path.dirname(os.path.abspath(realfile))
    #print(realfile_dir)
    #donothing() #and exit
    #exit()
    project = 'ukwiktionary'
    dumpspath = os.path.abspath( os.path.join(realfile_dir,'..','..','dumps'))
    #b = CreateLocalFilesFromNet(project,os.path.join(realfile_dir,'..','..','dumps'), numbered = False)
    #print('CreateLocalFilesFromNet returned:',b)
    #if not b: exit()


    #b = os.path.join(realfile_dir,'..','..','dumps',project + '-latest-pages-meta-current.xml.db')
    #t = os.path.join(realfile_dir,'..','..','dumps',project + '-latest-pages-meta-current.xml.txt')
    #p = os.path.join(realfile_dir,'..','..','dumps')
    #bz = os.path.join(realfile_dir,'..','..','dumps','dn',project + '-latest-pages-meta-current.xml.bz2')

    #myprint('b',b)
    #CreateLocalFilesFromNet(project,pathFromdbPath(b),checkhash = False)
    #b = Updater(os.path.join(realfile_dir,'..','..','dumps',project + '-latest-pages-meta-current.xml.db'))
    #b.checksmth('θάλασσα')
    #b.getAllChangedTitles()
    #b.updatefromjson()
    #b.getAllChanges()
    #CreateLocalFilesFromNet(project,p)
    #InitiateLocalFiles(bz, b, t, deleteoldfiles = True)
    #u = Updater(project,dumpspath)
    #u.getLatestDumpAndTitles(forcedownload = True, usedownloaded = True)
    #forcedownload = False, usedownloaded
    #u.jsonread()
    #u.updatefromjson()
    #u.getChanges()
