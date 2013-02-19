from Tkinter import *
from tkFileDialog import *
import os

class App(Frame):
    def __init__(self, win):
        Frame.__init__(self, win)
        b = Button(self, command = self.getFile, text = 'Press Me')
        b.pack()
        self.pack()
    def getFile(self):
        fname = asksaveasfilename(initialdir = 'C:/MyDocuments/kenken')
        print fname
    
root = Tk()
App(root)
root.mainloop()
