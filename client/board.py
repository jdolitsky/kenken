from Tkinter import *
import time
from puzzle import Update

NONE = ' '
ADD = '+'
SUB = u'\u2212'
MUL =u'\xd7'
DIV = '/'

operation = {"ADD":ADD, "SUB":SUB, "MUL":MUL, "DIV":DIV, "NONE":NONE}
clueFont = ('helevetica', 12, 'bold')
solutionFont = ('heletica', 20, 'bold')
candidateFont = ('courier', 10, 'bold')
cageColor = ('#FFDCA0', '#F0C8C8', '#DCFFFF', '#C4C4FF', '#E5D6B4', '#D6ED84')

class Board(Canvas):
    # View

    def __init__(self, parent, win, height = 600, width = 600,
                 bg = 'white', dim = 9, cursor = 'crosshair'):
        Canvas.__init__(self, win, height=height, width=width,
                        bg=bg, cursor=cursor)
        self.parent = parent
        msg = '  To begin, open a puzzle file (.ken)\nor load a saved partial solution (.kip)'
        self.create_text(width//2, height//2, text= msg, font = solutionFont)

    def draw(self, dim):
        self.bind('<Configure>', self.redraw)
        width = self.winfo_width()
        height= self.winfo_height()
        self.dim = dim
        self.createCells(height, width)

        control = self.parent.control
        for cage in control.getCages():
            self.drawCage(cage)
        updates = control.getEntries()
        self.postUpdates(updates)

        self.focusFill = None
        self.enterCell((0,0))         # initial focus in upper lefthand corner
        self.focus_set()              # make canvas respond to keystrokes

        self.activate()               # activate event bindings

    def redraw(self, event):
        self.clearAll()
        self.createCells(event.height, event.width)
        control = self.parent.control
        for cage in control.getCages():
            self.drawCage(cage)
        updates = control.getEntries()
        self.postUpdates(updates)
        try:
            self.enterCell(self.focus)
        except (AttributeError, TypeError):
            pass

    def createCells(self, height, width):
        dim = self.dim
        self.cellWidth  =  cw = (width - 10 ) // dim
        self.cellHeight = ch = (height - 10 ) // dim
        self.x0 = ( width - dim * cw ) // 2          # cell origin is (x0, y0)
        self.y0 = ( height - dim * ch ) // 2

        for j, x in enumerate(range(self.x0, self.x0+dim*cw, cw)):
            for k, y in enumerate(range(self.y0,  self.y0+dim*ch, ch)):
                tag = 'rect%d%d' % (j, k)
                id = self.create_rectangle(x, y, x +cw, y+ ch, tag = tag)

    def drawCage(self, cage):
        x0      = self.x0
        y0      = self.y0
        ch      = self.cellHeight
        cw      = self.cellWidth
        op      = cage.op
        value   = cage.value
        bground = cageColor[cage.color]

        for (j, k) in cage:
            self.itemconfigure('rect%d%d' % (j, k), fill = bground)
            w = x0 + j*cw
            e = w + cw
            n = y0 + k*ch
            s = n + ch
            if (j-1, k) not in cage:
                self.create_line(w, n, w, s, width=3, fill='black')  #western bdry
            if (j+1, k) not in cage:
                self.create_line(e, n, e,  s, width=3, fill='black')  #eastern bdry
            if (j, k-1) not in cage:
                self.create_line(w, n, e, n, width=3, fill='black')   # northern bdry
            if (j, k+1) not in cage:
                self.create_line(w, s, e, s, width=3, fill='black')    # southern bdry
            atag = 'a%d%d' % (j, k)
            ctag = 'c%d%d' % (j, k)
            x = (e + w) // 2
            y = (n + s) // 2
            self.create_text(x, y, text='', font = solutionFont, anchor = CENTER,
                             tag = atag, fill = 'black')
            self.addtag_withtag('atext', atag)
            x = e - 2
            y = n + 15
            self.create_text(x, y, text = '', font = candidateFont, tag = ctag,
                         anchor = NE, justify = LEFT, fill = 'black')
            self.addtag_withtag('ctext', ctag)

        # formula in upper lefthand corner

        kmin = min([k for (j,k) in cage])
        jmin = min([j for(j, k) in cage if k == kmin])
        j, k = x0+cw*jmin+4, y0 + ch*kmin+2
        self.create_text(j, k, text='%s %s' % (value,operation[op]),
                         font = clueFont, anchor = NW, fill = 'black', tag = 'formula')

    def clearAll(self):
        objects = self.find_all()
        for object in objects:
            self.delete(object)

    def drawNew(self, dim):
        # Draw a new board

        self.parent.setTitle()
        self.clearAll()
        self.createCells(self.winfo_height(), self.winfo_width(), dim)

    def highlight(self, cells, color='white', num = 2):
        # Flash given cells in the given highlight color, num times
        # It is assumed that the highlight color will never be the
        # background color of a cell, except perhaps for the cell that
        # has the focus.

        rects = []
        for cell in cells:
            tag = 'rect%d%d' %cell
            bg  = self.itemcget(tag, 'fill')
            if bg != color:
                rects.append((tag, bg, color))
            else:
                rects.append((tag, color, self.focusFill))
        for k in range(num):
            for tag, bg, col in rects:
                self.itemconfigure(tag, fill = col)
            self.update_idletasks()
            time.sleep(.1)
            for tag, bg, col in rects:
                self.itemconfigure(tag, fill = bg)
            self.update_idletasks()
            time.sleep(.1)

    def candidateString(self, cands):
        # String representation of a list of candidates

        if not cands:
            return ''
        string = ''.join([str(x) if x in cands else ' ' for x in range(1,1+self.dim)])
        return string[:3] + '\n' + string[3:6] + '\n' + string[6:]

    def enterCell(self, cell):
        # Cell is (col, row) pair
        # Give focus to cell
        # Sets self.focus and self.focusFill

        try:                                # release old focus, if any
            tag = 'rect%d%d' % self.focus
            self.itemconfigure(tag, fill = self.focusFill)
        except TypeError:
            pass
        tag = 'rect%d%d' % cell
        self.focus = cell
        self.focusFill = self.itemcget(tag, 'fill')
        self.itemconfigure(tag, fill = 'white')

    def postUpdates(self, updates):
        # Each update is an object of class Update

        for update in updates:
            coords = update.coords
            cands  = update.candidates
            answer = update.answer
            atag = 'a%d%d' % coords
            ctag = 'c%d%d' % coords

            if answer:
                self.itemconfigure(ctag, text = '' )
                self.itemconfigure(atag, text = str(answer))
            else:
                self.itemconfigure(ctag, text = self.candidateString(cands))
                self.itemconfigure(atag, text = '' )

    def shiftFocus(self, x, y):
        # User clicked the point (x, y)

        j = (x - self.x0) // self.cellWidth
        if not 0 <= j < self.dim:
            return
        k = (y - self.y0) // self.cellHeight
        if not 0 <= k < self.dim:
            return
        self.enterCell( (j, k) )

    def celebrate(self):
        # Indicate a win by flashing board green
        # Drop the focus
        # Deactivate the board

        all = [(x,y) for x in range(self.dim) for y in range(self.dim)]
        self.highlight(all, 'green', 4)
        tag = 'rect%d%d' % self.focus
        self.itemconfigure(tag, fill = self.focusFill)
        self.deactivate()
        del(self.focus)
        del(self.focusFill)

    def restart(self, updates):
        # Clear all solution data from the board, and then post the updates
        # User wants to start current puzzle over

        self.itemconfigure('atext', text = '')
        cstr = self.candidateString([])
        self.itemconfigure('ctext', text = cstr)
        self.postUpdates(updates)
        self.enterCell((0,0))
        self.activate()

    def deactivate(self):
        # Replace the 'Board' bindatg by 'Canvas'.
        # See defininition of Coontrol in control.py
        # Board will no longer respond to keypresses and mouseclicks

        tags = self.bindtags()
        tags = (tags[0], 'Canvas') + tags[2:]
        self.bindtags(tags)

    def activate(self):
        # Activate event bindings
        # Reverse of deactivate, above

        tags = self.bindtags()
        tags = (tags[0], 'Board') + tags[2:]
        self.bindtags(tags)




