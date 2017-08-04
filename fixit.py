#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import os, time, re , sys
import importlib.util
import inspect

if __name__ == "__main__":
    from wikitools import wiki, user, page, api
    import db
else:
    from . import db
    from .wikitools import wiki, page, api, user, category

PMCFILESTRING = '-pages-meta-current.xml'
LPMCFILESTRING = '-latest' + PMCFILESTRING

PAGECHANGEDFROMOLD = 'Η σελίδα έχει τροποποιηθεί'
CANTLOGIN = 'Δεν μπόρεσα να συνδεθώ.'

class FixDict:
    def __init__(self):
        self.ns = None
        self.summary = ''
        self.refrom = ''
        self.reto = ''
        self.ok = False

def listFromCategory(project, dumpspath, categorytitle, namespaces = None, username = None, password = None):
    mdlfixes, paths = loadPathsAndLibs(project, dumpspath)
    site = wiki.Wiki(paths['siteurl'], username, password)
    c = category.Category(site, categorytitle)
    titles = c.getAllMembers(namespaces)
    with open(paths['list'], 'wt', encoding ='utf_8') as ftitles:
        ftitles.write('\n'.join(titles))
        print('titles written')    

class CreateFixes:
    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        print('Exiting CreateFixes...')
        return True

    def __str__(self):
        output = 'Not yet'
        #if self.wiki:
            #output = 'using:' + self.wiki['wikiid']
        #else:
            #output = 'NOT connected:' + self.apibase + ":"
        return output

    def __repr__(self):
        output = 'Not yet'
        #if self.wiki:
            #output = 'using:' + self.wiki['wikiid']
        #else:
            #output = 'NOT connected:' + self.apibase + ":"
        return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(output)+">"

    def __init__(self, project, dumpspath):
        self.fixes, self.paths = loadPathsAndLibs(project, dumpspath)
        print(self.fixes,'self.fixes')

    def checkit(self):
        print('trying')
        print(__file__)
        b = inspect.getfile(db)
        print(b)
        ok = self.fixes.fixthis(b)

    def appendError(self, aline):
        with open(self.paths['errors file'], 'at+', encoding ='utf_8') as f:
            f.write(aline)
            print('error loged...')

    def appendFixesData(self, oldtext, newtext):        
        #print(os.path.join(self.paths['olds dir'], str(self.)))
        with open(os.path.join(self.paths['olds dir'], str(self.titlecounter)), 'wt', encoding ='utf_8') as f:
            f.write(oldtext)
        with open(os.path.join(self.paths['new dir'], str(self.titlecounter)), 'wt', encoding ='utf_8') as f:
            f.write(newtext)
        #print('data written')
        #ftitles.write(str(thenum) + ":" + thetitle + '\n')

    def tryFixing(self, pagetitle, oldwikitext):
        newtext, garbage = self.fixes.fixthis(pagetitle, oldwikitext)
        #print(newtext == oldwikitext)
        #print('lens', len(newtext), len(garbage))
        if garbage != '':
            self.errorcounter += 1
            self.appendError(pagetitle + ':' + garbage[:50].replace('\n','⁋')  +  '\n')
            return False                   
        elif newtext != oldwikitext:
            self.titlecounter += 1
            #print('appending fixes, fixedcounter=',self.titlecounter)
            self.appendFixesData( oldwikitext, newtext)
            return True
        return None

    def getPageTitles(self, dummy = None):
        #print('in generator of getPageTitles')
        with open(self.paths['list'], 'rt', encoding ='utf_8') as f:
            #print('in generator of getPageTitles, list opened.')
            for line in f.readlines():
                #print('in generator of getPageTitles, yielding')
                yield line.strip()

    def fixthem(self, fromlist, namespace = None, stopcounter = -1):
        print('in fixthem')
        with db.DB(self.paths['dbfullpath']) as mydb:
            print('in fixthem db')
            self.titlecounter = 0
            self.errorcounter = 0
            with open(self.paths['titles'], 'wt', encoding ='utf_8') as ftitles:
                print('in fixthem titles opened.')
                ftitles.write("summary=" + self.fixes.summary + '\n')
                if fromlist:
                    #print('fromlist')
                    thegenerator = self.getPageTitles
                else:
                    thegenerator = mydb.iterTitles
                #print('generator found')
                for pagetitle in thegenerator(namespace):
                    print('pagetitle:',pagetitle)
                    if self.titlecounter == stopcounter:
                        print(self.errorcounter, 'errorcounter')
                        print('stopcounter found, exiting fixes.')
                        return
                    #print('getting content')
                    oldwikitext, thets = mydb.getLemmaContent(pagetitle)
                    #print('got content')
                    ok = self.tryFixing(pagetitle, oldwikitext)
                    #print(ok,'ok')
                    if ok == True:
                        ftitles.write(str(self.titlecounter) + ":" + pagetitle + '\n')
                #print('generated finished')
            print('closed:',paths['titles'])
        print('exited db')

def clearFixesPaths(thepaths):
    pass

def appendError(thepaths):
    with open(thepaths['errors file'], 'at+', encoding ='utf_8') as f:
        f.write(comment)
        print('error loged...')

def appendFixesData(thepaths,thenum, thetitle, oldtext, newtext, ftitles):
    with open(os.path.join(thepaths['olds dir'], str(num)), 'wt', encoding ='utf_8') as f:
        f.write(oldtext)
    with open(os.path.join(thepaths['new dir'], str(num)), 'wt', encoding ='utf_8') as f:
        f.write(newtext)
    ftitles.write(str(thenum) + ":" + thetitle + '\n')

def fixFromGenerator(project, dumpspath, thegenerator, stopcounter = -1):
    mdlfixes, paths = loadPathsAndLibs(project, dumpspath)
    with db.DB(paths['dbfullpath']) as mydb:
        titlecounter = 0
        errorcounter = 0
        with open(paths['titles'], 'wt', encoding ='utf_8') as ftitles:
            ftitles.write("summary=" + mdlfixes.summary + '\n')
            for pagetitle in thegenerator:
                if titlecounter == stopcounter:
                    print(errorcounter, 'errorcounter')
                    print('stopcounter found, exiting fixes.')
                    return
                oldwikitext, thets = mydb.getLemmaContent(title)
                newtext, garbage = fixes.fixthis(pagetitle, oldwikitext)
                if garbage != '':
                    errorcounter += 1
                    appendError(pagetitle + ':' + garbage[:50].replace('\n','⁋')  +  '\n')                    
                elif newtext != oldwikitext:
                    titlecounter += 1
                    appendFixesData(paths, titlecounter, pagetitle, oldwikitext, newtext, ftitles)
            print('generated finished')
        print('closed:',paths['titles'])
    print('exited db')

class CreateFixes2:
    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        print('Exiting CreateFixes...')
        return True

    def __str__(self):
        output = 'Not yet'
        #if self.wiki:
            #output = 'using:' + self.wiki['wikiid']
        #else:
            #output = 'NOT connected:' + self.apibase + ":"
        return output

    def __repr__(self):
        output = 'Not yet'
        #if self.wiki:
            #output = 'using:' + self.wiki['wikiid']
        #else:
            #output = 'NOT connected:' + self.apibase + ":"
        return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(output)+">"

    def __init__(self, project, dumpspath):
        #self.db = None
        self.basic, self.fixes , self.paths = loadPathsAndLibs(project, dumpspath)
        self.project = project
        self.wiki = wiki.Wiki(self.paths['siteurl'])
        if self.paths:            
            self.test()
            #self.db = db.DB(self.paths['dbfullpath'])

    def test(self):
        self.basic.test()
        print(self.fixes.ns)

    def writefiles(self,num,oldtext,newtext):
        with open(os.path.join(self.paths['olds dir'], str(num)), 'wt', encoding ='utf_8') as f:
            f.write(oldtext)
        with open(os.path.join(self.paths['new dir'], str(num)), 'wt', encoding ='utf_8') as f:
            f.write(newtext)

    def writerrors(self, comment):
        with open(self.paths['errors file'], 'at+', encoding ='utf_8') as f:
            f.write(comment)

    def deleteoldtitles(self):
        olddir = os.getcwd()
        ok = False
        try:
            if not os.path.exists(self.paths['olds dir']):
                os.mkdir(self.paths['olds dir'])
            if os.path.isdir(self.paths['olds dir']):
                os.chdir(self.paths['olds dir'])
                b = [os.remove(f) for f in os.listdir()]
            #print('old removed')
            if not os.path.exists(self.paths['new dir']):
                os.mkdir(self.paths['new dir'])
            if os.path.isdir(self.paths['new dir']):
                os.chdir(self.paths['new dir'])
                b = [os.remove(f) for f in os.listdir()]
            #print('new removed')
            if os.path.exists(self.paths['errors file']):
                os.remove(self.paths['errors file'])
            if os.path.exists(self.paths['upload errors file']):
                os.remove(self.paths['upload errors file'])
            ok = True
        finally:
             os.chdir(olddir)
             #print('back to old dir.')
             return ok

    def generaterelistfromcategory(self, categorytitle, stopcounter = -1):
        print('generaterelistfromcategory', categorytitle)
        #self.wiki = wiki.Wiki(self.paths['siteurl'])
        #print(category.__file__)
        print(type(category))
        print('self.wiki',self.wiki)
        
        c = category.Category(self.wiki ,categorytitle)
        print(c)
        titles = c.getAllMembers( )
        #with db.DB(self.paths['dbfullpath']) as mydb:
            #titles = []
        print(len(titles), titles[0], titles[1])
        with open(self.paths['list'], 'wt', encoding ='utf_8') as ftitles:
            ftitles.write('\n'.join(titles))
            print('titles written')
        self.generaterelistfromlist()

    def generaterelistfromlist(self, stopcounter = -1):
        self.deleteoldtitles()
        errorcounter = 0
        print('generaterelistfromlist enter')
        self.basic.test()
        self.fixes.test(self.basic)
        with open(self.paths['list'], 'rt', encoding ='utf_8') as f:
            alltitles = f.readlines(False)
        print('generaterelistfromlist len list',len(alltitles))
        languages = {}
        parts = {}
        with db.DB(self.paths['dbfullpath']) as mydb:
            if self.project =='elwiktionary':
                thetext, thets = mydb.getLemmaContent('Module:Languages')
                languages = self.basic.getLanguagesFromString(thetext)
                thetext, thets = mydb.getLemmaContent('Module:PartOfSpeech')
                parts = self.basic.getPartsFromString(thetext)

            titlecounter = 0
            with open(self.paths['titles'], 'wt', encoding ='utf_8') as ftitles:
                ftitles.write("summary=" + self.fixes.summary + '\n')
                for title in alltitles:
                    if titlecounter == stopcounter:
                        if titlecounter == stopcounter:
                            print(errorcounter, 'errorcounter')
                            print('stopcounter found, exiting fixes.')
                            return
                    title = title.rstrip()
                    if title:
                        #print(title)
                        #print(languages,parts)
                        oldwikitext, thets = mydb.getLemmaContent(title)
                        #print('oldwikitext title, len:',title, len(oldwikitext))
                        #print('oldwikitext title:',oldwikitext)
                        #print('type(self.fixes.fixthis)',type(self.fixes.fixthis))
                        
                        #newtext, garbage = self.fixes.fixthis(title, oldwikitext, languages, parts, self.basic)
                        #newtext, garbage = self.fixes.fixthis4(title = title, wikitext = oldwikitext, languages = languages, parts = parts)#, basic = self.basic)
                        newtext, garbage = self.fixes.fixthis5(title= title, wikitext= oldwikitext, languages = languages, parts = parts, basic = self.basic)
                        #garbage = ''
                        #newtext, garbage = self.fixes.fixthis3( oldwikitext,self.basic)
                        #print('newtext:',len(newtext))
                        #print('garbage',garbage)
                        if garbage != '':
                            errorcounter += 1
                            self.writerrors(title + ':' + garbage[:50].replace('\n','⁋')  +  '\n')
                        elif newtext != oldwikitext:
                            #print('======================================lemma.title',title)
                            titlecounter += 1
                            #print(lemma.title,len(newsections))
                            ftitles.write(str(titlecounter) + ":" + title + '\n')
                            self.writefiles(titlecounter, oldwikitext, newtext)
        print('end errorcounter:', errorcounter)
        print('finished all fixes.')
                

    def generaterelistfromdb(self, stopcounter = -1):
        #print(self.paths['olds dir'])
        #print(len(os.listdir(self.paths['olds dir'])))
        self.deleteoldtitles()
        errorcounter = 0 
        if self.fixes.ns == 0:
            with db.DB(self.paths['dbfullpath']) as mydb:
                #print('db opened')
                #print(mydb)
                thetext, thets = mydb.getLemmaContent('Module:Languages')
                #print(thetext)
                languages = self.basic.getLanguagesFromString(thetext) 
                thetext, thets = mydb.getLemmaContent('Module:PartOfSpeech')
                parts = self.basic.getPartsFromString(thetext)
                #print(thetext)
                #print(self.paths['titles'])
                #print(parts)
                titlecounter = 0

                with open(self.paths['titles'], 'wt', encoding ='utf_8') as ftitles:
                    #print('titles opened')
                    ftitles.write("summary=" + self.fixes.summary + '\n')
                    for lemma in mydb.iterLemmas(ns = 0):
                        
                        #sys.stdout.flush()
                        #sys.stderr.write(lemma.title)
                        if titlecounter == stopcounter:
                            print(errorcounter, 'errorcounter')
                            print('stopcounter found, exiting fixes.')
                            return
                        #print(lemma)
                        oldwikitext = lemma.content
                        pagetitle = lemma.title.rstrip()
                        #sections = self.basic.getsections(oldwikitext, languages, parts)
                        newtext, garbage = self.fixes.fixthis(pagetitle, oldwikitext, languages, parts, self.basic)
                        #print('newsections',newsections)
                        #print(lemma.title)
                        if garbage != '':
                            errorcounter += 1
                            self.writerrors(pagetitle + ':' + garbage[:50].replace('\n','⁋')  +  '\n')
                        elif newtext != oldwikitext:
                            print(lemma.title)
                            titlecounter += 1
                            #print(lemma.title,len(newsections))
                            ftitles.write(str(titlecounter) + ":" + pagetitle + '\n')
                            self.writefiles(titlecounter, oldwikitext, newtext)
        print('errorcounter:', errorcounter)
        print('finished all fixes.')

class UploadFixes:
    '''Encapsulate all edits to a project.'''
    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        if self.wiki:
            self.wiki.logout()
        print('Exiting UploadFixes...')
        return True

    def __str__(self):
        if self.wiki:
            output = 'using:' + self.wiki['wikiid']
        else:
            output = 'NOT connected:' + self.apibase + ":"
        return output

    def __repr__(self):
        if self.wiki:
            output = 'using:' + self.wiki['wikiid']
        else:
            output = 'NOT connected:' + self.apibase + ":"
        return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(output)+">"

    def __init__(self, project, dumpspath, username = '', password = ''):
        self.basic, self.fixes , self.paths = loadPathsAndLibs(project, dumpspath)
        self.project = project
        self.wiki = wiki.Wiki(self.paths['siteurl'])
        self.username = username
        self.password = password
        if self.paths:            
            self.test()
        print('UploadFixes initilised')

    def test(self):
        self.basic.test()
        print(self.fixes.ns)

    def logUploaded(self, uploadcounter,line):
        with open(self.paths['log uploaded file'], 'at+', encoding ='utf_8') as ftitles:
            ftitles.write(str(uploadcounter) +':' + line.strip() + '\n' )            

    def saverest(self, summary, restoftitles):
        if len(restoftitles):
            with open(self.paths['titles'], 'wt', encoding ='utf_8') as ftitles:
                ftitles.write('summary=' + summary + '\n')
                ftitles.write("".join(restoftitles))
        else:
            os.remove(self.paths['titles'])

    def logUploadError(self, summary, aline):
        if not os.path.exists(self.paths['upload errors file']):
            with open(self.paths['upload errors file'], 'wt', encoding ='utf_8') as ftitles:
                ftitles.write('summary=' + summary.rstrip() )
        with open(self.paths['upload errors file'], 'at+', encoding ='utf_8') as ftitles:
            ftitles.write('\n' + aline.rstrip())            

    def uploadfromlist(self, sleeptime = 2, maxuploads = 5, minor = False):
        with open(self.paths['titles'], 'rt', encoding ='utf_8') as ftitles:
            alllines = ftitles.readlines()
        if not alllines[0].startswith('summary='):
            return False, "No summary"
        summary = alllines[0][len('summary='):]
        print(summary)
        del alllines[0]
        uploadcounter = 0
        while True:
            print('sleeping for ', sleeptime, 'seconds')
            time.sleep(sleeptime)
            if len(alllines) < 1 or (uploadcounter >= maxuploads):
                self.saverest(summary, alllines)
                return True
            #if uploadcounter >= maxuploads:
                #self.saverest(summary,alllines)
                #return True
            nexttitlesplit = alllines[0].split(":",maxsplit =1)
            num = nexttitlesplit[0]
            pagetitle = nexttitlesplit[1].strip()
            with open(os.path.join(self.paths['olds dir'],num), 'rt', encoding ='utf_8') as f:
                oldtext = f.read()
            with open(os.path.join(self.paths['new dir'],num), 'rt', encoding ='utf_8') as f:
                newtext = f.read()
            #print('we have the page',pagetitle, len(oldtext), len(newtext), summary)
            ok, comment = self.tryedit(pagetitle, oldtext, newtext, summary)
            if ok:
                #print('succeded',pagetitle)
                os.remove(os.path.join(self.paths['olds dir'],num))
                os.remove(os.path.join(self.paths['new dir'],num))
                uploadcounter += 1
                self.logUploaded(uploadcounter,alllines[0])
                del alllines[0]
                self.saverest(summary, alllines)
            else:
                if comment == CANTLOGIN:
                    print(CANTLOGIN)
                    return False
                #print('unsuccefull',pagetitle)
                if comment == PAGECHANGEDFROMOLD:
                    print(PAGECHANGEDFROMOLD)
                self.logUploadError(summary, alllines[0])
                del alllines[0]
        #return True

    #TODO:add minor
    def tryedit(self, pagetitle, oldtext, newtext, summary, watchlist = 'watch', minor = False):
        #print('in tryedit', pagetitle)
        #print('self.wiki', self.wiki)
        #print('self.username', self.username)
        if not self.wiki.isLoggedIn(self.username):
            print('not logged in. trying to login...')
            print("self.username, self.password",self.username, self.password)
            print('self.wiki',self.wiki)
            ok = self.wiki.login(self.username, self.password)
            if not ok:
                print('not logged in')
                return False, CANTLOGIN
        print('in tryedit 2', pagetitle)
        thepage = page.Page(self.wiki, pagetitle)
        wikitext = thepage.getWikiText()
        ts = thepage.lastedittime
        print('ts',ts)
        #minor = basic.fixes.minor
        #print('minor',minor)
        if oldtext == wikitext:
            editlemma = thepage.edit(text = newtext,
                        summary = summary,
                        basetimestamp = ts,
                        watchlist = watchlist,
                        minor = 1
                        )
            return True,''
            #print('editlemma',editlemma)
        print('oldtext >< wikitext')
        return False, PAGECHANGEDFROMOLD

def loadPathsAndLibs(project, dumpspath):
    paths = {}

    paths['project path'] = os.path.join(dumpspath,'fixdir',project)
    paths['titles'] = os.path.join(paths['project path'],'titles')
    paths['new dir'] = os.path.join(paths['project path'],'new')
    paths['olds dir'] = os.path.join(paths['project path'],'olds')
    paths['fixes.py'] = os.path.join(paths['project path'],'fixes.py')
    paths['dbfullpath'] = os.path.join(dumpspath,project + LPMCFILESTRING + '.db')
    paths['errors file'] = os.path.join(paths['project path'],'errors.txt')
    paths['upload errors file'] = os.path.join(paths['project path'],'uploaderrors.txt')
    paths['log uploaded file'] = os.path.join(paths['project path'],'uploaded.log')
    paths['list'] = os.path.join(paths['project path'],'listforfixes')
    try:
        with db.DB(paths['dbfullpath']) as mydb:
            paths['siteurl'] = mydb.getSiteURL() 
        spec = importlib.util.spec_from_file_location("fixes", paths['fixes.py'])
        fixes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixes)
        return fixes, paths
        #return paths
    except ImportError:
        return None, None, None


if __name__ == "__main__":
    realfile = os.path.realpath(__file__)
    realfile_dir = os.path.dirname(os.path.abspath(realfile))
    username =  'Tzatzbt'
    password = ''
    #project = 'elwiktionary'
    project = 'elwiki'
    dumpspath = os.path.join(realfile_dir, '../..','dumps')
    try:
        test1 = CreateFixes(project,dumpspath)
        #test1.generaterelistfromdb()
        test1.generaterelistfromlist()
    except Exception as e:
        raise e
