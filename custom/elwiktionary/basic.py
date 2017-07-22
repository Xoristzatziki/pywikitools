#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import re, os

sectionsre = "^(?P<AGROUP>=+)\s*?(?P<BGROUP>.+)\s*?(?P=AGROUP)(?P<CGROUP>.*)$"
translationsre = "(?P<STARTLINE>\{\{μτφ-αρχή.*\}\})\s*.*(?P<ENDLINE>\{\{μτφ-τέλος\}\})"

linere =  '(\*\s*?|\<--\s*?\*\s*?)\{\{(?P<LANGISO>)/}/}\s*?\:\s*?\{\{τ\|(?P=LANGISO)\|*.*'

def test():
    print(__file__)

#TODO
def sortonetable(content, languages, onlysort):
    splittedlines = content.splitlines()
    firstline = '{{μτφ-αρχή' + splittedlines[0]
    tablelines = []
    #tablesorted = False
    newcontent = ''
    if len(splittedlines)<2:
        return False,''
    for line in range(1,len(splittedlines)):
        thematch = re.match(linere, line)
        if thematch:
            if thematch('LANGISO') in languages:
                tablelines.append({'line':line, 'iso' : thematch('LANGISO'), 'sortname':languages[thematch('LANGISO')]['sortname']})
            else:
                 return False, ''
        elif line.strip() == '':
            pass
        elif line.startswith('{{μτφ-μέση}}'):
            pass
        else:
            return False, ''
    #TODO:check for duplicates
    newlist = sorted(tablelines, key=lambda k: k['sortname'])
    newlist = [x['line'] for x in newlist]
    insertplace = 1 + (len(newlist) // 2)
    newlist.insert(insertplace, '{{μτφ-μέση}}')
    newcontent = newlist.join('\n')
    return True, newcontent

#TODO:fix some of the errors in tables, like unknown iso
def sortlanguagesections(sections, languages, onlysort = True):
    langsections = [(k, sections[k]) for k in sections if sections[k]['depth'] == 2]
    doneatleastonesort = None
    for xcounter in range(len(sections)):
        if sections[xcounter]['title'] == 'μεταφράσεις':
            if sections[xcounter]['langiso'] != 'el':
                if onlysort:
                    return False, sections
                else:
                    #TODO: do not return, we may want to empty this section
                    #and return with the other (in el) sorted
                    return False, sections
            #else
            content = sections[xcounter]['content']
            newcontent = ''
            splitstarts = content.split('{{μτφ-αρχή')
            for splitted in splitstarts:
                if '{{μτφ-τέλος}}' in splitted:
                    splitend = splitted.split('{{μτφ-τέλος}}')
                    if len(splitend) > 2:
                        return False, sections
                    ok, tabletext = sortonetable(splitend[0], languages, onlysort)
                    if ok:
                        doneatleastonesort = True
                        newcontent += tabletext + '\n'
                        if len(splitend) == 2:
                            newcontent += splitend[1].rstrip() + '\n'
                    else:
                        return False, sections
                else:
                    #WARNING: full table may not end
                    newcontent += splitted
    #WARNING: we may have only one sort but not inserted in sections
    return doneatleastonesort, sections

def checksections(sections):
    minigarbage = sections[0]['minigarbage']
    pagetitle = sections[0]['title']
    for onesection in sections:
        section = sections[onesection]            
        if section['title'] == 'ετυμολογία':
            if not section['content'].startswith(":'''{{PAGENAME}}''' < "):
                 minigarbage += str(xcounter) + ': Μορφοποίηση έναρξης ετυμολογίας\n'
        if ispartofspeech:
            if headword != '' and headword not in section['content']:
                minigarbage += str(xcounter) + ': Δεν έχει ' + headword + ' (ή είναι λάθος) \n'
    sections[0]['minigarbage'] = minigarbage
    return sections



def getsections(pagetitle, wikitext, languages, parts):
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
    splittedlines = wikitext.splitlines(True)
    #print('splittedlines',len(splittedlines))
    sections = {}
    xcounter = 0
    sections[0] = {'depth':1, 'originaltitle':'', 'title': pagetitle, 'langiso':'', 'langname':'',
            'langhaswiki' : False, 'ispartofspeech' : False, 
            'titlelang' : '', 'content':'', 'garbage':'', 'mingarbage' : ''}
    lastlang = ''
    lastlangname = ''
    garbage = ''
    #minigarbage = ''
    headword = ''
    #print(len(splittedlines))
    for line in splittedlines:
        #g = re.match(sectionsre2,line)
        g = re.findall(sectionsre,line)
        ispartofspeech = False
        titlelang = ''
        if g:
            #print(g)
            xcounter += 1
            depth = len(g[0][0])
            title = g[0][1].strip()
            originaltitle = title
            garbage = g[0][2]
            
            if depth == 2:
                if len(g[0][1]) > 6:
                    possiblelang = g[0][1][3:-3]
                    if possiblelang in languages:
                        #print('lastlang',lastlang)
                        lastlang = possiblelang
                        lastlangname = languages[possiblelang]['όνομα']
                        if languages[possiblelang]['έχει βικιλεξικό'] and possiblelang != 'el':
                            headword = "{{τ|" + possiblelang + "|{{PAGENAME}}}}"
                        else:
                            headword = "'''{{PAGENAME}}'''"
                    else:
                        #print('Ανύπαρκτος κωδικός γλώσσας', originaltitle)
                        garbage += str(xcounter) + ':Depth 2:'+ title + '\n'
                        headword = ''
                        #title = 'ΣΦΑΛΜΑ ΤΙΤΛΟΥ ΕΝΟΤΗΤΑΣ'
                    #find lang
                else:
                    #print('Σφάλμα σε ενότητα γλώσσας', originaltitle)
                    garbage += str(xcounter) + ':Depth 2:'+ title + '\n'
                    #title = 'ΣΦΑΛΜΑ ΤΙΤΛΟΥ ΕΝΟΤΗΤΑΣ'
            else:
                if title.startswith('{{') and title.endswith('}}'):
                    title = title[2:-2]
                    if "|" in title:
                        splittedtitle = title.split("|")
                        title = splittedtitle[0]
                        possiblelang = splittedtitle[1]
                        if lastlang != possiblelang:
                            garbage += 'Διαφορά στη γλώσσα.' + '\n'
                        else:
                            #TODO:έλεγχος τι άλλο είναι
                            pass                            
                    else:
                        #titlelang = lastlang
                        #TODO:έλεγχος τι άλλο είναι
                        pass
                ispartofspeech = (title in parts)
            #print('section c', xcounter)
            sections[xcounter] = {'depth':depth, 'originaltitle':originaltitle, 'title':title, 'langiso':lastlang, 'langname':lastlangname,
                    'ispartofspeech' : ispartofspeech , 'titlelang' : '', 'content':''}
            if len(g) > 1:
                sections[xcounter]['garbage'] += g[1]
            #print(g)
        else:
            sections[xcounter]['content'] = sections[xcounter]['content'] + line        
    #for section in sections:
        #print(sections[section]['depth'],sections[section]['title'],sections[section]['ispartofspeech'],sections[section]['langiso'],
            #sections[section]['langname'],len(sections[section]['content']),len(sections[section]['garbage']) )
    if len(sections) < 2 or sections[len(sections)-1]['langiso'] == '':
        garbage += 'Δεν βρέθηκε σωστή ενότητα γλώσσας'
    #if garbage == '':
        #sections = checksections(sections)
        #ok, sections = sortlanguagesections(sections, languages)
    sections[0]['garbage'] = garbage
    #sections[0]['minigarbage'] = minigarbage
    return sections
    #except Exception as e:
        #raise e

def fixdecor(sections):
    if len(sections) > 2:
        pagetitle = sections[0]['title']
        hasel = False
        for xcounter in range(2, len(sections)):
            section = sections[xcounter]
            if section['title'] == 'προφορά':
                if '{{ήχος|' in section['content']:
                    soundre = '\{\{ήχος\|' + section['langiso'].capitalize() + '-' + pagetitle + '.ogg\|Ήχος\}\}'
                    soundre2 = '{{ήχος|' + section['langiso'] + '}}'
                    #minigarbage += str(xcounter) + ': Μορφοποίηση έναρξης ετυμολογίας\n'
                    #print(section['langiso'], soundre, soundre2)
                    section['content'] = re.sub(soundre, soundre2, section['content'])
            if section['depth'] == 2:
                if section['langiso'] == 'el' or section['langiso'] == 'grc' or section['langiso'] == 'gkm':
                    hasel = True
                if sections[xcounter-1]['langiso'] != section['langiso']: 
                    content = sections[xcounter-1]['content'].rstrip()
                    if not content.endswith('\n----') :
                        sections[xcounter-1]['content'] = content + '\n\n\n----\n\n'
            sections[xcounter-1]['content'] = sections[xcounter-1]['content'].rstrip() + '\n\n'
            if sections[xcounter-1]['content'] == '\n\n':sections[xcounter-1]['content'] = '\n'
        if hasel and ('{{κλείδα-ελλ}}' not in sections[len(sections)-1]['content']):
            sections[len(sections)-1]['content'] += '{{κλείδα-ελλ}}' + '\n'
    return sections

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

if __name__ == "__main__":
    '''Χρειάζεται στον ίδιο φάκελο τα αρχεία που θα χρησιμοποιηθούν.

    Languages (αντίγραφο του Module:Languages)
    μέρη του λόγου (αντίγραφο του Module:PartOfSpeech)
    αίμα (αντίγραφο του λήμματος αίμα)
    (ή όποιου άλλου λήμματος θέλουμε να ελέγξουμε).

    Μπορεί να κληθεί και από αλλού αλλά ...
    '''
    with open('Languages', mode='rt', encoding="utf-8") as f:
        b = f.read()
    langs = getLanguagesFromString(b)
    with open('μέρη του λόγου', mode='rt', encoding="utf-8") as f:
        b = f.read()
    parts = getPartsFromString(b)
    with open('test.lemma', mode='rt', encoding="utf-8") as f:
        b = f.read()
    try:
        sections = getsections(b, langs, parts)
        print('OK')
        sections = fixdecor(sections)
        print('OK 2')
    except Exception as e:
        raise e
