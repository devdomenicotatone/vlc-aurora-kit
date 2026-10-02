#!/bin/bash
# Compila libskins2_plugin.dll (VLC 3.0.24, x64) dai sorgenti patchati con il toolchain MSYS2/mingw64.
# Uso (da MSYS2 MINGW64): bash build.sh
# La cartella di lavoro B deve contenere src/vlc-3.0.24 (sorgenti), sdk/vlc-3.0.24/sdk (SDK win64) e
# skins2-patched (creata da apply_patch.py): e' la cartella dello script oppure la variabile SKINS2_BUILD.
HERE="$(cd "$(dirname "$0")" && pwd)"
B=${SKINS2_BUILD:-$HERE}
SDK=$B/sdk/vlc-3.0.24/sdk
P=${1:-$B/skins2-patched}
OBJ=$B/obj
rm -rf "$OBJ"; mkdir -p "$OBJ"
export CXX=g++
export DEFS='-DHAVE_CONFIG_H -D__PLUGIN__ -D_FILE_OFFSET_BITS=64 -D_REENTRANT -D_THREAD_SAFE -DMODULE_STRING="skins2" -DMODULE_NAME=skins2 -DWIN32_SKINS -U_OFF_T_ -U_off_t -D_WIN32_WINNT=0x0601 -DWINVER=0x0601 -D__USE_MINGW_ANSI_STDIO=1'
export INC="-I$HERE -I$B/src/vlc-3.0.24/include -I$P $(pkg-config --cflags freetype2)"
# VLC mette nei messaggi il percorso dei sorgenti (__FILE__): reso relativo alla cartella di lavoro, cosi' nella dll
# non finiscono i percorsi (e il nome utente) del PC su cui e' stata compilata
MAPPA="-ffile-prefix-map=$(cygpath -m "$B")=."
export CXXFLAGS="-O2 -fno-rtti -std=gnu++11 -fno-strict-aliasing -Wno-deprecated-declarations -Wno-unused-parameter $MAPPA"
export P OBJ
SRCS=$(grep -o 'gui/skins2/[a-z0-9_/]*\.cpp' "$P/Makefile.am" | sed 's#gui/skins2/##' | grep -v '^x11/\|^os2/\|^macosx/' | sort -u)
echo "sorgenti: $(echo "$SRCS" | wc -l)"
compile() {
    f=$1
    o=$OBJ/$(echo "$f" | tr '/' '_' | sed 's/\.cpp$/.o/')
    if ! $CXX $CXXFLAGS $DEFS $INC -c "$P/$f" -o "$o" 2> "$o.log"; then
        echo "ERRORE $f"
        head -12 "$o.log"
        return 1
    fi
    return 0
}
export -f compile
echo "$SRCS" | xargs -P 12 -I{} bash -c 'compile {}'
# sorgenti C del modulo (ft2_err.c) e funzioni di compatibilita' di VLC non presenti in mingw (realpath)
CSRCS="src/ft2_err.c"   # unico sorgente C del modulo (stringhe di errore FreeType)
CFLAGS="-O2 -std=gnu11 -fno-strict-aliasing $MAPPA"
NC=0
for f in $CSRCS; do
    o=$OBJ/$(echo "$f" | tr '/' '_' | sed 's/\.c$/.o/')
    gcc $CFLAGS $DEFS $INC -c "$P/$f" -o "$o" 2> "$o.log" || { echo "ERRORE $f"; head -8 "$o.log"; }
    NC=$((NC+1))
done
for f in realpath; do
    gcc $CFLAGS $DEFS $INC -c "$B/src/vlc-3.0.24/compat/$f.c" -o "$OBJ/compat_$f.o" 2> "$OBJ/compat_$f.o.log" || { echo "ERRORE compat/$f.c"; head -8 "$OBJ/compat_$f.o.log"; }
    NC=$((NC+1))
done
NOBJ=$(ls "$OBJ"/*.o 2>/dev/null | wc -l)
echo "oggetti compilati: $NOBJ (attesi $(( $(echo "$SRCS" | wc -l) + NC )))"
if [ "$NOBJ" -ne "$(( $(echo "$SRCS" | wc -l) + NC ))" ]; then echo "compilazione incompleta"; exit 1; fi
echo "--- link"
$CXX -shared -o "$B/libskins2_plugin.dll" "$OBJ"/*.o -static -static-libgcc -static-libstdc++ \
    $(pkg-config --static --libs freetype2) "$SDK/lib/libvlccore.lib" \
    -lole32 -luuid -lmsimg32 -lgdi32 -lcomctl32 -lshell32 -luser32 -lshlwapi -lwinmm -lws2_32 -ldwmapi -liphlpapi \
    -Wl,--no-undefined 2>&1 | tail -25
ls -la "$B/libskins2_plugin.dll" && objdump -p "$B/libskins2_plugin.dll" | grep -i "vlc_entry\|DLL Name" | head -14
