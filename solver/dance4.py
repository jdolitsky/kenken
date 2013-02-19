"""This script implements Knuth's 'dancing links' XDL algorithm for solving
the exact cover problem by backtrack"""

# Removed psyco since it doesn't work on python 2.7

# The basic idea is to represent the problem as a zero-one matrix.
# The rows represent subsets of some set U and the columns represent
# the elements of U, and a 1 in the matrix means set membership.
# The problem is to find a family of subsets of that parition U,

# that is, to find a set of rows of the matrix so that each column
# contains a 1 in exactly one row of the family.  Alternatively,
# one may ask for all such families, as Knuth does.

# Kunth also considers an extension where some of the columns are
# allowed to contain at most one 1.

# This script contains a variation of the DLX algorithm that might be
# called "iterated dancing links" or IDLX.  A problem with DLX is that
# there may be a great deal of overhead in updating nodes in this
# column, which will never be covered until the end of the process,
# anyway.  In such a case it may be beneficial to exclude such columns
# from the problem, and find partial solutions disregarding the
# constraints they reprsesent.  If it turns out that many rows cannot
# belong to such partial solutions, they can be deleted from the problem,
# and the long columns reinserted.  The revised problem can the be
# solved by the ordinary DLX algorithm.  If there are several long columns,
# it may be necessary to do this more than once.

# The "Dancing Links" paper is available at
# http://www-cs-faculty.stanford.edu/~uno/preprints.html

# import psyco
#from psyco.classes import *

class ColumnError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

#class Node(psyco.compact):
class Node(object):
    # A nonzero entry in the membership matrix

    def __init__(self,left=None,right=None,up=None,down=None,col=None,row=None):
                            # all lists are circular in both directions
        self.left  = left   # the column name of the previous 1 in this row
        self.right = right  # the column name of the next 1 in this row
        self.up    = up     # the row number of the previous 1 in this column
        self.down  = down   # the row number of the next 1 in this column
        self.col   = col    # the name of this column
        self.row   = row    # the number of this row  (or possibly 'head')

#class Column(psyco.compact):
class Column(object):
    #The column headers

    def __init__(self, next = None, prev = None):
        self.prev   = prev
        self.next   = next
        self.length = 0         # number of 1's in this column
        self.seconded = False   # temporarily made secondary?

#class Dancer(psyco.compact):
class Dancer(object):
    # The main class for dancing links.

    # Contains the sparse matrix and the methods for initializing it, backtracking
    # for a solution or all solutions, and outputting results.

    # If pattern (a compiled regular expression is supplied, then the iterated dancing
    # links alogorithm will be employed.  Any columns whose name matches the
    # pattern and whose length exceeds the bound will be initially excluded from the
    # problem.

    def __init__(self, primary, matrix, secondary = [], bound = 42000, pattern = None):
        if primary == []:
            raise RunTimeError("No primary columns!")
        if matrix == []:
            raise RunTimeError("No membership matrix")
        self.columns = primary + secondary
        for row in matrix:
            for col in row[:-1]:
                if not col in self.columns:
                    raise ColumnError(col)
        self.nodes   = {}
        self.headers = {}
        self.rows = {}
        self.updates = 0
        self.solutions = []
        self.bound = bound
        self.pattern = pattern

        self.setHeaders(primary, secondary)
        self.readRows(matrix)

    def _recorder(self, level, choice):

        # Record solution. Not to be called outside class

        answer = []
        #rows = self.rows

        for idx in range(0, level+1):
            num = choice[idx].row
            answer += [num]
        self.solutions.append(answer)

    def setHeaders(self, primary, secondary):
        """Sets up the header dictionary of column headers. The primary columns headers form a
        doubly-linked list, but the secondary column headers do not.  This is because we do
        not require that secondary columns be covered."""

        headers = self.headers
        nodes = self.nodes
        headers['root'] = Column()
        curCol = 'root'
        for p in primary:
            headers[curCol].next = p
            headers[p] = Column(prev = curCol)
            curCol = p
            nodes['head', p] = Node(up = 'head', down = 'head', col = curCol, row = 'head')
        headers[curCol].next = 'root'
        headers['root'].prev = curCol
        for s in secondary:
            headers[s] = Column(prev = s, next = s)
            nodes['head', s] = Node(up = 'head', down = 'head', col = curCol, row = 'head')

    def readRows(self, matrix):
        """Initialize the membership matrix.

        The input is a list of rows.  The rows are simply the names of the columns with a
        1 in this row,  except that the last entry in each row is a symbolic name for the row.
        The columns must be listed in the same order as in the primary
        and secondary inputs, primary columns first."""

        nodes   = self.nodes
        rows    = self.rows
        headers = self.headers

        for rowNum, row in enumerate(matrix):
            rows[rowNum] = row[-1]
            for i, c in enumerate(row[:-1]):
                c = row[i]
                h = nodes['head', c]
                next = row[i+1]         # wrong for the last 1 in the row

                # h.up points to last element in the column
                nodes[rowNum, c] = Node(row[i-1],next, h.up, 'head', c, rowNum)

                # hook the new node in at the bottom of the column
                # note that this will handle the first node in the column

                nodes[h.up, c].down = rowNum
                h.up = rowNum
                headers[c].length += 1

            # hook first and last 1s in row together

            nodes[rowNum, c].right = row[0]
            nodes[rowNum, row[0]].left = row[-2]



    def backTrack(self, findAll):
        #The main routine.

        # Returns the number of solutions found

        # Knuth's comments in his dance program say, in part, "Our strategy for generating all
        # exact covers will be to repeatedly choose always the column that appears to be
        # hardest to cover, namely, the column with the shortest list, from all columns that
        # still need to be covered.  And we explore all possibilities via depth-first serach.
        # ...
        # The basic operation is 'covering a column.'  This means removing it from the list of
        # columns needing to be covered, and 'blocking' its rows: removing nodes from other
        # lists whenever they belong to a row of a node in this column's list."
        #
        # This implementation is a little clunky, since I've translated Knuth's dance.c
        # program as literally as I can, and python lacks a goto.  I've simulated gotos
        # by setting a state variable.  Many of the comments are copied from Knuth.

        level  = 0    # number of choices in current partial solution
        choice = {}   # the list of such choices, for printing solution, or backtracking
        count  = 0    # number of solutions

        state   = 'forward'
        nodes   = self.nodes
        headers = self.headers
        root    = headers['root']
        rows    = self.rows

        while True:

            # forward:

            if state == 'forward':
                # Set best to best column for branching (one with fewest elements)
                minLength = 10000000  # infinity
                cur       = root.next

                while cur != 'root':
                    h = headers[cur]
                    if h.length < minLength:
                        best      = cur
                        minLength = h.length
                    cur = h.next
                self.cover(best)
                choice[level] = nodes[nodes['head', best].down, best]
                currNode = choice[level]

            #advance:

            if currNode.row == 'head':
                state = 'backup'            # goto backup
            else:

                #cover all other columns of currNode

                pp = nodes[currNode.row, currNode.right]
                while pp.col != best:
                    self.cover(pp.col)
                    pp = nodes[pp.row, pp.right]
                if headers['root'].next == 'root':

                    # record solution

                    self._recorder(level, choice)

                    if findAll:
                        state = 'recover'   # goto recover
                    else:
                        break               # done
                else:
                    level += 1
                    state = 'forward'
                    continue                # goto forward

            #backup:

            if state == 'backup':
                self.uncover(best)
                if level == 0:
                    break                   # done
                level   -= 1
                currNode = choice[level]
                best     = currNode.col

            #recover:  ( backup falls through to here )

            if state in ('backup', 'recover'):

                # uncover all other columns of currNode
                # We included left links, thereby making the list doubly linked, so that columns
                # would be uncovered in the correct LIFO order in this part of the program. -- Knuth

                pp = nodes[currNode.row, currNode.left]
                while pp.col != best:
                    self.uncover(pp.col)
                    pp = nodes[pp.row, pp.left]
                currNode = choice[level] = nodes[currNode.down, currNode.col]
                state    = 'advance'               # goto advance

    def cover(self, col):
        # When a row is blocked, it leaves all lists except the list of the column that
        # is being covered.  Thus, a node is never removed fom a list twice. -- Knuth

        updates = 1
        nodes   = self.nodes
        headers = self.headers
        left    = headers[col].prev
        right   = headers[col].next
        headers[left].next   = right               # remove col from the headers list
        headers[right].prev  = left
        rr = nodes['head', col].down               # next row in column
        while nodes[rr, col].row != 'head':
            nn = nodes[rr, nodes[rr, col].right]   # next column in row rr
            while nn.col != col:
                uu = nn.up
                dd = nn.down
                cc = nn.col
                nodes[uu, cc].down = dd
                nodes[dd, cc].up   = uu            # remove node from the column
                headers[cc].length -= 1
                updates += 1
                nn = nodes[nn.row, nn.right]         #next column
            rr = nodes[rr, col].down                    # next row
        self.updates += updates

    def uncover(self, col):
        # Uncovering is done in precisely the reverse order.  The pointers thereby execute an
        # exquisitely choreographed dance which returns them almost magically to their former
        # state. -- Knuth

        nodes   = self.nodes
        headers = self.headers
        rr      = nodes['head', col].up             # last row in column
        while nodes[rr, col].row != 'head':
            nn = nodes[rr, nodes[rr, col].left]     # next column in row rr
            while nn.col != col:
                uu = nn.up
                dd = nn.down
                cc = nn.col
                nodes[uu, cc].down = nodes[dd, cc].up = nn.row
                headers[cc].length += 1
                nn = nodes[nn.row, nn.left]         #next column
            rr = nodes[rr, col].up                  # next row
        left    = headers[col].prev
        right   = headers[col].next
        headers[left].next = headers[right].prev = col #put col back into headers list

    def cover2(self, col):
        # Variant of cover() for covering a long column
        # The difference is that in blocking the rows, we not only remove them
        # fom their columns, but also temporarily make the columns into
        # secondary columns.  That is, we remove their headers from the
        # the header list, and make their next and prev pointers
        # point to themselves.  We keep the old values in self.seconded,
        # so that we can undo this later.
        # We don't bother to adjust the length; it's not used
        # in a secondary column, and the DLX algorithm will set it back to its
        # original value at the end, anyway.

        # If col is secondary, removing it from the headers list
        # has no ill effects.
        # If col is (originally) primary, we don't want to remove
        # it a second time.

        seconded = self.seconded
        blocked  = self.blocked
        headers  = self.headers
        nodes    = self.nodes
        updates  = 0

        if not headers[col].seconded:
            updates                = 1
            left                   = headers[col].prev
            right                  = headers[col].next
            headers[left].next     = right        # remove col from the headers list
            headers[right].prev    = left
            headers[col].next      = col
            headers[col].prev      = col
            headers[col].seconded  = True
            seconded.append((col, left, right))
        rr = nodes['head', col].down               # next row in column
        while nodes[rr, col].row != 'head':
            blocked.append(rr)
            nn = nodes[rr, nodes[rr, col].right]   # next node in row rr
            while nn.col != col:

                # remove node from its column

                uu = nn.up
                dd = nn.down
                cc = nn.col
                nodes[uu, cc].down = dd
                nodes[dd, cc].up   = uu

                # temporarily make the column secondary

                if not headers[cc].seconded:

                    # remove cc from the headers list

                    left                 = headers[cc].prev
                    right                = headers[cc].next
                    headers[left].next   = right
                    headers[right].prev  = left
                    headers[cc].next     = cc
                    headers[cc].prev     = cc
                    headers[cc].seconded = True
                    seconded.append( (cc, left, right) )

                nn = nodes[nn.row, nn.right]         #next node in the row
                updates += 1
            rr = nodes[rr, col].down                 # next row
        self.updates += updates

    def uncover2(self, col):
        # Variant of uncover() for uncovering long columns.  Note that we don't undo
        # the seconding in this method.  That is done by unsecond().

        nodes   = self.nodes
        headers = self.headers
        rr      = nodes['head', col].up                 # last row in column
        while nodes[rr, col].row != 'head':
            nn = nodes[rr, nodes[rr, col].left]         # previous node in row rr
            while nn.col != col:
                uu = nn.up
                dd = nn.down
                cc = nn.col
                nodes[uu, cc].down = nodes[dd, cc].up = nn.row
                nn = nodes[nn.row, nn.left]             # previous node in row
            rr = nodes[rr, col].up                      # previous row in column

    def unsecond(self):
        headers = self.headers
        for col, left, right in reversed(self.seconded):
            headers[col].seconded = False
            headers[col].prev     = left
            headers[col].next     = right
            headers[left].next    = headers[right].prev = col

    def report(self):

        # Print report.  Intended to be called by class user.

        return [[self.rows[r] for r in s] for s in self.solutions]

    def solve(self, findAll = True):
        rows = self.rows
        longCols = []
        if self.pattern is not None:
            pattern = self.pattern
            headers = self.headers
            bound = self.bound
            longCols = [col for col in headers if pattern.match(col) \
                        and headers[col].length > bound]
        if longCols:
            self.seconded = []
            self.blocked  = []

            for col in longCols:
                self.cover2(col)    # computes self.seconded and self.blocked

            self.backTrack(findAll)
            goodRows = set(reduce(lambda x,y:x+y,self.solutions,[]))

            # put the matrix back in its original condition

            for col in reversed(longCols):
                self.uncover2(col)
            self.unsecond()

            # delete useless rows

            for row in self.rows:
                if row not in goodRows and row not in self.blocked:
                    self.deleteRow(row)

            self.solutions = []        # erase the partial solutions

        self.backTrack(findAll)
        return self.updates

    def deleteRow(self, row):
        nodes   = self.nodes
        headers = self.headers
        updates = 0
        for col in headers:
            if (row, col) in nodes: break
        nn = nodes[row, nodes[row, col].right]   # next column in row rr
        while nn.col != col:
            uu = nn.up
            dd = nn.down
            cc = nn.col
            nodes[uu, cc].down = dd
            nodes[dd, cc].up   = uu              # remove node from the column
            headers[cc].length -= 1
            nn = nodes[nn.row, nn.right]     #next column
            updates += .5                        # this update won't be undone

        # Now delete the original node

        uu = nn.up
        dd = nn.down
        cc = nn.col
        nodes[uu, cc].down = dd
        nodes[dd, cc].up   = uu
        headers[cc].length -= 1
        self.updates += int(updates + 1.1)

    def printColumn(self, col):
        rows    = self.rows
        nodes   = self.nodes

        print "%s: length %d " % (col, self.headers[col].length)
        rr = nodes['head', col].down
        while rr != 'head':
            row = rows[rr]
            print "    %s" % ' '.join([row[i:i+3] for i in range(0, len(row), 3)])
            rr = nodes[rr, col].down

    def printHeaders(self):
        headers = self.headers
        col = headers['root'].next
        while col != 'root':
            #print col
            self.printColumn(col)
            col = headers[col].next
        print






