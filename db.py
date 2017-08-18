#!/usr/bin/python3
#Δημιουργήθηκε από τον Xoristzatziki στο el.wiktionary.org
#2017
import os, sys
import sqlite3
import inspect

#try:
    #from . import auxiliary
#except:
    #import auxiliary

#myprint = auxiliary.myprint
#getnonZtime = auxiliary.getnonZtime
def getnonZtime(whichZtime):
    '''Return a TS in format YYYYMMDDHHMMSS'''
    if 'Z' in whichZtime:
        return whichZtime[:4] + whichZtime[5:7] + whichZtime[8:10] + whichZtime[11:13] + whichZtime[14:16] + whichZtime[17:19]
    else:
        #return as is, not a Z time
        return whichZtime

class DBRow:
    def __init__(self,title,ns,start,charlen,timestamp,content,isredirect):
        self.title = title
        self.ns = ns
        self.start = start
        self.charlen = charlen
        self.timestamp = timestamp
        self.content = content
        self.isredirect = isredirect
        #TODO?: if worth add these?
        #self.id = id
        #self.username = username.strip()
        #self.ipedit = ipedit
        #self.revisionid = revisionid
        #self.comment = comment


class DB:
    '''Encapsulate all comunication with the DB.'''
    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        if self.myconn != None:
            self.myconn.close()
        if self.txtfile != None:
            self.txtfile.close()
        return True

    def __str__(self):
        if self.myconn:
            output = 'connected to:' + self.dbfilename + ' and isolation_level:' + 'None' if self.myconn.isolation_level == None else self.myconn.isolation_level
        else:
            output = 'NOT connected to:' + self.dbfilename
        return output

    def __repr__(self):
        if self.myconn:
            output = 'connected to:' + self.dbfilename + ' and isolation_level:' + 'None' if self.myconn.isolation_level == None else self.myconn.isolation_level
        else:
            output = 'NOT connected to:' + self.dbfilename
        return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(output)+">"

    def __init__(self, dbfile, txtfile = None):
        self.dbfilename = os.path.abspath(dbfile)
        if txtfile:
            self.txtfilename = os.path.abspath(txtfile)
        else:
            self.txtfilename = dbfile[:-len('.db')] + '.txt'
        self.myconn = None
        self.txtfile = None
        #myprint( inspect.stack()[0][3],'self.txtfilename',self.txtfilename)
        if os.path.exists(self.dbfilename):
            self.myconn = sqlite3.connect(self.dbfilename, isolation_level = None)
            self.myconn.row_factory = sqlite3.Row
            #print('connected')
        if os.path.exists(self.txtfilename):
            #myprint( inspect.stack()[0][3],'file txt exists')
            self.txtfile = open(self.txtfilename,'r+t', encoding="utf-8")
            #myprint( inspect.stack()[0][3],'file txt opened')

    def test(self):
        print('DB TEST')

    def createAnEmptyDB(self):
        try:
            if os.path.exists(self.dbfilename):
                os.remove(self.dbfilename)
                print('old db deleted')
                time.sleep(2)
            with sqlite3.connect(self.dbfilename, isolation_level = 'EXCLUSIVE' ) as conn:
            #conn = sqlite3.connect(dbfilename)#, isolation_level = 'EXCLUSIVE' )
                conn.execute('''CREATE TABLE maintbl
                         (lemma text NOT NULL,
                         lns INTEGER, lredirect INTEGER, lstart INTEGER, lcharlen INTEGER, ltimestamp text);''')
                conn.commit()
                conn.execute('''CREATE TABLE attribstbl
                         (atimestamp text NOT NULL, adumpTS text NOT NULL, asiteurl text NOT NULL, asitenses text NOT NULL);''')
                conn.commit()
            #conn.close()
            #myprint(inspect.stack()[0][3], self.dbfilename)
            return True
        except Exception as e:
            print(inspect.stack()[0][3],e)

        return False

    def fillemptydb(self, listForDB, theTS, siteurl, sitenses):
        print('fiiling empty db')
        try:
            self.myconn.close()
            #print('connection closed 1')
            self.myconn = sqlite3.connect(self.dbfilename, isolation_level = 'EXCLUSIVE')
            #print('new connection opened EXCLUSIVE 1')
            #print(self.myconn)
            #print(self)
            #self.myconn.execute('''INSERT INTO maintbl(lemma, lns, lredirect, lstart, lcharlen, ltimestamp) VALUES (?,?,?,?,?,?);''', listForDB[0])
            #self.myconn.commit()
            #print(listForDB[0])
            #xcounter = 0
            #for arecord in listForDB:
                #xcounter += 1
                #if xcounter % 10000 == 0:
                    #self.myconn.commit()
                    #self.myconn.execute("begin")
                    #print('commited 100', xcounter)
                    #self.myconn.execute('''INSERT INTO maintbl(lemma, lns, lredirect, lstart, lcharlen, ltimestamp) VALUES (?,?,?,?,?,?);''', arecord)
            #affected = self.myconn.executemany('''INSERT INTO maintbl(lemma, lns, lredirect, lstart, lcharlen, ltimestamp) VALUES (?,?,?,?,?,?);''', listForDB).rowcount
            self.myconn.executemany('''INSERT INTO maintbl(lemma, lns, lredirect, lstart, lcharlen, ltimestamp) VALUES (?,?,?,?,?,?);''', listForDB)
            #self.myconn.commit()
            print('all commited')
            #print('time:', str(time.time() - starttime), 'affected', str(affected))
            #self.myconn.commit()
            self.myconn.execute('''CREATE INDEX "lnsndx" on maintbl (lns ASC)''')
            #self.myconn.commit()
            print( 'ns index created')
            self.myconn.execute('''CREATE INDEX "lemmandx" on maintbl (lemma ASC)''')
            #self.myconn.commit()
            print('lemma index created')
            self.myconn.execute('''CREATE INDEX "lTSndx" on maintbl (ltimestamp ASC)''')
            #self.myconn.commit()
            print('TS index created')
            mycursor = self.myconn.execute('''SELECT MAX(ltimestamp) FROM maintbl;''')
            arow = mycursor.fetchone()
            #print('arow', arow)
            #myprint('arow 0', arow[0])
            basemaxTS = getnonZtime(arow[0])
            #siteurl, sitenses = GetInfoFromDump(dbfullpath)
            self.myconn.execute('''INSERT INTO attribstbl(atimestamp, adumpTS, asiteurl, asitenses) VALUES (?,?,?,?);''', (basemaxTS, theTS, siteurl, sitenses))
            self.myconn.commit()
            #close and reopen because we may be in a with and someone will call after another function
            self.myconn.close()
            self.myconn = sqlite3.connect(self.dbfilename, isolation_level = None)
            self.myconn.row_factory = sqlite3.Row
            #myprint(inspect.stack()[0][3],basemaxTS, theTS, siteurl, sitenses)
            return True
        except self.myconn.Error as e:
            print('an error')
            print( e)
        except Exception as e:
            #myprint(inspect.stack()[0][3],e)
            #return False
            raise e

    def updateSiteInfo(self, newbaseTS, siteurl, sitenses):
        try:
            #myprint('updateSiteInfo')
            self.myconn.execute('''UPDATE attribstbl set atimestamp =?, asiteurl=?, asitenses=?;''', (newbaseTS, siteurl, sitenses))
            #myprint('updateSiteInfo ok')
        except Exception as e:
            #myprint('updateSiteInfo failed')
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise

    def updateSiteInfo3(self, sitenses):
        print(sitenses)
        print('updateSiteInfo3')

    def updateSiteInfo2(self, sitenses):
        try:
            #print('updateSiteInfo2')
            mycursor = self.myconn.execute('''SELECT MAX(ltimestamp) FROM maintbl;''')
            arow = mycursor.fetchone()
            #myprint('arow', arow)
            #myprint('arow 0', arow[0])
            newbaseTS = getnonZtime(arow[0])
            #print(newbaseTS)
            #siteurl, sitenses = GetInfoFromDump(dbfullpath)
            self.myconn.execute('''UPDATE attribstbl set atimestamp =?, asitenses=?;''', (newbaseTS, sitenses))
            #print('updateSiteInfo2 ok')
        except Exception as e:
            print('updateSiteInfo 2 failed')
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise e

    def getSiteInfo(self):
        #myprint(inspect.stack()[0][3],'one')
        #myprint('===================', self.myconn.row_factory)
        try:
            mycursor = self.myconn.cursor()
            mycursor.execute('''SELECT * FROM attribstbl;''')
            arow = mycursor.fetchone()
            #myprint(inspect.stack()[0][3],'got one', arow.keys())
            if arow[0] == None:
                return False, None
            else:
                return True, arow
        except Exception as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise

    def getSiteURL(self):
        try:
            mycursor = self.myconn.cursor()
            mycursor.execute('''SELECT asiteurl FROM attribstbl;''')
            arow = mycursor.fetchone()
            #myprint(inspect.stack()[0][3],'got one', arow.keys())
            return arow[0]
        except Exception as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise


    def getusablespace(self, thisstart):
        try:
            mycursor = self.myconn.cursor()
            mycursor.execute('''SELECT MIN(lstart) FROM maintbl WHERE lstart > ? ;''', ( thisstart,))
            arow = mycursor.fetchone()

            if arow[0] == None:
                mycursor.execute('''SELECT MAX(lstart), lcharlen FROM maintbl;''')
                arow = mycursor.fetchone()
                if int(arow[0]) == thisstart:
                    return -1
                else:
                    #myprint(inspect.stack()[0][3],'Start not found in db.')
                    raise
            else:
                return int(arow[0]) - thisstart - len('\n')
        except Exception as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise

    def deleteWithTransaction(self, listoftitles):
        #print('deleteWithTransaction')
        try:
            self.myconn.close()
            self.myconn = sqlite3.connect(self.dbfilename, isolation_level = 'EXCLUSIVE')
            self.myconn.execute("begin")
            for atitle in listoftitles:
                #self.deleteLemma(atitle)
                self.myconn.execute('''DELETE FROM maintbl WHERE lemma = ? ;''', (atitle,))
            self.myconn.commit()
            self.myconn.close()
            self.myconn = sqlite3.connect(self.dbfilename, isolation_level = None)
            self.myconn.row_factory = sqlite3.Row
            #print('deleteWithTransaction END')
        except sqlite3.Error as e:
            print(e)
            raise e
        except Exception as e:
            print(e)
            raise e

    def deleteLemma(self, title):
        #print('deleteLemma')
        try:
            #myprint("==================trying to delete:", title)
            mycursor = self.myconn.cursor()
            mycursor.execute('''SELECT * FROM maintbl WHERE lemma = ? ;''', ( title,))
            arow = mycursor.fetchone()
            if arow == None:
                #print('None found', title)
                #print('deleteLemma ---------- None found')
                return True
                #logit(self.errorlogfile, title + ' not found in db and not deleted.')
                #myprint(inspect.stack()[0][3],title + ' not found in db and not deleted.')
                #return True
            else:
                #print('======= found', arow)
                #return True
                start = int(arow['lstart'])
                usablespace = self.getusablespace(int(arow['lstart']))
                #first delete the entry then the txt
                mycursor.execute('''DELETE FROM maintbl WHERE lemma = ? ;''', (title,))
                self.textdelete(start, usablespace)
                #print('deleteLemma ---------- DELETED')
                return True
        except sqlite3.Error as e:
            #logit(self.errorlogfile, title + ' raised an error in deletelemma.')
            #myprint('title',title)
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            print('deleteLemma ---------- ERROR')
            raise e

    def appendWithTransaction(self, dictwithlemmas):
        fields = {}
        for pageid in dictwithlemmas:
            #print('appendWithTransaction 1',dictwithlemmas[pageid]['title'])
            #print("dictwithlemmas[pageid]",dictwithlemmas[pageid])
            titlestart = self.textappend(dictwithlemmas[pageid]['revisions'][0]['*'])
            fields[dictwithlemmas[pageid]['pageid']] = DBRow(title = dictwithlemmas[pageid]['title'],
                                                    ns = dictwithlemmas[pageid]['ns'],
                                                    isredirect = 1 if 'redirect' in dictwithlemmas[pageid] else 0,
                                                    timestamp = dictwithlemmas[pageid]['revisions'][0]['timestamp'],
                                                    start = titlestart,
                                                    charlen = len(dictwithlemmas[pageid]['revisions'][0]['*']),#rest are dummy values
                                                    content = ''
                                                    )
            #print('field added')
            #{'lemma': dictwithlemmas[pageid]['title'], 'lns': dictwithlemmas[pageid]['ns'],
                        #'lredirect':1 if 'redirect' in dictwithlemmas[pageid],
                        #'lstart':titlestart,
                        #'lcharlen':len(bytes(dictwithlemmas[pageid]['revisions'][0]['*'], 'utf-8')),
                        #'ltimestamp':dictwithlemmas[pageid]['revisions'][0]['timestamp']}
                        #lemma, lns, lredirect, lstart, lcharlen, ltimestamp
        self.myconn.close()
        self.myconn = sqlite3.connect(self.dbfilename, isolation_level = 'EXCLUSIVE')
        self.myconn.execute("begin")
        #print('started transaction')
        for pageid in fields:
            self.myconn.execute('''INSERT INTO maintbl(lemma, lns, lredirect, lstart, lcharlen, ltimestamp) VALUES (?,?,?,?,?,?);''',
                    (fields[pageid].title, fields[pageid].ns, fields[pageid].isredirect,
                    fields[pageid].start, fields[pageid].charlen, fields[pageid].timestamp))
        self.myconn.commit()
        self.myconn.close()
        self.myconn = sqlite3.connect(self.dbfilename, isolation_level = None)
        self.myconn.row_factory = sqlite3.Row
        #print('reopend (with isolation_level = None?)', self.myconn.isolation_level)

    def appendLemma(self, entry):
        #print('appendLemma')
        titlestart = self.textappend(entry.content)
        if titlestart:
            #myprint('insert new lemma in db',entry.title, entry.ns, titlestart, len(entry.content), entry.timestamp)
            #print('------------')
            self.myconn.execute('''INSERT INTO maintbl(lemma, lns, lredirect, lstart, lcharlen, ltimestamp) VALUES (?,?,?,?,?,?);''',
                    (entry.title, entry.ns, entry.isredirect, titlestart, len(entry.content), entry.timestamp))
            #print('appendLemma END')
            return True
        else:
            print('appendLemma END  ------- FALSE')
            return False

    def updateExistingLemmas(self, dictwithlemmas):
        #fields = {}

        #try:
        self.myconn.close()
        self.myconn = sqlite3.connect(self.dbfilename, isolation_level = 'EXCLUSIVE')
        self.myconn.execute("begin")
        #print('started transaction')
        for pageid in dictwithlemmas:
            #print(dictwithlemmas[pageid]['title'])
            #print('redirect' in dictwithlemmas[pageid])
            #print(dictwithlemmas[pageid]['ns'])
            #print(dictwithlemmas[pageid]['revisions'][0]['timestamp'])
            #print('appendWithTransaction 1',dictwithlemmas[pageid]['title'])
            #print("dictwithlemmas[pageid]",dictwithlemmas[pageid])
            titlestart = self.textappend(dictwithlemmas[pageid]['revisions'][0]['*'])
            #print(titlestart)
            self.myconn.execute('''UPDATE maintbl SET lns = ?, lredirect = ?, lstart = ?, lcharlen = ?, ltimestamp = ? WHERE lemma = ?;''',
                    ( dictwithlemmas[pageid]['ns'],
                    1 if 'redirect' in dictwithlemmas[pageid] else 0,
                    titlestart,
                    len(dictwithlemmas[pageid]['revisions'][0]['*']),
                    dictwithlemmas[pageid]['revisions'][0]['timestamp'],
                    dictwithlemmas[pageid]['title']))

            #fields[dictwithlemmas[pageid]['pageid']] = DBRow(title = dictwithlemmas[pageid]['title'],
                                                    #ns = dictwithlemmas[pageid]['ns'],
                                                    #isredirect = 1 if 'redirect' in dictwithlemmas[pageid] else 0,
                                                    #timestamp = dictwithlemmas[pageid]['revisions'][0]['timestamp'],
                                                    #start = titlestart,
                                                    #charlen = len(bytes(dictwithlemmas[pageid]['revisions'][0]['*'], 'utf-8')),#rest are dummy values
                                                    #content = ''
                                                    #)
            #print('field added')
            #{'lemma': dictwithlemmas[pageid]['title'], 'lns': dictwithlemmas[pageid]['ns'],
                        #'lredirect':1 if 'redirect' in dictwithlemmas[pageid],
                        #'lstart':titlestart,
                        #'lcharlen':len(bytes(dictwithlemmas[pageid]['revisions'][0]['*'], 'utf-8')),
                        #'ltimestamp':dictwithlemmas[pageid]['revisions'][0]['timestamp']}
                        #lemma, lns, lredirect, lstart, lcharlen, ltimestamp
        #print('started transaction')
        #for pageid in fields:
            #self.myconn.execute('''UPDATE maintbl SET lns = ?, lredirect = ?, lstart = ?, lcharlen = ?, ltimestamp = ?) WHERE lemma = ?;''',
                    #( fields[pageid].ns, fields[pageid].isredirect,
                    #fields[pageid].start, fields[pageid].charlen, fields[pageid].timestamp, fields[pageid].title))
        self.myconn.commit()
        self.myconn.close()
        self.myconn = sqlite3.connect(self.dbfilename, isolation_level = None)
        self.myconn.row_factory = sqlite3.Row
        #except sqlite3.Error as e:
            #print(e)
            #raise e
        #except Exception as e:
            #print(e)
            #raise e

    def updateExistingLemma(self,newentrywitholddata):
        #print('updateExistingLemma')

        start = int(newentrywitholddata.start)
        #print(' in updatelemma else' , start)
        usablespace = self.getusablespace(start)
        #print(' in updatelemma usablespace' , usablespace)
        byteslength = len(bytes(newentrywitholddata.content, 'utf-8'))

        if usablespace < byteslength:#either at end or no room for content
            ok = self.textdelete(start, usablespace)
            #print('updateExistingLemma textdeleted')
            #if not ok:
                #myprint()
                #return False
            newstart = self.textappend(newentrywitholddata.content)
        else:#enough space. Do not update start.
            ok = self.textinsertnew(newentrywitholddata.content, start, usablespace)
            newstart = start
        #print('updateExistingLemma text is ok. Try update',newstart)
        try:
            mycursor = self.myconn.cursor()
            mycursor.execute('''UPDATE maintbl SET lstart = ?, lcharlen = ?, ltimestamp =? WHERE lemma = ? ;''',
                            (newstart, len(newentrywitholddata.content), newentrywitholddata.timestamp, newentrywitholddata.title ))
            #print('UPDATE executed with',len(entry.content), entry.timestamp, entry.title)
            #print('updateExistingLemma END')
            return True
        except sqlite3.Error as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            #logit(self.errorlogfile, entry.title + ' raised an error in db update. ' + e.args)
            print('updateExistingLemma END ---------------  ERROR')
            raise e

    def updateLemma(self, entry):
        '''Write new data for an entry.

        If entry does not exist append it.
        If entry has enough space in the text file use that space. Change timestamp.
        If not enough space, delete the old data from text file, and append to end changing start (and len)
        '''
        #myprint(entry.title, entry.ns, len(entry.content), entry.timestamp,entry.content)
        #print(entry.title, entry.ns, len(entry.content), entry.timestamp,entry.content)
        #print('updateLemma')
        try:
            mycursor = self.myconn.cursor()
            mycursor.execute('''SELECT * FROM maintbl WHERE lemma = ?;''', ( entry.title , ))
            arow = mycursor.fetchone()
            #print("arow",arow)
            #myprint(' in updatelemma')

            if arow == None:
                #not found just append it
                #print('not found', entry.title, 'will append')
                #myprint('arow == None in updatelemma')
                titlestart = self.textappend(entry.content)
                if titlestart:
                    #myprint('insert new lemma in db',entry.title, entry.ns, titlestart, len(entry.content), entry.timestamp)
                    #print('------------')
                    self.myconn.execute('''INSERT INTO maintbl(lemma, lns, lredirect, lstart, lcharlen, ltimestamp) VALUES (?,?,?,?,?,?);''',
                            (entry.title, entry.ns, entry.isredirect, titlestart, len(entry.content), entry.timestamp))
                    #self.myconn.commit()
                    #myprint('INSERT DONE')
                    return True
                else:
                    #myprint('text not appended !!!!!!!!!!!!!!!!!!!!!!!!')
                    #logit(self.errorlogfile, entry.title + ' not appended. Could not append text.')
                    return False
            else:
                start = int(arow['lstart'])
                #print(' in updatelemma else' , start)
                usablespace = self.getusablespace(start)
                #print(' in updatelemma usablespace' , usablespace)
                byteslength = len(bytes(entry.content, 'utf-8'))
                if usablespace < byteslength:#either at end or no room for content
                    ok = self.textdelete(start, usablespace)
                    if not ok:
                        #myprint()
                        return False
                    newstart = self.textappend(entry.content)
                    try:
                        mycursor.execute('''UPDATE maintbl SET lstart = ?, lcharlen = ?, ltimestamp =? WHERE lemma = ? ;''',
                                    (newstart, len(entry.content), entry.timestamp, entry.title ))
                        #print('UPDATE executed with',len(entry.content), entry.timestamp, entry.title)
                        return True
                    except Exception as e:
                        #print('Exception as inst in updatelemma',inst.args)
                        #logit(self.errorlogfile, entry.title + ' raised an error in db update. ' + e.args)
                        #myprint('Exception in:', inspect.stack()[0][3],e.args)
                        raise
                else:#enough space. Do not update start.
                    ok = self.textinsertnew(entry.content, start, usablespace)
                    if ok:
                        try:
                            mycursor.execute('''UPDATE maintbl SET lcharlen = ?, ltimestamp =? WHERE lemma = ? ;''',
                                        (len(entry.content), entry.timestamp, entry.title ))
                            #print('UPDATE executed with',len(entry.content), entry.timestamp, entry.title)
                            return True
                        except Exception as e:
                            #myprint('Exception in:', inspect.stack()[0][3],e.args)
                            #logit(self.errorlogfile, entry.title + ' raised an error in db update. ' + e.args)
                            raise
        except Exception as e:
            #return False
            #logit(self.errorlogfile, entry.title + ' not updated. Raised an error.' + e.args)
            #myprint(' entry.title :',  entry.title )
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise

    def getLemmaContent(self,lemma):
        mycursor = self.myconn.cursor()
        try:
            mycursor.execute('''SELECT * FROM maintbl WHERE lemma = ?;''', (lemma,))
            myrow = mycursor.fetchone()
            #return (myrow != None), myrow
            #myprint('fetched one')
        except sqlite3.IntegrityError:
            return 'DB IntegrityError ERROR', None
        except Exception as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise
        if myrow != None:
            #myprint('fetched one myrow != None:',int(myrow['lstart']))
            #print('fetched one myrow != None:',int(myrow['lstart']), int(myrow['lcharlen']))
            self.txtfile.seek(int(myrow['lstart']))

            return self.txtfile.read(int(myrow['lcharlen'])), myrow['ltimestamp']
        else:
            #myprint('fetched one myrow != None:',lemma)
            return '',None

    def getLemmasLike(self,text):
        mycursor = self.myconn.cursor()
        try:
            mycursor.execute('''SELECT lemma FROM maintbl WHERE lemma LIKE ?;''', ('%' + text + '%',))
            manyrows = mycursor.fetchall()
            titles = [x[0] for x in manyrows]
            if len(titles):
                return '\n'.join(titles), ''
            else:
                return '' ,''
        except sqlite3.IntegrityError:
            return 'DB IntegrityError ERROR', None
        except Exception as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise

    def iterLemmas(self, ns = None):
        print("iterLemmas before all 1")
        try:
            #myprint("before all")
            #print("before all")
            mycursor = self.myconn.cursor()
            if ns != None:
                mycursor.execute('''SELECT * FROM maintbl WHERE lns = ? ORDER BY lstart;''', (ns,))
            else:
                mycursor.execute('''SELECT * FROM maintbl ORDER BY lstart;''')
            manyrows = mycursor.fetchall()
            print(len(manyrows),type(manyrows))
            for row in manyrows:
                #print("in row")
                ns = row['lns']
                start = row['lstart']
                charstoread = row['lcharlen']
                title = row['lemma']
                isredirect = (row['lredirect'] == 1)
                timestamp = row['ltimestamp']
                #myprint("in row")
                self.txtfile.seek(int(start))
                if charstoread == 0:
                    content = ''
                else:
                    content = self.txtfile.read(int(charstoread))
                #content = unescape(content)
                #myprint("before yield")
                #print("before yield")
                yield DBRow(title = title,
                        ns = ns,
                        start = start,
                        charlen = charstoread,
                        timestamp = timestamp,
                        content = content,
                        isredirect = isredirect)
        except sqlite3.IntegrityError:
            #print('IntegrityError in:')
            return None
        except Exception as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            #print('Exception in:')
            raise

    def textappend(self, text):
        try:
            self.txtfile.seek(0,2)
            titlestart = str(self.txtfile.tell())
            #titlelen = len(text)
            self.txtfile.write(text+ '\n')
            return titlestart
        except Exception as e:
            #return None
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise

    def textdelete(self, start, usablespace):
        #myprint('textdelete start, usablespace top', start, usablespace)
        try:
            if usablespace == -1:
                #is the last lemma
                #truncate to lstart and return true

                self.txtfile.truncate(start)
                self.txtfile.seek(start)
                return True
            elif usablespace < -1:
                #myprint( inspect.stack()[0][3],'usablespace < -1 in text delete, should not come here.')
                raise
            if usablespace < len('\n'):
                newtext = ''
            else:
                newtext = ''.ljust(usablespace-len('\n'))
            self.txtfile.seek(int(start))
            self.txtfile.write(newtext+'\n')
            return True
        except Exception as e:
            #return False
            #myprint('textdelete', start, usablespace)
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise e

    def getLemmasInList(self, tupleoflemmas):
        #print(self.myconn.isolation_level)
        mycursor = self.myconn.cursor()
        try:
            sql='''SELECT * FROM maintbl WHERE lemma IN ({seq})'''.format(
                        seq=','.join(['?']*len(tupleoflemmas)))
            #print('=============== SQL ==========')
            #print(sql)
            #print(tupleoflemmas)
            mycursor.execute(sql, tupleoflemmas)
            #mycursor.execute('''SELECT lemma FROM maintbl WHERE lemma IN (?);''', ('%' + text + '%',))
            manyrows = mycursor.fetchall()
            #print('returned from execute',len(manyrows))
            if len(manyrows):
                lemmasasfields = {}
                #lns, lredirect, lstart, lcharlen, ltimestamp
                #print('in manyrows',manyrows[0]['lemma'])
                for arow in manyrows:
                    #print('arow in getLemmasInList', arow)
                    #print(x['lemma'], '==================')
                    #print('lemma in manyrows',manyrows[x]['lemma'])
                    #print({key : x[key] for key in x.keys() if key != 'lemma'})

                    lemmasasfields[arow['lemma']] = { key : arow[key] for key in arow.keys() if key != 'lemma'}
                    #lemmasasfields[manyrows[x]['lemma']] = { 'lns': manyrows[x]['lns'],
                                    #'lredirect':manyrows[x]['lredirect'],
                                    #'lstart':manyrows[x]['lstart'],
                                    #'lcharlen':manyrows[x]['lcharlen'],
                                    #'ltimestamp':manyrows[x]['ltimestamp']
                                    #}
                #print(lemmasasfields['promulgate'])
                return lemmasasfields
            else:
                return {}
        except sqlite3.IntegrityError:
            print('DB IntegrityError ERROR')
            return None
        except Exception as e:
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            print('Exception in:getLemmasInList',e)
            raise e

    def textinsertnew(self, text, start, usablespaceinbytes):
        try:
            padding = usablespaceinbytes - len('\n') - len(bytes(text, 'utf-8'))
            newtext = text + (" " * padding)
            self.txtfile.seek(start)
            self.txtfile.write(newtext+'\n')
            return True
        except Exception as e:
            #return False
            #myprint('Exception in:', inspect.stack()[0][3],e.args)
            raise

if __name__ == "__main__":
    realfile = os.path.realpath(__file__)
    realfile_dir = os.path.dirname(os.path.abspath(realfile))
    dbf ='/home/ilias/Λήψεις/Προγραμματισμός1/dumps/ukwiktionary-latest-pages-meta-current.xml.db'
    txtf ='/home/ilias/Λήψεις/Προγραμματισμός1/dumps/ukwiktionary-latest-pages-meta-current.xml.txt'
    try:
        with DB(dbf,txtf) as localydb:
            print(localydb)
            localydb.updateSiteInfo2('blahblah')


            #b = db.getLemmasLike('zebra')
            #print(len(b))
            #for c in b:
                #print(db.getLemmaContent(c),end = '\t')
                #print("+++++++++++++-----++++++++++++++++")
                #print(c)
                #print("++++++++++++++++++++++++++++++++++")
                #print(db.getLemmaContent(c)[0])
                #print('----------------------------------')
            #print()
            #b = db.getLemmaContent('α')
            #print(b[0])
            #r = DBRow(title = 'α',
            #ns = 0,
            #content = 'mplah mplah \n blah',
            #timestamp = '20170606',
            #start = 0,
            #charlen = 0)
            #c = db.updatelemma(r)
            #try:
                #for l in db.iterLemmas(10):
                    #print("+++++++++++++-----++++++++++++++++")
                    #print(l.title)
                    #print("++++++++++++++++++++++++++++++++++")
                    #print(l.content)
                    #print('----------------------------------')
            #except:
                #raise
            #b = db.deletelemma('Template:Wikitext talk page converted to Flow')
            #print('b=',b)
    except Exception as e:
        raise


