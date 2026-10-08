@echo off
cd /d "%~dp0"
py -3 run.py
if errorlevel 1 (
  echo Lag Check konnte nicht starten. Python 3.12 oder neuer mit Tkinter benoetigt.
  echo Alternativ die portable Windows-Version aus den GitHub Releases verwenden.
  pause
)
