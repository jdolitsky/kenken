
from Tkinter import *
import time

class StopWatch(Frame):
    def __init__(self, win):
        Frame.__init__(self, win)
        self.label = Label(self)
        timeFont = ('helevetica', 12, 'bold')
        self.label.config(bd=4, relief=SUNKEN, bg='black', fg = 'yellow', text='00:00', font = timeFont)
        self.state = 'waiting'
        self.afterID = 0
        self.label.pack()

    def start(self):
        self.startTime = time.time()
        self.state = 'running'
        self.label.config(fg = 'green')
        self.onTimer()

    def stop(self):
        if self.state == 'running':
            self.after_cancel(self.afterID)
        self.label.configure(fg = 'red')
        self.state = 'stopped'

    def onTimer(self):
        elapsed = int(time.time() - self.startTime)
        if elapsed >= 3600:
            hours = elapsed // 3600
            elapsed -= 3600*hours
            minutes = elapsed // 60
            seconds = elapsed % 60
            timeText = '%d:%02d:%02d' % (hours, minutes, seconds)
        else:
            minutes = elapsed // 60
            seconds = elapsed % 60
            timeText = '%02d:%02d' % (minutes, seconds)
        self.label.config(text = timeText)
        if self.state == 'running':
            self.afterID = self.after(100, self.onTimer)

    def pause(self):
        self.after_cancel(self.afterID)
        self.label.configure(fg = 'yellow')
        self.elapsedTime = time.time() - self.startTime
        self.state = 'paused'

    def resume(self):
        self.startTime = time.time() - self.elapsedTime
        self.label.config(fg = 'green')
        self.state = 'running'
        self.onTimer()

    def time(self):
        return time.time() - self.startTime

    def setTime(self, seconds):
        self.elapsedTime = seconds

if __name__ == '__main__':
    root = Tk()
    watch=StopWatch(root)
    watch.pack()
    watch.start()
    root.mainloop()
