from pyparsing import oneOf, OneOrMore, Group, Word, nums, Suppress, pythonStyleComment, ParseException
import time
import os.path 

class Checkpoint(object):
    # Used to stop undo rollback 
    pass

class AnswerError(Exception):
    def __init__(self, cells):
        self.cells = cells
        
class CandidateError(Exception):
    def __init__(self, cells):
        self.cells = cells
        
class Cage(list):
    def __init__(self, op, val, cells, color):
        self.op = op
        self.value = val
        self.color = color
        for c in cells:
            self.append( (int(c[0]), int(c[1])) )
    
    def __str__(self):
        answer = '%s %s %s' %(self.op, str(self.value), '[ ')
        for cell in sorted(self):
            answer = answer + "%d%d " % (cell[0], cell[1])
        answer = answer + ( '] %d' % self.color )   
        return answer
            
class Update(object):
    def __init__(self, coords, ans, cand):
        self.coords, self.answer, self.candidates = coords, ans, cand

class Puzzle(object):            
    def __init__(self, fin, parent):
        
        # fin will be passed to pyparsing.  It must be an open file object
        
        def coords(idx):
            
            # utility function to convert list index to coordinates
            
            return (1+idx // dim, 1 + idx % dim)
        
        self.cages        = []
        self.solution     = {}
        self.history      = []
        self.answer       = {}
        self.candidates   = {}
        self.oneCellCages = []
        self.cageID       = {}     # map cell to its cage
        self.parent       = parent

        # use pyparsing to parse input file        
        
        try:
            
            # first assume that the file is in .ken format
            
            p = self.parseKen(fin)           
            type = 'ken'
        except ParseException:
            
             # attempt parsing in .kip format 
            
            fin.seek(0,0)          # rewind
            p = self.parseKip(fin)
            type = 'kip'
        except ParseException:
            raise
            
        self.infile    = fin.name
        self.isDirty   = False
        self.dim = dim = int(p.dim)    
        for i in range(1, dim+1):
            for j in range(1, dim+1):
                self.answer[(i,j)] = 0
                self.candidates[(i,j)] = []
        
        # Cells are numbered as (row, col), where 1 <= row, col <= dim
        
        for c in p.cages:
            cage = Cage( c.oper, int(c.value), c.cells, int(c.color) )
            self.cages.append(cage)
            for cell in cage:
                self.cageID[cell] = cage
            
            if len(c.cells) == 1:
                cell = c.cells[0]
                x = int(cell[0])
                y = int(cell[1])
                self.oneCellCages.append( (x, y) )
                self.answer[(x, y)] = int(c.value)
                                    
        for idx, val in enumerate(p.soln):
            self.solution[coords(idx)] = int(val)
        
        if type == 'ken':                    
            return
        
        # input file is in .kip format
        
        for idx, val in enumerate(p.answer):
            self.answer[coords(idx)] = int(val)
            
        for idx, val in enumerate(p.candidates):
            self.candidates[coords(idx)] = [] if val == '0' else [int(c) for c in val]
            
        for h in p.history:
            if h == 'checkpoint':
                self.history.append(Checkpoint())
            else:
                x, y = int(h.coords[0]), int(h.coords[1])
                ans  = int(h.answer)
                cand = [int(c) for c in h.candidates]
                if cand == [0]:
                    cand = []
                self.history.append(Update((x,y), ans, cand ))
                
        self.parent.control.setTime(int(p.time))            
                 
    def parseKen(self, fin):
        # parser for .ken files
        
        operator = oneOf("ADD SUB MUL DIV NONE")
        integer  = Word(nums)
        lbrack   = Suppress('[')
        rbrack   = Suppress(']')

        cage = Group( operator("oper") + integer("value") +\
                      lbrack + OneOrMore(integer)("cells") + rbrack +\
                      integer("color") )
        cages = OneOrMore(cage)("cages")         
        
        solution  = "Solution" + OneOrMore(integer)("soln")
        dimension ="dim" + integer("dim")

        puzzle = dimension + cages + solution
        
        puzzle.ignore(pythonStyleComment)
        
        return puzzle.parseFile(fin, parseAll = True)

    
    def parseKip(self, fin):
        # parser for .kip files
        
        operator = oneOf("ADD SUB MUL DIV NONE")
        integer  = Word(nums)
        lbrack   = Suppress('[')
        rbrack   = Suppress(']')
       
        cage = Group( operator("oper") + integer("value") +\
                      lbrack + OneOrMore(integer)("cells") + rbrack +\
                      integer("color") )
        cages = OneOrMore(cage)("cages")
        
        update  = Group( integer("coords") + integer("answer") +integer("candidates") )
        annal   = "checkpoint" ^ update 
        history = "History" + OneOrMore(annal)("history")
        
        dimension  ="dim" + integer("dim")
        solution   = "Solution" + OneOrMore(integer)("soln")
        answer     = "Answers"  + OneOrMore(integer)("answer")
        candidates = "Candidates" + OneOrMore(integer)("candidates")
        time       = "Time" + integer("time")

        puzzle = dimension + cages + solution + answer + candidates + history + time 
        puzzle.ignore(pythonStyleComment)
        
        return puzzle.parseFile(fin, parseAll = True)
    
    def enterAnswer(self, focus, value):
        
        # User enters an answer in a cell.

        # If the answer conflicts with a value already entered in another cell, 
        # or this answer completes a cage, and the arithmetic is wrong,
        # raise AnswerError.
        
        # If the user is entering (or changing) an answer, compute all resulting
        # inferences, enter them in the history, and return a list of all cells
        # whose values change (whether answers or candidates.)
        
        # If the user is simply reentering the same answer in a cell, do nothing
        # and return an empty list of updates.
        
        history     = self.history
        dim, answer = self.dim, self.answer
        
        if answer[focus] == value:
            return []
        
        row = [x for x in range(1, dim+1) if answer[(x, focus[1])] == value]
        col = [y for y in range(1, dim+1) if answer[(focus[0], y)] == value]
        cells = [(x, focus[1]) for x in row] + [(focus[0], y) for y in col]
        
        if cells:
            raise AnswerError(cells)
        
        cage = self.cageID[focus]
        
        if len([x for x in cage if x != focus and answer[x]]) == len(cage) - 1:
            if not self.goodAnswer(cage, focus, value):
                raise AnswerError(cage)
            
        self.isDirty = True
        history.append(Checkpoint())

        updates =  self.propagate(focus, value)
        for upd in updates:
            history.append( Update(upd.coords, upd.answer, upd.candidates) )
        return updates
    
    def annal(self, focus):
        return Update(focus, self.answer[focus], self.candidates[focus][:])
    
    def propagate(self, focus, value):
        # When an answer is entered in a cell, eliminate that value as a 
        # candidate in all cells in the same line.
        # In cases where that reduces then number of candidates to one,
        # enter the answer and recursively propagate it.
        # All changes are entered in the history.
        # A list of changes is returned
        
        candidates, answer = self.candidates, self.answer
        history, dim       = self.history, self.dim
        x, y = focus
        updates = []
        
        ann = self.annal(focus)
        history.append(ann)
        answer[focus] = value
        updates.append(self.annal(focus))
        for k in range(1, dim+1):
            for coords in ( (x, k), (k, y) ):
                if answer[coords]: 
                    continue
                cand = candidates[coords]
                if  value not in cand: 
                    continue
                if len(cand) == 2:                                       
                    # the element != value equals sum(cand) - value                
                    updates.extend(self.propagate(coords, sum(cand)-value))
                else:
                    ann = self.annal(coords)
                    history.append(ann)
                    candidates[coords].remove(value)
                    updates.append(self.annal(coords))
        return updates
    
    def allCandidates(self, focus):
        # Enter all possible candidates in cell given by focus
        # Ignore if answer already in cell
        # Enter transaction in history and return a list of updates        
        
        history, dim, answer = self.history, self.dim, self.answer
        if answer[focus]:
            return []
        ann = self.annal(focus)
        self.isDirty = True
        history.append(Checkpoint())
        history.append(ann)
        cand = range(1, dim+1)
        x, y = focus
        for k in range(1, dim+1):
            try:
                cand.remove(answer[x, k])
            except ValueError:
                pass
            try:
                cand.remove(answer[k, y])
            except ValueError:
                pass
        if len(cand) != 1:
            self.candidates[focus] = cand
            update = self.annal(focus)
            return [update]                     # only one update
        else:
            updates =  self.propagate(focus, cand[0])
        for upd in updates:
            history.append( Update(upd.coords, upd.answer, upd.candidates) )
        return updates
    
    def fillAllCandidates(self):
        # For each cell withpout an answer or any candidates, enter
        # all possible candidates
        # Enter transaction in history and return a list of updates
        
        candidates, answer, history = self.candidates, self.answer, self.history
        history.append(Checkpoint())  # assume there will be an update
        dirty = self.isDirty          # save current state
        self.isDirty = True
        rng = range(1, self.dim+1)
        updates = []
        
        cells = [(x, y) for x in rng for y in rng]
        for cell in cells:
            if answer[cell] or candidates[cell]:
                continue
            ann = self.annal(cell)
            history.append(ann)            
            cand = rng[:]
            x, y = cell
            for k in rng:
                try:
                    cand.remove(answer[x, k])
                except ValueError:
                    pass
                try:
                    cand.remove(answer[k, y])
                except ValueError:
                    pass
            if len(cand) != 1:
                self.candidates[cell] = cand
                update = self.annal(cell)
                updates.append(update)
            else:
                ups =  self.propagate(cell, cand[0])
                updates.extend(ups)
                for upd in ups:
                    history.append( Update(upd.coords, upd.answer, upd.candidates) )
        if not updates:
            history.pop()           # remove the checkpoint
            self.isDirty = dirty    # restore state
            
        return updates
        
    
    def toggleCandidate(self, focus, value):
        # Ignore if answer already in focus cell.
        # Otherwise, toggle the candidate value on or off.
        
        # If the user attempte to enter a value that is laready an 
        # answer  in the same line, raise CandidateError.
        
        # Enter transaction in history and return a list of updates
        
        history, dim, answer, candidates = \
               self.history, self.dim, self.answer, self.candidates
        
        if answer[focus]:                         # answer present
            return []
        
        ann = self.annal(focus)                  
        
        if value in candidates[focus]:            # toggle value off
            self.isDirty = True
            history.append(Checkpoint())
            history.append(ann)    
            candidates[focus].remove(value)
            update = self.annal(focus)
            return [update]                       # only one update
            
        conflicts = []                            # toggle value on --
        x, y = focus                              # check for conflicts
        for k in range(1, dim+1):
            for coords in ( (x, k), (k, y) ):
                if answer[coords] == value: 
                    conflicts.append(coords)
        if conflicts:                             # conflict found
            raise CandidateError(conflicts)       
        
        self.isDirty = True
        history.append(Checkpoint())              # no conflicts, toggle value on
        history.append(ann)
        candidates[focus].append(value)
        update = self.annal(focus)
        return [update]                           # only one update
    
    def getAllEntries(self):
        # Return a list of updates for all cell that have a value (answer or candidate).
        # Used for initializing the board, whether for one-cell cages or loading a
        # partially-completed solution.
        
        dim = self.dim
        answer, candidates = self.answer, self.candidates
        updates = []
        for j in range(1, dim+1):
            for k in range(1, dim+1):
                if answer[(j, k)] or candidates[(j, k)]:
                    updates.append(self.annal( (j, k) ))
        return updates        
    
    def undo(self):
        # Undo items from the history until a checkpoint is encountered
        # Return a list of the updates made
        
        answer, candidates, history = self.answer, self.candidates, self.history
        try:
            ann = history.pop()
        except IndexError:                    # user tried one too many undos
            return []
        updates = []
        self.isDirty = True
        while not isinstance(ann, Checkpoint):
            coords             = ann.coords
            answer[coords]     = ann.answer
            candidates[coords] = ann.candidates
            updates.append(ann)
            ann                = history.pop()
        return updates
    
    def clearCell(self, focus):
        # If there is an answer in the current cell clear it.
        # If there is no answer, clear the candidate list.
        # Return a list of updates
        
        answer, candidates, history = self.answer, self.candidates, self.history
        if not answer[focus] and not candidates[focus]:
            return []                                # nothing to clear
        
        ann = self.annal(focus)        
        if answer[focus]:
            answer[focus] = 0
        else:
            candidates[focus] = []
        self.isDirty = True
        history.append(Checkpoint())
        history.append(ann) 
        return [self.annal(focus)]
    
    def checkAnswers(self):
        # Compare user's answers to solution, and return a list of errors
        
        dim, answer, solution = self.dim, self.answer, self.solution
        errors = []
        for x in range(1, dim+1):
            for y in range(1, dim+1):
                if answer[(x,y)] and answer[(x,y)] != solution[(x,y)]:
                    errors.append( (x,y) )        
        return errors
    
    def isCompleted(self):
        # Has user entered answer in each cell?
        
        if len([x for x in self.answer.values() if x]) == self.dim ** 2:
            return True
        else:
            return False
        
    def save(self, fname):
        dim = self.dim
        elapsedTime = self.parent.control.getTime()
        fout = file(fname, 'w')
        fout.write('# %s\n' % os.path.split(fname)[1])
        fout.write('# %s\n' % time.strftime("%A, %d %B %Y %H:%M:%S"))
        fout.write('dim %d\n' % dim)    
        for c in self.cages:
            fout.write(c.__str__() + '\n')

        fout.write('#\nSolution\n')
        for row in range(1, dim+1):
            for col in range(1, dim+1):
                fout.write( '%d ' %self.solution[(row, col)] )
            fout.write('\n')
            
        fout.write('#\nAnswers\n')
        for row in range(1, dim+1):
            for col in range(1, dim+1):
                fout.write( '%d ' %self.answer[(row, col)] )
            fout.write('\n')
        
        fout.write('#\nCandidates\n')
        for row in range(1, dim+1):
            for col in range(1, dim+1):
                cand = self.candidates[(row, col)]
                cstr = ''.join([str(c) for c in cand])
                fout.write('%s ' % (cstr if cstr else '0') )
            fout.write('\n')
            
        fout.write('#\nHistory\n')
        for h in self.history:
            if isinstance(h, Checkpoint):
                fout.write('checkpoint\n')
            else:
                fout.write('%d%d ' % h.coords)
                fout.write('%d ' % h.answer)
                cstr = ''.join([str(c) for c in h.candidates])
                fout.write('%s\n' % (cstr if cstr else '0') )

        fout.write('#\nTime %d\n' % elapsedTime)
        
        fout.close() 
        
    def restart(self):
        # Clear all user-entered data
        # User wants to start over
        
        dim = self.dim
        for i in range(1, dim+1):
            for j in range(1, dim+1):
                self.candidates[(i,j)] = []
                if (i, j) not in self.oneCellCages:
                    self.answer[(i,j)] = 0
        self.history = []        
        

    def goodAnswer(self, cage, focus, value):
        # Precondition: Evey cell in cage, except focus, has an filled in
        # Return true iff filling value into focus makes the
        # arithmetic work out
        

        operands = [self.answer[x] for x in cage if x != focus]
        operands += [value]
        if cage.op == "ADD":
            return sum(operands) == cage.value
        if cage.op == "SUB":
            return max(operands) - min(operands) == cage.value
        if cage.op == "MUL":
            product = 1
            for x in operands:
                product *= x
            return product == cage.value
        if cage.op == "DIV":
            return max(operands) // min(operands) == cage.value
        if cage.op == "NONE":            
            return operands[0] == cage.value            
        
if __name__ == '__main__':
    p = Puzzle('../docs/31May2009.ken')
    
