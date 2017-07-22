#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import inspect #remove in production?

import os, re, sys
import bz2
import time
import io

#because we may want to move to 2nd disk and os.rename copies instead of move
import shutil

from itertools import islice

import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

 
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

justAQueryingAgentHeaders = {'User-Agent':'Xoristzatziki fishing only boat','version': version}
WEBPAGEOFDUMPS = 'https://dumps.wikimedia.your.org/'
INDEXPAGEOFDUMPS = 'https://dumps.wikimedia.your.org/backup-index.html'
PMCFILESTRING = '-pages-meta-current.xml'
LPMCFILESTRING = '-latest' + PMCFILESTRING

MAX_LE_OR_RC = 500
MAX_PAGES_IN_CHUNK = 30
MAX_LAG = 4
MAX_SPECIALEXPORT_TRIES = 5


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

def MoveToBackup(project,dumpspath):
    myprint('moving 2 files to backup')
    try:
        bpath = os.path.join(dumpspath, 'backup')
        dbfullname = os.path.join(dumpspath, project+ LPMCFILESTRING + '.db') 
        txtfullname = os.path.join(dumpspath, project+ LPMCFILESTRING + '.txt') 
        if not os.path.exists(bpath):
            os.mkdir(bpath)
        else:
            if not os.path.isdir(bpath):
                return False
        bdbfullname = shutil.move(dbfullname, bpath)
        bdbfullname = shutil.move(txtfullname, bpath)
        return True
    except Exception as e:
        return False

def MoveFromBackup(project, dumpspath):
    myprint('moving 2 files back from backup')
    try:
        bpath = os.path.join(dumpspath, 'backup')
        bdbfullname = os.path.join(bpath, project+ LPMCFILESTRING + '.db') 
        btxtfullname = os.path.join(bpath, project+ LPMCFILESTRING + '.txt') 

        dbfullname = shutil.move(bdbfullname, dumpspath)
        dbfullname = shutil.move(btxtfullname, dumpspath)
        return True
    except Exception as e:
        return False

def DeleteBackup(project, dumpspath):
    myprint('deleting backup files as no more for use.')
    try:
        bpath = os.path.join(dumpspath, 'backup')
        bdbfullname = os.path.join(bpath, project+ LPMCFILESTRING + '.db') 
        btxtfullname = os.path.join(bpath, project+ LPMCFILESTRING + '.txt') 
        os.remove(bdbfullname)
        os.remove(btxtfullname)
        return True
    except Exception as e:
        return False

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
    def __init__(self, dbfile, jsprefix = '', fnrefresh = None):
        self.fnrefresh = fnrefresh
        self.dbfile = os.path.abspath(dbfile) #may be a dummy file path to get dumps path
        self.jsprefix = jsprefix
        self.jsonfile = os.path.join(os.path.split(self.dbfile)[0], 'dn', self.jsprefix + 'log.json')
        #myprint('self.jsonfile:', self.jsonfile)
        siteinfo = None
        self.siteurl = ''
        self.apiurl =  ''
        self.dbTS = ''
        self.continueTS = ''
        self.fillselfSiteInfo()
#        if os.path.exists(self.dbfile):
#            with db.DB(self.dbfile) as tmpdb:
#                ok, siteinfo = tmpdb.getSiteInfo()
#                self.siteurl = siteinfo['asiteurl']
#                self.dbTS = siteinfo['atimestamp']
#                self.continueTS = siteinfo['atimestamp']
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
                self.dbTS = siteinfo['atimestamp']
                self.continueTS = siteinfo['atimestamp']
                #myprint('self.siteurl 0',self.siteurl, len(siteinfo),siteinfo[0])#, siteinfo[1],siteifno[2])
                #for b in siteinfo:
                    #myprint(b)
                #myprint('-----')
                return True
        return False

    def checksmth(self,a):
        with db.DB(self.dbfile) as tmpdb:
            print(tmpdb.getLemmaContent(a))

    def getNewerDump(self):
        '''Get a newer dump if exists.'''
        project = projectFromdbPath(self.dbfile)
        dumpspath = pathFromdbPath(self.dbfile)
        if os.path.exists(self.dbfile):
            if checkIfThereIsANewerDump(project, self.dbTS):
                myprint('There is a newer dump.')
                backupcreated = MoveToBackup(project,dumpspath)
                if backupcreated:
                    myprint('Moved 2 files to backup folder.')
                    ok = CreateLocalFilesFromNet(project, dumpspath)
                    if not ok:
                        myprint('New local files from Net NOT created.')
                        ok = MoveFromBackup(project, dumpspath)
                        myprint('Old files moved back.')
                        backupcreated = False
                    else:
                        self.fillselfSiteInfo()
                        myprint('got new site info')
                        ok = DeleteBackup(project, dumpspath)
                        myprint('Deleted old backup files.')
                        return True
        else:
            #myprint('getNewerDump project',project,'dumpspath',dumpspath)
            myprint('No old files. Downloading latest.')
            ok = CreateLocalFilesFromNet(project, dumpspath)
            if ok:
                self.fillselfSiteInfo()
                myprint('got new site info')
                return True
            else:
                myprint('We do not have any dump for project:' + str(project))
                raise NotImplementedError
        return False

    def getLatestDumpAndTitles(self, checkfornewer = True):
        if checkfornewer:
            try:
                print('where?')
                ok = self.getNewerDump()
            except NotImplementedError:
                myprint(inspect.stack()[0][3],'Error geting first Dump.')
                return        
        self.fillselfSiteInfo()
        #continueTS = 
        #myprint('do we have newer dump?:', ok)
        siteurl = self.siteurl + 'w/api.php'
        print(siteurl)
        theTS = self.continueTS
        #theTS = '20170702230000'
        ok = self.jsonread()
        if ok and len(self.changes):
            print('updating from json')
            self.getAndUpdateTheContent()
            #return
        #TODO:check1
        #return
        with wiki.Wiki(url = siteurl) as mywiki:
            try:
                #Get recent edits and new titles.
                #print('get')
                urldata = { 'action':'query',
                'list':'recentchanges',
                'rcprop':'title|timestamp|loginfo',
                'rctype':'log|edit|new',
                'rcdir':'newer',
                'rcstart':theTS,
                #'continue':self.dummycontinue,
                #'rclimit':MAX_LE_OR_RC,
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
            #for b in sorted(self.changes, key=lambda x: self.changes[x]['timestamp']):
                #print( self.changes[b]['timestamp'], b, self.changes[b]['isdel'])
            if len(self.changes):
                self.jsondump()
                #print('start deleting')
                with db.DB(self.dbfile) as tmpdb:
                    for title in [x for x in self.changes if self.changes[x]['isdel']]:
                        #print('was del')
                        del self.changes[title]
                        #myprint('found title for deletion', title)
                        #ok = tmpdb.deleteLemma(title)
                        #if ok:
                            #del self.changes[title]
                        #myprint('delete from self changes', title)
                #print('end deleting','len(self.changes)',len(self.changes))
                if len(self.changes):
                    #print('start changing','len(self.changes)',len(self.changes))
                    for item in self.changes:
                        #print(self.changes[item]['timestamp'])
                        self.changes[item]= self.changes[item]['timestamp']
        self.jsondump()
        self.getAndUpdateTheContent()
 
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

    def updateSiteInfoInDb(self, newmaxts, mywiki, localdb):
        #print('in updateSiteInfoInDb')
        if newmaxts == '': return
        #print(mywiki.namespaces)
        nses = {}
        for key, val in mywiki.namespaces.items():
            #print(key, val, val['*'] )
            nses[key] = val['*']
        nses[0] = 'main'
        #print(nses)
        sitenses = '\n'.join((str(key) + '#' + nses[key]) for key in sorted(nses, key=int))
        #print(sitenses)
        localdb.updateSiteInfo(getnonZtime(newmaxts), self.siteurl, sitenses)
        myprint(' siteinfo updated.')

    def getAndUpdateTheContent(self):
        previouscounter = 0
        newmaxts = ''
        try:
            with db.DB(self.dbfile) as localdb:
                with wiki.Wiki(url = self.apiurl) as mywiki:                    
                    while True:        
                        myprintstay('remaining changed pages:',len(self.changes),'  ')
                        #if self.fnrefresh:
                            #self.fnrefresh('remaining changed pages:' + len(self.changes))
                        if len(self.changes) == 0:
                            myprint(inspect.stack()[0][3],'No (more) titles in self.changes.')
                            self.updateSiteInfoInDb(newmaxts, mywiki, localdb)
                            return True
                            #break
                        if len(self.changes) == previouscounter:
                            myprint(inspect.stack()[0][3],'No changes done!!!')
                            return False
                        previouscounter = len(self.changes)
                        listoftitlestoget = list(islice([l for l in sorted(self.changes,key=self.changes.get)], MAX_PAGES_IN_CHUNK))
                        #myprint('UpdateChangedLemmas, getting next chunk...')
                        urldata = { 'action':'query',
                        'titles':'|'.join(listoftitlestoget),
                        'prop':'revisions',
                        'rvprop':'content|timestamp'
                        }
                        #print(mywiki, urldata)
                        therequest = api.APIRequest(mywiki, urldata)
                        #print('therequest check')
                        fullreq = therequest.querySimple()
                        if fullreq:
                            req = fullreq['query']
                            #print('got one req')
                            #print(req)
                            if 'normalized' in req:
                                #myprint('has normalized')
                                for normalised in req['normalized']:
                                    listname = normalised['from']
                                    newname = normalised['to']
                                    self.changes[newname] = self.changes[listname]
                                    del self.changes[listname]
                                    listoftitlestoget.pop(listname)
                                    listoftitlestoget.append(newname)
                            #myprint('after normalized')
                            #print(req)
                            for pageidtxt in req['pages']:
                                #print('pageidtxt',pageidtxt)
                                #for test in req['pages'][pageidtxt]:
                                    #print (test)
                                apage = req['pages'][pageidtxt]
                                #pageidint = int(apage)
                                #myprint('pageid',pageidint)
                                #myprint('pageid',type(apage))
                                #for test in apage:
                                    #print (test)
                                if int(pageidtxt) < 1:
                                    #print ('int(pageidtxt) < 1')
                                    #someone deleted it meanwhile
                                    #which means there are more recent changes
                                    ok = localdb.deleteLemma(apage['title'])
                                    #myprint('deleted=', ok)
                                else:
                                    #print ('int(pageidtxt) >= 1')
                                    #print ('len page[revisions]',type(apage['revisions']))
                                    #print ('int(pageidtxt) >= 1   2')
                                    newentry = db.DBRow(title = apage['title'],
                                    ns = apage['ns'],
                                    timestamp = apage['revisions'][0]['timestamp'],
                                    content = apage['revisions'][0]['*'],#rest are dummy values
                                    start = 0,
                                    charlen = 0
                                    )
                                    #print('newentry',newentry)
                                    #print(type(localdb))
                                    #print('conn', localdb.myconn)
                                    #print(str(localdb))
                                    ok = localdb.updateLemma(newentry)
                                    #myprint('updated', ok)
                                    newmaxts = max(newmaxts, apage['revisions'][0]['timestamp'])
                                #TODO: fill it later with a SELECT in db
                                #myprint('one to go 1')                                
                                del self.changes[apage['title']]
                                listoftitlestoget.remove(apage['title'])
                                #myprint('one to go 2')
                            #myprintstay('remaining:', len(self.changes))
                            self.jsondump()
                            #myprint('jsondumped')
                    #all done
                    #update the table
                    #siteinfo = mywiki.setSiteinfo()
                    #TODO:get latest info about nses

        except Exceptions as e:
            myprint(inspect.stack()[0][3],e)
            raise e

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

##################################################################################################################################################################
def checkIfThereIsANewerDump(project, latestdumpTS):
    '''Return if there is a newer Dump from the last downloaded.

    '''
    ok, thebz2link = LinkOfDump(project, numbered = False)
    if not ok:return False
    thesha1sumslink = thebz2link[:-len(PMCFILESTRING + '.bz2')] + '-sha1sums.txt '
    ok, tmpfname = dnfile(thesha1sumslink)
    #myprint('ok, tmpfname = dnfile(thesha1sumslink)',ok)
    if not ok:return False
    with open(tmpfname, mode='rt', encoding="utf-8") as f:
        for line in f.readlines():
            if line.strip() != '':#just grab the first non empty line and create a TS
                print('line',line.split(" "))
                myTS = list(filter(bool,line.split(" ")))[1].split('-')[1]
                print('ts from sha1',myTS, 'reported',latestdumpTS,"###",myTS[:8] , latestdumpTS[:8])
                return (myTS[:8] > latestdumpTS[:8])
    return False

def ExtractFrombz2(project, dumpspath, theTS, deleteoldfiles = False):
    dnpath = os.path.join(dumpspath,'dn')
    bz2fullname = os.path.join(dnpath, project + LPMCFILESTRING + '.bz2')
    dbfullname = os.path.join(dumpspath, project + LPMCFILESTRING + '.db')
    txtfullname = os.path.join(dumpspath, project + LPMCFILESTRING + '.txt')
    #TSfullname = os.path.join(dumpspath, project + LPMCFILESTRING + '.TS')
    if os.path.exists(bz2fullname):
        myprint('creating empty files...')
        ok = InitiateLocalFiles(bz2fullname, dbfullname, txtfullname, deleteoldfiles = deleteoldfiles)
        if not ok:
            return False, 'Something went wrong in: ' + inspect.stack()[0][3]
        listForDB = []
        #starttime = time.time()
        writtenbytes = 0
        #myprint('creating the txt file...')
        #print(DumpNames.bz2filename)
        siteurl = ''
        sitenses = ''
        try:
            myprint('reading bz2 and writing txts...')
            with open(txtfullname, 'wt') as ftxt:
                with xmldumpreader.XmlDump(bz2fullname) as myDump:
                    #print('reading from bz2 file...')
                    for entry in myDump.parse():
                        #listForDB.append((entry.title, entry.ns, str(ftxt.tell()), str(len(entry.text)),entry.timestamp))
                        listForDB.append((entry.title, entry.ns, ftxt.tell(), len(entry.text),entry.timestamp))
                        ftxt.write(entry.text + '\n')
                    dsiteinfo = myDump.getSiteInfo()
                    siteurl = urllib.parse.urljoin(dsiteinfo.base,'/')
                    sitenses = '\n'.join((key + '#' + dsiteinfo.namespaces[key]) for key in sorted(dsiteinfo.namespaces, key=int))
            myprint('                  ...DONE')
            #myprint('filling db, siteurl, sitenses...', siteurl, sitenses)
            ok = False
            with db.DB(dbfullname) as tmpdb:
                ok = tmpdb.fillemptydb(listForDB, theTS, siteurl, sitenses)
            if not ok:
                print( 'db not filled')
                return
            print( 'The 2 files created')
            print('deleting bz2...')
            os.remove(bz2fullname)
            #with open(TSfullname, 'wt') as ftxt:
                #ftxt.write(theTS)
            print('bz2 deleted')
            print('DONE creating files from bz2')
            return True
        except Exception as e:
            myprint(inspect.stack()[0][3],'Problem.')
            raise
    else:
        return False, 'bz2 file not found'
#TODO: change checkhash
def CreateLocalFilesFromNet(project, dumpspath, numbered = False, deleteoldbz2 = False, checkhash = False):
    dnlpath = os.path.join(dumpspath, 'dn')
    bz2saveas = os.path.join(dnlpath, project + LPMCFILESTRING + '.bz2')
    myprint('saveas',bz2saveas)
    #TODO: remove "checkhash = False" if problem fixed or provide in DownloadLatestDump another way to bypass it
    ok, theTS = DownloadLatestDump(project, dumpspath, numbered = numbered, removeold = deleteoldbz2, checkhash = checkhash)
    #myprint('bz2saveas ok',ok)
    if not ok:return False
    #we want older files deleted 
    return ExtractFrombz2(project, dumpspath, theTS, deleteoldfiles = True)

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

def DownloadLatestDump(project, dumpspath, numbered = False, removeold = False, checkhash = True):
    '''Download a dump.

    '''
    #digest can only be checked if original file name is known
    #latest is always changed. Only numbered remain the same.
    try:
        #myprint("1",inspect.stack()[0][3],'dumpspath=', dumpspath)
        #myprint(inspect.stack()[0][3],'*********************************************')
        #myprint("2",inspect.stack()[0][3],'project=', project)
        saveas = os.path.join(dumpspath, 'dn', project+ LPMCFILESTRING + '.bz2')
        ok, thebz2link = LinkOfDump(project, numbered)
        #myprint('thebz2link', thebz2link, 'saveas', saveas)
        if not ok: return False,''
        myprint(inspect.stack()[0][3],saveas)
        if os.path.exists(saveas):
            if removeold:
                try:os.remove(saveas)
                except Exception as e:
                    myprint('could not remove old dump', inspect.stack()[0][3])
                    return False,''
                ok, tmpfname = dnfile(thebz2link)
                if not ok: return False,''
                shutil.move(tmpfname, saveas)
            else:
                #myprint('An old dump exists. Use removeold attr to remove it.', inspect.stack()[0][3])
                #return False,''
                myprint('Keeping old bz2')
                pass
        else:#TODO: how to compact this?
            ok, tmpfname = dnfile(thebz2link)
            if not ok: return False,''
            shutil.move(tmpfname, saveas)

        thesha1sumslink = thebz2link[:-len(PMCFILESTRING + '.bz2')] + '-sha1sums.txt '
        myprint('tmpfname = dnfile(thesha1sumslink)',thesha1sumslink)
        ok, tmpfname = dnfile(thesha1sumslink)
        myprint('2 ok, tmpfname = dnfile(thesha1sumslink)',ok)
        if ok:
            with open(tmpfname, mode='rt', encoding="utf-8") as f:
                #myprint('sha1 opened')
                for line in f.readlines():
                    #myprint('sha1 line ', line)
                    
                    if checkhash:
                        
                        if PMCFILESTRING in line:
                            #myprint('sha1 found')
                            myprint('Checking sha1 hash...')
                            splitted = list(filter(bool,line.split(" ")))
                            mysha1 = splitted[0].strip()
                            myTS = splitted[1].split('-')[1]
                            return checksha1hash(saveas, mysha1), myTS
                    else:#just grab the first line and create a TS
                        if len(line.split(" "))>1:
                            print('line',line.split(" "))
                            #print('line',line.split(" ")[1])
                            myTS = line.strip().split(" ")[2].split('-')[1]
                            #myTS = list(filter(bool,line.split(" ")))[2].split('-')[1]
                            print('myTS',myTS)
                            return True, myTS
                myprint('sha1 NOT found')
    except Exception as e: myprint(inspect.stack()[0][3],e) #pass
    return False,''

def PageOfProjectLatestDumps(project):
    '''Return the URL of the page with all latest dumps for this project.'''
    ok, pagedata = dnpage(INDEXPAGEOFDUMPS)
    #print('_SetProjectLatestPage')
    if ok:
        relativelink = ''
        try:relativelink = re.search('(<a href.+'+project+'.+'+project+'</a>)',pagedata).group(0).split('"')[1]
        except Exception as e:return False,e.args

        if relativelink != '':
            thelink = urllib.parse.urljoin(WEBPAGEOFDUMPS, relativelink)
            return True, thelink
        else:
            myprint('=================PAGE:',INDEXPAGEOFDUMPS )
            myprint(pagedata)
            return False, 'No link found.'
    else:
        myprint('xm')
        return False, pagedata

def LinkOfDump (project, numbered = True):
    '''Return the URL of the latest pages-meta-current.xml.bz2 file'''
    if not numbered:
        return True, urllib.parse.urljoin(WEBPAGEOFDUMPS, project + '/latest/' + project + LPMCFILESTRING + '.bz2')
    ok, theprojectlink = PageOfProjectLatestDumps(project)
    if not ok:
        return False, 'Page of all dumps returned False'
    ok, pagedata = dnpage(theprojectlink)
    #myprint(inspect.stack()[0][3],ok, pagedata)
    if ok:
        relativelink = ''
        try:relativelink = re.search('(<a href.+' + project + '.+' + PMCFILESTRING + '.bz2' + '</a>)',pagedata).group(0).split('"')[1]
        except:pass
        if relativelink != '':
            #myprint('rel link',relativelink)
            thelink = urllib.parse.urljoin(pageurl, relativelink)
            #myprint('the link',thelink)
            return True, thelink
        else:
            return False, 'No link found.'
    else:
        myprint('xm...',inspect.stack()[0][3])
        return

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
        with wiki.Wiki('https://el.wiktionary.org/w/api.php') as mywiki:
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
    project = 'elwiktionary'
    #b = CreateLocalFilesFromNet(project,os.path.join(realfile_dir,'..','..','dumps'), numbered = False)
    #print('CreateLocalFilesFromNet returned:',b)
    #if not b: exit()

    try:
        b = os.path.join(realfile_dir,'..','..','dumps',project + '-latest-pages-meta-current.xml.db')
        t = os.path.join(realfile_dir,'..','..','dumps',project + '-latest-pages-meta-current.xml.txt')
        p = os.path.join(realfile_dir,'..','..','dumps')
        bz = os.path.join(realfile_dir,'..','..','dumps','dn',project + '-latest-pages-meta-current.xml.bz2')

        #myprint('b',b)
        #CreateLocalFilesFromNet(project,pathFromdbPath(b),checkhash = False)
        #b = Updater(os.path.join(realfile_dir,'..','..','dumps',project + '-latest-pages-meta-current.xml.db'))
        #b.checksmth('θάλασσα')
        #b.getAllChangedTitles()
        #b.updatefromjson()
        #b.getAllChanges()
        #CreateLocalFilesFromNet(project,p)
        #InitiateLocalFiles(bz, b, t, deleteoldfiles = True)
        u = Updater(b)
        u.getLatestDumpAndTitles(checkfornewer = False)
    except Exception as e:
        print(e)
