#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import os, time, re , sys
import importlib.util

def test():
    print(__file__)

PMCFILESTRING = '-pages-meta-current.xml'
LPMCFILESTRING = '-latest' + PMCFILESTRING

parts = ['antonimy',
'czytania',
'determinatywy',
'etymologia',
'frazeologia',
'hanja',
'hiperonimy',
'hiponimy',
'holonimy',
'klucz',
'kody',
'kolejność',
'kolokacje',
'kreski',
'meronimy',
'morfologia',
'odmiana',
'pochodne',
'pokrewne',
'przykłady',
'składnia',
'słowniki',
'synonimy',
'tłumaczenia',
'transkrypcja',
'transliteracja',
'uwagi',
'warianty',
'wymowa',
'zapis hieroglificzny',
'złożenia',
'znaczenia',
'znaczenia',
'źródła']
langre = re.compile("== (.*?) \(\{\{język (?P<LANGGROUP>.*?)(?P<DEFAULTSORTGROUP>\|.*?\}\}\)|\}\}\)) ==")
#print("\{\{(?P<SUBSECTIONNAME>" + "|".join(parts) + ")\}\}")
subsectionsre = re.compile("\{\{(?P<SUBSECTIONNAME>" + "|".join(parts) + ")\}\}")

odmiana1re = '\[\[Aneks:(?P<ODMIANAGROUP>.*?)(\|.*?\]\]|\]\])'

def getSections(pagetitle, wikitext):
    splittedlines = wikitext.splitlines(True)
    sections = {}
    xcounter = 0
    sections[0] = {'depth':1, 'title': pagetitle, 'lang':'', 'contentinline': '',
            'content':'', 'garbage':'', 'mingarbage' : ''}
    
    lastlang = ''
    garbage = ''
    content = ''
    sectioncounter = 0
    for line in splittedlines:
        r1 = re.match(langre, line)
        r2 = re.match(subsectionsre, line)
        title = ''
        content = ''
        contentinline = ''
        depth = 0
        if r1 or r2:
            sectioncounter += 1
            if r1:
                #lang section found
                #print('lang section found')
                lastlang = r1.groupdict()['LANGGROUP']
                #defaultsort = r1.groupdict()['DEFAULTSORTGROUP'][:-3]
                title = lastlang
                depth = 2
                sectioncounter += 1
            else:
                depth = 3
                title = r2.groupdict()['SUBSECTIONNAME']
                contentinline = line[len("{{" + title + "}}"):]
            sections[sectioncounter] = {'depth':depth, 'title': title,
                            'lang':lastlang,
                            'content':content,
                            'contentinline':contentinline}
        else:
            sections[sectioncounter]['content'] += line
    return sections

def fixoldodmiana(sections):
    for section in sections:
        asection = sections[section]
        if asection['lang'] == 'nowogrecki' and asection['title'] == 'odmiana':
            #, asection['contentinline']
            if asection['contentinline'] != '\n':
                asection['content'] = ":" + asection['contentinline'] + asection['content']
                asection['contentinline'] = '\n'

def appendtoodmianagroups(odmianagroups, sections):
    for section in sections:
        asection = sections[section]
        if asection['lang'] == 'nowogrecki' and asection['title'] == 'odmiana':
            #, asection['contentinline']
            #print('======')
            #print(asection['contentinline'])
            #print('------')
            #print(asection['content'])
            #print('######')
            
            if asection['contentinline'] != '\n':
                #print(len(asection['contentinline']))
                asection['content'] = ":" + asection['contentinline'] + asection['content']
                #asection['contentinline'] = '\n'
                #print(asection['content'])
                #print('######')
            g = re.findall(odmiana1re, asection['content'])
            if g:
                #print('found g',len(g))
                for onegoup in g:
                    #print("---------------------------",onegoup[0])
                    odmianagroup = onegoup[0].split("#")[0]
                    if odmianagroup not in odmianagroups:
                        odmianagroups.append(odmianagroup)
                        #print("----------------appended:",odmianagroup)
                    
                #print(g.groupdict())
                #print(g)


def getBasicsAndPaths(libpath):
    projectfixpath, tail = os.path.split(os.path.realpath(__file__))
    #print(os.path.realpath(__file__))
    #print(projectfixpath)
    fixespath,projectname = os.path.split(projectfixpath)
    dumpspath, tail = os.path.split(fixespath)
    #print(dumpspath)
    wikPldbpath = os.path.join(dumpspath, 'plwiktionary' + LPMCFILESTRING + '.db')
    wikEldbpath = os.path.join(dumpspath, 'elwiktionary' + LPMCFILESTRING + '.db')
    dbmdl = importdbmodule(os.path.join(libpath,'db.py'))
    #print(wikTdbpath)
    #print(dbmdl)
    return dumpspath, dbmdl, wikPldbpath, wikEldbpath

def importdbmodule(thedbmodulepath):
    print('trying import')
    spec = importlib.util.spec_from_file_location("db", thedbmodulepath)
    db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db)
    print('imported')
    return db

if __name__ == "__main__":
    #realfile = os.path.realpath(__file__)
    #print(realfile)
    libpath = '/home/ilias/Λήψεις/Προγραμματισμός1/v.0.5.18/_lib'
    dumpspath, dbmdl, wikPldbpath, wikEldbpath = getBasicsAndPaths(libpath)
    odmianagroups = []
    xcounter = 0
    with dbmdl.DB(wikPldbpath) as wdb:
        for entry in wdb.iterLemmas(ns=0):
            if "({{język nowogrecki" in entry.content:
                xcounter += 1
                print(xcounter)
                #print(entry.title)
                sections = getSections(entry.title, entry.content)
                #print('sections found')
                appendtoodmianagroups(odmianagroups, sections)
    print(odmianagroups)
    
    #with open('test.lemma', 'rt',  encoding ='utf_8') as f:
        #wikitext = f.read()
    #sections = getSections("test.lemma", wikitext)
    #for section in sorted(sections, reverse=True):
        #asection = sections[section]
        #print(asection['depth'], asection['lang'], asection['title'], asection['contentinline'])
