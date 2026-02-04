import tkinter as Tk
from tkinter import *
import subprocess

win=Tk()   #start of window
win.geometry("400x300")
Label(win, text="Volume:") #label

v1=DoubleVar()


vol = Scale(win, variable=v1, from_=0, to=100, orient=HORIZONTAL)
vol.pack()



subprocess.run(["amixer", "sset", "'Master'", f"{v1.get()}%"])   #applying the volume, doesnt work yet

win.mainloop()   #end of window

