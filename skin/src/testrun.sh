#!/bin/bash
# Avvia un'istanza di PROVA di VLC con configurazione separata (--config test-vlcrc) e la skin
# appena generata, attende, cattura le finestre della skin e mostra gli avvisi skins2 nel log.
# Non tocca il VLC dell'utente ne' il suo vlcrc. Uso: testrun.sh <shot.png> [argomenti extra vlc...]
SB="$(cd "$(dirname "$0")" && pwd)"
SHOT="${1:-test.png}"; shift || true
cd "$SB"
if [ -f test.pid ]; then
  powershell -NoProfile -Command "Stop-Process -Id $(cat test.pid) -Force -ErrorAction SilentlyContinue" >/dev/null 2>&1
  rm -f test.pid; sleep 1
fi
python mk_testcfg.py ${TEST_X:-3600} ${TEST_Y:-300} "${TEST_VISIBLE:-main,playlist,eqwin,fstest}" || exit 1
LOG="$SB/vlc_test.log"; rm -f "$LOG"
WLOG="$(cygpath -w "$LOG")"
WCFG="$(cygpath -w "$SB/test-vlcrc")"
EXTRA=""
for a in "$@"; do EXTRA="$EXTRA,'$a'"; done
PID=$(powershell -NoProfile -Command "\$p = Start-Process 'C:/Program Files/VideoLAN/VLC/vlc.exe' -ArgumentList '--config=\"$WCFG\"','--no-one-instance','--no-qt-privacy-ask','--no-qt-updates-notif','--verbose=2','--file-logging','--logfile=\"$WLOG\"'$EXTRA -PassThru; \$p.Id")
echo "$PID" > test.pid
echo "TESTPID $PID"
sleep ${TEST_WAIT:-10}
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$SB/shot2.ps1")" -Out "$(cygpath -w "$SB/$SHOT")" -ProcId "$PID" 2>&1 | grep -E "SAVED|NO_|WIN" || true
echo "--- skins2 warn/err:"
grep -i "skins2" "$LOG" | grep -v -i "debug" | grep -v "skin: Aurora" || echo "(nessuno)"
