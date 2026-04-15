import tkinter as Tk
from tkinter import *
import subprocess
import re
import shutil

def get_amixer_control():   #finds correct audio control name
    result = subprocess.run(
        ["amixer", "scontrols"],
        capture_output=True,
        text=True
    )
    match = re.search(r"'([^']+)'", result.stdout)
    if match:
        return match.group(1)
    return 0   #no control found so fallback to 0

def set_volume(v1):   #sets system volume
    if shutil.which("amixer"):
        control = get_amixer_control()
        if control:
            subprocess.run(["amixer", "sset", control, f"{int(v1)}%"]) 
    elif shutil.which("wpctl"):   #pipewire volume control
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", str(int(v1) / 100)])


def get_volume():   #gets current system volume
    if shutil.which("amixer"):
        control = get_amixer_control()
        if control:
            result = subprocess.run(
                ["amixer", "get", control],
                capture_output=True,
                text=True
            )
            match = re.search(r"\[(\d+)%\]", result.stdout)
            if match:
                return int(match.group(1))
        return 0   #no valid amixer output found

    elif shutil.which("wpctl"):   #pipewire volume read
        result = subprocess.run(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
            capture_output=True,
            text=True
        )
        match = re.search(r"(\d+\.\d+)", result.stdout)
        if match:
            return int(float(match.group(1)) * 100)
        return 0   #no valid wpctl output found

    return 0   #no audio backend available


def mute():   #mutes system audio
    if shutil.which("amixer"):
        control = get_amixer_control()
        if control:
            subprocess.run(["amixer", "sset", control, "0%"])
    elif shutil.which("wpctl"):   #pipewire mute
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0"])


def v_up():   #increase volume by 1 step
    new_vol = min(100, get_volume() + 1)
    set_volume(new_vol)
    v1.set(new_vol)

def v_down():   #decrease volume by 1 step
    new_vol = max(0, get_volume() - 1)
    set_volume(new_vol)
    v1.set(new_vol)


win = Tk()   #main window
win.geometry("400x200")

v1 = DoubleVar()   #slider value holder

l = Label(win, text="Volume:")   #volume label
l.pack()

vol = Scale(
    win,
    variable=v1,
    from_=0,
    to=100,
    orient=HORIZONTAL,
    command=set_volume   #updates volume when slider moves
)
vol.pack(fill="x")

btn_down = Button(win, text="<", command=v_down)   #lower volume button
btn_down.pack(side=LEFT)

btn_up = Button(win, text=">", command=v_up)   #raise volume button
btn_up.pack(side=RIGHT)

b = Button(win, text="Mute", command=mute)   #mute button
b.pack(side=BOTTOM)


#dark mode detection using system theme
try:
    theme = subprocess.check_output(
        ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
        text=True,
        stderr=subprocess.DEVNULL
    ).lower()
except subprocess.CalledProcessError:
    theme = ""

if "dark" in theme:   #apply dark background
    win.config(background="#636363")
    vol.config(background="#636363")
    l.config(background="#636363")
    b.config(background="#636363")


v1.set(get_volume())   #sync slider with real system volume

win.mainloop()   #end of window
