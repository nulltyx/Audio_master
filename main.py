import tkinter as Tk
from tkinter import *
import subprocess
import re
v1 = DoubleVar()



def set_volume(v1):
    subprocess.run(["amixer", "sset", "Master", f"{int(v1)}%"])  #sets the volume

def get_volume():   #finds what vol im at
    result = subprocess.run(
        ["amixer", "get", "Master"],
        capture_output=True,
        text=True
    )
    match = re.search(r"\[(\d+)%\]", result.stdout)   #makes [75%] into 75
    return int(match.group(1))      #makes the value into 75

def preset():  
    subprocess.run(["amixer", "sset", "Master", "50%"])

win = Tk()    #start of window
win.geometry("400x200")


Label(win, text="Volume:").pack()


vol = Scale(   #slider
    win,
    variable=v1,
    from_=0,
    to=100,
    orient=HORIZONTAL,
    command=set_volume   
)
vol.pack()


btn = Button(win, text = "Preset 1" command=preset) #preset button
btn.pack()



v1.set(get_volume()) #sets the volume to the current volume


win.mainloop()   #end of window


