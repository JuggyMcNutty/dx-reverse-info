#!/bin/sh
# Captures the original launcher's wizard, run under wine in this distrobox
# (never on the host), for the recreation to be compared against:
#
#   tools/wine/wizard-capture.sh [OUTDIR]     default: reference/original-wizard/
#
# Each page as the screen shows it (.bmp) and its controls' rectangles (.json),
# from wizard_drive.py, which runs inside a Wine virtual desktop and works the
# wizard with Win32 messages -- the owner's mouse and keyboard are not used,
# but the desktop window appears on their screen. The scenarios, in order:
# -firstrun through every page, -changevideo, -safe through SafeOptions to a
# relaunch that stops at the CD prompt (CdPath pointed nowhere for the run;
# its command line saved as safe-relaunch.txt), the RecoveryMode page the
# prompt's Cancel leaves behind, and -make's error box. The files the
# original writes -- DeusEx.ini, User.ini, Detected.*, DeusEx.log,
# Running.ini -- are put back as they were.
#
# Wine is the Proton build the IDA tools use, in the same prefix, which has
# the Python the driver runs on (tools/ida/idalib-mcp.sh). A prefix of its
# own (WIZ_PREFIX) needs only that Python: wineboot -i, then python.org's
# Windows installer, /quiet InstallAllUsers=1 (3.14.10's works). The
# captures are the game's pictures: keep them out of the repositories.
set -eu
: "${WIZ_PREFIX:=$HOME/Games/umu/umu-default}"
: "${WIZ_PROTON:=$HOME/.local/share/Steam/compatibilitytools.d/Proton-CachyOS Latest}"
: "${WIZ_PYTHON:=C:\\Program Files\\Python314\\python.exe}"
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../.." && pwd)                 # the parent folder of the repositories
# GOG's install where goggamefiles/ holds it, as the harness takes it (DXEngine's
# tools/dxcap.sh): Steam's DeusEx.exe is packed and starts only under Steam's
# client, so in gamefiles/ no wizard comes up. WIZ_SYSTEM names another.
system="${WIZ_SYSTEM:-$root/goggamefiles/System}"
[ -n "${WIZ_SYSTEM:-}" ] || [ -f "$system/DeusEx.exe" ] || system="$root/gamefiles/System"
out=${1:-"$root/reference/original-wizard"}
mkdir -p "$out"
[ -f "$system/DeusEx.exe" ] || { echo "no DeusEx.exe in $system" >&2; exit 1; }

winpath() { printf 'Z:%s' "$1" | tr / '\\'; }
keep=$(mktemp -d)
for f in DeusEx.ini User.ini Detected.ini Detected.log DeusEx.log Running.ini; do
    [ -e "$system/$f" ] && cp -p "$system/$f" "$keep/"
done
restore() {
    for f in DeusEx.ini User.ini Detected.ini Detected.log DeusEx.log Running.ini; do
        if [ -e "$keep/$f" ]; then cp -p "$keep/$f" "$system/$f"; else rm -f "$system/$f"; fi
    done
    rm -rf "$keep"
    echo "game files put back as they were"
}
trap restore EXIT

run() {  # scenario
    (cd "$system" && WINEPREFIX="$WIZ_PREFIX" WINEDEBUG=-all WINEDLLOVERRIDES="winemenubuilder.exe=d" \
        timeout 400 "$WIZ_PROTON/files/bin/wine" explorer /desktop=dxwiz,1024x768 \
        "$WIZ_PYTHON" "$(winpath "$here/wizard_drive.py")" "$1" "$(winpath "$out")" "$(winpath "$system")" \
        >/dev/null 2>&1) || true
    cat "$out/$1.log"
}

run firstrun

# -changevideo's page comes only once the game has run: on an untouched ini,
# FirstRun 0, the first-run wizard comes first. Raised for the rest, as the
# first run's Finish raises it.
python3 - "$system/DeusEx.ini" <<'EOF'
import re, sys
p = sys.argv[1]
data = open(p, "rb").read()
data, n = re.subn(rb"(?m)^FirstRun=\d*\r$", b"FirstRun=1100\r", data)
if n != 1:
    sys.exit("FirstRun not found once in " + p)
open(p, "wb").write(data)
EOF
run changevideo

# The relaunch stops at the CD prompt: point CdPath nowhere for this run.
python3 - "$system/DeusEx.ini" <<'EOF'
import sys
p = sys.argv[1]
data = open(p, "rb").read()
old = b"CdPath=..\\\r\n"
if data.count(old) != 1:
    sys.exit("CdPath=..\\ not found once in " + p)
open(p, "wb").write(data.replace(old, b"CdPath=Z:\\nowhere\\\r\n"))
EOF
rm -f "$out/cdprompt.ready" "$out/cdprompt.go"
run safe &
for _ in $(seq 1 120); do [ -e "$out/cdprompt.ready" ] && break; sleep 1; done
# The game's own process, its program a Windows path to DeusEx.exe, not
# another naming the file (IDA's DeusEx.exe.i64, a shell's command line)
ps -eo args | awk 'tolower($1) ~ /\\deusex\.exe$/' > "$out/safe-relaunch.txt" || true
touch "$out/cdprompt.go"
wait
echo "relaunched as: $(cat "$out/safe-relaunch.txt")"
# With no CD prompt (an exe that checks no disc) the relaunched game plays:
# ended here, killed so it writes nothing, or the scenarios after hand their
# command lines to it and open no window of their own.
ps -eo pid,args | awk 'tolower($2) ~ /\\deusex\.exe$/ { print $1 }' | xargs -r kill -9 2>/dev/null || true

run recovery
run make
