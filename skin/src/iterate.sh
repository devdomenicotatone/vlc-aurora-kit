#!/bin/bash
# Ricostruisce la skin, la installa, riavvia VLC con log e cattura uno screenshot.
# uso: iterate.sh <nome_screenshot.png> [argomenti extra per vlc...]
set -e
SB="${SKINBUILD:-$(cd "$(dirname "$0")" && pwd)}"   # cartella di lavoro: quella dello script, oppure la variabile SKINBUILD
SHOT="${1:-shot.png}"; shift || true
cd "$SB"
python build_aurora.py
cp Aurora.vlt "$APPDATA/vlc/skins2/Aurora.vlt"
taskkill //IM vlc.exe >/dev/null 2>&1 || true
for i in 1 2 3 4 5 6; do sleep 1; tasklist | grep -qi vlc.exe || break; done
tasklist | grep -qi vlc.exe && powershell -NoProfile -Command "Get-Process vlc -ErrorAction SilentlyContinue | Stop-Process -Force" || true
LOG="$SB/vlc_skin.log"; rm -f "$LOG"
WLOG="$(cygpath -w "$LOG")"
EXTRA=""
for a in "$@"; do EXTRA="$EXTRA,'$a'"; done
powershell -NoProfile -Command "Start-Process 'C:\Program Files\VideoLAN\VLC\vlc.exe' -ArgumentList '--verbose=2','--file-logging','--logfile=\"$WLOG\"'$EXTRA"
sleep 6
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$SB/shot.ps1")" -Out "$(cygpath -w "$SB/$SHOT")" 2>&1 | grep -E "SAVED|NO_|WIN" || true
echo "--- skins2 warn/err:"
grep -i "skins2" "$LOG" | grep -v -i "debug" | grep -v "skin: Aurora" || echo "(nessuno)"
