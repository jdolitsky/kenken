''' Graphic user interface for kenken puzzle solver.
   Allows user to enter, edit, and solve puzzle.
   Puzzle is solved by dancing links algorithm.
   Interactive solving is not supported.
   Puzzle may be saved in .ken format for interactive solving in a different program.
'''
from __future__ import division
from Tkinter import *
from tkMessageBox import *                    # get standard dialogs
from tkFileDialog import *
import threading, time
from dance4 import Dancer                     # DLX
import time, re
from scrolledText import ScrolledText
import os.path

NONE = ' '
ADD = '+'
#SUB = '-'
SUB = u'\u2212'  # not recognized by canvas.postscript: rendered as "?"
MUL =u'\xd7'
DIV = '/'

clueFont = ('helevetica', 12, 'bold')
solutionFont = ('heletica', 20, 'bold')

def multiSum(value, num, limit):
    # a list of all lists of num integers from 1 to limit (repetitions allowed),  whose sum is value

    if num == 1:
        if 1 <= value <= limit:
            yield [value]
        else:
            yield None
    else:
        for n in range(1, limit+1):
            for m in multiSum(value-n, num-1, limit):
                if m is not None:
                    yield m + [n]

def multiProduct(value, num, limit):
    # a list of all lists of num integers from 1 to limit (repetitions allowed),  whose product is value

    if num == 1:
        if 1 <= value <= limit:
            yield [value]
        else:
            yield None
    else:
        for n in range(1, limit+1):
            if value % n != 0:
                continue
            for m in multiProduct(value // n, num-1, limit):
                if m is not None:
                    yield m + [n]

class CageError(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)

class Cage(list):
    def __init__(self, op, valStr, cells, dim):

        if len(cells) == 0:
            raise CageError("No cells selected")
        try:
            value = int(valStr)
            if value <= 0:
                raise CageError("Value must be positive integer")
        except ValueError:
            raise CageError("Value must be positive integer")
        if not self.contiguous(cells):
            raise CageError("Cage cells not adjacent.")

        if len(cells) == 1 and op != NONE:
            raise CageError("One-cell cage has no operation.")
        if op == NONE and len(cells) != 1:
            raise CageError("Operation lacking.")
        if op == NONE and not 1 <= value <= dim:
            raise CageError("%d is not possible value for cell" % value)
        if op == DIV and len(cells) != 2:
            raise CageError('Division only valid for two-cell cage')
        if op == DIV and not 1 <= value <= dim:
            raise CageError('%d is not possible value for quotient' % value)
        if op == SUB and len(cells) != 2:
            raise CageError('Subtraction only valid for two-cell cage')
        if op == SUB and not 1 <= value < dim:
            raise CageError('%d is not possible value for difference' % value)
        if op == ADD and not self.validateSum(cells, value, dim):
            raise CageError('%d is not possible value for sum' % value)
        if op == MUL and not self.validateProduct(cells, value, dim):
            raise CageError('%d is not possible value for product' % value)

        list.__init__(self, cells)
        self.op = op
        self.value = value
        self.dim = dim

    def contiguous(self, cells):
        if len(cells) == 1:
            return True
        componentNum = {}
        for c in cells[1:]:
            componentNum[c] = 0
        componentNum[cells[0]] = 1

        def component(u):
            x, y = u
            for c in [(x, y-1), (x, y+1), (x-1, y), (x+1, y) ]:
                if c in cells and componentNum[c] == 0:
                    componentNum[c] = 1
                    component(c)

        component(cells[0])
        if 0 in componentNum.values():
            return False
        return True

    def validateSum(self, cage, total, dim):

    # Is it possible to fill in the cage with numbers  with the given total?
    # If we can find DISTINCT number with the given total, then there
    # is no problem,, since there can't be repetitions.
    # If not, we find all  mutisums with the given total.  Implicitly, these
    # are in the same order as the cage cells to which they are assigned,
    # so we just work with indices.
    # We generate a multisum and test for lack of repetitions.
    # Return True on first success, otherwise return False.

        lower = sum(range(1, 1+len(cage)))
        upper = sum(range(dim - len(cage) + 1, dim+1))

        if len(cage) <= dim and lower <= total<= upper:
            return True

        adjacent = {}
        for c in cage:
            adjacent[cage.index(c)] = [cage.index(x) for x in cage if x != c and (x[0] == c[0] or x[1] == c[1])]

        for x in multiSum(total, len(cage), dim):
            for k in range(len(x)):
                if x[k] in [x[j] for j in adjacent[k]]:
                    break                   # number repeated in row or column
            else:
                return True               # loop else -- no repetitions
        return False

    def validateProduct(self, cage, product, dim):
        # Is it possible to fill in the cage with numbers  with the given product?

        # We find all  mutiproducts with the given product.  Implicitly, these
        # are in the same order as the cage cells to which they are assigned,
        # so we just work with indices.
        # We generate a multiproduct and test for lack of repetitions.
        # Return True on first success, otherwise return False.

        primes = [ p for p in [2, 3, 5, 7, 11, 13, 17, 19] if p <= dim]

        val = product
        for p in primes:
            while val % p == 0:
                val //= p
        if val != 1:
            return False   # product cannot be factored into primes <= dim

        adjacent = {}
        for c in cage:
            adjacent[cage.index(c)] = [cage.index(x) for x in cage if x != c and (x[0] == c[0] or x[1] == c[1])]

        for x in multiProduct(product, len(cage), dim):
            for k in range(len(x)):
                if x[k] in [x[j] for j in adjacent[k]]:
                    break                   # number repeated in row or column
            else:
                return True               # loop else -- no repetitions
        return False

    def __str__(self):
        oper = {ADD:"ADD ", SUB:"SUB ", MUL:"MUL ", DIV:"DIV ", NONE: "NONE "}
        answer = '%s %s %s' %(oper[self.op], str(self.value), '[ ')
        for cell in sorted(self, key = lambda x: self.dim * x[1] + x[0]):
            answer = answer + "%d%d " % (cell[1]+1, cell[0]+1)
        answer = answer + ']'
        return answer

class TiledCage(object):
    # The cage is represented as a list of cell coordinates (x,y).
    # The tiles represent all ways of "tiling" the cells with numbers.
    # Each tile will generate one row in the dancing links matrix.
    # Assignment of number n to cell (x, y) generates two ones in the matrix,
    # with symbolic names 'nCx' (n in column x) and 'nRy'  (n in row y)
    # Each cage has a unique id c.  The column Cc (cage c) is a member of each tile,
    # since the cage must be tiled exactly once.

    # A tiling is represented as a list of numbers, in the same order as the cells
    # they tile are listed in self.cage.  The corresponding row is a sorted list of
    # column names.

    def __init__(self, cage, dim, id):
        # Precondition: All parameters are valid.  There is at least one legal tiling.

        self.cage = cage
        op = cage.op
        value = cage.value
        #self.rows = []
        if op == NONE:
            self.tiles = self.tileNone(value)
        elif op == ADD:
            self.tiles = self.tileAdd(value, dim)
        elif op == SUB:
            self.tiles = self.tileSub(value, dim)
        elif op == MUL:
            self.tiles = self.tileMul(value, dim)
        elif op == DIV:
            self.tiles = self.tileDiv(value, dim)
        self.code = self.encode(id)

    def tileNone(self, value):
        return [[value]]

    def tileSub(self, value, dim):
        answer = []
        for n in range(value+1, dim+1):
            if 1 <= n - value <= dim:
                answer += [[n, n - value], [n-value, n]]
        return answer

    def tileDiv(self, value, dim):
        answer = []
        for n in range(value, dim+1):
            if n % value == 0:
                answer += [[n, n // value], [n//value, n]]
        return answer

    def tileAdd(self, value, dim):
        cage = self.cage
        colineal = {}
        for c in cage:
            colineal[cage.index(c)] = [cage.index(x) for x in cage if x != c and (x[0] == c[0] or x[1] == c[1])]

        answer = []
        for x in multiSum(value, len(cage), dim):
            for k in range(len(x)):
                if x[k] in [x[j] for j in colineal[k]]:
                    break                   # number repeated in row or column
            else:                             # normal exit means valid tiling
                answer.append(x)
        return answer

    def tileMul(self, value, dim):
        cage = self.cage
        colineal = {}
        for c in cage:
            colineal[cage.index(c)] = [cage.index(x) for x in cage if x != c and (x[0] == c[0] or x[1] == c[1])]

        answer = []
        for x in multiProduct(value, len(cage), dim):
            for k in range(len(x)):
                if x[k] in [x[j] for j in colineal[k]]:
                    break                   # number repeated in row or column
            else:                             # normal exit means valid tiling
                answer.append(x)
        return answer

    def encode(self, id):

        # Each tiling is a list of columns IDS, indicating what constraints the tiling statisfies.
        # The constraints are either primary (meaning that they must be satisifed exactly once) or
        # secondary, meaning that they can be satisfied at most once.)  This is in accordance
        # with Knuth's DLX terminology.  There are no secondary constraints in kenken.
        # Primary constraints are either of the form, "n in row r", or "n in column c", or "tile cage id".
        # The last element of each list is an encoding of the tiling.  The remaining elements are
        # sorted alphabetically.  The encoding is simply a catenation of strings of the form "%d%d%d" %(n,x,y)
        # meaning that digit n is placed in column x, row y.

        cageCol = 'C' + str(id)
        cage = self.cage
        tiles = self.tiles
        answer = []
        for tile in tiles:
            name = ''
            row = [cageCol]
            for n, (x,y) in zip(tile, cage):
                row += [str(n) + 'C' + str(x)]
                row += [str(n) + 'R' + str(y)]
                name = name + "%d%d%d" %(n,x,y)
            row.sort()
            row += [name]
            answer += [row]
        return answer

class Board(Canvas):
    # View

    def __init__(self, win, parent, height = 600, width = 600, bg = 'white', dim = 9, cursor = 'crosshair'):
        Canvas.__init__(self, win, height=height, width=width, bg=bg, cursor=cursor)
        self.parent = parent
        self.createCells(height, width)
        self.frozen = False       # respond to mouse clicks
        self.bind('<ButtonPress-1>', self.onClick)
        self.bind('<ButtonPress-3>', self.onRightClick)

    def createCells(self, height, width):
        dim = self.parent.dim
        self.cellWidth  =  cw = (width - 10 ) // dim
        self.cellHeight = ch = (height - 10 ) // dim
        self.x0 = ( width - dim * cw ) // 2          # cell origin is (x0, y0)
        self.y0 = ( height - dim * ch ) // 2
        self.cells = []                 # all cells (Rectangles) on the board

        for n in range(dim):
            self.cells.append([])
        for j, x in enumerate(range(self.x0, self.x0+dim*cw, cw)):
            for y in range(self.y0,  self.y0+dim*ch, ch):
                id = self.create_rectangle(x, y, x +cw, y+ ch, tag='cell')
                self.cells[j].append(id)

    def redraw(self, event):
        self.createCells(event.height, event.width)

    def onClick(self, event):
        if self.frozen:
            return
        dim = self.parent.dim
        canvas = event.widget
        x, y = event.x, event.y
        j = (x - self.x0) // self.cellWidth
        if not 0 <= j < dim:
            return
        k = (y - self.y0) // self.cellHeight
        if not 0 <= k < dim:
            return
        obj = self.cells[j][k]
        if canvas.type(obj) == 'rectangle':             # got a cell
            tags = canvas.gettags(obj)
            if 'cage' in [tag[:4] for tag in tags]:     # already in a cage?
                return
            if 'selected' not in tags:       # No, toggle selection
                canvas.itemconfigure(obj, tag = 'selected', fill = 'blue')
            else:
                canvas.itemconfigure(obj, tag = 'cell', fill = '')

    def onRightClick(self, event):
        # Edit an existing cage

        if self.frozen:
            return
        dim = self.parent.dim
        canvas = event.widget
        x, y = event.x, event.y
        j = (x - self.x0) // self.cellWidth
        if not 0 <= j < dim:
            return
        k = (y - self.y0) // self.cellHeight
        if not 0 <= k < dim:
            return
        obj = self.cells[j][k]
        if canvas.type(obj) != 'rectangle':                                         # got a cell?
            return
        tags = canvas.gettags(obj)
        labels = [tag for tag in tags if tag.startswith('cage')]
        if not labels:               # in a cage?
            return
        if len(labels) > 1:
            raise ValueError, "Cell in two cages"

        self.clearCurrentCage()                                                     # de-select any selected cells
        id = labels[0][4:]

        self.itemconfigure(labels[0], tag = 'selected', fill = 'blue')    # highlight cells in edited cage

        formula = self.find_withtag('formula'+id)[0]                        # find formula for edited cage
        form = self.itemcget(formula, 'text')
        value = form[:-1]
        op = form[-1]
        self.delete(formula)
        self.parent.control.setFormula(value, op)                            # set formula in control

        self.delete('edge'+id)                                                      # delete cage boundaries

        self.parent.deleteCage(int(id))                                         # delete cage in KenKen (parent)


        # Now we are in the same state as when we were entering this cage, just before pressing "Okay".

    def freeze(self):
        # turn off clicking on cells

        self.frozen = True

    def unfreeze(self):
        # turn off clicking on cells

        self.frozen = False

    def currentCage(self):
        # return a list of the coordinates of all currently selected cells

        x0, y0 = self.x0, self.y0
        cw, ch = self.cellWidth, self.cellHeight
        answer = []

        # subtract the board origin from the center of the cells
        # divide by cell width and height to get coords

        for id in self.find_withtag('selected'):
            x1, y1, x2, y2 = self.coords(id)
            j = int( (.5*(x1+x2)-x0)/cw)
            k = int( (.5*(y1+y2)-y0)/ch)
            answer += [(j, k)]
        return answer

    def drawCurrentCage(self, op, value):
        self.drawCage(op, value, self.currentCage(), self.parent.nextCage)

    def drawCage(self, op, value, cage, cageID):
        x0 = self.x0
        y0 = self.y0
        ch = self.cellHeight
        cw = self.cellWidth

        eTag = 'edge%d' % cageID
        for (x, y) in cage:
            w = x0 + x*cw
            e = w + cw
            n = y0 + y*ch
            s = n + ch
            if (x-1, y) not in cage:
                self.create_line(w, n, w, s, width=3, fill='black', tag = eTag)  #western bdry
            if (x+1, y) not in cage:
                self.create_line(e, n, e,  s, width=3, fill='black', tag = eTag)  #eastern bdry
            if (x, y-1) not in cage:
                self.create_line(w, n, e, n, width=3, fill='black', tag = eTag)   # northern bdry
            if (x, y+1) not in cage:
                self.create_line(w, s, e, s, width=3, fill='black', tag = eTag)    # southern bdry

        ymin = min([y for (x,y) in cage])
        xmin = min([x for(x, y) in cage if y == ymin])
        x, y = x0+cw*xmin+4, y0 + ch*ymin+2

        fTag = 'formula%d' % cageID
        self.create_text(x, y, text='%s %s' % (value,op), font = clueFont, anchor = NW, tag = fTag)

        cTag = 'cage%d' % cageID
        for (x, y) in cage:
            obj = self.cells[x][y]
            self.itemconfigure(obj, tag = cTag, fill = 'gray')

    def clearCurrentCage(self):
        self.itemconfigure('selected', fill = '', tag = 'cell')

    def printSolution(self, solution):
        cells = [obj for obj in self.find_all() if self.type(obj) == 'rectangle']
        for cell in cells:
            self.itemconfigure(cell, fill = '')
        self.delete('Solution')
        x0 = self.x0
        y0 = self.y0
        ch = self.cellHeight
        cw = self.cellWidth
        ch2 = ch // 2
        cw2 = cw // 2
        for tile in solution:
            for cell in [tile[n:n+3] for n in range(0,len(tile), 3)]:
                x = x0 + int(cell[1]) * cw + cw2
                y = y0 + int(cell[2]) * ch  + ch2
                self.create_text(x, y, text='%s' % cell[0], font = solutionFont, anchor = CENTER, tag='Solution')

    def printBoard(self):
        fout = asksaveasfilename( filetypes=[('postscript files', '.ps')],
                                title='Print to File',
                                defaultextension='ps')
        if fout:
            self.postscript(colormode="gray",file=fout, rotate=False)

    def clearAll(self):
        objects = self.find_all()
        for object in objects:
            self.delete(object)

    def drawNew(self):
        # Draw a new board

        self.parent.setTitle()
        self.clearAll()
        self.createCells(self.winfo_height(), self.winfo_width())
        self.parent.log.clear()
        self.parent.control.getReady()


class Control(Frame):
    def __init__(self, parent, win):
        Frame.__init__(self, win)
        self.parent = parent
        self.helpButton = None              # configurable for context-sensitive help
        self.okayButton = None              #  configurable context-sensitive action
        self.entry          = None             #  Entry for cage value
        self.op             = StringVar()
        self.op.set(NONE)

        self.pack(side = BOTTOM, expand = NO, fill = X)
        self.helpButton = Button(self, text = 'Help', command = self.cageHelp)
        self.helpButton.pack(side = LEFT, expand = YES)

        radio = Frame(self)
        radio.pack(side=LEFT, expand = YES)
        Label(radio, text = 'Cage Operation').pack(side = TOP)
        for (key, op) in [('Add', ADD), ('Sub', SUB), ('Mul', MUL), ('Div', DIV), ('None', NONE)]:
            Radiobutton(radio, text = key, variable = self.op, value = op).pack(side = LEFT)

        value = Frame(self)
        value.pack(side = LEFT, expand = YES)
        Label(value, text = 'Cage Value').pack()
        self.entry = Entry(value)
        self.entry.pack()
        self.entry.focus_set()

        self.OkayButton = Button(self, text = 'Okay', command = self.okayCage)
        self.OkayButton.pack(side = LEFT, expand = YES)

        self.entry.bind('<Key-Return>', self.okayCage)
        self.entry.bind('<Key-KP_Enter>', self.okayCage)

        self.key2op = {'plus':ADD, 'KP_Add':ADD,
                             'minus':SUB, 'KP_Subtract':SUB,
                              'asterisk':MUL, 'KP_Multiply':MUL,
                              'slash':DIV, 'KP_Divide':DIV,
                              'period':NONE, 'space':NONE, 'KP_Decimal':NONE}

        for key in self.key2op:
            self.bind_all('<'+key+'>', self.keyOp)


    def cageHelp(self):
        msg = 'Click cells to select or deselect.\n' +\
                  'Choose operation and enter value.\n' +\
                  'Press Okay when done.\n' +\
                  'Right-click a cage to edit it.'
        showinfo("Create Cage",msg)

    def okayCage(self, event=None):

        # The dummy event argument is so that the Enter key will trigger
        # this function if pressed in the value entry.  The Okay button
        # doesn't send this argument, of course.

        op, value =  self.op.get(), self.entry.get()
        kenken = self.parent
        board = kenken.board
        cage = kenken.validateCurrentCage(op, value)
        if cage:
            value = cage.value
            board.drawCurrentCage(op, value)
            kenken.tileCurrentCage(cage)
            board.clearCurrentCage()
            self.entry.delete(0, END)

    def setFormula(self, value, op):
        self.op.set(op)
        e = self.entry
        e.delete(0,END)
        e.insert(0,value.rstrip())

    def disable(self):
        self.OkayButton.configure(state = 'disabled')
        self.entry.configure(state = 'disabled')

    def keyOp(self, event):
        self.op.set(self.key2op[event.keysym])

        # Remove illegal character from entry widget

        if event.widget == self.entry:
            s = self.entry.get()
            t = ''.join([x for x in s if x.isdigit()])
            self.entry.delete(0,END)
            self.entry.insert(0,t)

    def getReady(self):
        self.entry.focus_set()

class KenKen(object):
    updates = 0                         # class variable

    class TileThread(threading.Thread):

        mutex = threading.Lock()        # class variable

        def __init__(self, cage, dim, id, cageDict):
            self.cage = cage
            self.dim = dim
            self.id = id
            self.cageDict = cageDict
            threading.Thread.__init__(self)

        def run(self):
            cage = TiledCage(self.cage, self.dim, self.id)
            self.mutex.acquire()
            self.cageDict[self.id] = cage
            self.mutex.release()

    def __init__(self, win, height = 600, width = 600, bg = 'white', dim = 9, cursor = 'crosshair'):
        self.dim = dim
        self.win = win
        self.setTitle()
        self.control=Control(self, win)
        self.board = Board(win, self, dim = dim, height = height, width = width, bg = bg, cursor=cursor)
        self.board.pack(side = TOP, expand=YES, fill=BOTH)
        self.menu = self.makeMenu(win)
        #self.board.bind('<Configure>', self.board.redraw)

        self.log = ScrolledText(win, width = 60, height = 6, wrap = "none")
        self.log.pack(side = BOTTOM, expand=YES, fill=X)

        self.cageID  = {}             # associate cell with cage
        self.nextCage = 0             # unique cage id number
        self.threads = []             # list threads so we can wait for them to exit
        self.tiledCages = {}          # associate tiled cage with ID
        self.fileSaveDir = '.'        # directory for saving puzzles

    def setTitle(self):
        N = self.dim
        self.win.title('KenKen DLX Solver %d-by-%d' %(N,N))

    def makeMenu(self, win):
        def notdone():
            showerror('Not implemented', 'Not yet available')

        top = Menu(win)                                # win=top-level window
        win.config(menu=top)                           # set its menu option

        file = top.file = Menu(top, tearoff = 0)
        file.add_command(label='New...',  command=self.dimensionDialog, underline=0)
        file.add_command(label='Print',   command=self.board.printBoard, underline=0)
        file.add_command(label='Save',    command=self.savePuzzle, underline=0)
        file.add_command(label='Quit',    command=win.quit, underline=0)
        file.entryconfigure('Save', state="disabled")

        top.add_cascade(label='File',     menu=file,                      underline=0)
        return top

    def validateCurrentCage(self, op, valStr):
        board = self.board
        cells = board.currentCage()

        try:
            cage = Cage(op, valStr, cells, self.dim)
        except CageError, e:
            showerror('Cage Error', e)
            return None
        return cage

    def tileCurrentCage(self, cage):
        ID = self.nextCage
        thrd = self.TileThread(cage, self.dim, ID, self.tiledCages)
        self.threads.append(thrd)
        for cell in cage:
            self.cageID[cell] = ID
        self.nextCage += 1
        thrd.start()

        # if all cells have been assigned to a cage, wait for threads to exit
        if len(self.cageID) == self.dim * self.dim:
            for thrd in self.threads:
                thrd.join()

            self.dumpLog()

            if askokcancel("All Cells Filled", "Ready to Solve?", parent = self.board):
                start = time.clock()
                cursor = self.board.cget('cursor')
                self.board.configure(cursor = 'watch')
                self.board.update()
                self.solve()
                self.board.configure(cursor = cursor)
                elapsed = time.clock() - start
                self.log.text.insert(INSERT, "%d updates %.1f seconds\n\n" % (self.updates, elapsed))
                self.updates = 0
                self.report()

    def solve(self):
        # Prepare input for dancing links solver and call solver

        digits=   [str(x) for x in range(1, self.dim+1)]
        lines =   [str(x) for x in range(self.dim)]
        idents =  set(self.cageID.values())
        self.solns = []

        # Some tiled cages may not correspond to any existing cage,
        # because of the cage may have been edited after tiling.

        cages = self.tiledCages
        temp = [(idx, cages[idx]) for idx in cages if idx in idents]
        cages = self.tiledCages = dict(temp)
        primary = ['C'+ str(c) for c in idents] + [n+'R'+x for n in digits for x in lines] +\
                      [n+'C'+x for n in digits for x in  lines]
        primary.sort()
        matrix = [tile for cage in cages.values() for tile in cage.code ]

        DLX = Dancer(primary, matrix, pattern = re.compile(r'C\d+$'))
        self.updates = DLX.solve()
        self.solns = DLX.report()

    def report(self):
        solns = self.solns
        if not solns:
            showerror('Bad Problem', 'No Solution')
        elif len(solns) == 1:
            self.menu.file.entryconfigure('Save', state='normal')
            if askyesno('One Solution', 'Display the solution?', default='no'):
                self.board.printSolution(solns[0])
        else:
            for idx, soln in enumerate(solns):
                if askyesno('%d Solutions' % len(solns), 'Display solution number %d?' %(idx+1)):
                    self.board.printSolution(soln)
                else:
                    break

    def deleteCage(self, id):
        # remove all cells in cage id from the cageId dict and return a list of the deleted cells

        ID = self.cageID
        answer = [cell for cell in ID if ID[cell] == id]
        for cell in answer:
            del(ID[cell])
        return answer

    def clear(self, dim):
        for thread in self.threads:         # make sure all threads have finished
            thread.join()
        self.cageID = {}
        self.nextCage = 0
        self.threads = []
        self.tiledCages = {}
        self.dim = dim

    def dimensionDialog(self):

        # **************** TODO ****************************
        # Change this to a reusable class

        win = self.winDim = Toplevel()
        win.withdraw()  # Remain invisible while we figure out the geometry
        relx= .5
        rely = .3
        master = self.win
        win.transient(master)

        self.var = IntVar(value = self.dim)
        for idx, pick in enumerate(range(4,10)):
            rad = Radiobutton(win, text=str(pick), value=pick, variable=self.var)
            rad.grid(row = 0, column = idx)
        ok = Button(win, text = 'Okay', command = self.okayDim)
        cancel = Button(win, text = 'Cancel', command = self.cancelDim)
        ok.grid(row = 1, column = 1)
        cancel.grid(row = 1, column = 4)

        win.update_idletasks() # Actualize geometry information
        if master.winfo_ismapped():
            m_width = master.winfo_width()
            m_height = master.winfo_height()
            m_x = master.winfo_rootx()
            m_y = master.winfo_rooty()
        else:
            m_width = master.winfo_screenwidth()
            m_height = master.winfo_screenheight()
            m_x = m_y = 0
        w_width = win.winfo_reqwidth()
        w_height = win.winfo_reqheight()
        x = m_x + (m_width - w_width) * relx
        y = m_y + (m_height - w_height) * rely
        if x+w_width > master.winfo_screenwidth():
            x = master.winfo_screenwidth() - w_width
        elif x < 0:
            x = 0
        if y+w_height > master.winfo_screenheight():
            y = master.winfo_screenheight() - w_height
        elif y < 0:
            y = 0
        win.geometry("+%d+%d" % (x, y))
        win.title('Dimension')

        win.deiconify()          # Become visible at the desired location
        win.wait_visibility()
        win.grab_set()           # make modal

    def okayDim(self):
        self.winDim.destroy()
        self.clear(self.var.get())
        self.board.drawNew()

    def cancelDim(self):
        self.winDim.destroy()

    def dumpLog(self):
        log = self.log
        helpStr1 = 'Cell coordinates displayed as rc, where r = row and c = column.  \n'
        helpStr2 = 'For example, 31 means row 3, column 1\n\n'

        log.text.insert(INSERT, helpStr1)
        log.text.insert(INSERT, helpStr2)

        # Some tiled cages may not correspond to any existing cage,
        # because of the cage may have been edited after tiling.
        idents =  set(self.cageID.values())
        for idx in idents:
            cage = self.tiledCages[idx]
            self.log.text.insert(INSERT, 'Cage %d: length %d: %s\n' %(idx, len(cage.code), cage.cage))

    def savePuzzle(self):
        # Menu item is enabled if and only if the puzzle has been solved
        # and has exactly one solution

        dim = self.dim
        fname = asksaveasfilename( filetypes = [('KenKen Files', '.ken')],
                                   title = 'Save Puzzle',
                                   defaultextension = 'ken',
                                   initialdir = self.fileSaveDir)
        if not fname: return
        self.fileSaveDir = os.path.split(fname[0])
        fout = file(fname, 'w')
        fout.write('# %s\n' % os.path.split(fname)[1])
        fout.write('# %s\n' % time.strftime("%A, %d %B %Y %H:%M:%S"))
        fout.write('dim %d\n' % dim)
        cages = [tc.cage for tc in self.tiledCages.values()]
        self.colorCages(cages)
        for cage in cages:
            fout.write(cage.__str__())
            fout.write(' %s\n' % cage.color)
        fout.write('#\nSolution\n')
        c = [tile[n:n+3] for tile in self.solns[0] for n in range(0, len(tile),3)]
        c = tuple([x[0] for x in sorted(c, key = lambda y: y[2] + y[1] )])
        fmt = dim* '%s ' + '\n'
        for row in range(dim):
            fout.write( fmt % c[row*dim: (row+1)*dim] )
        fout.write('#\n')
        logText = self.log.gettext()
        for line in logText.split('\n'):
            fout.write('# ' + line +'\n')
        fout.close()

    def colorCages(self, cages):

        ident = {}       # associates each cell with its cage
        adjacent = {}     # adjacency list for cages

        for idx, c in enumerate(cages):
            c.color = None
            for x,y in c:
                ident[(x,y)] = idx
                adjacent[idx] = []

        for x, y in ident:
            cage = ident[(x,y)]
            for z in [(x+1, y), (x, y+1), (x-1, y), (x, y-1)]:
                try:
                    idz = ident[z]
                    if idz != cage and idz not in adjacent[cage]:
                        adjacent[cage].append(idz)
                except KeyError:
                    pass

        self.color6(cages, adjacent)

    def color6(self, cages, graph):   # six-color a planar graph
        # graph is a dict of adjacency lists
        # both the keys and the elements of the lists are
        # indices into the self.cages list

        if len(graph) == 1:
            idx = graph.keys()[0]
            cages[idx].color = 0
            return
        for idx in graph:            # there must be a vertex of degree < 6
            if len(graph[idx]) <= 5:
                break
        nbd = graph[idx]             # delete this vertex from the graph
        del(graph[idx])
        for v in graph:
            try:
                graph[v].remove(idx)
            except ValueError:
                pass
        self.color6(cages, graph)           # color the remainder, then use first available
                                            # color for the deleted vertex

        nbdColors = [cages[n].color for n in nbd]
        cages[idx].color = min([x for x in range(6) if x not in nbdColors])

def main():
    root = Tk()
    KenKen(root, dim=9)
    root.mainloop()

if __name__ == "__main__":
    main()
