#!/usr/bin/python
# File: uligo.py

##   This is the main part of uliGo 0.3, a program for practicing
##   go problems. For more information, see http://www.u-go.net/uligo/

##   Copyright (C) 2001-3 Ulrich Goertz (u@g0ertz.de)

##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2 of the License, or
##   (at your option) any later version.

##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

##   You should have received a copy of the GNU General Public License
##   along with this program (gpl.txt); if not, write to the Free Software
##   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
##   The GNU GPL is also currently available at
##   http://www.gnu.org/copyleft/gpl.html


from Tkinter import *
from tkMessageBox import *
from ScrolledText import ScrolledText
import tkFileDialog
import tkFont
import time
import pickle
from random import randint
import os
import sys
from string import split
from math import sqrt
import webbrowser

from sgfparser import *

import clock
from board1 import *


# ---------------------------------------------------------------------------------------

class BunchTkVar:
    """ This class is used to collect the Tk variables where the options
        are stored. """
    
    def saveToDisk(self, filename, onFailure = lambda:None):
        d = {}
        for x in self.__dict__.keys():
            d[x] = self.__dict__[x].get()
        try:
            f = open(filename, 'w')
            pickle.dump(d,f)
            f.close()
        except IOError:
            onFailure()
            

    def loadFromDisk(self, filename, onFailure = lambda:None):
        try:
            f = open(filename)
            d = pickle.load(f)
            f.close()
        except IOError:
            onFailure()
        else:
            for x in self.__dict__.keys():
                if d.has_key(x): self.__dict__[x].set(d[x])

# ---------------------------------------------------------------------------------------

class EnhancedCursor(Cursor):
    """ Adds the following features to Cursor in sgfparser.py: 
        - comments from the SGF file in the current node are automatically displayed
          in the ScrolledText widget self.comments 
        - It remembers if it is in a 'wrong variation', and correctChildren returns a list
          of the correct children variations. """

    def __init__(self, sgf, comments):
        self.comments = comments
        self.wrongVariation = 0
        Cursor.__init__(self, sgf, 1)

    def displayComment(self):
        self.comments.config(state=NORMAL)
        self.comments.delete('1.0', END)
        if self.currentNode().has_key('C'):    
            self.comments.insert('1.0', self.currentNode()['C'][0])
        self.comments.config(state=DISABLED)

    def correctChildren(self):
        if self.wrongVariation:
            return []
        
        corr = []
        n = self.currentN.next
        i = 0
        
        while n:
            c = n.getData()
            if not (c.has_key('TR') or c.has_key('WV')):
                corr.append(i)
            n = n.down
            i += 1
        return corr

    def reset(self):
        self.game(0)
        self.wrongVariation = 0
        self.displayComment()

    def next(self, varnum=0):
        n = Cursor.next(self, varnum)
        if not self.wrongVariation and (n.has_key('TR') or n.has_key('WV')): self.wrongVariation = 1
        elif self.wrongVariation:
            self.wrongVariation = self.wrongVariation + 1
        self.displayComment()
        return n

    def previous(self):
        n = Cursor.previous(self)
        if self.wrongVariation:
            self.wrongVariation = self.wrongVariation - 1
        self.displayComment()
        return n
    
# ---------------------------------------------------------------------------------------

class StatusBar(Frame):
    """ This class administrates the 'status bar' showing if a problem has
        been solved correctly, or if a wrong move has been made. """
    
    def __init__(self, master):
        p = os.path.join(sys.path[0],'gifs')
        try:                                                     # try to load the gif's
            self.solved1 = PhotoImage(file=os.path.join(p,'solved1.gif'))
            self.solved2 = PhotoImage(file=os.path.join(p,'solved2.gif'))
            self.wrong   = PhotoImage(file=os.path.join(p,'wrong.gif'))
            self.empty   = PhotoImage(file=os.path.join(p,'empty.gif'))
            self.end     = PhotoImage(file=os.path.join(p,'end.gif'))
        except TclError:
            self.gifsFound = 0
        else:
            self.gifsFound = 1
        Frame.__init__(self, master, height=20, width=65)
        self.label = Label(self, bd=1, anchor=W)
        if self.gifsFound: self.label.config(image=self.empty)
        else:              self.label.config(font=('Helvetica', 24))
        self.label.pack(fill=X)

    def set(self, status=None):
        if   status == 'solved1':
            if self.gifsFound: self.label.config(image = self.solved1)
            else:              self.label.config(fg='green', text = 'solved!')
        elif status == 'solved2':
            if self.gifsFound: self.label.config(image = self.solved2)
            else:              self.label.config(fg='blue', text='solved')
        elif status == 'wrong':
            if self.gifsFound: self.label.config(image = self.wrong)
            else:              self.label.config(fg='red', text='wrong!')
        elif status == 'end':
            if self.gifsFound: self.label.config(image = self.end)
            else:              self.label.config(fg='red', text='end')
        else                    :
            if self.gifsFound: self.label.config(image = self.empty)
            else:              self.label.config(text='')
        self.label.update_idletasks()


# ---------------------------------------------------------------------------------------

class PbmRecord:
    """ Stores the number of right/wrong answers etc. for each problem. A list of problems
        is maintained (and stored in a .dat file) in which problems that have been asked
        already are moved to the end of the list (if answered correctly), or moved to the
        second half of the list (if not answered correctly); thus the problems at the
        beginning of the list are good choice for the problem asked next. This list is
        stored in a '.dat' file. It also contains information on how often a problem has
        been asked already, and with which results.
        Three modes are available for choosing the order of problems to ask:
        random, sequential (change .dat to keep track of correct/wrong answers),
        sequential, don't change .dat file. """

    def __init__(self, path, filename, noOfPbms, defMode):
        """ defMode is a Tk IntVar which stores the mode for choosing the order of the problems.
            0 = random, 1 = sequential (change .dat to keep track of correct/wrong answers),
            2 = sequential, don't change .dat file """
        
        self.modeVar = IntVar()
        self.defModeVar = defMode
        
        if filename[-4:] == '.sgf': self.filename = filename[:-4] + '.dat'
        else:                       self.filename = filename + '.dat'

        self.path = path

        self.history = [] # list of pbms asked in this session, for the "back" button

        try:
            f = open(os.path.join(self.path,self.filename))
            s = f.readline();
            if s == 'uligo01\n':            # this is a .dat file from uligo 0.1 or 0.2
                f.seek(0)
                self.noOfPbms, self.pbmsAsked, self.noRight, self.noWrong, self.list = pickle.load(f)
                f.close()
                self.modeVar.set(defMode.get())
                self.current = -1
                self.handleCurrent = -1
            else:
                self.noOfPbms, self.pbmsAsked, self.noRight, self.noWrong, \
                               self.current, self.handleCurrent, help, self.list = pickle.load(f)
                self.modeVar.set(help)
        except IOError:
            # create new list:
          
            self.noOfPbms = noOfPbms
            self.pbmsAsked = 0
            self.noRight = self.noWrong = 0
            self.modeVar.set(defMode.get())
            self.current = -1
            self.handleCurrent = -1
            
            self.list = []
            
            for i in range(noOfPbms):
                self.list.append((i, 0, -1, 0, 0)) # no of corresp problem, no. asked, 
                                                   # when asked for last time (this is not evaluated directly),
                                                   # no. right answers, no. wrong answers 


    def getNext(self):
        """ This function returns a randomly chosen number (with probability 5/6 in the first third
            of the list, with probability 1/6 in the third sixth). """
        if self.modeVar.get() == 0:
            if randint(0,1):
                self.handleCurrent = randint(0,self.noOfPbms/3)
            else:
                self.handleCurrent = randint(0,self.noOfPbms/2)
            self.current = self.list[self.handleCurrent][0]
        elif self.modeVar.get() == 1:
            self.handleCurrent = 0
            self.current = self.list[0][0]
        elif self.modeVar.get() == 2:
            self.handleCurrent = -1
            self.current = (self.current + 1) % self.noOfPbms
        co = randint(0,1)
        ori = randint(0,7)
        self.history.append((self.handleCurrent, self.current, co, ori))
        return self.current, co, ori

    def getPrevious(self):
        if len(self.history) <= 1: raise Exception()
        self.history.pop()
        self.handleCurrent, self.current, co, ori = self.history[-1]
        return self.current, co, ori


    def printStatistics(self):
        """ Returns some statistics on the problems asked so far."""
        if self.pbmsAsked:
            rightPercentage = ' (' + str(self.noRight*100/self.pbmsAsked) + ' % )'
            wrongPercentage = ' (' + str(100 - (self.noRight*100/self.pbmsAsked) ) + ' % )'
        else: rightPercentage = wrongPercentage = ''
        return    'Number of problems in database: ' + str(self.noOfPbms) +'\n' \
               +  'Number of questions asked     : ' + str(self.pbmsAsked) +'\n' \
               +  'Number of right answers       : ' + str(self.noRight) \
                      + rightPercentage + '\n' \
               +  'Number of wrong answers       : ' + str(self.noWrong) \
                      + wrongPercentage + '\n' \


    def store(self, correct):
        """ After a problem has been answered, this function is called to update the list. """
        if self.handleCurrent < 0 or self.modeVar.get() == 2:            
            return
        i = self.handleCurrent
        self.pbmsAsked = self.pbmsAsked + 1
        newEntry = (self.list[i][0], self.list[i][1]+1, self.pbmsAsked,   # update no. of times asked,
                    self.list[i][3]+correct, self.list[i][4]+1-correct)   # and no. of right/wrong answers
        
        self.list[i:i+1] = []   # delete old entry
        if correct:             # and insert new one
            self.list.append(newEntry)
            self.noRight = self.noRight + 1
        else:
            l = randint(self.noOfPbms/2, 2*self.noOfPbms/3)
            self.list.insert(l, newEntry)
            self.noWrong = self.noWrong + 1


    def saveToDisk(self):
        """ Write list to disk. """
        
        try:
            if not os.path.exists(self.path): os.makedirs(self.path)
            f = open(os.path.join(self.path,self.filename), 'w')
            f.write('uligo03\n')
            help = self.modeVar.get()
            pickle.dump((self.noOfPbms, self.pbmsAsked, self.noRight, self.noWrong, \
                         self.current, self.handleCurrent, help, self.list),f)
            f.close()
        except IOError, OSError: showwarning('IO Error', 'Could not write .dat file')


    def changeModeQuit(self,w,h1,h2,e):
        """This method is called when the user presses the OK button of the
           'change mode' window. It reads out the integer from the entry field,
           and destroys the window. """
        
        self.modeVar.set(h1.get())
        if self.modeVar.get() == 2:
            try:
                self.current = (int(e.get()) - 2) % self.noOfPbms  # - 2 because: pbm 1 has number 0 in the list,
                                                                   # and getNext will add 1 to self.current for
                                                                   # the next problem
            except ValueError:
                self.current = -1
                
        if h2.get():
            self.defModeVar.set(self.modeVar.get())

        w.destroy()


    def changeMode(self):
        """ This method opens a window which asks in which order to present
            the problems. """
        
        window = Toplevel()
        window.title("Order of the problems")
        f1 = Frame(window)
        f2 = Frame(window)

        e = Entry(f1, width=5)
        if self.modeVar.get() in [0,1]: e.config(state=DISABLED)

        h1 = IntVar()
        h1.set(self.modeVar.get())
        b1 = Radiobutton(f1, text='Random order', variable=h1, value=0,
                         command=lambda e=e: e.config(state=DISABLED))
        b2 = Radiobutton(f1, text='Sequential order (keep track of correct/wrong answers)',
                         variable=h1, value=1,
                         command=lambda e=e: e.config(state=DISABLED))
        b3 = Radiobutton(f1, text='Sequential order (don\'t record results); start with problem no. ',
                         variable=h1, value=2,
                         command=lambda e=e: e.config(state=NORMAL))

        h2 = IntVar()
        h2.set(0)
        c = Checkbutton(f1, text='Use this mode as default', variable = h2)

        OKbutton = Button(f2, text='OK',
                          command = lambda s=self, w=window, h1=h1, h2=h2, e=e: s.changeModeQuit(w, h1, h2, e))
        cancelButton = Button(f2, text='Cancel', command=window.destroy)
        
        b1.grid(row=0, column=0, sticky=NW)
        b2.grid(row=1, column=0, sticky=NW)
        b3.grid(row=2, column=0, sticky=NW)
        e.grid(row=2, column=1, sticky=NW)
        c.grid(row=3, column=0, sticky=NW)
        
        cancelButton.pack(side=RIGHT)
        OKbutton.pack(side=RIGHT)

        f1.pack(side=TOP)
        f2.pack(side=TOP)
        
        window.update_idletasks()  
        window.focus()
        window.grab_set()
        window.wait_window()

# ---------------------------------------------------------------------------------------

class App:
    """ This is the main class of uligo. Here the GUI is built, the SGF database is read
        and administrated, the moves are evaluated, etc.
        Almost everything that happens here has a counterpart in the GUI, so if you
        are looking for something, take a look at the __init__ method first, where
        the GUI is initialized; there you should find a reference to the method you
        are searching."""

    def printStatistics(self, showWindow=1):
        """Show / update the statistics window. If showwindow==0, the window is updated,
           but may remain iconified."""
        
        if showWindow and self.statisticsWindow.state() in ['withdrawn', 'iconic']:
            self.statisticsWindow.deiconify()
            
        if self.pbmRec:
            s = self.pbmRec.printStatistics()
        else: s=''
        if self.currentFile:
            cf = os.path.basename(self.currentFile)
        else:
            cf = 'None'
        s = 'Database: '+ cf + '\n\n' + s
        self.statisticsText.set(s)
     

    def convCoord(self, x, orientation=0):
        """ This takes coordinates in SGF style (aa - qq), mirrors/rotates the
            board according to orientation, and returns the corresponding
            integer coordinates (between 1 and 19). """
        
        m = map(None, 'abcdefghijklmnopqrs', range(1,20))
        pos0 = filter(lambda z, x=x: z[0]==x[0], m)[0][1]
        pos1 = filter(lambda z, x=x: z[0]==x[1], m)[0][1]

        if orientation == 0: return (pos0, pos1)
        elif orientation == 1: return (20 - pos0, pos1)
        elif orientation == 2: return (pos0, 20-pos1)
        elif orientation == 3: return (pos1, pos0)
        elif orientation == 4: return (20 - pos1, pos0)
        elif orientation == 5: return (pos1, 20 - pos0)
        elif orientation == 6:  return (20 - pos1, 20 - pos0)
        elif orientation == 7: return (20 - pos0, 20 - pos1)


    def setup(self, c, n = '', changeOri=1, co=None, ori=None):
        """ Set up initial position of problem. """

        self.board.clear()
        self.noMovesMade = 0

        # Choose colors and orientation (i.e. mirror/rotate the board) randomly

        if co is None: co = randint(0,1)
        if ori is None: ori = randint(0,7)

        if changeOri:
            self.invertColor = co * self.options.allowInvertColorVar.get()
            self.orientation = ori * self.options.allowRotatingVar.get()

        if self.invertColor: bColor, wColor = 'W', 'B'
        else:                bColor, wColor = 'B', 'W'

        # display problem name
        pbmName = ''
        if c.currentNode().has_key('GN'): pbmName = c.currentNode()['GN'][0][:15]
        if n: pbmName = pbmName + n
        self.pbmName.set(pbmName)
            
        # look for first relevant node
        while not (c.currentNode().has_key('AB') or c.currentNode().has_key('AW') \
                   or c.currentNode().has_key('B') or c.currentNode().has_key('W')): c.next()

        # and put stones on the board
        while not (c.currentNode().has_key('B') or c.currentNode().has_key('W')):
            if c.currentNode().has_key('AB'):
                for x in c.currentNode()['AB']:
                    self.board.play(self.convCoord(x, self.orientation), bColor)
            if c.currentNode().has_key('AW'):
                for x in c.currentNode()['AW']:
                    self.board.play(self.convCoord(x, self.orientation), wColor)
            c.next()

        if c.currentNode().has_key('B'):   self.board.currentColor = self.inputColor = bColor
        elif c.currentNode().has_key('W'): self.board.currentColor = self.inputColor = wColor
        
        c.previous()
        self.cursor = c


    def nextMove(self, p):
        """ React to mouse-click, in 'normal mode', i.e. answering a problem
            (as opposed to 'show solution' or 'try variation' mode). """

        self.board.play(p)  # put the stone on the board
        x, y = p

        if (self.inputColor == 'B' and not self.invertColor) or \
           (self.inputColor == 'W' and self.invertColor):
            nM = 'B'
            nnM = 'W'
        else:
            nM = 'W'
            nnM = 'B'

        nnMove = self.board.invert(self.inputColor)

        try:
       
            # look for the move in the SGF file
            done = 0 
            for i in range(self.cursor.noChildren()):
                c = self.cursor.next(i) # try i-th variation
                if c.has_key(nM) and self.convCoord(c[nM][0], self.orientation)==(x,y): # found the move
                    done = 1
                    if self.cursor.wrongVariation == 1:        # just entered wrong variation
                        if self.creditAvailable:
                            self.pbmRec.store(0)
                            self.creditAvailable = 0
                        if self.options.wrongVar.get() == 1:
                            self.statusbar.set('wrong')
                            if self.clock.running: self.clock.stop()
                        if self.options.wrongVar.get() == 2:
                            self.cursor.previous()
                            self.statusbar.set('wrong')
                            if self.clock.running: self.clock.stop()
                            time.sleep(0.5 * self.options.replaySpeedVar.get() + 0.5) # show the move for a short time,
                            self.board.undo()                                         # then delete it
                            self.statusbar.set('empty')
                            break

                    if not self.cursor.atEnd:                  # respond to the move
                        c = self.cursor.next(randint(0,self.cursor.noChildren()-1))
                        pos = self.convCoord(c[nnM][0], self.orientation)
                        self.board.play(pos, nnMove)
                        self.noMovesMade = self.noMovesMade + 2
                    else:
                        self.noMovesMade = self.noMovesMade + 1
                    if self.cursor.atEnd:                      # problem solved / end of wrong var.
                        if self.clock.running: self.clock.stop()
                        if self.cursor.wrongVariation:
                            self.statusbar.set('wrong')
                        else:
                            if self.creditAvailable:
                                self.statusbar.set('solved1')
                                self.pbmRec.store(1)
                                self.creditAvailable = 0
                            else:
                                self.statusbar.set('solved2') 
                            self.showSolutionButton.config(state=DISABLED)                        

                        self.board.state('disabled')
                    break
            
                else:
                    self.cursor.previous()
            
            if not done:                                  # not found the move in the SGF file, so it's wrong
                self.statusbar.set('wrong')
                if self.clock.running: self.clock.stop()
                if self.creditAvailable:
                    self.pbmRec.store(0)
                    self.creditAvailable = 0
                time.sleep(0.5 * self.options.replaySpeedVar.get() + 0.5) # show the move for a short time,
                self.board.undo()                                         # then delete it
                self.statusbar.set('empty')

        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
            return


    def markRightWrong(self):
        """ Used in 'navigate solution' mode: mark the correct/wrong variations. """

        try:
            if self.cursor.atEnd: return
            c = self.cursor.currentN.next.getData()
            if c.has_key('B'): color = 'B'
            else:              color = 'W'

            correct = self.cursor.correctChildren()
            n = self.cursor.currentN.next
            for i in range(self.cursor.noChildren()):
                c = n.getData()
                if i in correct:
                    self.board.placeMark(self.convCoord(c[color][0], self.orientation),'green')
                else:
                    self.board.placeMark(self.convCoord(c[color][0], self.orientation),'red')
                n = n.down
        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
        

    def markAll(self):
        """ Used in 'navigate solution' mode: mark all variations starting at this point. """
        try:
            if self.cursor.atEnd: return
            c = self.cursor.currentN.next.getData()
            if c.has_key('B'): color = 'B'
            else:              color = 'W'

            n = self.cursor.currentN.next
            while n:
                c = n.getData()
                self.board.placeMark(self.convCoord(c[color][0], self.orientation),'blue')
                n = n.down
        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
        

    def navSolutionNextMove(self, p):
        """ React to mouse-click in navigate-solution mode """

        x, y = p

        if (self.board.currentColor == 'B' and not self.invertColor) or \
                      (self.board.currentColor == 'W' and self.invertColor):
            nM, nnM = 'B', 'W'
        else:
            nM, nnM = 'W', 'B'

        try:
       
            done = 0
            for i in range(self.cursor.noChildren()):             # look for the move in the SGF file
                if (not done):
                    c = self.cursor.next(i)
                    if c.has_key(nM) and self.convCoord(c[nM][0], self.orientation)==p:  # found
                        self.board.play(p)
                        self.board.delMarks()
                        done = 1
                        self.noSolMoves = self.noSolMoves + 1
                        if not self.cursor.atEnd:
                            if self.board.currentColor == self.inputColor: self.markRightWrong()
                            else:                                          self.markAll()
                        else:
                            self.board.state('disabled')
                            if self.cursor.wrongVariation: self.statusbar.set('wrong')
                            else:                          self.statusbar.set('solved2')

                    else:
                        self.cursor.previous()
        
        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
        

    def undo2(self):
        """ Undo in normal move; undo the last two moves (resp. the last move,
            if it wasn't answered). """

        try:
        
            if self.noMovesMade > 0:
                self.creditAvailable = 0
                self.statusbar.set('empty')
                if self.cursor.atEnd:
                    self.showSolutionButton.config(state=NORMAL)
                    self.board.state('normal', self.nextMove)

                if (self.board.currentColor == self.inputColor):
                    self.board.undo(2)
                    self.cursor.previous()
                    self.cursor.previous()
                    self.noMovesMade = self.noMovesMade - 2
                else:
                    self.board.undo()
                    self.cursor.previous()
                    self.noMovesMade = self.noMovesMade - 1

        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
        

    def undoTryVar(self):
        """ Undo in 'try variation' mode. """

        if self.noTryVarMoves > 0:
            self.board.undo()
            self.noTryVarMoves = self.noTryVarMoves - 1
            

    def undoNavSol(self):
        """ Undo in 'navigate solution' mode. """

        try:

            if self.noSolMoves or self.noMovesMade:
                self.board.undo()
                self.statusbar.set('empty')
                self.board.state('normal', self.navSolutionNextMove)
                self.cursor.previous()
                self.board.delMarks()
                if self.board.currentColor == self.inputColor: self.markRightWrong()
                else:                                          self.markAll()
        
                if self.noSolMoves > 0:
                    self.noSolMoves = self.noSolMoves - 1 
                else:
                    self.noMovesMade = self.noMovesMade - 1

        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')


    def showSolution(self):
        """ Switch between normal and 'show solution' mode. """

        try:
        
            if self.showSolVar.get():                  # switch to 'show solution' mode
                self.statusbar.set('empty')
                self.creditAvailable = 0
                self.optionsmenu.entryconfig(5, state=DISABLED)
                self.clock.stop()
                self.noSolMoves = 0                    # remember how many moves have been played
                                                   # in this mode, so we can return to the
                                                   # correct point afterwards

                if self.options.animateSolVar.get():   # animate solution
                    self.board.state('disabled')
                    self.undoButton.config(state=DISABLED)
                
                    for i in range(self.cursor.wrongVariation):    # if in a wrong var. currently, go back first
                        self.board.undo()
                        self.cursor.previous()
                        self.noMovesMade = self.noMovesMade - 1
                        self.board.update_idletasks()
                        time.sleep(0.5 * self.options.replaySpeedVar.get())

                    if (self.inputColor == 'B' and not self.invertColor) or \
                       (self.inputColor == 'W' and self.invertColor):
                        nM = 'B'
                        nnM = 'W'
                    else:
                        nM = 'W'
                        nnM = 'B'
       
                    nnMove = self.board.invert(self.inputColor)
 
                    while not self.cursor.atEnd:          # play out solution
                        corr = self.cursor.correctChildren()
                        c = self.cursor.next(corr[randint(0,len(corr)-1)])  # choose one of the correct variations
                                                                            # by random
                        pos = self.convCoord(c[nM][0], self.orientation)
                        self.board.play(pos,self.inputColor)
                        self.noSolMoves = self.noSolMoves+1
                        self.master.update_idletasks()
                        time.sleep(0.5 * self.options.replaySpeedVar.get())
                        if not self.cursor.atEnd:
                            c = self.cursor.next(randint(0,self.cursor.noChildren()-1)) # choose an answer randomly
                            pos = self.convCoord(c[nnM][0], self.orientation)
                            self.board.play(pos, nnMove)
                            self.noSolMoves = self.noSolMoves+1
                            self.master.update_idletasks()
                            time.sleep(0.5 * self.options.replaySpeedVar.get())
                    self.statusbar.set('solved2')
                        
                else:              # navigate Solution
                    self.statusbar.set('empty')
                    self.board.state('normal', self.navSolutionNextMove)
                    self.undoButton.config(command = self.undoNavSol)
                    self.markRightWrong()
                
            else:                             # switch back to normal mode
                self.statusbar.set('empty')
                self.board.delMarks()
                self.undoButton.config(state=NORMAL, command = self.undo2)
                self.optionsmenu.entryconfig(5, state=NORMAL)

                self.board.state('normal', self.nextMove)
                self.board.undo(self.noSolMoves)
                for i in range(self.noSolMoves):
                    self.cursor.previous()
                self.noSolMoves=0

        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')


    def giveHint(self):

        try:
            self.board.state('disabled')
            self.creditAvailable = 0
            for i in range(self.cursor.wrongVariation):    # if in a wrong var. currently, go back first
                self.board.undo()
                self.cursor.previous()
                self.noMovesMade = self.noMovesMade - 1
                self.board.update_idletasks()
                time.sleep(0.5 * self.options.replaySpeedVar.get())


            if (self.inputColor == 'B' and not self.invertColor) or \
               (self.inputColor == 'W' and self.invertColor):
                nM = 'B'
                nnM = 'W'
            else:
                nM = 'W'
                nnM = 'B'
       
            nnMove = self.board.invert(self.inputColor)

            if not self.cursor.atEnd:
                corr = self.cursor.correctChildren()
                c = self.cursor.next(corr[randint(0,len(corr)-1)])  # choose one of the correct variations
                                                                    # by random
                pos = self.convCoord(c[nM][0], self.orientation)
                self.board.play(pos,self.inputColor)
                self.noMovesMade = self.noMovesMade + 1
                self.master.update_idletasks()
                time.sleep(0.5 * self.options.replaySpeedVar.get())
                if not self.cursor.atEnd:
                    c = self.cursor.next(randint(0,self.cursor.noChildren()-1)) # choose an answer randomly
                    pos = self.convCoord(c[nnM][0], self.orientation)
                    self.board.play(pos, nnMove)
                    self.master.update_idletasks()
                    time.sleep(0.5 * self.options.replaySpeedVar.get())
                    self.noMovesMade = self.noMovesMade + 1
                else:                      # problem solved
                    if self.clock.running: self.clock.stop()
                    self.statusbar.set('solved2') 
                    self.showSolutionButton.config(state=DISABLED)                        
                    self.board.state('disabled')

            self.board.state('normal', self.nextMove)
        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')


    def findNextParenthesis(self,s,i):
        """ Finds the first '(' after position i in the string s.
            Used to split the SGF file into single problems in readProblemColl. """
        
        j = i
        while j<len(s) and s[j] != '(':
            j = j + 1
        return j


    def findMatchingParenthesis(self,s,i):
        """ Finds the ')' matching the '(' at position i in the string s.
            Used to split the SGF file into single problems in readProblemColl. """
        
        j = i+1
        counter = 0
        while j < len(s) and counter >= 0 :
            if s[j] == '(' : counter = counter + 1
            elif s[j] == ')' : counter = counter - 1
            j = j+1
        return j-1


    def readProblemColl(self, path = None, filename = None):
        """ Read a collection of problems from the SGF file given by filename (if None, ask
            for a filename. The file is then split into single problems. The actual parsing
            is done in nextProblem (only the current problem is parsed), to save time. """

        if not self.options.problemModeVar.get():
            self.packGM(0)
            self.options.problemModeVar.set(1)
        
        if self.pbmRec:                  # save statistics for old problem collection
            self.pbmRec.saveToDisk()

        self.creditAvailable = 0
        self.clock.stop()
        self.clock.reset()
        self.cursor = None
        
        if not path or not filename:
            path, filename = os.path.split(tkFileDialog.askopenfilename(filetypes=[('SGF files', '*.sgf'),
                                                                                   ('All files', '*')],
                                                                        initialdir=self.sgfpath))
        if filename:
            try:
                f = open(os.path.join(path,filename))
                s = f.read()
                f.close()
            except IOError:
                showwarning('Open file', 'Cannot open this file\n')
                return
        else:
            self.currentFile = ''
            self.sgfpath = ''
            return
        
        i = 0
                
        self.comments.config(state=NORMAL)
        self.comments.delete('1.0', END)
        self.comments.insert('1.0', 'Reading SGF file ...')
        self.comments.config(state=DISABLED)
        self.board.clear()
        self.board.delMarks()
        self.statusbar.set('empty')
        self.pbmName.set('')
                
        if self.tryVarVar.get():
            self.tryVarButton.deselect()
            self.tryVariation()
        if self.showSolVar.get():
            self.showSolutionButton.deselect()
            self.showSolution()
        self.disableButtons()
        self.board.state('disabled')
        self.master.update()

        # Display everything before the first '(' as a comment:

        j = self.findNextParenthesis(s,0)
        comment = s[0:j]

        # split the file into single SGF games:

        self.pbms=[]
        while i<len(s):
            i = self.findNextParenthesis(s, i)
            if i<len(s):
                j = self.findMatchingParenthesis(s, i)
                self.pbms.append(s[i:j+1])
                i = j+1

        self.comments.config(state=NORMAL)
        self.comments.delete('1.0', END)
        self.comments.insert('1.0', comment)
        self.comments.config(state=DISABLED)

        self.pbmRec = PbmRecord(self.datpath + path, filename,
                                len(self.pbms), self.options.modeVar)

        if self.pbms:                             
            self.currentFile = filename
            self.sgfpath = path
            self.optionsmenu.entryconfig(9,state=NORMAL, command=self.pbmRec.changeMode)
        else:
            self.optionsmenu.entryconfig(9,state=DISABLED)

       
    def quit(self):
        """ Save statistics and name of current database and exit the program. """
        if self.pbmRec: self.pbmRec.saveToDisk()

        filename = os.path.join(self.optionspath, 'uligo.def')
        try:
            f = open(os.path.join(filename),'w')
            f.write('uligo03\n')
            f.write('s '+self.sgfpath+'\n')
            if self.currentFile: f.write('f '+self.currentFile +'\n')
            f.close()
        except IOError:
            showwarning('IOError', 'Could not write %s' % filename)

        self.saveOptions()
        self.frame.quit()


    def nextProblem(self):
        """ Display the next problem. """
        
        if not self.pbms: return

        n, co, ori = self.pbmRec.getNext()
        self.creditAvailable = 1

        try:
            c = EnhancedCursor(self.pbms[n], self.comments)
        except SGFError:
            showwarning('Parsing Error', 'Error in SGF file!')
            return

        self.statusbar.set('empty')

        if self.tryVarVar.get():
            self.tryVarButton.deselect()
            self.tryVariation()
        if self.showSolVar.get():
            self.showSolutionButton.deselect()
            self.showSolution()

        self.board.state('normal', self.nextMove)
        self.activateButtons()
        try:
            self.setup(c, ' ('+str(n+1)+')', 1, co, ori) # display problem
        except SGFError:
            showwarning('Parsing Error', 'Error in SGF file!')
            return

        self.setWhoseTurn(self.inputColor)
        self.printStatistics(0) # update statistics window
        self.clock.stop()
        self.clock.reset()
        self.clock.start() # and start the clock ...


    def setWhoseTurn(self, c):
        self.whoseTurnCanv.delete(ALL)
        
        if self.BsTurn:
            if c == 'B': self.whoseTurnCanv.create_image(40,50, image=self.BsTurn)
            else: self.whoseTurnCanv.create_image(40,50, image=self.WsTurn)
            self.whoseTurnCanv.create_text(100,50, text='TO PLAY', font=('Helvetica', 10, 'bold'))
        else:
            if c=='B': color = 'black'
            else: color = 'white'
            self.whoseTurnCanv.create_oval(53,53,78,78,fill=color,outline='')
         

    def backProblem(self):
        if self.pbms:
            try:
                n, co, ori = self.pbmRec.getPrevious()
            except:
                return
            self.creditAvailable = 0

            try:
                c = EnhancedCursor(self.pbms[n], self.comments)
            except SGFError:
                showwarning('Parsing Error', 'Error in SGF file!')
                return

            self.statusbar.set('empty')

            if self.tryVarVar.get():
                self.tryVarButton.deselect()
                self.tryVariation()
            if self.showSolVar.get():
                self.showSolutionButton.deselect()
                self.showSolution()

            self.board.state('normal', self.nextMove)
            self.activateButtons()
            try:
                self.setup(c, ' ('+str(n+1)+')', 1, co, ori) # display problem
            except SGFError:
                showwarning('Parsing Error', 'Error in SGF file!')
                return

            self.setWhoseTurn(self.inputColor)
            self.printStatistics(0) # update statistics window
            self.clock.stop()
            self.clock.reset()
            self.clock.start() # and start the clock ...


    def restartProblem(self):
        if self.cursor is None: return
        
        if self.creditAvailable:
            self.pbmRec.store(0)
            self.creditAvailable = 0
        self.statusbar.set('empty')

        if self.noMovesMade: changeOri = 0
        else: changeOri = 1

        if self.tryVarVar.get():
            self.tryVarButton.deselect()
            self.tryVariation()
            changeOri = 0
        if self.showSolVar.get():
            self.showSolutionButton.deselect()
            self.showSolution()
            changeOri = 0
            
        self.board.state('normal', self.nextMove)
        self.activateButtons()

        try:
            self.cursor.reset()
            self.setup(self.cursor, ' ('+str(self.pbmRec.current+1)+')', changeOri) # display problem
        except SGFError:
            showwarning('Parsing Error', 'Error in SGF file!')
            return

        self.setWhoseTurn(self.inputColor)
            
        self.clock.stop()
        self.clock.reset()
        self.clock.start() # and start the clock ...


    def playVar(self, p):
        """ React to mouse clicks in 'try variation' mode. """
        
        self.board.play(p)
        self.noTryVarMoves = self.noTryVarMoves + 1



    def timeover(self):
        """ React to timeover. """
        if self.creditAvailable:
            self.pbmRec.store(0)
            self.creditAvailable = 0

    
    def tryVariation(self):
        """ Switch between normal and 'try variation' mode. """
        
        if self.tryVarVar.get():                      # enter 'try variation' mode
            self.clock.stop()
            self.creditAvailable=0
            self.showSolutionButton.config(state=DISABLED)
            self.noTryVarMoves = 0
            self.board.state('normal', self.playVar)
            self.undoButton.config(state=NORMAL, command=self.undoTryVar)
            self.board.delMarks()
        else:                                         # exit 'try variation' mode
            if self.cursor.atEnd: self.board.state('disabled')
            else:           
                self.board.state('normal', self.nextMove)
            if self.cursor.wrongVariation or not self.cursor.atEnd:
                self.showSolutionButton.config(state=NORMAL)
            self.board.undo(self.noTryVarMoves)
            self.undoButton.config(command=self.undo2)
            if self.showSolVar.get():
                if self.options.animateSolVar.get():
                    self.undoButton.config(state=DISABLED)
                else:
                    self.undoButton.config(command=self.undoNavSol)
                    self.board.state('normal', self.navSolutionNextMove)
                    if self.inputColor == self.board.currentColor: self.markRightWrong()
                    else:                                          self.markAll()
                self.showSolutionButton.config(state=NORMAL)
        

    def clearStatistics(self):
        if not self.pbmRec: return
        path, filename = self.pbmRec.path, self.pbmRec.filename
        try:
            os.remove(os.path.join(path, filename))
        except IOError:
            showwarning('I/O Error', 'Could not delete .dat file.')

        self.pbmRec = None
        self.readProblemColl(path, filename[:-4]+'.sgf')
        self.printStatistics()

    def disableButtons(self):
        """ Disable 'Show solution', 'Try variation' and 'Undo' button. """

        
        self.showSolutionButton.deselect()
        self.tryVarButton.deselect()

        for b in [self.showSolutionButton, self.tryVarButton, self.undoButton,
                  self.hintButton]:
            b.config(state=DISABLED)


    def activateButtons(self):
        """ Enable 'Show solution', 'Try variation' and 'Undo' button. """

        for b in [self.showSolutionButton, self.tryVarButton, self.undoButton,
                  self.hintButton]:
            b.config(state=NORMAL)

    # ---- replay game mode ---------------------------------------------------------

    def packGM(self, pack):
        if pack:
            self.clock.pack_forget()
           
            self.gameInfoCanv.pack(expand=NO, fill=X, side=TOP)
            self.guessModeButtonFrame.pack(expand=NO, fill=X, side=TOP)
            self.guessModeCanvas.pack(expand=NO, side=BOTTOM)
            self.showSolutionButton.config(state=DISABLED)
            self.undoButton.config(state=DISABLED)
        
            self.tryVarButton.config(state=DISABLED)
            self.hintButton.config(state=NORMAL, command=self.giveHintGM)
            self.nextButton.config(state=DISABLED)
            self.backButton.config(state=DISABLED)
            self.restartButton.config(state=NORMAL, command=self.restartGM)

        else:
            self.guessModeButtonFrame.pack_forget()
            self.guessModeCanvas.pack_forget()
            self.gameInfoCanv.pack_forget()
            self.clock.pack(expand=NO)
            self.showSolutionButton.config(state=DISABLED)
            self.undoButton.config(state=DISABLED)
        
            self.tryVarButton.config(state=DISABLED)
            self.hintButton.config(state=NORMAL, command=self.giveHint)
            self.nextButton.config(state=NORMAL, command=self.nextProblem)
            self.backButton.config(state=NORMAL, command=self.backProblem)
            self.restartButton.config(state=NORMAL, command=self.restartProblem)


    def nextGM(self):
        if self.inputColor == 'B':
            nM = 'B'
            nnM = 'W'
        else:
            nM = 'W'
            nnM = 'B'
       
        nnMove = self.board.invert(self.inputColor)

        try:

            if not self.cursor.atEnd:
                corr = self.cursor.correctChildren()
                c = self.cursor.next()
                pos = self.convCoord(c[nM][0], self.orientation)
                self.board.play(pos,self.inputColor)
                self.noMovesMade = self.noMovesMade + 1
                self.master.update_idletasks()
            
            if self.cursor.atEnd:
                self.statusbar.set('end')
                self.board.state('disabled')

        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
            
            
    def restartGM(self):
        self.replayGame(self.sgfpath, self.currentFile)
        

    def changeModeGM(self):
        if self.options.modeVarGM.get() in ['B', 'W'] and self.options.modeVarGM.get() != self.inputColor:
            self.nextGM()
            self.inputColor = self.options.modeVarGM.get()
            

    def giveHintGM(self):
        if self.options.modeVarGM.get() == 'BW':
            self.nextGM()
            self.inputColor = self.board.invert(self.inputColor)
        else:
            self.nextGM()
            self.inputColor = self.board.invert(self.inputColor)
            time.sleep(0.3 * self.options.replaySpeedVar.get() + 0.3)
            self.nextGM()
            self.inputColor = self.board.invert(self.inputColor)

    
    def replayGame(self, path=None, filename=None, force=0):
        if self.options.problemModeVar.get() or force:
            self.packGM(1)
            self.options.problemModeVar.set(0)
            
            if self.pbmRec:
                self.pbmRec.saveToDisk()
                self.pbmRec = None
            self.clock.stop()
            self.clock.reset()
            if self.tryVarVar.get():
                self.tryVarButton.deselect()
                self.tryVariation()
            if self.showSolVar.get():
                self.showSolutionButton.deselect()
                self.showSolution()

            self.board.state('disabled')
            self.master.update()

            self.guessRightWrong = [0,0]
            self.guessModeCanvas.delete('non-bg')
            self.guessModeCanvas.create_rectangle(1,1,79,79, fill='#f99f59', outline='black', tags='non-bg')

        self.cursor = None
        if path is None:
            path, filename = os.path.split(tkFileDialog.askopenfilename(filetypes=[('SGF files', '*.sgf'),
                                                                                   ('All files', '*')],
                                                                        initialdir=self.sgfpath))
        if filename:
            try:
                f = open(os.path.join(path,filename))
                s = f.read()
                f.close()
            except IOError:
                showwarning('Open file', 'Cannot open this file\n')

            self.board.clear()
            self.board.delMarks()
            self.statusbar.set('empty')
            self.pbmName.set('')

            self.invertColor = 0
            self.orientation = 0
        else:
            self.currentFile = ''
            self.sgfpath = ''
            return

        self.board.state('normal', self.nextMoveReplay)
        
        self.comments.config(state=NORMAL)
        self.comments.delete('1.0', END)
        self.comments.config(state=DISABLED)
        self.currentFile = filename
        self.sgfpath = path
        self.optionsmenu.entryconfig(9,state=DISABLED)
        
        self.statusbar.set('empty')
        
        try:
            cursor = EnhancedCursor(s, self.comments)
            self.setup(cursor, '', 0, self.invertColor, self.orientation)
        except SGFError:
            showwarning('Parsing Error', 'Error in SGF file!')
            return
        
        self.whoseTurnCanv.delete(ALL)
        self.gameInfoCanv.delete(ALL)

        try:
            d = self.cursor.getRootNode(0)
            i = 0
            for tag, label in [('PW', 'White: '), ('PB', 'Black: '), ('DT', 'Date: '), ('RE', 'Result: ')]:
                if d.has_key(tag): self.gameInfoCanv.create_text(10, 20+20*i, text=label+d[tag][0], anchor='w')
                i += 1
        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
            return
        
        self.changeModeGM()

        
    def nextMoveReplay(self, p):
        """ React to mouse-click, in 'normal mode', i.e. answering a problem
            (as opposed to 'show solution' or 'try variation' mode). """

        self.board.play(p)  # put the stone on the board
        x, y = p

        if self.inputColor == 'B':
            nM = 'B'
            nnM = 'W'
        else:
            nM = 'W'
            nnM = 'B'

        nnMove = self.board.invert(self.inputColor)
       
        # look for the move in the SGF file

        try:
            done = 0 
            
            c = self.cursor.next(0)
            if c.has_key(nM): right_pos = self.convCoord(c[nM][0])
            if c.has_key(nM) and self.convCoord(c[nM][0], self.orientation)==(x,y): # found the move
                done = 1
                self.guessSuccess()
                if self.options.modeVarGM.get() in ['B', 'W'] and not self.cursor.atEnd: # respond to the move
                    self.board.update_idletasks()
                    time.sleep(0.3 * self.options.replaySpeedVar.get() + 0.3)
                    c = self.cursor.next()
                    pos = self.convCoord(c[nnM][0], self.orientation)
                    self.board.play(pos, nnMove)
                    self.noMovesMade = self.noMovesMade + 2
                else:
                    self.noMovesMade = self.noMovesMade + 1
                    self.inputColor = self.board.invert(self.inputColor)
                if self.cursor.atEnd:                      # problem solved / end of wrong var.
                    self.statusbar.set('end')
                    self.board.state('disabled')

            else:
                self.cursor.previous()
            
            if not done:                                  # not found the move in the SGF file, so it's wrong
                time.sleep(0.3 * self.options.replaySpeedVar.get() + 0.3) # show the move for a short time,
                self.board.undo()                                         # then delete it
                self.guessFailure(right_pos, (x,y))
        except SGFError:
            showwarning('SGF Error', 'Error in SGF file!')
            

    def guessSuccess(self):
        self.guessModeCanvas.delete('non-bg')
        self.guessModeCanvas.create_rectangle(1,1,79,79, fill='#f99f59', outline='black', tags='non-bg')

        self.guessModeCanvas.create_rectangle(10,10,70,70, fill='green', tags='non-bg')

        self.guessRightWrong[0] += 1

        perc = int(self.guessRightWrong[0] *
                   100.0/(self.guessRightWrong[0] + self.guessRightWrong[1]))
        self.guessModeCanvas.create_text(110, 20, text = `self.guessRightWrong[0]` + '/' + \
                                         `self.guessRightWrong[0] + self.guessRightWrong[1]`, tags='non-bg')
        self.guessModeCanvas.create_text(110, 40, text = `perc` + '%', tags='non-bg')
        
        if self.cursor.atEnd:
            self.guessModeCanvas.create_text(40, 40, text = 'END', font=('Helvetica', 16), tags='non-bg')


    def guessFailure(self, right, pos):
        self.guessModeCanvas.delete('non-bg')
        self.guessModeCanvas.create_rectangle(1,1,79,79, fill='#f99f59', outline='black', tags='non-bg')

        if self.cursor.atEnd:
            self.guessModeCanvas.create_rectangle(10,10,70,70, fill='green', tags='non-bg')
            
            self.guessModeCanvas.create_text(110, 20, text = `self.guessRightWrong[0]` + '/' + \
                                                        `self.guessRightWrong[0] + self.guessRightWrong[1]`, tags='non-bg')

            try:
                perc = int(self.guessRightWrong[0] *
                           100.0/(self.guessRightWrong[0] + self.guessRightWrong[1]))
                self.guessModeCanvas.create_text(110, 40, text = `perc` + '%', tags='non-bg')
            except ZeroDivisionError: pass
            self.guessModeCanvas.create_text(40, 40, text = 'END', font=('Helvetica', 16), tags='non-bg')
            return

        if not right or not pos:
            dx = 50
            dy = 50
            p0 = 40
            p1 = 40
        else:
            dist = int(4 * sqrt((right[0]-pos[0])*(right[0]-pos[0]) + (right[1]-pos[1])*(right[1]-pos[1])))

            dx = max(2, dist/3 + randint(0, dist/3))
            dy = max(2, dist/3 + randint(0, dist/3))

            p0 = right[0] * 4 + 2
            p1 = right[1] * 4 + 2

        self.guessModeCanvas.create_rectangle(p0-dx, p1-dy, min(80, p0+dx), min(80,p1+dx), fill='red',
                                              outline = '', tags='non-bg')

        self.guessRightWrong[1] += 1
        
        perc = int(self.guessRightWrong[0] *
                   100.0/(self.guessRightWrong[0] + self.guessRightWrong[1]))
        self.guessModeCanvas.create_text(110, 20, text = `self.guessRightWrong[0]` + '/' + \
                                                    `self.guessRightWrong[0] + self.guessRightWrong[1]`, tags='non-bg')
        self.guessModeCanvas.create_text(110, 40, text = `perc` + '%', tags='non-bg')
     
        

        
    # -------------------------------------------------------------------------------   

    def saveOptions(self):
        """ Save options to disk (to file 'uligo.opt'). """
        
        self.options.windowGeom = StringVar()
        self.options.windowGeom.set(self.master.geometry())
        self.options.saveToDisk(os.path.join(self.optionspath,'uligo.opt'),
                                lambda: showwarning('Save options', 'IO Error'))

        
    def loadOptions(self):
        """ Load options from disk. """
        
        self.options.windowGeom = StringVar()
        self.options.loadFromDisk(os.path.join(self.optionspath,'uligo.opt'))
        if self.options.windowGeom.get():
            self.master.geometry(self.options.windowGeom.get())


    def helpAbout(self):
        """ Display the 'About ...' window with the logo and some basic information. """
        
        t = 'uliGo 0.3 - written by Ulrich Goertz (u@g0ertz.de)\n\n'
        t = t + 'uliGo is a program to practice go problems.\n'
        t = t + 'You can find more information on uliGo and the newest '
        t = t + 'version at http://www.u-go.net/uligo/\n\n'
        
        t = t + 'uliGo is free software; it is published under the '
        t = t + 'GNU General Public License.\n\n'
        t = t + 'It is written in Python (see http://www.python.org/).\n\n'
        t = t + 'The images of the board and the stones were created by Patrice Fontaine.'
        
        window = Toplevel()
        window.title('About uliGo ...')

        canv = Canvas(window, width=400,height=200, highlightthickness=0)
        canv.pack()
        canv.create_image(200,100,image=self.logo)

        text = Text(window, height=15, width=60, relief=FLAT, wrap=WORD)
        text.insert(1.0, t)
 
        text.config(state=DISABLED)
        text.pack()

        b = Button(window, text="OK", command = window.destroy)
        b.pack(side=RIGHT)
        
        window.update_idletasks()
        
        window.focus()
        window.grab_set()
        window.wait_window


    def helpLicense(self):
        """ Display the GNU General Public License. """
        t = 'uliGo was written by Ulrich Goertz (u@g0ertz.de).\n' 
        t += 'It is published under the GNU General Public License (see below). ' 
        t += 'In particular you may freely distribute it if you do not change the ' 
        t += 'copyright notices and include all the files that belong to uliGo.\n' 
        t += 'This program is distributed WITHOUT ANY WARRANTY!\n\n'
        gpldeb = os.path.join('/usr', 'share', 'common-licenses', 'GPL')
        gpluli = os.path.join(self.uligopath, 'doc', 'license.txt')
        if os.path.exists(gpldeb): file = open(gpldeb)
        elif os.path.exists(gpluli): file = open(gpluli)
        else: file = None
        if file:
            t += '------------------------------------------------------------------------\n\n'
            t = t + file.read()
            file.close()
        self.textWindow(t,'uliGo license')


    def helpDoc(self):
        """ Display the documentation. """
        docdeb = os.path.join('/usr', 'share', 'doc', 'uligo', 'manual.html')
        doculi = os.path.join(self.uligopath, 'manual.html')
        if os.path.exists(docdeb): webbrowser.open('file:'+docdeb, new=1)
        elif os.path.exists(doculi): webbrowser.open('file:'+doculi, new=1)
        else:
            showwarning('Manual not found',
                        "The uliGo manual could not be found at %s or %s. Please check your uliGo installation." % (docdeb, doculi))

    def textWindow(self, t, title='', grab=1):
        """ Open a window and display the text in the string t.
            The window has the title title, and grabs the focus if grab==1. """
        
        window = Toplevel()
        window.title(title)
        text = ScrolledText(window, height=25, width=80, relief=FLAT, wrap=WORD)
        text.insert(1.0, t)
 
        text.config(state=DISABLED)
        text.pack()

        b = Button(window, text="OK", command = window.destroy)
        b.pack(side=RIGHT)
        
        window.update_idletasks()
        if grab:
            window.focus()
            window.grab_set()
            window.wait_window



    def __init__(self, master):
        """ Initialize the GUI, some variables, etc. """

        # The main window
        
        self.master = master
        self.frame = Frame(master)
        self.frame.pack(expand=YES, fill=BOTH)

        leftFrame = Frame(self.frame)
        rightFrame = Frame(self.frame)
        middleFrame = Frame(self.frame, width=10)
        leftFrame.pack(side=LEFT)
        middleFrame.pack(side=LEFT)
        rightFrame.pack(side=RIGHT, expand=YES, fill=BOTH)

        # The board and the clock

        self.board = Board(rightFrame, 19, (30,25))
        self.clockFrame = Frame(leftFrame)
        self.clock = clock.Clock(self.clockFrame, 150, self.timeover)

        self.options = BunchTkVar()
        self.options.maxTime = self.clock.maxTime
        self.options.use3Dstones = self.board.use3Dstones
        self.options.problemModeVar = IntVar()
        self.options.problemModeVar.set(1)

        # ---- 'guess next move' mode stuff --------------------------------------------------------

        self.gameInfoCanv = Canvas(self.clockFrame, width=100, height=100, highlightthickness=0)

        self.guessModeButtonFrame = Frame(self.clockFrame)
        self.guessModeCanvas = Canvas(self.clockFrame, height=80, width=150)
        self.options.modeVarGM = StringVar()
        self.options.modeVarGM.set('BW')
        Label(self.guessModeButtonFrame, text='Guess ').pack(side=LEFT, expand=NO)
        self.BbuttonGM = Radiobutton(self.guessModeButtonFrame, text='B', variable=self.options.modeVarGM,
                                     indicatoron=0,
                                     command=self.changeModeGM, value='B')
        self.WbuttonGM = Radiobutton(self.guessModeButtonFrame, text='W', variable=self.options.modeVarGM,
                                     indicatoron=0,
                                     command=self.changeModeGM, value='W')
        self.BWbuttonGM= Radiobutton(self.guessModeButtonFrame, text='BW', variable=self.options.modeVarGM,
                                     indicatoron=0,
                                     command=self.changeModeGM, value='BW')
        for b in [self.BbuttonGM, self.WbuttonGM, self.BWbuttonGM]: b.pack(side=LEFT, expand=NO)
        
        # ------------------------------------------------------------------------------------------
        # The menus

        menu = Menu(master)
        master.config(menu=menu)

        filemenu = Menu(menu)
        menu.add_cascade(label='File', underline=0, menu=filemenu)
        filemenu.add_command(label='Open problem collection ...', underline=0, command=self.readProblemColl)
        filemenu.add_command(label='Replay game', underline=0, command=self.replayGame)
        filemenu.add_separator()
        filemenu.add_command(label='Clear Statistics', underline=0, command=self.clearStatistics)
        filemenu.add_command(label='Statistics', underline=0, command=self.printStatistics)
        filemenu.add_separator()
        filemenu.add_command(label='Exit', underline =1, command=self.quit)
        self.optionsmenu = Menu(menu)
        menu.add_cascade(label='Options', underline=0, menu=self.optionsmenu)

        self.options.fuzzy = self.board.fuzzy    # make 'save options' easy
        self.optionsmenu.add_checkbutton(label='Fuzzy stone placement', underline = 0, 
                                         variable=self.options.fuzzy, command=self.board.fuzzyStones)

        self.options.shadedStoneVar = self.board.shadedStoneVar
        self.options.shadedStoneVar.set(1)
        self.optionsmenu.add_checkbutton(label='Shaded stone mouse pointer', underline = 0, 
                                         variable=self.options.shadedStoneVar)

        self.options.allowInvertColorVar = IntVar()
        self.options.allowInvertColorVar.set(1)
        self.optionsmenu.add_checkbutton(label='Allow color switch', underline = 7, 
                                         variable=self.options.allowInvertColorVar)

        self.options.allowRotatingVar = IntVar()
        self.options.allowRotatingVar.set(1)
        self.optionsmenu.add_checkbutton(label='Allow mirroring/rotating', underline = 6,
                                         variable=self.options.allowRotatingVar)

        self.options.animateSolVar = IntVar()
        self.options.animateSolVar.set(1)
        animSolMenu = Menu(self.optionsmenu)
        self.optionsmenu.add_cascade(label='Show solution mode', underline = 7, menu=animSolMenu)
        animSolMenu.add_radiobutton(label='animate', variable = self.options.animateSolVar, value = 1)
        animSolMenu.add_radiobutton(label='navigate', variable = self.options.animateSolVar, value = 0)

        self.options.replaySpeedVar = IntVar()
        self.options.replaySpeedVar.set(2)
        replaySp = Menu(self.optionsmenu)
        self.optionsmenu.add_cascade(label='Replay speed', underline = 0, menu=replaySp)
        replaySp.add_radiobutton(label='very fast', variable=self.options.replaySpeedVar, value=0)
        replaySp.add_radiobutton(label='fast', variable=self.options.replaySpeedVar, value=1)
        replaySp.add_radiobutton(label='medium', variable=self.options.replaySpeedVar, value=2)
        replaySp.add_radiobutton(label='slow', variable=self.options.replaySpeedVar, value=4)

        self.optionsmenu.add_command(label='Change clock settings', underline=7, 
                                     command=self.clock.changeMaxtime)

        wrongmenu = Menu(self.optionsmenu)
        self.optionsmenu.add_cascade(label='Wrong variations', menu=wrongmenu)
        self.options.wrongVar = IntVar()
        self.options.wrongVar.set(1)
        wrongmenu.add_radiobutton(label='Show WRONG at the end of variation',
                                         variable=self.options.wrongVar, value=0)
        wrongmenu.add_radiobutton(label='Show WRONG when entering variation',
                                         variable=self.options.wrongVar, value=1)
        wrongmenu.add_radiobutton(label='Do not descend into wrong variations',
                                         variable=self.options.wrongVar, value=2)

        self.optionsmenu.add_command(label='Random/sequential order mode', underline=2,
                                     state=DISABLED)
        self.options.modeVar = IntVar()
        self.options.modeVar.set(0)

        self.optionsmenu.add_checkbutton(label='Use 3D stones', variable=self.options.use3Dstones,
                                         command=self.board.resize)

        self.helpmenu = Menu(menu, name='help')
        menu.add_cascade(label='Help', underline=0, menu=self.helpmenu)

        self.helpmenu.add_command(label='About ...', underline=0, command=self.helpAbout)
        self.helpmenu.add_command(label='Documentation', underline=0, command=self.helpDoc)
        self.helpmenu.add_command(label='License', underline=0, command=self.helpLicense)

        # The buttons

        bframe = Frame(leftFrame)
        bframe.pack(side=TOP)

        self.backButton = Button(bframe, text='Back', fg='blue', command=self.backProblem,
                                 underline=0)
        self.restartButton = Button(bframe, text='Re', fg='blue', command=self.restartProblem,
                                 underline=0)
        self.nextButton = Button(bframe, text='Next', fg='blue', command=self.nextProblem,
                                 underline = 0)
        self.frame.bind('<n>', lambda e, s=self.nextButton: s.invoke())
        self.frame.bind('<q>', lambda e, self=self: self.quit())
        
        self.whoseTurnCanv = Canvas(leftFrame, height = 180, width = 130, highlightthickness=0)
        self.whoseTurnID = 0

        self.statusbar = StatusBar(leftFrame)

        b1frame = Frame(leftFrame)
        b1frame.pack(side=TOP)

        self.showSolVar = IntVar()
        self.showSolutionButton = Checkbutton(b1frame, text='Show solution', fg='blue',
                                              underline=0,
                                              indicatoron=0, variable=self.showSolVar, command=self.showSolution)
        self.frame.bind('<s>', lambda e, s=self.showSolutionButton: s.invoke())

        self.hintButton = Button(b1frame, text='Hint', command=self.giveHint)

        b2frame = Frame(leftFrame)
        b2frame.pack(side=TOP)

        self.undoButton = Button(b2frame, text='Undo', fg='blue', command=self.undo2,
                                 underline=0)
        self.frame.bind('<u>', lambda e, s=self.undoButton: s.invoke())

        self.tryVarVar = IntVar()
        self.tryVarButton = Checkbutton(b2frame, text='Try variation', fg='blue', 
                                        indicatoron=0, variable=self.tryVarVar, command=self.tryVariation)
        self.frame.bind('<t>', lambda e, s=self.tryVarButton: s.invoke())

        self.pbmName = StringVar()
        self.pbmNameLabel = Label(leftFrame, height=1, width=15, relief=SUNKEN, justify=LEFT,
                                  textvariable=self.pbmName)

        self.comments = ScrolledText(rightFrame, height = 5, width = 70, wrap=WORD, 
                              relief=SUNKEN, state = DISABLED)

        self.uligopath = sys.path[0]     # the path where uligo.py, board.py, clock.py, Sgflib,
                                         # uligo.doc and uligo.def reside (if uligo is installed
                                         # system-wide under Unix, each user may additionally
                                         # have his own uligo.def in $HOME/.uligo

        self.sgfpath = os.path.join(self.uligopath,'sgf') # default path for sgf files, may be overridden
                                                          # in uligo.def
        self.datpath = ''                  # default prefix to get the path for .dat files from sgfpath
                                           # (if sgf's and dat's are in the same directory, this is '',
                                           # if dat's are in  $HOME/.uligo (under Unix), this should
                                           # be '/home/username/.uligo'
        self.optionspath = self.uligopath  # default path for .opt and (individual) .def files
        self.currentFile = ''              # default sgf file


        # try to load button images

        self.tkImages = []
        try:
            for button, imageFile in [(self.backButton, 'left'), (self.restartButton, 'reload'),
                                      (self.nextButton, 'right'), (self.hintButton, 'hint'),
                                      (self.showSolutionButton, 'showsol'),
                                      (self.tryVarButton, 'tryvar'), (self.undoButton, 'undo'),
                                      (self.BbuttonGM, 'b'), (self.WbuttonGM, 'w'), (self.BWbuttonGM, 'bw')]:
                im = PhotoImage(file = os.path.join(self.uligopath, 'gifs', imageFile+'.gif'))
                button.config(image=im)
                self.tkImages.append(im)
        except (TclError, IOError): pass

        try:
            im = PhotoImage(file = os.path.join(self.uligopath, 'gifs', 'bgd.gif'))
            self.guessModeCanvas.create_image(75,40, image=im)
            self.tkImages.append(im)
        except (TclError, IOError): pass

        try:
            self.BsTurn = PhotoImage(file = os.path.join(self.uligopath, 'gifs', 'BsTurn.gif'))
            self.WsTurn = PhotoImage(file = os.path.join(self.uligopath, 'gifs', 'WsTurn.gif'))
        except (TclError, IOError):
            self.BsTurn = None
            self.WsTurn = None

        # pack everything

        self.backButton.pack(side=LEFT, expand=YES, fill=BOTH)
        self.restartButton.pack(side=LEFT, expand=YES, fill=BOTH)                         
        self.nextButton.pack(side=LEFT, expand=YES, fill=BOTH)
        self.hintButton.pack(side=LEFT, expand=YES, fill=BOTH)
        self.showSolutionButton.pack(expand=YES, fill=BOTH)
        self.undoButton.pack(side=LEFT, expand=YES, fill=BOTH)
        self.tryVarButton.pack(expand=YES, fill=BOTH)

        emptySpace = Frame(leftFrame, height=40)
        emptySpace.pack(expand=YES, fill=BOTH, side=BOTTOM)

        self.statusbar.pack(expand=YES, fill=BOTH, side=BOTTOM)
        self.pbmNameLabel.pack(expand=NO, fill=X, side=BOTTOM)

        emptySpace = Frame(leftFrame, height=10)
        emptySpace.pack(expand=YES, fill=BOTH, side=BOTTOM)

        self.clockFrame.pack(expand=YES, fill=X, side=BOTTOM)
        self.clock.pack(expand=NO, side=BOTTOM)
        self.whoseTurnCanv.pack(expand=YES, fill=BOTH)
        self.comments.pack(expand=YES, fill=BOTH, side=BOTTOM)
        self.board.pack(expand=YES, fill=BOTH)

        # The statistics window (initially withdrawn)

        self.statisticsWindow = Toplevel()
        self.statisticsWindow.withdraw()
        self.statisticsWindow.title('Statistics')
        self.statisticsText = StringVar()
        Label(self.statisticsWindow, height=10, width=50, justify=LEFT, font = ('Courier', 12),
               textvariable=self.statisticsText).pack()
        self.statisticsWindow.protocol('WM_DELETE_WINDOW', self.statisticsWindow.withdraw)        

        # load options, and some initialization
 
        self.pbms = []
        self.pbmRec = None

        self.disableButtons()
        self.board.update_idletasks()

        # read the uligo.def file (default problem collection)

        try:
            f = open(os.path.join(self.uligopath,'uligo.def'))
            s = split(f.read(),'\n')
            f.close()
        except IOError:
            pass
        else:
            if s[0]=='uligo03':      # otherwise this is an old .def file which should be ignored
                counter = 1
                while 1:
                    line = s[counter]
                    counter = counter + 1
                    if line and line[0] == 'i':            # refer to individual def-file
                        l = line[2:]
                        self.optionspath = os.path.join(os.getenv('HOME',l),'.uligo')
                        self.datpath = self.optionspath
                        
                        if not os.path.exists(self.optionspath):
                            os.mkdir(self.optionspath)
                        try:
                            f1 = open(os.path.join(self.optionspath, 'uligo.def'))
                            s1 = split(f1.read(),'\n')
                            for l1 in s1: s.append(l1)
                        except IOError:
                            pass
                    elif line and line[0] == 'd':          # new datpath
                        s1 = split(line)
                        if len(s1)>1: self.datpath = line[2:]
                        else: self.datpath = ''
                    elif line and line[0] == 's':          # new sgfpath
                        self.sgfpath = line[2:]
                    elif line and line[0] == 'f':          # default sgf file
                        self.currentFile = line[2:]
                    if counter >= len(s): break
                    
        self.loadOptions()
        master.deiconify()
        self.cursor = None

        # display the logo
        
        currentTime = time.time()
        self.board.update()
        
        try:
            self.logo = PhotoImage(file=os.path.join(self.uligopath,'gifs/logo.gif'))
            s = 2 * self.board.canvasSize[0] + 18 * self.board.canvasSize[1]  # size of canvas in pixel
            im = self.board.create_image(max(0,(s-400)/2),max(0,(s-190)/2),
                                         image=self.logo, tags='logo', anchor=NW)
            self.board.tkraise(im)
            self.board.update_idletasks()
        except TclError:
            pass
                
        
        if self.options.problemModeVar.get():
            if self.currentFile: self.readProblemColl(self.sgfpath, self.currentFile)
        else:
            if self.currentFile: self.replayGame(self.sgfpath, self.currentFile, 1)

        # and remove the logo ...
        
        if time.time()-currentTime < 1:
            time.sleep(1 - time.time() + currentTime) # show logo for at least 1 second
        self.board.delete('logo')

# ---------------------------------------------------------------------------------------

root = Tk()
root.withdraw()

try:
    root.option_readfile(os.path.join(sys.path[0], 'uligo.app'))
except TclError:
    showwarning('Error', 'Error reading uligo.app')
    
app = App(root)

root.protocol('WM_DELETE_WINDOW', app.quit)
root.title('uliGo')

root.resizable(1,1)

app.frame.focus_force()
root.tkraise()

root.mainloop()
