''' Graphic user interface for kenken puzzle client.
    Read puzzle file created by solver in .ken format and solve manually
    Allows user to save partially completed puzzle in .kip (kenken in progress) format
    to load later and resume solving.
'''
from __future__ import division
from Tkinter import *
from tkMessageBox import *                    # get standard dialogs
from tkFileDialog import *
from tkSimpleDialog import Dialog
from pyparsing import ParseException
import time, os, re

from control   import Control
from board     import Board
from puzzle    import Puzzle
from stopwatch import StopWatch
        
class DeleteDialog(Dialog):
    def __init__(self, parent, filenames):
        # fnames = list of files to delete
        self.fnames = filenames
        
        Dialog.__init__(self, parent, title= "Confirm Delete")
    
    def body(self, master):
        self.index  = 0          # index into filenames
        self.label = Label(master, justify=LEFT)
        self.msg()
        self.label.grid(row=0, padx=5, sticky=W)
        return self.label
    
    def buttonbox(self):
        box = Frame(self)

        w = Button(box, text="Yes to All", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Yes", width=10, command=self.yes)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="No", width=10, command=self.no)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()
        
    def msg(self):
        name = self.fnames[self.index]
        text = os.path.split(name)[1]
        msg = "%s will be erased from the disk.  Proceed?" % text
        self.label.configure(text = msg)
                
    def yes(self):
        self.index += 1
        try:
            self.msg()
        except IndexError:
            self.ok()
    
    def no(self):
        del self.fnames[self.index]
        try:
            self.msg()
        except IndexError:
            self.ok()
    
    def apply(self):
        for fname in self.fnames:
            try:
                os.remove(fname)
            except WindowsError:
                import tkMessageBox
                tkMessageBox.showwarning("Delete Failed", 
                                         "Could not delete %s" %fname,
                                         parent = self)
                                         
class KenClient(object):            
    def __init__(self, win, height = 600, width = 600, cursor = 'crosshair', bg = 'white'):    
        self.win = win
        self.win.title('KenKen')        
        self.control = Control(self, win)                
        self.board = Board(self, win, dim = 9, height = height, width = width, bg = bg, cursor=cursor)
        self.timer = StopWatch(win)
        
        self.win.wm_protocol("WM_DELETE_WINDOW", self.control.onClose)
        
        self.menu = self.makeMenu(win)
        self.fileOpenDir = '.'    # directory for puzzle files
        
        self.timer.pack()
        self.board.pack(side = TOP, expand=YES, fill=BOTH)
        
        # self.board.bind('<Configure>', self.board.redraw)
        # self.puzzle set from Open or Load menu item 
        
    def makeMenu(self, win):                              
        def notDone():  
            showerror('Not implemented', 'Not yet available') 
    
        top = Menu(win)                                # win=top-level window
        win.config(menu=top)                           # set its menu option
        fileMenu = top.fileMenu = Menu(top, tearoff = 0)
        fileMenu.add_command(label='Open...',  command=self.openFile,        underline=0)        
        fileMenu.add_command(label='Load...',  command=self.loadFile,        underline=0) 
        fileMenu.add_command(label = 'Delete Puzzles', command = self.deletePuzzle, underline=0)
        fileMenu.add_command(label='Exit',     command=self.control.onClose, underline=1) 
       
        top.add_cascade(label='File',     menu=fileMenu,                 underline=0)
        
        puzzleMenu = top.puzzleMenu = Menu(top, tearoff = 0)
        puzzleMenu.add_command(label='Check',  command=self.control.check,    underline=0)        
        puzzleMenu.add_command(label = 'Restart', command = self.control.clearPuzzle, underline=0)
        puzzleMenu.add_command(label='Save',     command=self.saveFile,        underline=0)
              
        top.add_cascade(label='Puzzle',           menu=puzzleMenu,            underline=0)
        top.entryconfigure(2, state='disabled')
        
        return top
    
    def openFile(self):
        
        try:
            if self.puzzle.isDirty:
                if self.promptSave() == None:
                    return
        except AttributeError:
            pass
        
        fname = askopenfile( filetypes = [('KenKen Files', '.ken')],
                             title = 'Open Puzzle File',
                             defaultextension = 'ken',
                             initialdir = self.fileOpenDir)
        if not fname:
            return
        self.fileOpenDir = os.path.dirname(fname.name)
        try:            
            base = os.path.basename(fname.name)
            ext = os.path.splitext(fname.name)[1]
            self.puzzle = Puzzle(fname, self)
            dim = self.puzzle.dim
            self.win.title('KenKen %d-by-%d  %s' % (dim, dim, base[:-len(ext)]))
            self.board.draw(dim)
            self.menu.entryconfigure(2, state='normal')
            self.timer.start()
        except ParseException:
            showerror("Input Error", "%s doesn't seem to be a kenken file" % base)
            return
        
    def saveFile(self):
        fname = asksaveasfilename( filetypes = [('KenKen Files', '.kip')],
                             title = 'Save Puzzle File',
                             defaultextension = '.kip',
                             initialdir = self.fileOpenDir)
        if not fname:
            return
        self.fileOpenDir= os.path.split(fname[0])        
        self.puzzle.save(fname)
        self.puzzle.isDirty = False
        
    def loadFile(self):
        
        try:
            if self.puzzle.isDirty:
                if self.promptSave() == None:
                    return
        except AttributeError:
            pass
        
        fname = askopenfile( filetypes = [('KenKen Files', '.kip')],
                             title = 'Load Puzzle-in-Progress File',
                             defaultextension = 'ken',
                             initialdir = self.fileOpenDir)
        if not fname:
            return
        self.fileOpenDir = os.path.dirname(fname.name)
        try:            
            base = os.path.basename(fname.name)
            ext = os.path.splitext(fname.name)[1]
            self.puzzle = Puzzle(fname,self)
            dim = self.puzzle.dim
            self.win.title('KenKen %d-by-%d  %s' % (dim, dim, base[:-len(ext)]))
            self.board.draw(dim)
            self.menu.entryconfigure(2, state='normal')
            self.timer.resume()
        except ParseException:
            showerror("Input Error", "%s doesn't seem to be a kenken file" % base)
            return
        
    def deletePuzzle(self):
        fnames = askopenfilename( 
                   filetypes  = [('KenKen Files', '.ken'), ('KenKen Files', '.kip') ],
                   title      = 'Delete Puzzle Files',
                   initialdir = self.fileOpenDir, parent = self.win, multiple=1)
        
        # askopenfilename returns a blank-separated string of filenames.
        # Should one of the filenames contain a balnk, it is encolsed in curly
        # braces within the returned string.  The rigmarole below extracts
        # the correct substrings, then strips off the braces.
                
        if fnames:
            pattern = re.compile(r'''[^\{} ]+      # one or more not brace or space 
                                 |\{[^\{]*\}       # any string inside braces (shortest)'''
                                 ,re.VERBOSE)
            fnames = [name.strip('{}') for name in pattern.findall(fnames)]
            DeleteDialog(self.board, fnames)
                
    def promptSave(self):
        # Return value is None if user chooses cancel, True for Yes, False for No

        msg  = "Do you want to you want to save the solution in progress?" 
        save = askyesnocancel("Save Partial Solution?",msg)
        if save:
            self.saveFile()
        return save
                    
def main():
    root = Tk()                             
    KenClient(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()
                
            
            
        