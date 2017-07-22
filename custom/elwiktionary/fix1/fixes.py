#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import re

summary = 'προσθήκη ονομαΑ'
ns = 0

nameAre = '(ανδρικό\s*όνομα|ανδρικό\s*\[\[όνομα]])'

def test():
    print(__file__)

def fixthis2(sections, languages, parts):
    categoriesnotfound = []
    #print('check one')
    for onesection in sections:
        #print(sections[onesection]['title'])
        section = sections[onesection]
        langiso = section['langiso']
        repstring = '{{ονομαΑ'
        if langiso != 'el':
            repstring += '|' + langiso
        basicstring = repstring
        repstring += '}}'
        newcontent = re.sub(nameAre, repstring, section['content'])
        if section['title'] == 'κύριο όνομα':
            if basicstring not in newcontent:
                #print('brhka ===========',  sections[0]['title'],section['langiso'] )
                newcontent = newcontent.rstrip() + '\n# '+ repstring + '\n\n'
                #print(section['content'])
        if section['content'] != newcontent:
            #category = '[[Κατηγορία:Ανδρικά ονόματα (' + section['langname'] + ')]]'
            categoryre = '\[\[Κατηγορία:Ανδρικά ονόματα \(' + section['langname'] + '\)\|*?[^\]]*]]'
            #print(onesection, categoryre)
            newcontent2 = re.sub(categoryre,'', newcontent)
            if newcontent2 == newcontent:
                categoriesnotfound.append(categoryre)
                #print('categoriesnotfound')
            else:
                newcontent = newcontent2
            #print('=========== new ==========')
            #print(newcontent)
            section['content'] = newcontent
    #print("len(sections)-1,'len(sections)-1'",len(sections)-1,'len(sections)-1')
    lastesection = sections[len(sections)-1]
    #αντικατέστησε τις κατηγορίες που δεν βρήκες μέσα στις ενότητες
    for categorynotfound in categoriesnotfound:
        oldcontent = lastesection['content']
        newcontent = re.sub(categorynotfound,'',oldcontent) 
        lastesection['content'] = newcontent
    #print('return sections')
    return sections

def fixthis(wikitext, languages, parts, basic):
    #print('inside')
    nameAAllre = nameAre + '|\[\[Κατηγορία:Ανδρικά ονόματα \('
    b = re.search(nameAAllre, wikitext)
    #print('inside 2')
    if '[[Κατηγορία:Ανδρικά ονόματα (ελληνικά)]]' in wikitext and '{{ονομαΑ}}' in wikitext:
        return wikitext.replace('[[Κατηγορία:Ανδρικά ονόματα (ελληνικά)]]', '').rstrip(), ''
    elif b:
        #print('found one')
        sections = basic.getsections(wikitext, languages, parts)
        
        if sections[0]['garbage'] != '':
            print('HAS GARBAGE')
            return wikitext, sections[0]['garbage'] 
        #if '{{τ|en|Democritus}}' in wikitext:
            #print(sections)
        #print(sections)
        newsections = fixthis2(sections, languages, parts)
        newsections = basic.fixseparators(newsections)
        newtext = newsections[0]['content'] 
        for xcounter in range(1,len(newsections)):
            depth = newsections[xcounter]['depth']
            newtext += "=" * depth + newsections[xcounter]['originaltitle'] + "=" * depth + '\n'
            newtext += newsections[xcounter]['content']
        newtext = newtext.rstrip()
        #print("return newtext, ''")
        return newtext, ''
    return wikitext, ''
