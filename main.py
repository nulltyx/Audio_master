from tkinter import *
from tkinter import ttk
import subprocess
import re
import shutil

def get_amixer_control():   #need find corect audio control name, amixer is pain sometime
    result = subprocess.run(["amixer", "scontrols"], capture_output=True, text=True)
    match = re.search(r"'([^']+)'", result.stdout)
    if match:
        return match.group(1)
    return None   #find nothing, other function deal with this

def set_volume(v1):   #set volume, wpctl is better so use that first
    if shutil.which("wpctl"):   #pipewire way, more modern
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{int(float(v1)) / 100:.2f}"])
    elif shutil.which("amixer"):   #if no wpctl then try amixer
        control = get_amixer_control()
        if control:
            subprocess.run(["amixer", "sset", control, f"{int(float(v1))}%"])

def get_volume():   #read volume from system, try wpctl first then amixer
    if shutil.which("wpctl"):   #wpctl give something like "Volume: 0.76" so parse that
        result = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True)
        match = re.search(r"(\d+\.?\d*)", result.stdout)
        if match:
            return int(float(match.group(1)) * 100)   #make 0.76 become 76 for slider
        return 0
    elif shutil.which("amixer"):   #amixer give "[76%]" so need diferent regex
        control = get_amixer_control()
        if control:
            result = subprocess.run(["amixer", "get", control], capture_output=True, text=True)
            match = re.search(r"\[(\d+)%\]", result.stdout)
            if match:
                return int(match.group(1))
    return 0   #if reach here something very wrong happen so gl debugging ts gng

def mute():   #put volume to 0, not save old volume here, toggle_mute do that
    if shutil.which("wpctl"):
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.00"])
    elif shutil.which("amixer"):
        control = get_amixer_control()
        if control:
            subprocess.run(["amixer", "sset", control, "0%"])

def unmute():   #bring back volume from before mute
    set_volume(pre_mute_vol)
    v1.set(pre_mute_vol)

def toggle_mute():   #this is actual mute button thing, save volume then mute, or restore
    global pre_mute_vol, muted
    if muted:
        unmute()
        b.config(text="Mute")
        muted = False
    else:
        pre_mute_vol = get_volume()   #save volume before mute so can restore later
        mute()
        v1.set(0)
        b.config(text="Unmute")
        muted = True

def v_up():   
    new_vol = min(100, get_volume() + 1)
    set_volume(new_vol)
    v1.set(new_vol)

def v_down():  
    new_vol = max(0, get_volume() - 1)
    set_volume(new_vol)
    v1.set(new_vol)

def get_app_streams():   #ask pactl what apps are playing audio right now
    result = subprocess.run(["pactl", "list", "sink-inputs"], capture_output=True, text=True)
    streams = []
    current = {}
    for line in result.stdout.splitlines():   #pactl output is many lines so go one by one
        m = re.match(r"Sink Input #(\d+)", line)
        if m:
            if current:
                streams.append(current)   #save previous app before start new one
            current = {"id": m.group(1), "name": "Unknown", "volume": 100}
        m = re.match(r"\s+application\.name\s*=\s*\"(.+)\"", line)
        if m and current:
            current["name"] = m.group(1)   #get app name like "Firefox" or "Spotify" or wtw
        m = re.match(r"\s+Volume:.*?(\d+)%", line)
        if m and current:
            current["volume"] = int(m.group(1))
    if current:
        streams.append(current)   #not forget last one
    return streams   #give back list of dict like [{id, name, volume}]

def set_app_volume(sink_id, value):   #set volume for one specific app using its sink id
    subprocess.run(["pactl", "set-sink-input-volume", sink_id, f"{int(float(value))}%"])

def refresh_app_sliders():   #redraw app list every 3 second so new app show up automatic
    for widget in app_frame.winfo_children():
        widget.destroy()   #delete old widget before draw new
    streams = get_app_streams()
    if not streams:
        Label(app_frame, text="No apps playing audio", fg="grey").pack()   #nothing playing if ts is on you probs messed smtng up lowk
    for stream in streams:
        row = Frame(app_frame)
        row.pack(fill="x", padx=5, pady=2)
        Label(row, text=stream["name"], width=18, anchor="w").pack(side=LEFT)
        var = DoubleVar(value=stream["volume"])
        sid = stream["id"]
        s = Scale(
            row,
            variable=var,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            command=lambda val, s=sid: set_app_volume(s, val)   #lambda here so each slider control own app, still dont know what lambda does :sob:
        )
        s.pack(side=LEFT, fill="x", expand=True)
    if is_dark:
        apply_dark(app_frame)   #new widget need dark style too or look weird
    win.after(3000, refresh_app_sliders)   #call again after 3s, like loop but for tkinter

def apply_dark(widget):   #go thru all widget and make dark
    try:
        widget.config(background="#636363", foreground="#ffffff")
    except TclError:
        try:
            widget.config(background="#636363")   #some widget have no fg, is ok
        except TclError:
            pass   #if widget really not want dark mode just skip
    for child in widget.winfo_children():
        apply_dark(child)   #imma be honest idk what i did here, it was midnight and i was js doing anything

# --- eq part ---
# this use pactl null sink trick for eq, not best method but need no extra install
# basically make fake audio device, send audio thru it with filter, then send to real output

EQ_BANDS = [   #5 band, cover main frequency range
    {"label": "Bass",     "freq": 100},
    {"label": "Low-Mid",  "freq": 500},
    {"label": "Mid",      "freq": 1000},
    {"label": "High-Mid", "freq": 3000},
    {"label": "Treble",   "freq": 8000},
]

eq_module_index = None   #save module index so can unload later, very important
eq_sink_index = None     #same for loopback module
eq_values = [DoubleVar for _ in EQ_BANDS]   #this get replace later when build ui

def get_eq_filter_string():   #build filter string from slider value
    parts = []
    for i, band in enumerate(EQ_BANDS):
        gain = eq_vars[i].get()   #gain in db, go from -12 to +12
        freq = band["freq"]
        #peak filter format, look confusing but just standard eq filter syntax
        parts.append(f"equalizer=f={freq}:width_type=o:width=1:gain={gain:.1f}")
    return ",".join(parts)   #join all band into one big string

def apply_eq():   #remove old eq modules and load new one with current setting
    global eq_module_index, eq_sink_index
    #unload old modules first or will make infinite virtual device, very bad
    if eq_sink_index is not None:
        subprocess.run(["pactl", "unload-module", str(eq_sink_index)], stderr=subprocess.DEVNULL)
        eq_sink_index = None
    if eq_module_index is not None:
        subprocess.run(["pactl", "unload-module", str(eq_module_index)], stderr=subprocess.DEVNULL)
        eq_module_index = None
    #if all slider at 0 then no need load filter, just bypass
    if all(eq_vars[i].get() == 0 for i in range(len(EQ_BANDS))):
        eq_status.config(text="EQ: Flat (bypassed)")
        return
    filter_str = get_eq_filter_string()
    #load virtual sink, this where eq filter live
    result = subprocess.run(
        ["pactl", "load-module", "module-null-sink",
         "sink_name=eq_sink",
         f"sink_properties=device.description=EQ_Sink",
         f"format=s16le", "rate=44100", "channels=2"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        eq_module_index = result.stdout.strip()
        #loopback from eq sink monitor port to real speaker output
        result2 = subprocess.run(
            ["pactl", "load-module", "module-loopback",
             "source=eq_sink.monitor",
             f"sink=$(pactl get-default-sink)",
             f"latency_msec=1"],
            capture_output=True, text=True
        )
        if result2.returncode == 0:
            eq_sink_index = result2.stdout.strip()
            eq_status.config(text="EQ: Active")
        else:
            eq_status.config(text="EQ: Loopback fail, maybe permission problem")
    else:
        eq_status.config(text="EQ: Module load fail, something wrong")   #not good

def reset_eq():   #put all band back to 0 and remove filter
    for var in eq_vars:
        var.set(0)
    apply_eq()   #call apply with all zero = bypass eq

def show_main():   #go to main page
    eq_page.pack_forget()
    main_page.pack(fill="both", expand=True)

def show_eq():   #go to eq page
    main_page.pack_forget()
    eq_page.pack(fill="both", expand=True)

# --- state variable ---
muted = False       #is mute on right now
pre_mute_vol = 50   #volume before mute, default 50 just in case something go wrong
is_dark = False     #get set properly later when check theme

# --- make main window ---
win = Tk()
win.title("Audio Master")
win.geometry("450x420")

# --- main page ---
main_page = Frame(win)
main_page.pack(fill="both", expand=True)

master_frame = Frame(main_page)
master_frame.pack(fill="x", padx=5, pady=5)

l = Label(master_frame, text="Master Volume:")
l.pack(anchor="w")

slider_row = Frame(master_frame)
slider_row.pack(fill="x")

v1 = DoubleVar()   #master slider value live here

btn_down = Button(slider_row, text="<", width=2, command=v_down)   #small button for go down
btn_down.pack(side=LEFT)

vol = Scale(slider_row, variable=v1, from_=0, to=100, orient=HORIZONTAL, command=set_volume)
vol.pack(side=LEFT, fill="x", expand=True)

btn_up = Button(slider_row, text=">", width=2, command=v_up)   #small button for go up
btn_up.pack(side=LEFT)

btn_row = Frame(master_frame)
btn_row.pack(fill="x", pady=3)

b = Button(btn_row, text="Mute", command=toggle_mute)   #mute button, text change to Unmute when muted
b.pack(side=LEFT, padx=5)

eq_btn = Button(btn_row, text="Equaliser ›", command=show_eq)   #open eq page
eq_btn.pack(side=RIGHT, padx=5)

Label(main_page, text="── App Volume ──", fg="grey").pack(pady=(5, 0))

#scrollable area for per app volume, need scroll incase many app open
app_canvas = Canvas(main_page, borderwidth=0)
app_scroll = Scrollbar(main_page, orient="vertical", command=app_canvas.yview)
app_frame = Frame(app_canvas)

app_frame.bind("<Configure>", lambda e: app_canvas.configure(scrollregion=app_canvas.bbox("all")))
app_canvas.create_window((0, 0), window=app_frame, anchor="nw")
app_canvas.configure(yscrollcommand=app_scroll.set)

app_canvas.pack(side=LEFT, fill="both", expand=True)
app_scroll.pack(side=RIGHT, fill="y")

# --- eq page ---
eq_page = Frame(win)

eq_top = Frame(eq_page)
eq_top.pack(fill="x", padx=5, pady=5)

Button(eq_top, text="‹ Back", command=show_main).pack(side=LEFT)   #go back
Label(eq_top, text="Equaliser", font=("TkDefaultFont", 12, "bold")).pack(side=LEFT, padx=10)

eq_bands_frame = Frame(eq_page)
eq_bands_frame.pack(fill="x", padx=10, pady=10)

eq_vars = []   #list of doublevars, one for each eq band, store the db value
for i, band in enumerate(EQ_BANDS):
    col = Frame(eq_bands_frame)
    col.pack(side=LEFT, expand=True, fill="x", padx=5)
    Label(col, text=band["label"]).pack()
    Label(col, text=f"{band['freq']}Hz", fg="grey", font=("TkDefaultFont", 7)).pack()   #show frequency number
    var = DoubleVar(value=0)
    eq_vars.append(var)
    #vertical slider, up is boost (+12db) down is cut (-12db)
    s = Scale(col, variable=var, from_=12, to=-12, orient=VERTICAL, resolution=0.5, length=150)
    s.pack()
    Label(col, text="dB", font=("TkDefaultFont", 7)).pack()

eq_btn_row = Frame(eq_page)
eq_btn_row.pack(pady=5)

Button(eq_btn_row, text="Apply", command=apply_eq).pack(side=LEFT, padx=5)   #eq not update live, need press this after change slider
Button(eq_btn_row, text="Reset", command=reset_eq).pack(side=LEFT, padx=5)   #make all band flat again

eq_status = Label(eq_page, text="EQ: Flat (bypassed)", fg="grey", font=("TkDefaultFont", 8))
eq_status.pack(pady=3)   #show if eq is doing something or not

# --- check if dark mode ---
try:
    theme = subprocess.check_output(
        ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
        text=True,
        stderr=subprocess.DEVNULL
    ).lower()   #lowercase so match both "Dark" and "dark"
except subprocess.CalledProcessError:
    theme = ""   #js use light mode

is_dark = "dark" in theme

if is_dark:
    apply_dark(win)   #make everything dark go thru all widget recursiv


def on_close():   #VERY IMPORTANT must unload eq modules when close or stay in system forever
    if eq_sink_index is not None:
        subprocess.run(["pactl", "unload-module", str(eq_sink_index)], stderr=subprocess.DEVNULL)
    if eq_module_index is not None:
        subprocess.run(["pactl", "unload-module", str(eq_module_index)], stderr=subprocess.DEVNULL)
    win.destroy()

win.protocol("WM_DELETE_WINDOW", on_close)   #connect X button to cleanup function

v1.set(get_volume())   
refresh_app_sliders()  
win.mainloop() 
