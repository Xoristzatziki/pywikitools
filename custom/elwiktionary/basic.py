#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import os, time, re , sys
import importlib.util

from collections import OrderedDict

PMCFILESTRING = '-pages-meta-current.xml'
LPMCFILESTRING = '-latest' + PMCFILESTRING

#Αρχίζει με = έχει κάποιο κείμενο, τελειώνει με ίδιο αριθμό = και ίσως με σκουπίδια
sectionsre = "(?P<AGROUP>=+)\s*?(?P<BGROUP>.+)\s*?(?P=AGROUP)(?P<CGROUP>.*)$"
#Αρχίζει με {{ και κλείνει με }}. Να έχουν αφαιρεθεί τα κενά στην αρχή και στο τέλος
sectionTFULLre = "(?P<TEMPLSTART>\{\{)(?P<TEMPLFULL>((?P<TEMPNAME>.*?)\|{1}(?P<PARAMS>.*))|(?P<TEMPNAMENOPARAMS>.*?))(?P<TEMPLEND>\}\})$"
translationsre = "(?P<STARTLINE>\{\{μτφ-αρχή.*\}\})\s*.*(?P<ENDLINE>\{\{μτφ-τέλος\}\})"
translinere =  '^([*]\s*?|<!--\s*?\*\s*?)\{\{(?P<LANGISO>.*?)\}\}\s*?:\s*?\{\{τ\|(?P=LANGISO)\|.*'

def test():
    print(__file__)

def getFixedTranslations(lemmatitle, lemmacontent, libpath):
    languages, parts, translationsODict, dbmdl = getBasics(libpath)
    #print('========translationsODict==============')
    #print(translationsODict)
    sections = getSections(lemmatitle, lemmacontent, languages, parts)
    translationtbls = []
    for s in sections:
        if sections[s]['title'] == 'μεταφράσεις':
            translationtbls.append(fixtNranslations(sections[s]['content'],translationsODict))
    return translationtbls

def hasLangSections(sections):
    #print('len(sections) 2',len(sections))
    #print('',sections[len(sections)-1])
    if len(sections) < 2:return False
    return  (sections[len(sections)-1]['langiso'] != '') 

def getSections(pagetitle, wikitext, languages, parts):
    '''Επιστρέφει πίνακα με τα περιεχόμενα όλων των ενοτήτων.
    Το κείμενο μπορεί να αναδημιουργηθεί χρησιμοποιώντας τα depth, originaltitle και content.
    depth: περιέχει τον αριθμό των = που χρησιμοποιεί ο τίτλος της ενότητας
    originaltitle: το ακριβές κείμενο μεταξύ των =
    content: το περιεχόμενο κάτω από τη γραμμή ενότητας
    βοηθητικά:
    title: τίτλος για την ενότητα
    langiso: το iso της γλώσσας στην οποία ανήκει η ενότητα
    ΠΡΟΣΟΧΗ !!! κρατάει το πρηγούμενο αν δεν βρει σωστό
    ispartofspeech: αν η ενότητα είναι γνωστό μέρος του λόγου
    garbage: πιθανά σκουπίδια.
    '''
    #try:
    #print(wikitext)
    splittedlines = wikitext.splitlines(False)
    #print('splittedlines',len(splittedlines))
    sections = {}
    xcounter = 0
    sections[0] = {'depth':1, 'originaltitleline':'', 'title': pagetitle, 'langiso':'', 'langname':'',
            'langhaswiki' : False, 'ispartofspeech' : False, 
            'titlelang' : '', 'content':'', 'garbage':'', 'mingarbage' : ''}
    lastlang = ''
    lastlangname = ''
    garbage = ''
    #minigarbage = ''
    headword = ''
    #print('len(splittedlines)',len(splittedlines))
    for line in splittedlines:
        g = re.match(sectionsre,line)
        ispartofspeech = False
        titlelang = ''
        if g:
            #print(g)
            xcounter += 1
            agroup = g.groupdict()['AGROUP']
            bgroup = g.groupdict()['BGROUP']
            cgroup = g.groupdict()['CGROUP']
            depth = len(agroup)
            title = bgroup.strip()
            originaltitleline = line
            garbage = cgroup
            thetemplate =''          
            if depth == 2:#probably: lang section or comments
                if len(bgroup) > 6:
                    possiblelang = bgroup[3:-3]
                    if possiblelang in languages:
                        #print('lastlang',lastlang)
                        lastlang = possiblelang
                        lastlangname = languages[possiblelang]['όνομα']
                        if languages[possiblelang]['έχει βικιλεξικό'] and possiblelang != 'el':
                            headword = "{{τ|" + possiblelang + "|{{PAGENAME}}}}"
                        else:
                            headword = "'''{{PAGENAME}}'''"
                    else:
                        #print('Λάθος γλώσσα ή ενότητα παραπομπών ή λάθος αριθμός = για την ενότητα', originaltitle)
                        garbage += str(xcounter) + ':Depth 2:'+ title + '\n'
                        headword = ''
                else:
                    #ίδιο με το σφάλμα στη γλώσσα
                    #print('ενότητα παραπομπών ή λάθος αριθμός = για την ενότητα', originaltitle)
                    garbage += str(xcounter) + ':Depth 2:'+ title + '\n'
                    headword = ''
            else:#Κεφαλίδα υποενότητας στην τελευταία γλώσσα ή ενότητα που βρήκαμε
                thematch = re.match(sectionTFULLre, title)
                #if pagetitle == 'μυτιλοτροφείο':
                    #print(thematch)
                    #print(thematch.groupdict())
                if thematch:
                    #print(thematch.groupdict())
                    if thematch.groupdict()['TEMPNAMENOPARAMS']:
                        thetemplate = thematch.groupdict()['TEMPNAMENOPARAMS'].strip()
                        theparamsstring = ''
                    elif thematch.groupdict()['TEMPNAME']:
                        thetemplate = thematch.groupdict()['TEMPNAME'].strip()
                        theparamsstring = thematch.groupdict()['PARAMS']
                        splitted = theparamsstring.split("|")
                        possiblelang = splitted[0]
                        if lastlang == possiblelang:
                            #Έχει ίδια γλώσσα
                            pass
                        else:
                            #Ή δεν έχει ίδια γλώσσα ή είναι κάτι άλλο με παραμέτρους(;)
                            #Αν έχει άλλη γνωστή γλώσσα είναι λάθος
                            if possiblelang in languages:
                                garbage += 'Διαφορά στη γλώσσα.' + '\n'
                            if thetemplate == 'ετυμολογία':
                                #ξεκινάει άλλη ετυμολόγηση;
                                pass
                    else:
                        #κενές αγκύλες ή κάποιο άλλο πρόβλημα
                        pass
                else:
                    #Δεν έχει πρότυπο ή έχει και σκουπίδια μετά το πρότυπο
                    #titlelang = lastlang
                    #TODO:έλεγχος τι άλλο είναι
                    pass
                ispartofspeech = (thetemplate in parts)
                title = thetemplate
            #print('section c', xcounter)
            sections[xcounter] = {'depth':depth, 'originaltitleline':originaltitleline, 'title':title, 'langiso':lastlang, 'langname':lastlangname,
                    'ispartofspeech' : ispartofspeech , 'content':''}
            if len(cgroup):
                    sections[0]['garbage'] += cgroup + '\n'
            #print(g)
        else:
            #print('ELSE')
            sections[xcounter]['content'] = sections[xcounter]['content'] + line  +  '\n'    
    #print('END')
    return sections

def fixonetable(thelineslist, translationsODict):
    garbage = []
    duplicates = []
    langnotinODict = []
    langfoundbutnotinODict = []
    #fixed = { 'fixed': translationsODict, 'garbage' : [], 'duplicates':[]}
    xcounter = 0
    for line in thelineslist:
        thematch = re.match(translinere, line.strip())
        if thematch:
            lang = thematch.groupdict()['LANGISO']
            if lang in translationsODict:
                #print('found lang',lang)
                xcounter += 1
                if translationsODict[lang] == '':
                    translationsODict[lang] = line.strip()
                else:
                    duplicates.append(line.strip())
            else:
                #TODO:Append to langfoundbutnotinODict if needed 
                langnotinODict.append(line.strip())
        else:
            #print('garbage 2', line)
            garbage.append(line.strip())
    if xcounter > 5:
        for lang in translationsODict:
            if translationsODict[lang] == '':
                translationsODict[lang] = '<!-- * {{' + lang + '}} : {{τ|' + lang + '|ΧΧΧ}} -->'
    return translationsODict, duplicates, langnotinODict, garbage

def fixtNranslations(thestring,translationsODict):
    alltranslsplitted = thestring.split('{{μτφ-αρχή')
    translationtables = []
    for transltbl in alltranslsplitted:
        spl = transltbl.split('{{μτφ-τέλος}}', maxsplit = 1 )
        if len(spl) > 0:
            #transl = spl[0].replace( '{{μτφ-μέση}}\n','')
            #print(spl[0])
            lines = spl[0].replace( '{{μτφ-μέση}}\n','').splitlines(False)
            #print('lines',lines)
            if len(lines):
                first = lines[0]
                #print('first',first)
                #print('lines[1:]',lines[1:])
                fixed, duplicates, langnotinODict, garbage = fixonetable(lines[1:],translationsODict)
                translationtables.append({'type' : 1, 'start' : first, 'lines' : fixed, 'duplicates' : duplicates, 'langnotinODict' : langnotinODict, 'garbage' : garbage})
            else:
                translationtables.append({'type' : 2, 'garbage' : lines})
            if len(spl)>1:
                translationtables.append({'type' : 3, 'garbage' : spl[1]})
        else:
            translationtables.append({'type' : 4, 'garbage' : transltbl})
    return translationtables

def recreatetable(onetable):
    newlines = []
    newlines.append( '{{μτφ-αρχή' + onetable['start']) 
    xcounter = 0
    middle, plus = divmod(len(onetable['lines']), 2)
    middlenum = middle + plus
    for lang in onetable['lines']:
        newlines.append (onetable['lines'][lang])
        xcounter += 1
        if xcounter == middlenum:
            newlines.append ( '{{μτφ-μέση}}') 
    newlines.append ('{{μτφ-τέλος}}')
    if len(onetable['duplicates'] ):
        #newlines.append (' ============================== duplicates ==============================')
        newlines.append ('\n'.join(onetable['duplicates']))
    if len(onetable['langnotinODict'] ):
        #newlines.append (' ============================== langnotinODict ==============================')
        newlines.append ('\n'.join(onetable['langnotinODict']))
    if len(onetable['garbage'] ):
        #newlines.append (' ============================== garbage ==============================')
        newlines.append ('\n'.join(onetable['garbage']))
    #print(' ============================== ALL ==============================')
    #print(newlines)
    #print('\n'.join(newlines))
    return '\n'.join(newlines)

def getNtranslFromString(thestring):
    transl = thestring.split('{{μτφ-αρχή}}\n')[1].split('{{μτφ-τέλος}}')[0]
    #print(transl)
    transl = transl.replace( '{{μτφ-μέση}}\n','')
    translationsNdict = OrderedDict()
    for line in transl.splitlines(False):
        #print(line)       
        thematch = re.match(translinere, line.strip())        
        translationsNdict[thematch.groupdict()['LANGISO']] =''
    #print('=====================================================================',translationsNdict)
    return translationsNdict

def getPartsFromString(thestring):
    '''Διάβασε τα μέρη του λόγου από αλφαριθμητικό.'''
    #langre = "^Languages\['(?P<LANG>.*)']\s*=\s*\{\s*name\s*'\s*(?P<LANGNAME>.+)'\s*,\s*cat\s*="
    parts = {}
    partre = "pos\['(?P<PART>.*)']\s*=\s*\{\s*\['link']\s*=\s*'(?P<PARTLINK>.+)'\s*,\s*\['κατηγορία']"
    splittedlines = thestring.splitlines()
    for line in splittedlines:
        thematch = re.match(partre, line)
        if thematch:
            #print(thematch.group('PART'))
            parts[thematch.group('PART')] = { 'link' : thematch.group('PARTLINK')}
    return parts

def getLanguagesFromString(thestring):
    '''Διάβασε τις γλώσσες από αλφαριθμητικό.'''
    #langre = "^Languages\['(?P<LANG>.*)']\s*=\s*\{\s*name\s*'\s*(?P<LANGNAME>.+)'\s*,\s*cat\s*="
    languages = {}
    langre = "Languages\['(?P<LANGISO>.*)']\s*=\s*\{\s*name\s*=\s*'\s*(?P<LANGNAME>.+)'\s*,\s*cat\s*=.*wikiExists\s*=\s*(?P<HASWIKI>.*)\s*}"
    splittedlines = thestring.splitlines()
    for line in splittedlines:
        thematch = re.match(langre, line)
        if thematch:
            #print(thematch.group('LANGNAME'))
            languages[thematch.group('LANGISO')] = { 'όνομα' : thematch.group('LANGNAME'), 'έχει βικιλεξικό' : (thematch.group('HASWIKI') == 'true')}
    return languages

def getBasicsAndPaths(libpath):
    projectfixpath, tail = os.path.split(os.path.realpath(__file__))
    #print(os.path.realpath(__file__))
    #print(projectfixpath)
    fixespath,projectname = os.path.split(projectfixpath)
    dumpspath, tail = os.path.split(fixespath)
    #print(dumpspath)
    wikIdbpath = os.path.join(dumpspath, 'elwiki' + LPMCFILESTRING + '.db')
    wikTdbpath = os.path.join(dumpspath, 'elwiktionary' + LPMCFILESTRING + '.db')
    dbmdl = importdbmodule(os.path.join(libpath,'db.py'))
    #print(wikTdbpath)
    #print(dbmdl)
    with dbmdl.DB(wikTdbpath) as wdb:
        #print('inside')
        languagesstring, ts = wdb.getLemmaContent('Module:Languages')
        #print('languagesstring',languagesstring)
        partsstring, ts = wdb.getLemmaContent('Module:PartOfSpeech')
        #print('partsstring',partsstring)
        Ntranslstring, ts = wdb.getLemmaContent('Βοήθεια:Γρήγορη δημιουργία/ουσ-')
        languages = getLanguagesFromString(languagesstring)
        parts = getPartsFromString(partsstring)
        #print('parts',parts)
        translationsODict = getNtranslFromString(Ntranslstring)
    return languages, parts, translationsODict, dumpspath, dbmdl
    

def getBasics(libpath):
    projectfixpath, tail = os.path.split(os.path.realpath(__file__))
    #print(os.path.realpath(__file__))
    #print(projectfixpath)
    fixespath,projectname = os.path.split(projectfixpath)
    dumpspath, tail = os.path.split(fixespath)
    print(dumpspath)
    wikIdbpath = os.path.join(dumpspath, 'elwiki' + LPMCFILESTRING + '.db')
    wikTdbpath = os.path.join(dumpspath, 'elwiktionary' + LPMCFILESTRING + '.db')
    dbmdl = importdbmodule(os.path.join(libpath,'db.py'))
    #print(wikTdbpath)
    #print(dbmdl)
    with dbmdl.DB(wikTdbpath) as wdb:
        print('inside')
        languagesstring, ts = wdb.getLemmaContent('Module:Languages')
        #print('languagesstring',languagesstring)
        partsstring, ts = wdb.getLemmaContent('Module:PartOfSpeech')
        Ntranslstring, ts = wdb.getLemmaContent('Βοήθεια:Γρήγορη δημιουργία/ουσ-')
        languages = getLanguagesFromString(languagesstring)
        parts = getPartsFromString(partsstring)
        #print('parts',parts)
        translationsODict = getNtranslFromString(Ntranslstring)
    return languages, parts, translationsODict, dbmdl

def importdbmodule(thedbmodulepath):
    print('trying import')
    spec = importlib.util.spec_from_file_location("db", thedbmodulepath)
    db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db)
    print('imported')
    return db


if __name__ == "__main__":
    '''Χρειάζεται στον ίδιο φάκελο τα αρχεία που θα χρησιμοποιηθούν.
    Languages (αντίγραφο του Module:Languages)
    μέρη του λόγου (αντίγραφο του Module:PartOfSpeech)
    αίμα (αντίγραφο του λήμματος αίμα)
    (ή όποιου άλλου λήμματος θέλουμε να ελέγξουμε).
    Μπορεί να κληθεί και από αλλού αλλά ...
    '''
    #realfile = os.path.realpath(__file__)
    #print(realfile)
    libpath = '/home/ilias/Λήψεις/Προγραμματισμός1/v.0.5.18/_lib'
    languages, parts, translationsODict, dumpspath, dbmdl = getBasicsAndPaths(libpath)
    #print(languages, parts)
    wikTdbpath = os.path.join(dumpspath, 'elwiktionary' + LPMCFILESTRING + '.db')
    #print('wikTdbpath',wikTdbpath)
    with dbmdl.DB(wikTdbpath) as wdb:
        #print('db opend',wdb)
        wdb.test()
        #print(wdb.myconn)
        #print(wdb.txtfile)
        #print(type(wbd.iterLemmas))
        try:
            #xcounter = 0
            with open('errorlangsection.log', 'wt',  encoding ='utf_8') as f:
                for entry in wdb.iterLemmas(ns=0):
                    #print('a lemma')
                    #print('a lemma',entry.title)
                    #print('a lemma', entry.content)
                    #print(parts)
                    #print(entry.isredirect)
                    #xcounter += 1
                    #print(xcounter,entry.title)
                    #if entry.title == 'δίκροτο':
                        #print('δίκροτο', entry.content)
                    if not entry.isredirect == 1:
                        sections = getSections(entry.title, entry.content, languages, parts)
                        #print('len(sections)',len(sections))
                        if not hasLangSections(sections):
                            print('no LangSections', entry.title)
                            f.write('* [[' + entry.title + ']]\n')
                    #else:
                        #print('good')
                print('END checking lang sections')
                    
        except Exception as e:
            print(e)
            raise e
