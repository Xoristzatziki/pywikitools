#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import os, time, re , sys
import importlib.util

if __name__ == "__main__":
    from wikitools import wiki, user, page, api
    import auxiliary
    import db
else:
    from . import auxiliary
    from . import db
    from .wikitools import wiki, page, api, user

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
        #self.db = None
        self.basic, self.fixes , self.paths = loadPathsAndLibs(project, dumpspath)
        self.project = project
        
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
                        #sections = self.basic.getsections(oldwikitext, languages, parts)
                        newtext, garbage = self.fixes.fixthis(oldwikitext, languages, parts, self.basic)
                        #print('newsections',newsections)
                        #print(lemma.title)
                        if garbage != '':
                            errorcounter += 1
                            self.writerrors(lemma.title + ':' + garbage[:50].replace('\n','⁋')  +  '\n')
                        elif newtext != oldwikitext:
                            print(lemma.title)
                            titlecounter += 1
                            #print(lemma.title,len(newsections))
                            ftitles.write(str(titlecounter) + ":" + lemma.title + '\n')
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
        with open(self.paths['log uploaded file'], 'wt+', encoding ='utf_8') as ftitles:
            ftitles.write(str(uploadcounter) +':' + line.strip() + '\n' )            

    def saverest(self, summary, restoftitles):
        if len(restoftitles):
            with open(self.paths['titles'], 'wt', encoding ='utf_8') as ftitles:
                ftitles.write('summary=' + summary + '\n')
                ftitles.write("\n".join(restoftitles))
        else:
            os.remove(self.paths['titles'])

    def logUploadError(self, summary, aline):
        if not os.path.exists(self.paths['upload errors file']):
            with open(self.paths['upload errors file'], 'wt', encoding ='utf_8') as ftitles:
                ftitles.write('summary=' + summary )
        with open(self.paths['upload errors file'], 'at+', encoding ='utf_8') as ftitles:
            ftitles.write('\n' + aline.rstrip())            

    def uploadfromlist(self, sleeptime = 2, maxuploads = 5):
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

    def tryedit(self, pagetitle, oldtext, newtext, summary, watchlist = 'watch'):
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
        if oldtext == wikitext:
            editlemma = thepage.edit(text = newtext,
                        summary = summary,
                        basetimestamp = ts,
                        watchlist = watchlist
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
    paths['basic.py'] = os.path.join(paths['project path'],'basic.py')
    paths['fixes.py'] = os.path.join(paths['project path'],'fixes.py')
    paths['dbfullpath'] = os.path.join(dumpspath,project + LPMCFILESTRING + '.db')
    paths['errors file'] = os.path.join(paths['project path'],'errors.txt')
    paths['upload errors file'] = os.path.join(paths['project path'],'uploaderrors.txt')
    paths['log uploaded file'] = os.path.join(paths['project path'],'uploaded.log')

    try:
        with db.DB(paths['dbfullpath']) as mydb:
            paths['siteurl'] = mydb.getSiteURL() + 'w/api.php'
        spec = importlib.util.spec_from_file_location("basic", paths['basic.py'])
        basic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(basic)
        spec = importlib.util.spec_from_file_location("fixes", paths['fixes.py'])
        fixes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixes)
        basic.test()
        return basic, fixes, paths
        #return paths
    except ImportError:
        return None, None, None

def testimport(project, dumpspath):
    paths = {}
    
    paths['project path'] = os.path.join(dumpspath,'fixdir',project)
    paths['pr dir'] = os.path.join(paths['project path'],'__init__.py')
    paths['new dir'] = os.path.join(paths['project path'],'new')
    paths['olds dir'] = os.path.join(paths['project path'],'olds')
    paths['basic.py'] = os.path.join(paths['project path'],'basic.py')
    paths['fixes.py'] = os.path.join(paths['project path'],'fixes.py')
    paths['errors file'] = os.path.join(paths['project path'],'erros.txt')
    
    #sys.path.append(os.path.join(os.path.dirname(dumpspath),project))
    print(dumpspath)
    for k in paths:
        print(k,paths[k])
    
    try:
        #spec = importlib.util.spec_from_file_location("module.name", "/path/to/file.py")
        #spec = importlib.util.spec_from_file_location("basic.py", paths['project path'])
        spec = importlib.util.spec_from_file_location(project, paths['project path'])
        #spec = importlib.util.spec_from_file_location(project, paths['pr dir'])
        pckg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pckg)
        #from pckg import basic
        #pckg.basic.test()
        pckg.basic.test()
        pckg.fixes.test()
        
    except ImportError:
        #sys.stderr.write("ERROR: missing python module: ")
        print("ERROR: missing python module: ", project)
        raise
    #print(basic.test())
    #print(fixes.test())

if __name__ == "__main__":
    realfile = os.path.realpath(__file__)
    realfile_dir = os.path.dirname(os.path.abspath(realfile))
    username =  'Tzatzbt'
    password = ''
    project = 'elwiktionary'
    dumpspath = os.path.join(realfile_dir, '..','dumps')
    test1 = CreateFixes(project,dumpspath)
    #test1.generaterelist()
    
