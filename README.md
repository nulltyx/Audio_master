Description

Audio Master is a Linux desktop app for controlling system audio. It is built with Python and Tkinter. It gives you control over master volume, per application volume, mute, and a basic equaliser with presets.

Features

  Control system volume with slider and buttons
  Mute and unmute system audio
  Adjust volume per running application
  Automatic detection of audio streams using pactl
  Basic equaliser with frequency bands
  Equaliser presets for quick sound profiles
  Dark mode support based on system theme
  Auto refresh of active audio apps

Usage

  Start the application with Python
  Use master slider for system volume
  Adjust per app sliders for individual control
  Use mute button to toggle sound
  Open equaliser tab to adjust frequencies
  Select a preset for quick EQ setup
  Press Apply if manual changes are made

Notes

  Presets overwrite manual EQ values
  Equaliser uses a basic PipeWire module setup
  Behavior depends on Linux distribution and audio stack
  Some features require pactl or wpctl support
