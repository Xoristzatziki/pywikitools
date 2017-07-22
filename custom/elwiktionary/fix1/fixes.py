#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import re

summary = 'προσθήκη ονομαΑ'
ns = 0

nameAre = '(ανδρικό\s*όνομα|ανδρικό\s*\[\[όνομα]])'

def test():
    print(__file__)

def fixthis(wikitext, languages, parts, basic):
    #print('inside')
    nameAAllre = nameAre + '|\[\[Κατηγορία:Ανδρικά ονόματα \('
    #print('inside 2')
    if '[[Κατηγορία:Ανδρικά ονόματα (ελληνικά)]]' in wikitext and '{{ονομαΑ}}' in wikitext:
        return wikitext.replace('[[Κατηγορία:Ανδρικά ονόματα (ελληνικά)]]', '').rstrip(), ''
    matched = re.search(nameAAllre, wikitext)
    #print('inside 3')
    if matched:
        #print('inside 4')
        sections = basic.getsections(wikitext, languages, parts)
        if sections[0]['garbage'] != '':
            print('HAS GARBAGE')
            return wikitext, sections[0]['garbage'] 
        #if '{{τ|en|Democritus}}' in wikitext:
            #print(sections)
        #print(sections)
        newsections, haschanges = fixthis2(sections, languages, parts)
        #print('haschanges', haschanges)
        newtext = newsections[0]['content']
        if haschanges:
            #μόνο αν έχει αλλαγές
            newsections = basic.fixseparators(newsections)
            newtext = newsections[0]['content'] 
            for xcounter in range(1, len(newsections)):
                depth = newsections[xcounter]['depth']
                newtext += "=" * depth + newsections[xcounter]['originaltitle'] + "=" * depth + '\n'
                newtext += newsections[xcounter]['content']
            newtext = newtext.rstrip()
            #print("return newtext, ''")
            return newtext, ''
    return wikitext, ''

def fixthis2(sections, languages, parts):
    categoriesnotfound = []
    haschanges = False
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
        newcontent = section['content']
        hasoldstyle = re.search(nameAre,section['content'])
        if hasoldstyle:
            #replace it, check category
            newcontent = re.sub(nameAre, repstring, section['content'])
            haschanges = True
            categoryre = '\[\[Κατηγορία:Ανδρικά ονόματα \(' + section['langname'] + '\)\|*?[^\]]*]]'
            hascategory = re.search(categoryre, newcontent)
            if hascategory:
                newcontent = re.sub(categoryre,'', newcontent)
            else:
                categoriesnotfound.append(categoryre)
            section['content'] = newcontent
    lastesection = sections[len(sections)-1]
    #αντικατέστησε τις κατηγορίες που δεν βρήκες μέσα στις ενότητες
    #και ίσως έχουν μπει στο τέλος
    for categorynotfound in categoriesnotfound:
        newcontent = re.sub(categorynotfound,'', lastesection['content'])
        if lastesection['content'] != newcontent:
            haschanges = True
            lastesection['content'] = newcontent
    #print('return sections')
    return sections, haschanges
