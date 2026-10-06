#!/bin/sh
# Headless IDA for Claude Code: ida-pro-mcp's idalib supervisor as a stdio MCP
# server. Runs in this distrobox, never on the host: the Windows IDA and its
# Python live in a Wine prefix (IDA_PREFIX), driven by a Proton build's wine,
# so a GUI IDA open at the same time shares its wineserver. Needs the Claude
# Code plugin ida-pro-mcp@mrexodia installed, whose copy of ida-pro-mcp it runs.
# Register, in the folder Claude Code starts in:
# claude mcp add --scope local ida -- "$PWD/dx-reverse-info/tools/ida/idalib-mcp.sh"
# (README.md#working-on-the-binaries).
set -eu

: "${IDA_PREFIX:=$HOME/Games/umu/umu-default}"
: "${IDA_PROTON:=$HOME/.local/share/Steam/compatibilitytools.d/Proton-CachyOS Latest}"
: "${IDA_PYTHON:=C:\\Program Files\\Python314\\python.exe}"

# ida-pro-mcp itself is the Claude Code plugin's copy, the one IDA's GUI
# plugin links to, so the two never differ.
src=$(python3 -c '
import json, os
d = json.load(open(os.path.expanduser("~/.claude/plugins/installed_plugins.json")))
print(d["plugins"]["ida-pro-mcp@mrexodia"][0]["installPath"] + "/src")')

export WINEPREFIX="$IDA_PREFIX" WINEDEBUG=-all WINEDLLOVERRIDES="winemenubuilder.exe=d"
export PYTHONPATH="Z:$(printf %s "$src" | tr / '\\')"

# --unsafe keeps py_eval and py_exec_file, which run tools/ida/*.py.
exec "$IDA_PROTON/files/bin/wine" "$IDA_PYTHON" -m ida_pro_mcp.idalib_supervisor --stdio --unsafe "$@"
