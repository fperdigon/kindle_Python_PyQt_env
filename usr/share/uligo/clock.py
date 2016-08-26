# file: clock.py

##   This file is part of uliGo, a program for exercising go problems.
##   It contains a class that implements a simple stop watch.

##   Copyright (C) 2001-3 Ulrich Goertz (uliGo@g0ertz.de)

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
import time
import math
import os

class Clock(Canvas):
    """ This is a simple stop watch displayed on a Tkinter canvas.
        It is given a size (diameter in pixel), a maxTime (this is how long it will take the hand
        to go round the clock once; after that the clock stops, the clock's face becomes red and
        'time is over'), and a function that is called when time is over.
        The clock is started with Clock.start; it can be stopped with the Clock.stop function
        (returns the elapsed time) and reset with Clock.reset.
        The maxTime can be changed with the changeMaxTime function; it makes a new window with
        a scale pop up, where the time in seconds can be chosen.
        When the clock is running, the system clock is checked every 100 milliseconds, but the
        clock hand is updated only once a second.
        """
    
    def __init__(self, master, maxTime=0, f=None):
        Canvas.__init__(self, master, height=120, width=120, highlightthickness=0)
        self.size = 100
        self.offset = 10
        self.hand = None
        gifpath = os.path.join(sys.path[0],'gifs')
        
        try:
            self.img = PhotoImage(file=os.path.join(gifpath, 'clock.gif'))
            self.create_image(60,60, image=self.img)
        except TclError:
            pass

        self.drawClockface()
        self.currentTime = None
        self.running = 0
        self.maxTime = IntVar()
        self.maxTime.set(maxTime)
        self.callOnMaxtime = f
        self.bind("<Button-3>", self.changeMaxtime)
        self.red = 0
        
        
    
    def start(self):
        """ Start the clock. """
        if not self.running and self.maxTime.get():
            self.reset()
            self.tick = 360.0/self.maxTime.get()
   
            self.running = 1
            self.elapsedTime = 0

            self.currentTime = time.localtime(time.time())[5]
            self.updateClock()


    def stop(self):
        """ Stop the clock. """
        if self.running:
            self.running = 0
            return self.elapsedTime


    def reset(self):
        """ Reset the hand."""
        if not self.running:
            self.drawHand()
            if self.red: self.delete(self.red)

    def updateClock(self):
        """ This function is called every 100 milliseconds when the clock is running (first
            by start(), and then by self.after(). If the time (as given by time.time())
            jumped to a new second, the hand is drawn in its new position. """
        
        if self.running:
            s = time.localtime(time.time())[5]
            if s != self.currentTime:                 # second jumped
                if s-self.currentTime<0 :
                    self.elapsedTime = self.elapsedTime + s - self.currentTime + 60
                else:
                    self.elapsedTime = self.elapsedTime + s - self.currentTime
                self.currentTime = s
                
                if self.maxTime.get() and self.elapsedTime >= self.maxTime.get():   # time over?
                    self.drawHand()
                    self.running = 0
                    self.red = self.create_oval(1+self.offset,1*self.offset,
                                                self.size+self.offset-1,self.size+self.offset-1, fill="red")
                    self.tkraise('fg')
                    self.callOnMaxtime()
                    return
                self.drawHand(self.elapsedTime*self.tick)
                
            self.after(100, self.updateClock)             # next update after 100 ms
            

    def changeMaxtime(self, event=None):
        """ Change the maxTime; makes a new window with a scale where the new maxTime can be chosen.
            Does not work while the clock is running. """
        if not self.running:
            window = Toplevel()
            window.title("Change time settings")
            sc = Scale(window, label='Pick time in seconds (0=off)', length=300,
                       variable = self.maxTime, from_=0, to = 480,
                       tickinterval = 60, showvalue=YES, orient='horizontal')
            sc.pack()
            b = Button(window, text="OK", command = window.destroy)
            b.pack(side=RIGHT)
            window.update_idletasks()  # grab_set won't work without that
            window.focus()
            window.grab_set()
            window.wait_window()
         

    def drawClockface(self):
        for i in range(12):
            (x,y) = self.ptOnCircle(i*360/12)
            self.create_oval(self.offset+x-2,self.offset+y-2,self.offset+x+2,self.offset+y+2,
                             fill="blue", outline ="", tags='fg')
        self.create_oval(self.offset+self.size/2-3, self.offset+self.size/2-3,
                         self.offset+self.size/2+3, self.offset+self.size/2+3, fill="black", tags='fg')
        self.drawHand()

        
    def drawHand(self, degree=0):
        x,y = self.ptOnCircle(degree)
        if self.hand: self.delete(self.hand)
        self.hand = self.create_line(self.offset+self.size/2, self.offset+self.size/2,
                                     self.offset+x, self.offset+y, fill="black", width=2, tags='fg')


    def ptOnCircle(self, degree):
        radPerDeg = math.pi/180
        r = self.size/2
        x = int((r-5)*math.cos((degree-90)*radPerDeg) + r)
        y = int((r-5)*math.sin((degree-90)*radPerDeg) + r)
        return (x,y)




