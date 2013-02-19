#convert.py
# One-tiem program to convert old .ken files without coloring information
# to new-format files

from pyparsing import *
import os, glob, sys, time

class Cage(list):
    def __init__(self, op, val, cells):
        self.op = op
        self.value = val
        for c in cells:
            self.append( (int(c[0]), int(c[1])) )
            
    def __str__(self):
        #oper = {ADD:"ADD ", SUB:"SUB ", MUL:"MUL ", DIV:"DIV ", NONE: "NONE "}
        answer = '%s %s %s' %(self.op, str(self.value), '[ ')
        for cell in sorted(self):
            answer = answer + "%d%d " % (cell[0], cell[1])
        answer = answer + ']'
        return answer

class Puzzle(object):            
    def __init__(self, fin):
        
        # fin will be passed to pyparsing.  It must be an open file object
        
        def coords(idx):
            
            # utility function to convert list index to coordinates
            
            return (1+idx // dim, 1 + idx % dim)
        
        self.cages        = []
        self.solution     = {}

        # use pyparsing to parse input file        
        
        try:
            p = self.parseKen(fin)           
            type = 'ken'
        except ParseException:
            raise
        self.dim = dim = int(p.dim)
        # Cells are numbered as (row, col), where 1 <= row, col <= dim
        
        for c in p.cages:
            cage = Cage( c.oper, int(c.value), c.cells )
            self.cages.append(cage)
            
                                    
        for idx, val in enumerate(p.soln):
            self.solution[coords(idx)] = int(val)
                   
                 
    def parseKen(self, fin):
        # parser for .ken files
        
        operator = oneOf("ADD SUB MUL DIV NONE")
        integer  = Word(nums)
        lbrack   = Suppress('[')
        rbrack   = Suppress(']')

        cage = Group( operator("oper") + integer("value") +\
                      lbrack + OneOrMore(integer)("cells") + rbrack)
        cages = OneOrMore(cage)("cages")         
        
        solution  = "Solution" + OneOrMore(integer)("soln")
        dimension ="dim" + integer("dim")

        puzzle = dimension + cages + solution
        
        puzzle.ignore(pythonStyleComment)
        
        return puzzle.parseFile(fin, parseAll = True)
    
    def colorCages(self):
                    
        ident = {}       # associates each cell with its cage
        adjacent = {}     # adjacency list for cages
        
        for idx, c in enumerate(self.cages):
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
                
        self.color6(self.cages, adjacent)
        
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
        
    def writeFile(self, fname):
        fout = file(fname, 'w')
        fout.write('# %s\n' % os.path.split(fname)[1])
        fout.write('# %s\n' % time.strftime("%A, %d %B %Y %H:%M:%S"))
        fout.write('dim %d\n' % self.dim)
        self.colorCages()
        for cage in self.cages:
            fout.write(cage.__str__())
            fout.write(' %s\n' % cage.color)
        fout.write('#\nSolution\n')
        dim = self.dim
        for j in range(1,1+dim):
            for k in range(1, 1+dim):
                fout.write('%2d' %self.solution[(j,k)])
            fout.write('\n')
        fout.close()

def main(indir, outdir):
    os.chdir(indir)
    kenkens = glob.glob('*.ken')
    for fname in kenkens:
        fin = file(fname)
        p = Puzzle(fin)
        fin.close()
        p.colorCages()
        p.writeFile(os.path.join(outdir,fname))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
    