# Rebuilds dist\PomodoroTimer.exe as a single standalone Windows executable.
# Requires: Python 3 + PyInstaller  ->  py -m pip install pyinstaller
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

py -m PyInstaller `
    --onefile `
    --windowed `
    --clean `
    --noconfirm `
    --name PomodoroTimer `
    --icon "$root\pomodoro_timer.ico" `
    --add-data "$root\pomodoro_timer.ico;." `
    --distpath "$root\dist" `
    --workpath "$env:TEMP\pomodorotimer-build" `
    --specpath "$env:TEMP\pomodorotimer-build" `
    "$root\pomodoro_timer.py"

if ($?) { "`nBuilt: $root\dist\PomodoroTimer.exe" }
