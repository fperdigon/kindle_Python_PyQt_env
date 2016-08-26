# file: board1.py

##   This file is part of Kombilo, a go database program
##   It contains classes implementing an abstract go board and a go
##   board displayed on the screen.

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
from random import randint
import math
import sys
import os

try:   # PIL installed?
    import GifImagePlugin
    import Image
    import ImageTk
    import ImageEnhance
    PILinstalled = 1
except:
    PILinstalled = 0


class abstractBoard:
    """ This class administrates a go board.
        It keeps track of the stones currently on the board in the dictionary self.status,
        and of the moves played so far in self.undostack

        It has methods to clear the board, play a stone, undo a move. """

    def __init__(self, boardSize = 19):
        self.status = {}
        self.undostack = []
        self.boardSize = boardSize

    def neighbors(self,x):
        """ Returns the coordinates of the 4 (resp. 3 resp. 2 at the side / in the corner) intersections
            adjacent to the given one. """
        if   x[0]== 1              :     l0 = [2]
        elif x[0]== self.boardSize :     l0 = [self.boardSize-1]
        else:                            l0 = [x[0]-1, x[0]+1]

        if   x[1]== 1              :     l1 = [2]
        elif x[1]== self.boardSize :     l1 = [self.boardSize-1]
        else:                            l1 = [x[1]-1, x[1]+1]

        l = []
        for i in l0: l.append((i,x[1]))
        for j in l1: l.append((x[0],j))

        return l

    def clear(self):
        """ Clear the board """
        self.status = {}
        self.undostack=[]        

    def play(self,pos,color):
        """ This plays a color=black/white stone at pos, if that is a legal move
            (disregarding ko), and deletes stones captured by that move.
            It returns 1 if the move has been played, 0 if not. """

        if self.status.has_key(pos):                # check if empty
            return 0

        l = self.legal(pos,color)
        if l:                                       # legal move?
            captures = l[1]
            for x in captures: del self.status[x]   # remove captured stones, if any
            self.undostack.append((pos,color,captures))   # remember move + captured stones for easy undo
            return 1
        else: return 0

    def legal(self, pos, color):
        """ Check if a play by color at pos would be a legal move. """
        c = [] # captured stones
        for x in self.neighbors(pos):
            if self.status.has_key(x) and self.status[x]==self.invert(color):
                c = c + self.hasNoLibExcP(x, pos)        

        self.status[pos]=color

        if c:
            captures = []
            for x in c:
                if not x in captures: captures.append(x)
            return (1, captures)

        if self.hasNoLibExcP(pos):
            del self.status[pos]
            return 0
        else: return (1, [])

    def hasNoLibExcP(self, pos, exc = None):
        """ This function checks if the string (=solidly connected) of stones containing
            the stone at pos has a liberty (resp. has a liberty besides that at exc).
            If no liberties are found, a list of all stones in the string is returned.

            The algorithm is a non-recursive  implementation of a simple flood-filling:
            starting from the stone at pos, the main while-loop looks at the intersections
            directly adjacent to the stones found so far, for liberties or other stones that belong
            to the string. Then it looks at the neighbors of those newly found stones, and so
            on, until it finds a liberty, or until it doesn't find any new stones belonging
            to the string, which means that there are no liberties.
            Once a liberty is found, the function returns immediately. """
            
        st = []            # in the end, this list will contain all stones solidly connected to the
                           # one at pos, if this string has no liberties
        newlyFound = [pos] # in the while loop, we will look at the neighbors of stones in newlyFound
        foundNew = 1
        
        while foundNew:
            foundNew = 0
            n = []         # this will contain the stones found in this iteration of the loop
            for x in newlyFound:
                for y in self.neighbors(x):
                    if not self.status.has_key(y) and y != exc:    # found a liberty
                        return []
                    elif self.status.has_key(y) and self.status[y]==self.status[x] \
                         and not y in st and not y in newlyFound: # found another stone of same color
                        n.append(y)
                        foundNew = 1

            st[:0] = newlyFound
            newlyFound = n

        return st     # no liberties found, return list of all stones connected to the original one

    def undo(self, no=1):
        """ Undo the last no moves. """
        for i in range(no):
            if self.undostack:
                pos, color, captures = self.undostack.pop()
                del self.status[pos]
                for p in captures: self.status[p] = self.invert(color)

    def remove(self, pos):
        """ Remove a stone form the board, and store this action in undostack. """
        
        self.undostack.append(((-1,-1), self.invert(self.status[pos]), [pos]))
        del self.status[pos]

    def invert(self,color):
        if color == 'B': return 'W'
        else: return 'B'


class Board(abstractBoard, Canvas):
    """ This is a go board, displayed on the associated canvas.
        canvasSize is a pair, the first entry is the size of the border, the second
        entry is the distance between two go board lines, both in pixels.

        The most important methods are:

        - play: play a stone of some color at some position (if that is a legal move)
        - undo: undo one (or several) moves
        - state: activate (state("normal", f) - the function f is called when a stone
                 is placed on the board) or disable (state("disabled")) the board;

        - placeMark: place a colored label (slightly smaller than a stone) at some position
        - delMarks: delete all these labels
        - placeLabel: place a label (a letter, a circle, square, triangle or cross)
    """

    def __init__(self, master, boardSize = 19, canvasSize = (30,25), fuzzy=1, labelFont = None,
                 focus=1, callOnChange=None):

        self.focus = focus
        self.coordinates = 0
        
        self.canvasSize = canvasSize
        size = 2*canvasSize[0] + (boardSize-1)*canvasSize[1] # size of the canvas in pixel
        Canvas.__init__(self, master, height = size, width =  size, highlightthickness = 0)

        abstractBoard.__init__(self, boardSize)

        self.changed = IntVar()  # this is set to 1 whenever a change occurs (placing stone, label etc.)
        self.changed.set(0)      # this is used for Kombilo's 'back' method 

        if callOnChange: self.callOnChange = callOnChange
        else: self.callOnChange = lambda: None
        self.noChanges = 0

        self.fuzzy = IntVar()   # if self.fuzzy is true, the stones are not placed precisely
        self.fuzzy.set(fuzzy)   # on the intersections, but randomly a pixel off

        if labelFont:
            self.labelFont = labelFont
        else:
            self.labelFont = (StringVar(), IntVar(), StringVar())
            self.labelFont[0].set('Helvetica')
            self.labelFont[1].set(5)
            self.labelFont[2].set('bold')
            
        self.shadedStoneVar = IntVar()  # if this is true, there is a 'mouse pointer' showing
        self.shadedStonePos = (-1,-1)   # where the next stone would be played, given the current
                                        # mouse position

        self.currentColor = 'B'     # the expected color of the next move

        self.stones = {}            # references to the ovals placed on the canvas, used for removing stones
        self.marks = {}             # references to the (colored) marks on the canvas
        self.labels = {}
        
        self.bind("<Configure>", self.resize)
        self.resizable = 1

        global PILinstalled
        gifpath = os.path.join(sys.path[0],'gifs')
        
        try:
            self.img = PhotoImage(file=os.path.join(gifpath, 'board.gif'))
        except TclError:
            self.img = None

        self.use3Dstones = IntVar()
        self.use3Dstones.set(1)

        if PILinstalled:
            try:
                self.blackStone = Image.open(os.path.join(gifpath, 'black.gif')).convert('RGBA')
                self.whiteStone = Image.open(os.path.join(gifpath, 'white.gif')).convert('RGBA')
            except IOError:
                PILinstalled = 0

        self.drawBoard()


    def drawBoard(self):
        """ Displays the background picture, and draws the lines and hoshi points of
            the go board.
            If PIL is installed, this also creates the PhotImages for black, white stones. """

        self.delete('non-bg')     # delete everything except for background image
        c0, c1 = self.canvasSize
        size = 2*c0 + (self.boardSize-1)*c1
        self.config(height=size, width=size)
        
        if self.img:
            self.delete('board')
            for i in range(size/100 + 1):
                for j in range(size/100 + 1):
                    self.create_image(100*i,100*j,image=self.img, tags='board')

        color = 'black'

        for i in range(self.boardSize):
	    self.create_line(c0, c0 + c1*i, c0 + (self.boardSize-1)*c1, c0 + c1*i, fill=color, tags='non-bg')
	    self.create_line(c0 + c1*i, c0, c0 + c1*i, c0+(self.boardSize-1)*c1, fill=color, tags='non-bg')

        # draw hoshi's:

        if c1 > 7:

            if self.boardSize in [13,19]:
                b = (self.boardSize-7)/2
                for i in range(3):
                    for j in range(3): 
                        self.create_oval(c0 + (b*i+3)*c1 - 2, c0 + (b*j+3)*c1 - 2,
                                         c0 + (b*i+3)*c1 + 2, c0 + (b*j+3)*c1 + 2, fill = 'black', tags='non-bg')
            elif self.boardSize == 9:
                self.create_oval(c0 + 4*c1 - 2, c0 + 4*c1 - 2,
                                 c0 + 4*c1 + 2, c0 + 4*c1 + 2, fill = 'black', tags='non-bg')

        # draw coordinates:

        if self.coordinates:
            for i in range(self.boardSize):
                a = 'ABCDEFGHJKLMNOPQRST'[i]
                self.create_text(c0 + c1*i, c1*self.boardSize+3*c0/4+4, text=a,
                                 font = ('Helvetica', 5+c1/7, 'bold'))
                self.create_text(c0 + c1*i, c0/4+1, text=a, font = ('Helvetica', 5+c1/7, 'bold'))
                self.create_text(c0/4+1, c0+c1*i, text=`self.boardSize-i`,font = ('Helvetica', 5+c1/7, 'bold'))
                self.create_text(c1*self.boardSize+3*c0/4+4, c0 + c1*i, text=`self.boardSize-i`, font = ('Helvetica', 5+c1/7, 'bold'))
                


        global PILinstalled
        if PILinstalled:
            try:
                self.bStone = ImageTk.PhotoImage(self.blackStone.resize((c1,c1)))
                self.wStone = ImageTk.PhotoImage(self.whiteStone.resize((c1,c1)))
            except:
                PILinstalled = 0




    def resize(self, event = None):
        """ This is called when the window containing the board is resized. """

        if not self.resizable: return

        self.noChanges = 1

        if event: w, h = event.width, event.height
        else:     w, h = int(self.cget('width')), int(self.cget('height'))
        m = min(w,h)

        self.canvasSize = (m/20 + 4, (m - 2*(m/20+4))/(self.boardSize-1))

        self.drawBoard()
            

        # place a gray rectangle over the board background picture
        # in order to make the board quadratic

        self.create_rectangle(h+1, 0, h+1000, w+1000,
                              fill ='grey88', outline='', tags='non-bg')     
        self.create_rectangle(0, w+1, h+1000, w+1000,
                              fill='grey88', outline='', tags='non-bg')

            
        for x in self.status.keys(): self.placeStone(x, self.status[x])
        for x in self.marks.keys(): self.placeMark(x, self.marks[x])
        for x in self.labels.keys(): self.placeLabel(x, '+'+self.labels[x][0], self.labels[x][1])

        self.tkraise('sel') # this is for the list of previous search patterns ...

        self.noChanges = 0


    def play(self, pos, color=None):
        """ Play a stone of color (default is self.currentColor) at pos. """

        if color is None: color = self.currentColor
        if abstractBoard.play(self, pos, color):                    # legal move?
            captures = self.undostack[len(self.undostack)-1][2]     # retrieve list of captured stones
            for x in captures:
                self.delete(self.stones[x])
                del self.stones[x]
            self.placeStone(pos, color)
            self.currentColor = self.invert(color)
            self.delShadedStone()
            return 1
        else: return 0

    def state(self, s, f=None):
        """ s in "normal", "disabled": accepting moves or not
            f the function to call if a move is entered 
            [More elegant solution might be to replace this by an overloaded bind method,
            for some event "Move"?!]  """

        if s == "normal":
            self.callOnMove = f
            self.bound1 = self.bind("<Button-1>", self.onMove)  
            self.boundm = self.bind("<Motion>", self.shadedStone)
            self.boundl = self.bind("<Leave>", self.delShadedStone)
        elif s == "disabled":
            self.delShadedStone()
            try:
                self.unbind("<Button-1>", self.bound1)
                self.unbind("<Motion>", self.boundm)
                self.unbind("<Leave>", self.boundl)
            except (TclError, AttributeError): pass                     # if board was already disabled, unbind will fail
            
    def onMove(self, event):
        # compute board coordinates from the pixel coordinates of the mouse click

        if self.focus:
            self.master.focus()
        x,y = self.getBoardCoord((event.x, event.y), self.shadedStoneVar.get())
        if (not x*y): return

        if abstractBoard.play(self,(x,y), self.currentColor): # would this be a legal move?
            abstractBoard.undo(self)
            self.callOnMove((x,y))

    def onChange(self):
        if self.noChanges: return
        self.callOnChange()
        self.changed.set(1)


    def getPixelCoord(self, pos, nonfuzzy = 0):
        """ transform go board coordinates into pixel coord. on the canvas of size canvSize """

        fuzzy1 = randint(-1,1) * self.fuzzy.get() * (1-nonfuzzy)
        fuzzy2 = randint(-1,1) * self.fuzzy.get() * (1-nonfuzzy)
        c1 = self.canvasSize[1]
        a = self.canvasSize[0] - self.canvasSize[1] - self.canvasSize[1]/2 
        b = self.canvasSize[0] - self.canvasSize[1] + self.canvasSize[1]/2 
        return (c1*pos[0]+a+fuzzy1, c1*pos[1]+a+fuzzy2, c1*pos[0]+b+fuzzy1, c1*pos[1]+b+fuzzy2) 

    def getBoardCoord(self, pos, sloppy=1):
        """ transform pixel coordinates on canvas into go board coord. in [1,..,boardSize]x[1,..,boardSize]
            sloppy refers to how far the pixel may be from the intersection in order to
            be accepted """

        if sloppy: a, b = self.canvasSize[0]-self.canvasSize[1]/2, self.canvasSize[1]-1
        else:      a, b = self.canvasSize[0]-self.canvasSize[1]/4, self.canvasSize[1]/2

        if (pos[0]-a)%self.canvasSize[1] <= b: x = (pos[0]-a)/self.canvasSize[1] + 1
        else:                                  x = 0
        
        if (pos[1]-a)%self.canvasSize[1] <= b: y = (pos[1]-a)/self.canvasSize[1] + 1
        else:                  y = 0

        if x<0 or y<0 or x>self.boardSize or y>self.boardSize: x = y = 0

        return (x,y)    

    def placeMark(self, pos, color):
        """ Place colored mark at pos. """
        x1, x2, y1, y2 = self.getPixelCoord(pos, 1)
        self.create_oval(x1+2, x2+2, y1-2, y2-2, fill = color, tags=('marks','non-bg'))
        self.marks[pos]=color
        self.onChange()

    def delMarks(self):
        """ Delete all marks. """
        if self.marks: self.onChange()
        self.marks = {}
        self.delete('marks')

    def delLabels(self):
        """ Delete all labels. """
        if self.labels: self.onChange()
        self.labels={}
        self.delete('label')

    def remove(self, pos):
        """ Remove the stone at pos, append this as capture to undostack. """
        if self.status.has_key(pos):
            self.onChange()
            self.delete(self.stones[pos])
            del self.stones[pos]
            abstractBoard.remove(self, pos)
            self.update_idletasks()
            return 1
        else: return 0

    def placeLabel(self, pos, type, text=None, color=None, override=None):
        """ Place label of type type at pos; used to display labels
            from SGF files. If type has the form +XX, add a label of type XX.
            Otherwise, add or delete the label, depending on if there is no label at pos,
            or if there is one."""

        if type[0] != '+':

            if self.labels.has_key(pos):
                if self.labels[pos][0] == type:
                    for item in self.labels[pos][2]: self.delete(item)
                    del self.labels[pos]
                    return
                else:
                    for item in self.labels[pos][2]: self.delete(item)
                    del self.labels[pos]

            self.onChange()

        else: type = type[1:]

        labelIDs = []

        if override:
            fcolor = override[0]
            fcolor2 = override[1]
        elif self.status.has_key(pos) and self.status[pos]=='B':
            fcolor = 'white'
            fcolor2 = '#FFBA59'
        elif self.status.has_key(pos) and self.status[pos]=='W':
            fcolor = 'black'
            fcolor2 = ''
        else:
            fcolor = color or 'black'
            fcolor2 = '#FFBA59'
                    
        x1, x2, y1, y2 = self.getPixelCoord(pos, 1)
        if type == 'LB':
            labelIDs.append(self.create_oval(x1+3, x2+3, y1-3, y2-3, fill=fcolor2, outline='',
                                             tags=('label', 'non-bg')))
            labelIDs.append(self.create_text((x1+y1)/2,(x2+y2)/2, text=text, fill=fcolor,
                                             font = (self.labelFont[0].get(), self.labelFont[1].get() + self.canvasSize[1]/5,
                                                     self.labelFont[2].get()),
                                             tags=('label', 'non-bg')))
        elif type == 'SQ':
            labelIDs.append(self.create_rectangle(x1+6, x2+6, y1-6, y2-6, fill = fcolor, tags=('label','non-bg')))
        elif type == 'CR':
            labelIDs.append(self.create_oval(x1+5, x2+5, y1-5, y2-5, fill='', outline=fcolor, tags=('label','non-bg')))
        elif type == 'TR':
            labelIDs.append(self.create_polygon((x1+y1)/2, x2+5, x1+5, y2-5, y1-5, y2-5, fill = fcolor,
                                                tags = ('label', 'non-bg')))
        elif type == 'MA':
            labelIDs.append(self.create_oval(x1+2, x2+2, y1-2, y2-2, fill=fcolor2, outline='',
                             tags=('label', 'non-bg')))
            labelIDs.append(self.create_text(x1+12,x2+12, text='X', fill=fcolor,
                                             font = (self.labelFont[0].get(), self.labelFont[1].get() + 1 + self.canvasSize[1]/5,
                                                     self.labelFont[2].get()),
                                             tags=('label', 'non-bg')))
            
        self.labels[pos] = (type, text, labelIDs)


            
    def placeStone(self, pos, color):
        self.onChange()
        p = self.getPixelCoord(pos)
        if not self.use3Dstones.get() or not PILinstalled or self.canvasSize[1] <= 7:
            if color=='B':
                self.stones[pos] = self.create_oval(p, fill='black', tags='non-bg')
            elif color=='W':
                self.stones[pos] = self.create_oval(p, fill='white', tags='non-bg')
        else:
            if color=='B': self.stones[pos] = self.create_image(((p[0]+p[2])/2, (p[1]+p[3])/2),
                                                                image=self.bStone, tags='non-bg')
            elif color=='W': self.stones[pos] = self.create_image(((p[0]+p[2])/2, (p[1]+p[3])/2),
                                                                  image=self.wStone, tags='non-bg')
            
    def undo(self, no=1, changeCurrentColor=1):
        """ Undo the last no moves. """

        for i in range(no):
            if self.undostack:
                self.onChange()
                pos, color, captures = self.undostack.pop()
                if self.status.has_key(pos):
                    del self.status[pos]
                    self.delete(self.stones[pos])
                    del self.stones[pos]
                for p in captures:
                    self.placeStone(p, self.invert(color)) 
                    self.status[p] = self.invert(color)
                # self.update_idletasks()
                if changeCurrentColor:
                    self.currentColor = self.invert(self.currentColor)

    def clear(self):
        """ Clear the board. """
        abstractBoard.clear(self)
        for x in self.stones.keys():
            self.delete(self.stones[x])
        self.stones = {}
        self.onChange()

    def ptOnCircle(self, size, degree):
        radPerDeg = math.pi/180
        r = size/2
        x = int(r*math.cos((degree-90)*radPerDeg) + r)
        y = int(r*math.sin((degree-90)*radPerDeg) + r)
        return (x,y)

    def shadedStone(self, event):
        x, y = self.getBoardCoord((event.x, event.y), 1)
        if (x,y) == self.shadedStonePos: return     # nothing changed

        self.delShadedStone()
        if self.currentColor == 'B': color = 'black'
        else: color = 'white'

        if (x*y) and self.shadedStoneVar.get() and abstractBoard.play(self, (x,y), self.currentColor):
            abstractBoard.undo(self)

            if sys.platform[:3]=='win':     # 'stipple' is ignored under windows for
                                            # create_oval, so we'll draw a polygon ...
                l = self.getPixelCoord((x,y),1)
                m = []

                for i in range(18):
                    help = self.ptOnCircle(l[2]-l[0], i*360/18)
                    m.append(help[0]+l[0])
                    m.append(help[1]+l[1])
                 
                self.create_polygon(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9],
                                    m[10], m[11], m[12], m[13], m[14], m[15], m[16], m[17],
                                    m[18], m[19], m[20], m[21], m[22], m[23], m[24], m[25],
                                    m[26], m[27], m[28], m[29], m[30], m[31], m[32], m[33],
                                    m[34], m[35],
                                    fill=color, stipple='gray50',
                                    outline='', tags=('shaded','non-bg') )
            else:
                self.create_oval(self.getPixelCoord((x,y), 1), fill=color, stipple='gray50',
                                 outline='', tags=('shaded','non-bg')) 

            self.shadedStonePos = (x,y)
    
    def delShadedStone(self, event=None):
        self.delete('shaded')
        self.shadedStonePos = (-1,-1)

    def fuzzyStones(self):
        """ switch fuzzy/non-fuzzy stone placement according to self.fuzzy """
        for p in self.status.keys():
            self.delete(self.stones[p])
            del self.stones[p]
            self.placeStone(p, self.status[p])
        self.tkraise('marks')
        self.tkraise('label')
