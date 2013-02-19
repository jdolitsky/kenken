# a simple text or file viewer component
# Modified slightly from "programming Python", 2d edition
# Biggest modification is gridding instead of packing, after example 24-10
# in Brent Welch's "Practical Programming in Tcl and Tk"

from Tkinter import *

class ScrolledText(Frame):

    def __init__(self, parent=None, text='', file=None, **kwargs):
        Frame.__init__(self, parent)
        self.makewidgets(**kwargs)
        self.grid()
        self.rowconfigure(0, weight = 1)
        self.columnconfigure(0, weight = 1)
        self.settext(text, file)

    def makewidgets(self, **kwargs):
        yscroll = Scrollbar(self, orient = VERTICAL)
        xscroll = Scrollbar(self, orient = HORIZONTAL)
        text = Text(self, relief=SUNKEN, **kwargs)
        yscroll.config(command=text.yview)
        xscroll.config(command=text.xview)
        text.config(yscrollcommand=yscroll.set)
        text.config(xscrollcommand=xscroll.set)
        text.grid(column = 0, row = 0, sticky = "news")
        yscroll.grid(column = 1, row = 0, sticky= "news")
        xscroll.grid(column = 0, row = 1, sticky = "ew")
        self.text = text

    def settext(self, text='', file=None):
        if file:
            text = open(file, 'r').read()
        self.text.delete('1.0', END)                     # delete current text
        self.text.insert('1.0', text)                    # add at line 1, col 0
        self.text.mark_set(INSERT, '1.0')                # set insert cursor
        self.text.focus()                                # save user a click

    def gettext(self):                                   # returns a string
        return self.text.get('1.0', END+'-1c')           # first through last

    def clear(self):
        self.text.delete('1.0', END)

if __name__ == '__main__':
    root = Tk()
    try:
        st = ScrolledText(file=sys.argv[1], wrap = "none") # filename on cmdline
    except IndexError:
        st = ScrolledText(text='Words\ngo here', wrap = "none")   # or not: 2 lines
    def show(event):
        print (repr(st.gettext()))        # show as raw string
    root.bind('<Key-Escape>', show)       # esc = dump text
    root.mainloop()


