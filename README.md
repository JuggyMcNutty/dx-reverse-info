# dx-reverse-info

Deus Ex's original binaries, reverse-engineered: what `DeusEx.exe` and the
game's DLLs do, written down as behaviour in our own words with the addresses,
offsets and names it was read from. It is the record
[Port Ex Machina](https://github.com/JuggyMcNutty/port-ex-machina) works
from. None of the game's files are here, and no decompiled code
([what goes in](#working-on-the-binaries)). Two efforts:

- **The launcher.** `System/DeusEx.exe` was reverse-engineered before any
  launcher of ours was written: [`launcher.md`](launcher.md). Complete.
  [deusex-launcher](https://github.com/JuggyMcNutty/deusex-launcher)'s `main`
  recreates it almost 1:1.
- **The game's DLLs.** The original C++ behind Deus Ex's natives, read to find
  what Surreal Engine lacks or has wrong and to port it into
  [VibeEngine](https://github.com/JuggyMcNutty/VibeEngine) -- patch 0034 was
  the first ([what the fork changes](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/ENGINE.md#what-the-fork-changes)).
  Each DLL is read ([the binaries](#the-binaries)); `Render.dll` as far as a
  feature's drawing lives there, and its mesh detail and lighting. What the
  engine still lacks of them, and the work that would fill it, is VibeEngine's
  [`NATIVES.md`](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/NATIVES.md).

## The binaries

All in the game's `System/`, from the GOG build of 1.112fm; the DLLs were built
in March 2001. The engine recognises the install by `DeusEx.exe`'s SHA1
([`launcher.md`](launcher.md#the-binary)).

| Binary | What it holds | Notes | Read |
|---|---|---|---|
| `DeusEx.exe` | the `Launch` module: a bootstrap shell, not the game | [`launcher.md`](launcher.md) | complete |
| `DeusEx.dll` | package DeusEx: the player, NPCs (`ScriptedPawn`), saving and the save directory, particle and laser effects | [`deusex-dll.md`](deusex-dll.md) | read |
| `Engine.dll` | package Engine: UE1's actors, pawns, levels and rendering interfaces, traces, and the network protocol ([`network.md`](network.md)), with Deus Ex's additions (AI senses and events, NPC movement tests, blend animations, stasis) | [`engine-dll.md`](engine-dll.md) | read |
| `Core.dll` | package Core: objects, names, packages, configuration and the script interpreter, with Deus Ex's `GetConfig`, `CriticalDelete` and debug system | [`core-dll.md`](core-dll.md) | read |
| `Extension.dll` | package Extension: the UI's windows and graphics contexts, flags, and the game engine and input that put the UI in front of the game | [`extension-dll.md`](extension-dll.md) | read |
| `ConSys.dll` | package ConSys: conversations and their events, and what binds them to actors | [`consys-dll.md`](consys-dll.md) | read |
| `DeusExText.dll` | package DeusExText: the parser of the texts the player reads (books, datacubes, newspapers, emails, bulletins, the credits) | [`deusextext-dll.md`](deusextext-dll.md) | read |
| `Render.dll` | package Render: UE1's scene renderer -- which actors are drawn, render iterators, render time, coronas, mesh detail, lighting | [`render-dll.md`](render-dll.md) | where a feature's drawing lives there; mesh detail and lighting |
| `D3DDrv.dll` | the Direct3D 7 display driver: gamma, the light maps' brightness on screen, fog, detail textures, and each pass's blending -- the look's reference | [`d3ddrv-dll.md`](d3ddrv-dll.md) | read |
| `IpDrv.dll` | package IpDrv: the sockets -- the UDP net driver, the script's TCP and UDP links, GameSpy's validation, Epic's master server | [`ipdrv-dll.md`](ipdrv-dll.md) | read |
| `Galaxy.dll` | package Galaxy: the audio subsystem over the Galaxy sound library -- channels and which sound wins, sounds behind walls, ambient sounds, lip sync, music, zone reverb | [`galaxy-dll.md`](galaxy-dll.md) | read |
| `Fire.dll` | package Fire: the fractal textures -- fire, water (lit, or bending another texture) and ice -- that the energy weapons, lasers, fires, gas and water effects are made of | [`fire-dll.md`](fire-dll.md) | read, and checked against its own routines |
| `WinDrv.dll` | the Windows client and viewport: the game's window, DirectDraw, DirectInput, the joystick, which render device a viewport opens with | [`windrv-dll.md`](windrv-dll.md) | its command-line flags |
| `Window.dll` | the Win32 widgets and dialog templates of the launcher and the editor | [`wizard.md`](wizard.md#page-layouts) | the launcher's dialog templates, as data |

Beside them in `gamefiles/System/`, copied in by the owner
(2026-09-24) and not the game's:

- **`RGalaxy.dll`** is `Galaxy.dll` with 8 bytes changed: 7 rename its package
  to RGalaxy, so both can be installed, and 1 makes the `MUSICORDER` console
  command change the music's order when the playing pattern ends, not at
  once ([the console](galaxy-dll.md#hardware-and-the-console)).
- **`ALAudio.dll`** is OldUnreal's OpenAL audio driver built for Deus Ex
  ("OpenAL Audio for DeusEX", 2016): lip sync, EFX reverb with a mode that
  emulates the old one, HRTF, Doppler, OGG, and tracker music through libxmp.
  It needs `OpenAL32.dll` (copied too), `ALURE32.dll` and `libxmp.dll` (not
  copied).

## Working on the binaries

The work happens beside the Port Ex Machina workspace: this repository is
cloned as `dx-reverse-info/` in the parent folder of its repositories, beside
the game install (`gamefiles/`) and the reference material (`reference/`);
the paths below that are not this repository's are that parent folder's.

- **IDA runs headless, in the distrobox.** Windows IDA 9.4 is installed in
  the Lutris prefix (`~/Games/umu/umu-default`), and
  [`tools/ida/idalib-mcp.sh`](tools/ida/idalib-mcp.sh) runs
  ida-pro-mcp's `idalib` supervisor there as Claude Code's `ida` MCP server,
  over stdio, under the Proton wine Lutris runs IDA with (so IDA's window and
  the workers share one wineserver). Nothing runs on the host: umu and
  Proton's own launcher drop a program's stdin, so the script calls that
  Proton's `wine` directly. Once per machine: the prefix's Python gets IDA's
  `idapro` wheel (IDA's `idalib\python`), the container gets
  `lib32-glibc` (this wine starts every program through its 32-bit loader),
  and `claude mcp add --scope local ida -- "$PWD/dx-reverse-info/tools/ida/idalib-mcp.sh"`,
  run in the parent folder, where Claude Code starts, registers it, with the
  plugin's own `plugin:ida-pro-mcp:idalib` (a Linux idalib, which is not here)
  disabled in `/mcp`. The script enables `py_eval` and `py_exec_file`. IDA
  sees the parent folder as `X:\Documents\projects\deusex` and the whole
  filesystem as `Z:\`,
  so a script in any scratch directory runs through `py_exec_file`. `py_eval`
  keeps its top-level names as locals, which a function or comprehension
  defined there cannot see: put the code in a function, or in a file.
- **One database per binary**, beside it: `gamefiles/System/DeusEx.exe.i64`
  and the like, unpacked while open -- the `.id0`, `.id1`, `.id2`, `.nam` and
  `.til` files beside it are working files, and the `.i64` is only written on
  save. Backups in `reference/idb-backup/`. `idb_open` opens one by its `X:\`
  path in a worker of its own and names the session, which every other call
  then takes as `database`; up to four are open at once. A worker outlives the
  session and saves and exits after ten idle minutes (a longer
  `idle_ttl_sec` on `idb_open` keeps it); `idb_close` saves and exits at
  once. Either way the close leaves the working files behind -- with
  `save: true` too, the `.i64` rewritten beside them (2026-09-28) -- and the
  next `idb_open` opens them rather than the `.i64`: delete them after a
  close to go back to the saved database, and move them aside to check what
  a save wrote. A database is open in one place at a time: the
  supervisor adopts one that IDA's window has open rather than open it twice.
- **Types.** [`tools/ida/ue1_types.py`](tools/ida/ue1_types.py) gives a
  database the layout of every native class, struct and enum, from the
  script source in the game's packages, and checks each class against the size
  the DLL registers for it. Run it in IDA (File > Script file, or the MCP's
  `py_exec_file`), again after reopening a database without saving. On the
  host, `--check` compares a DLL's registrations without IDA, and `--layout
  <class>` prints a class's fields at their offsets -- the quickest way to name
  an offset seen in `objdump`. A class that is C++ only (`ULevel`,
  `UEventManager`, `DDeusExGameEngine`) has no script and so no layout from it;
  its SDK header has its members, packed to 4 bytes: a `QWORD` or `DOUBLE` is
  not aligned to 8 (`ULevel::TimeSeconds` is at 0xdc). `Render.dll`'s types
  are all C++, and [`tools/ida/render_types.py`](tools/ida/render_types.py)
  declares them from those headers ([`Render.dll`](render-dll.md#the-binary)).
  Extension's and ConSys's native arrays are typed as `TArray`s
  ([why](extension-dll.md#the-binary)).
- **Strings.** This build is Unicode: its strings are UTF-16, and IDA takes
  many for 8-bit ones, which the decompiler shows as nonsense.
  [`tools/ida/utf16_strings.py`](tools/ida/utf16_strings.py), run after
  the types, redefines them; a function decompiled before then needs
  decompiling again. The MCP's own preview of a string (the `refs` of
  `decompile`) still shows a UTF-16 one as nonsense: the database is right.
- **Names.** [`tools/ida/ue1_names.py`](tools/ida/ue1_names.py) names
  the functions a UE1 DLL registers its classes and natives from, which IDA
  leaves as `sub_...`, and the class object of each class the DLL does not
  export (`Engine.dll`'s AI events), with the name its export would have. So
  a new database gets the three scripts in turn: types, strings, names; the
  types again after the names checks the unexported classes too.
- **The script and the headers.** Every native class declares its fields in
  its script, in the order its C++ class has them: after `UObject`'s 0x28
  bytes, bools packed 32 to a dword, bytes packed, the rest aligned to 4, a
  string 12 bytes. The SDK (`reference/ReleaseSDK1112f/Headers/DxHeaders.zip`)
  has this build's own headers: hand-written classes (`Engine/Inc/UnEventManager.h`,
  `Engine/Inc/UnRenderIterator.h`, all of `Extension/Inc/` and `ConSys/Inc/`)
  and generated ones (`Engine/Inc/EngineClasses.h`, `DeusEx/Inc/DeusExClasses.h`),
  but none of the script's structs. Where script and header disagree, the
  registered size shows which the DLL was built with: `ADeusExPlayer` has a
  field (`LastinHand`) the SDK's header lacks, and ConSys's `DConCamera` and
  `DConEventAnimation` are as their headers have them
  ([`ConSys.dll`](consys-dll.md#the-binary)).
- **Without IDA**, `objdump` reads the DLLs. `objdump -p` lists the exports
  under their C++ names (`?AICanSee@APawn@@QAEMPAVAActor@@MHHHH@Z`, and
  `?execAICanSee@...` for its script entry); an `Engine.dll` export is a jump
  to the code, from incremental linking, to follow. `objdump -d -M intel
  --start-address=... --stop-address=...` gives a function, and its calls into
  `Core.dll` resolve through the import table (`appAtan`, `FVector::Rotation`).
- **Dialog templates** are resources, data rather than code:
  [`tools/pe/dialogs.py`](tools/pe/dialogs.py) prints a binary's -- each
  control's class, id, style and rectangle, and the font -- with nothing but
  Python. `Window.dll` has the launcher's wizard and its pages, `DeusEx.exe`
  the splash ([page layouts](wizard.md#page-layouts)).
- **The original launcher runs under wine here too**, in the IDA prefix:
  [`tools/wine/wizard-capture.sh`](tools/wine/wizard-capture.sh) captures every
  page of its wizard, driven by Win32 messages from inside a virtual desktop,
  and puts the install's files back after
  ([the second run](live-verification.md#the-second-run-every-page-2026-09-27)).
- **A native's `exec` function holds the defaults of its optional
  parameters**: each is set before its argument is read. Upstream's natives
  take them as `std::optional`, and a default is not always false
  (`IsValidEnemy` checks the alliance unless told not to).
- **A subsystem's `Exec` runs on its `FExec` part.** It is called through the
  `FExec` vtable, with `this` 0x28 past the object, so the decompiler's field
  names in it are 0x28 short (`Galaxy.dll`'s `Exec` "toggles"
  `UseReverb` where it toggles its stats flag).
- **MSVC reverses overload groups in the vtable.** In `FConfigCache`,
  `GetString(FString&)` sits at **+12**, *before* `GetString(TCHAR*, INT)` at
  **+16**. Resolve every `GConfig` call by argument arity and types, never by
  index arithmetic. This is the one place blind index math silently produces
  wrong documentation.
- **The game's UnrealScript source is embedded in `System/DeusEx.u`** (and the
  other `.u` files). Search it -- a regex over the file -- before guessing what
  the game's script does: that is how the `CycleActors` semantics, the
  `bIgnoreNextShowMenu` swallow and the key-menu command list were found.
- **What goes in this repository** is behaviour in our own words, with
  addresses, offsets and names -- never a decompiled listing or a disassembly.
  The repository is public, and the code is not ours.

## Files

| File | Contents |
|---|---|
| [`launcher.md`](launcher.md) | `DeusEx.exe`: anchors, struct sizes, findings |
| [`launch-flow.md`](launch-flow.md), [`wizard.md`](wizard.md), [`cli-flags.md`](cli-flags.md), [`ini-keys.md`](ini-keys.md), [`porting-notes.md`](porting-notes.md), [`types/launch.h`](types/launch.h), [`live-verification.md`](live-verification.md) | the launcher's details ([its index](launcher.md)) |
| [`deusex-dll.md`](deusex-dll.md), [`engine-dll.md`](engine-dll.md), [`core-dll.md`](core-dll.md), [`extension-dll.md`](extension-dll.md), [`consys-dll.md`](consys-dll.md), [`deusextext-dll.md`](deusextext-dll.md), [`render-dll.md`](render-dll.md), [`d3ddrv-dll.md`](d3ddrv-dll.md), [`ipdrv-dll.md`](ipdrv-dll.md), [`galaxy-dll.md`](galaxy-dll.md), [`fire-dll.md`](fire-dll.md), [`windrv-dll.md`](windrv-dll.md) | each DLL: the binary, its classes, what each function does, with addresses |
| [`network.md`](network.md) | how the original plays over a network: joining, packets, replication, remote calls |
| [`tools/ida/`](tools/ida/) | the IDA scripts: types, strings, names ([above](#working-on-the-binaries)); `idalib-mcp.sh`, the headless server |
| [`tools/pe/`](tools/pe/) | `dialogs.py`: a Windows binary's dialog templates as text, without IDA ([above](#working-on-the-binaries)) |
| [`tools/wine/`](tools/wine/) | `wizard-capture.sh` and `wizard_drive.py`: the original launcher's wizard, captured page by page under wine ([above](#working-on-the-binaries)) |
