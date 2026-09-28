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
# its command line saved as safe-relaunch.txt), and the RecoveryMode page the
# prompt's Cancel leaves behind. The files the original writes -- DeusEx.ini,
# User.ini, Detected.*, DeusEx.log, Running.ini -- are put back as they were.
#
# Wine is the Proton build the IDA tools use, in the same prefix, which has
# the Python the driver runs on (tools/ida/idalib-mcp.sh). The captures are
# the game's pictures: keep them out of the repositories.
set -eu
: "${WIZ_PREFIX:=$HOME/Games/umu/umu-default}"
: "${WIZ_PROTON:=$HOME/.local/share/Steam/compatibilitytools.d/Proton-CachyOS Latest}"
: "${WIZ_PYTHON:=C:\\Program Files\\Python314\\python.exe}"
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../.." && pwd)                 # the parent folder of the repositories
system="$root/gamefiles/System"
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
ps -eo args | grep -i '[d]eusex\.exe' > "$out/safe-relaunch.txt" || true
touch "$out/cdprompt.go"
wait
echo "relaunched as: $(cat "$out/safe-relaunch.txt")"

run recovery
