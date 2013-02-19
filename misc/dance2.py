"""This script implements Knuth's 'dancing links' DLX algorithm for solving
the exact cover problem by backtrack"""

# The basic idea is to represent the problem as a zero-one matrix.  
# The rows represent subsets of some set U and the columns represent
# the elements of U, and a 1 in the matrix means set membership.
# The problem is to find a family of subsets of that parition U,

# that is, to find a set of rows of the matrix so that each column
# contains a 1 in exactly one row of the family.  Alternatively,
# one may ask for all such families, as Knuth does.

# Kunth also considers an extension where some of the columns are
# allowed to contain at most one 1.

# The "Dancing Links" paper is available at
# http://www-cs-faculty.stanford.edu/~uno/preprints.html

import time
import psyco

class ColumnError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Node:

    #A one in the membership matrix
    #Each row is represented as a list of nodes.  
    #The up and down links indicate the columns
    
    def __init__(self,up=None,down=None,col=None,row=None):

        self.up      = up        # reference tothe previous 1 in this column
        self.down  = down    # reference to the next 1 in this column
        self.col     = col        # reference to the header node of this column
        self.row    = row       # the number of this row  (or possibly 'head')
        
class Column:

    #The column headers
    
    def __init__(self, next = None, prev = None, length = 0):
        self.prev   = prev        # referference to the previous column (or perhaps 'head')
        self.next   = next        # referference to the next column (or perhaps 'head')        
        self.length = length    # number of 1's in this column
        self.row = 'head'         # this is how we know we've processed the whole column

class Dancer:
    """The main class for dancing links.

    Contains the sparse matrix and the methods for initializing it, backtracking
    for a solution or all solutions, and outputting results."""
    
    def __init__(self, primary, matrix, secondary = []):
        if primary == []:
            raise RunTimeError("No primary columns!")
        if matrix == []:
            raise RunTimeError("No membership matrix")
        self.columns = primary + secondary
        for row in matrix:
            for col in row[:-1]:
                if not col in self.columns:
                    raise ColumnError(col)

        headers = {}                # temporary dict used to construct self.matrix
        self.matrix = []             # "jagged array" of nodes: a list of lists of ones in the matrix 
        self.rows = {}               # symbolic names for the rows, indexed by row number
        self.root = Column()
        self.readColumns(primary, secondary, headers)   # modifies headers
        self.readRows(headers, matrix)                         # initializes self.matrix and self.rows
        self.solutions = []
        self.updates = 0
        psyco.bind(self.backTrack)
                
    def _recorder(self, level, choice):
        
        # Record solution. Not to be called outside class
       
        answer = []
        rows = self.rows
        
        for idx in range(0, level+1):
            num = choice[idx].row
            answer += [rows[num]] 
        self.solutions.append(answer)
    
    def report(self):

        # Print report.  Intended to be called by class user.
        
        return self.solutions
        
    def readColumns(self, primary, secondary, headers):
        
        # Sets up the list of column headers. The primary columns headers form a
        # doubly-linked list, but the secondary column headers do not.  This is because we do
        # not require that secondary columns be covered.
        
        # The headers parameter is a dict of references to the column headers, indexed by column names.
        # This is needed to set up the membership matrix.
        
        curCol = root = self.root

        for p in primary:
            nextCol = headers[p] = Column(prev = curCol, next = root)
            nextCol.up = nextCol.down = nextCol
            curCol.next = nextCol
            curCol = nextCol
        curCol.next = root
        root.prev = curCol
        
        for s in secondary:
            col =  headers[s] = Column()
            col.prev = col.next = col.up = col.down = col

    def readRows(self, headers, matrix):
        # Initialize the membership matrix.

        # The input is a list of rows.  The rows are simply the names of the columns with a
        # 1 in this row, except that the last entry in each row is a symbolic name for the row.
        # The columns must be listed in the same order as in the primary
        # and secondary inputs, primary columns first.
        
        # The headers parameter is a dict of header nodes, indexed by column names

        for num, row in enumerate(matrix):
            newRow = []
            self.rows[num] = row[-1]
            for col in row[:-1]:           # for each column with a 1 in this row
                h = headers[col]
                
                # insert new node at the bottom of it column
                # h.up points to last element in the column
                
                n = Node(up = h.up, down = h, col = h, row = num)
                h.length += 1    
                
                # adjust the column header and old last node
                # note that this works correctly on the first node in the column

                h.up.down = n
                h.up = n 
                
                newRow += [n]
            self.matrix.append(newRow)
                

    def backTrack(self, findAll):
        """The main routine.

        Returns the number of solutions found"""
        
        # Knuth's comments in his dance program say, in part, "Our strategy for generating all
        # exact covers will be to repeatedly choose always the column that appears to be
        # hardest to cover, namely, the column with the shortest list, from all columns that
        # still need to be covered.  And we explore all possibilities via depth-first search.
        # ...
        # The basic operation is 'covering a column.'  This means removing it from the list of
        # columns needing to be covered, and 'blocking' its rows: removing nodes from other
        # lists whenever they belong to a row of a node in this column's list."
        #
        # This implementation is a little clunky, since I've translated Knuth's dance.c
        # program as literally as I can, and python lacks a goto.  I've simulated gotos
        # by setting a state variable.  Many of the comments are copied from Knuth.

        count = 0     # number of solutions
        level  = 0     # number of choices in current partial solution
        choice = {}  # the list of such choices, for printing solution, or backtracking
        
        state   = 'forward'
        matrix = self.matrix
        root = self.root

        while True:

            # forward:

            if state is 'forward':
               
                # Set best to best column for branching (one with fewest elements)

                minLength = 10000000  # infinity
                cur = root.next
                while cur != root:
                    if cur.length < minLength:
                        best = cur
                        minLength = cur.length
                    cur = cur.next
                self.cover(best)
                
                # choose each one in the column, going downwards
                
                currNode = choice[level] = best.down  

            #advance:

            if currNode.row == 'head':
                state = 'backup'            # goto backup
            else:

                #cover all other columns of currNode

                for pp in matrix[currNode.row]:
                    if pp.col != best:
                        self.cover(pp.col)                    
                        
                if root.next == root:    # no more primary columns to cover

                    # record solution
                                    
                    self._recorder(level, choice)
                    count += 1
                    
                    if findAll:
                        state = 'recover'   # goto recover
                    else:
                        break               # done
                else:
                    level += 1
                    state = 'forward'
                    continue                # goto forward

            #backup:

            if state is 'backup':
                self.uncover(best)
                if level == 0:
                    break                   # done
                level -= 1
                currNode = choice[level]    
                best = currNode.col

            #recover:  ( backup falls through to here )             

            if state in ('backup', 'recover'):
                
                # Uncover all other columns of currNode
                # Done in reverse order of covering
                
                for pp in reversed(matrix[currNode.row]):
                    if pp.col != best:
                        self.uncover(pp.col)

                currNode = choice[level] = currNode.down
                state = 'advance'               # goto advance
        return count

    def cover(self, col):
        # When a row is blocked, it leaves all lists except the 
        # list of the column that is being covered.  Thus, a node 
        # is never removed fom a list twice. -- Knuth"""
        
        matrix  = self.matrix
        updates = 1
        left    = col.prev
        right   =col.next
        left.next   = right      # remove col from the headers list
        right.prev = left
        rr = col.down            # first one in column         
       
        while rr.row != 'head':     # for each one in column
            for nn in matrix[rr.row]:            
                if nn.col != col:
                    updates += 1
                    uu = nn.up
                    dd = nn.down
                    uu.down = dd
                    dd.up   = uu               # remove node from the column
                    nn.col.length -= 1
            rr = rr.down      # next row
        self.updates += updates

    def uncover(self, col):
        
        # Uncovering is done in precisely the reverse order.  
        # The pointers thereby execute an
        # exquisitely choreographed dance which returns them 
        # almost magically to their former state. -- Knuth

        matrix  = self.matrix
        rr = col.up                                          # last one in column
        while rr.row is not 'head':
            for nn in reversed(matrix[rr.row]):     # next column in row rr
                if nn.col != col:
                    uu = nn.up
                    dd = nn.down
                    uu.down = dd.up = nn
                    nn.col.length += 1
            rr = rr.up                  # next row
        left    = col.prev
        right   = col.next
        left.next = right.prev = col #put col back into headers list
     
    def solve(self, findAll = False):
        start = time.clock()
        num = self.backTrack(findAll)
        elapsed = time.clock() - start
        return (num, elapsed, self.updates)