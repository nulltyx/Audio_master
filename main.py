import tkinter as Tk
from tkinter import *
import subprocess
import re
import shutil




def set_volume(v1):
    if shutil.which("amixer"):   #ubuntu audio system
        subprocess.run(["amixer", "sset", "Master", f"{int(v1)}%"])  #sets the volume
    if shutil.which("wpctl"):     #fedora audio system
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{int(v1)}%"])  
    

def get_volume():   #finds what vol im at
    if shutil.which("amixer"):   #Ubuntu audio system
        result = subprocess.run(["amixer", "get", "Master"],capture_output=True,text=True)
        match = re.search(r"\[(\d+)%\]", result.stdout)   #makes [75%] into 75
        return int(match.group(1))      #makes the value into 75
    if shutil.which("wpctl"):   #fedora audio system
        result = subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@"],capture_output=True,text=True)
        match = re.search(r"\[(\d+)%\]", result.stdout)   
        return int(match.group(1))      
    

def mute():
    if shutil.which("amixer"):   #ubuntu audio system
        subprocess.run(["amixer", "sset", "Master", "0%"])  #sets the volume
    if shutil.which("wpctl"):     #fedora audio system
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0%"])  


win = Tk()    #start of window
win.geometry("400x200")



v1 = DoubleVar()

l=Label(win, text="Volume:",)
l.pack()



vol = Scale(   #slider
    win,
    variable=v1,
    from_=0,
    to=100,
    orient=HORIZONTAL,
    command=set_volume   
)
vol.pack()


Button(win, text="Mute", command=mute).pack()
Button(win, text="Unmute", command= unmute).pack()  #doesnt do anything yet

f = subprocess.check_output(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],text=True).strip()  #checks if im usind dark or light mode
if f == "'prefer-dark'":
    win.config(background="#636363") #sets dark mode on all the things
    vol.config(background="#636363")
    l.config(background="#636363")
else:
    pass

v1.set(get_volume()) #sets the volume to the current volume


win.mainloop()   #end of window