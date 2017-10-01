#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017

import os, time, re , sys
import importlib.util

from _lib.wikitools import wiki, user, page, api, category

PAGECHANGEDFROMOLD = 'Η σελίδα έχει τροποποιηθεί.'
CANTLOGIN = 'Δεν μπόρεσα να συνδεθώ.'
PAGEPROBLEM = 'Πρόβλημα με τη σελίδα.'
NOTLOGGEDIN = 'Δεν είναι συνδεδεμένος.'

SLEEPTIME = 8

MAXERRORS = 3

def remove_text(wikitext, text):
    pass

def remove_category_from_members(CP, categoryfulltitle, namespaces = None, username = None, password = None):
    #print(CP.dbstrings['site url'])
    summary = 'Αφαίρεση κατηγορίας ' + categoryfulltitle
    with wiki.Wiki(CP.dbstrings['site url'], httpuser = username, httppass = password) as wikiinst:
    #wikiinst = wiki.Wiki(CP.dbstrings['site url'], httpuser = username, httppass = password)
        if not wikiinst.isLoggedIn(username):
            print('not logged in. trying to login for first time...')
            ok = wikiinst.login(username = username, password = password)
            if not ok:
                print('not logged in')
                return False, CANTLOGIN
            print('logged in wiki')
        wikiinst.setAssert('user')
        categoryinst = category.Category(wikiinst, categoryfulltitle)
        errors = 0
        for alemmatitle in categoryinst.getAllMembersGen():
            print(alemmatitle, CP.dbstrings['site url'])
            pageinst = page.Page(wikiinst, title = alemmatitle)
            #print('got pageinst')
            oldwikitext = pageinst.getWikiText()
            #print('got oldwikitext')
            oldts = pageinst.lastedittime
            #print('got oldts')
            newtext = oldwikitext.replace('\n[[' + categoryfulltitle + ']]\n', '\n')
            if oldwikitext == newtext:
                newtext = oldwikitext.replace('\n:[[' + categoryfulltitle + ']]\n', '\n')
                #print('replaced 1')
            if oldwikitext == newtext:
                newtext = oldwikitext.replace('[[' + categoryfulltitle + ']]', '')
                #print('replaced 1')
            if oldwikitext != newtext:
                #print('has changes', 'trying to edit')
                ok, result = tryedit(wikiobj = wikiinst,
                                pageobj = pageinst,
                                newtext = newtext,
                                oldts = oldts,
                                summary = summary,
                                username = username,
                                password = password,
                                minor = True)
                print(alemmatitle, 'ok', result)
                if not ok:
                    print('not edited', 'increasing error count')
                    errors += 1
            else:
                print('no changes', 'increasing error count')
                errors += 1
            if errors > MAXERRORS:
                print(MAXERRORS, 'MAXERRORS reached')
                return
            print('sleeping for ',SLEEPTIME)
            time.sleep(SLEEPTIME)
    print('====== finished listing ======')

def tryedit(wikiobj, pageobj, newtext, oldts, summary, username = None, password = None, watchlist = 'watch', minor = False):
    if not wikiobj.isLoggedIn(username):
        return False, NOTLOGGEDIN
    ok = pageobj.edit(text = newtext,
                    summary = summary,
                    basetimestamp = oldts,
                    watchlist = watchlist,
                    minor = 1,
                    nocreate = 1
                    )
    if ok:
        return True,''
    else:
        return False, PAGEPROBLEM
