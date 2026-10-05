# dx-reverse-info

Deus Ex's original binaries, reverse-engineered: what `DeusEx.exe` and the game's DLLs do,
as behaviour in our own words with the addresses, offsets and names it was read from. It is
the record [Port Ex Machina](https://github.com/JuggyMcNutty/port-ex-machina) works from.
None of the game's files are here, and no decompiled code
([what goes in](#working-on-the-binaries)). Two efforts:

- **The launcher.** `System/DeusEx.exe`, read in full: [`launcher.md`](launcher.md).
  [deusex-launcher](https://github.com/JuggyMcNutty/deusex-launcher)'s `main` recreates it
  almost 1:1.
- **The game's DLLs.** The C++ behind Deus Ex's natives, read to find what Surreal Engine
  lacks or has wrong and to port it into
  [VibeEngine](https://github.com/JuggyMcNutty/VibeEngine)
  ([what the fork changes](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/ENGINE.md#what-the-fork-changes)).
  Each is read as far as the work needs ([the binaries](#the-binaries)). Where the fork
  still differs from the original, feature by feature: VibeEngine's
  [`NATIVES.md`](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/NATIVES.md).

## The binaries

All in the game's `System/`, from the GOG build of 1.112fm; the DLLs' build date is March
2001. The engine recognises the install by `DeusEx.exe`'s SHA1
([`launcher.md`](launcher.md#the-binary)). Each DLL's doc gives the binary, its classes and
what each function does, with addresses.

| Binary | What it holds | Docs | Read |
|---|---|---|---|
| `DeusEx.exe` | the `Launch` module: a bootstrap shell, not the game | [`launcher.md`](launcher.md), the index of [`launch-flow.md`](launch-flow.md), [`wizard.md`](wizard.md), [`cli-flags.md`](cli-flags.md), [`ini-keys.md`](ini-keys.md), [`types/launch.h`](types/launch.h) | complete |
| `DeusEx.dll` | package DeusEx: the player, NPCs (`ScriptedPawn`), saving and the save directory, particle and laser effects | [`deusex-dll.md`](deusex-dll.md) | read |
| `Engine.dll` | package Engine: UE1's actors, pawns, levels and rendering interfaces, traces, and the network protocol (joining, packets, replication, remote calls), with Deus Ex's additions (AI senses and events, NPC movement tests, blend animations, stasis) | [`engine-dll.md`](engine-dll.md), [`network.md`](network.md) | read |
| `Core.dll` | package Core: objects, names, packages, configuration and the script interpreter, with Deus Ex's `GetConfig`, `CriticalDelete` and debug system | [`core-dll.md`](core-dll.md) | read |
| `Extension.dll` | package Extension: the UI's windows and graphics contexts, flags, and the game engine and input that put the UI in front of the game | [`extension-dll.md`](extension-dll.md) | read |
| `ConSys.dll` | package ConSys: conversations and their events, and what binds them to actors | [`consys-dll.md`](consys-dll.md) | read |
| `DeusExText.dll` | package DeusExText: the parser of the texts the player reads (books, datacubes, newspapers, emails, bulletins, the credits) | [`deusextext-dll.md`](deusextext-dll.md) | read |
| `Render.dll` | package Render: UE1's scene renderer: which actors are drawn, render iterators, render time, coronas, what a pawn holds, which mesh faces are drawn, mesh detail, lighting | [`render-dll.md`](render-dll.md) | where a feature's drawing lives there; mesh detail and lighting |
| `D3DDrv.dll` | the Direct3D 7 display driver: gamma, the textures' depth, the light maps' brightness on screen, fog, detail textures, and each pass's blending; the look's reference | [`d3ddrv-dll.md`](d3ddrv-dll.md) | read |
| `IpDrv.dll` | package IpDrv: the sockets: the UDP net driver, the script's TCP and UDP links, GameSpy's validation, Epic's master server | [`ipdrv-dll.md`](ipdrv-dll.md) | read |
| `Galaxy.dll` | package Galaxy: the audio subsystem over the Galaxy sound library: channels and which sound wins, sounds behind walls, ambient sounds, lip sync, music, zone reverb | [`galaxy-dll.md`](galaxy-dll.md) | read |
| `Fire.dll` | package Fire: the fractal textures (fire, water lit or bending another texture, ice) that the energy weapons, lasers, fires, gas and water effects are made of | [`fire-dll.md`](fire-dll.md) | read, and checked against its own routines |
| `WinDrv.dll` | the Windows client and viewport: the game's window, DirectDraw, DirectInput, the joystick, which render device a viewport opens with | [`windrv-dll.md`](windrv-dll.md) | its command-line flags |
| `Window.dll` | the Win32 widgets and dialog templates of the launcher and the editor | [`wizard.md`](wizard.md#page-layouts) | the launcher's dialog templates, as data |

Beside them in `gamefiles/System/`, not the game's:

- **`RGalaxy.dll`** is `Galaxy.dll` with 8 bytes changed: 7 rename its package to RGalaxy,
  so both can be installed, and 1 makes the `MUSICORDER` console command change the music's
  order when the playing pattern ends, not at once
  ([the console](galaxy-dll.md#hardware-and-the-console)).
- **`ALAudio.dll`** is OldUnreal's OpenAL audio driver built for Deus Ex ("OpenAL Audio for
  DeusEX", copyright 2016): lip sync, EFX reverb with a mode that emulates the old one,
  HRTF, Doppler, OGG, and tracker music through libxmp. It needs `OpenAL32.dll`,
  `ALURE32.dll` and `libxmp.dll`, beside it.

## Working on the binaries

This repository is cloned as `dx-reverse-info/` in the folder that holds Port Ex Machina's
repositories, beside the game install (`gamefiles/`) and the reference material
(`reference/`). Paths below that are not this repository's are that folder's.

- **IDA runs headless, through Hex-Rays' own IDA MCP server.** IDA Pro 9.4 for Linux is in
  `~/ida-pro-9.4`, its `idalib` named in the user's `~/.idapro/ida-config.json`. Claude Code
  runs the server (`ida-mcp stdio`, under `uv`) from the plugin `ida-mcp@HexRaysSA`,
  installed once per machine for the user, so in every folder:
  `claude plugin marketplace add HexRaysSA/claude-marketplace`, then
  `claude plugin install ida-mcp@HexRaysSA`. Its tools:
  `open_database` (a database by its path, in a headless `idalib` worker of its own),
  `execute_python` (IDAPython and Hex-Rays' `ida-domain` API; `db` is the open database;
  names and imports persist while the session holds it; a script runs by `exec`-ing its
  file), `reference` (the API), `list_databases`, `save_database`, `close_database`. IDA's
  own window, with the same plugin in `~/.idapro/plugins/`, lends the server a database it
  has open. Without IDA for Linux, [`tools/ida/idalib-mcp.sh`](tools/ida/idalib-mcp.sh)
  serves databases from Windows IDA under Proton's wine (ida-pro-mcp's idalib supervisor,
  over stdio, in the distrobox).
- **One database per binary**, beside it ([the databases](#the-databases)). Closing a
  database (`close_database`) rewrites its `.i64` even without `save_database`, and leaves
  no working files beside it: back it up first.
- **Types.** [`tools/ida/ue1_types.py`](tools/ida/ue1_types.py) gives a database the layout
  of every native class, struct and enum from the script source in the game's packages, and
  checks each class against the size the DLL registers for it. Run it in IDA (File > Script
  file, or `execute_python` `exec`-ing the file; `PXM_GAME_DIR` names the game when the
  database is not in its `System/`), and again after reopening a database without saving.
  On the host, `--check` compares a DLL's registrations without IDA, and `--layout <class>`
  prints a class's fields at their offsets: the quickest way to name an offset seen in
  `objdump`. A C++-only class (`ULevel`, `UEventManager`, `DDeusExGameEngine`) has no script
  and so no layout; its SDK header has its members, packed to 4 bytes, so a `QWORD` or
  `DOUBLE` is not aligned to 8 (`ULevel::TimeSeconds` is at 0xdc). `Render.dll`'s types are
  all C++: [`tools/ida/render_types.py`](tools/ida/render_types.py) declares them from those
  headers ([`Render.dll`](render-dll.md#the-binary)). Extension's and ConSys's native arrays
  are typed as `TArray`s ([why](extension-dll.md#the-binary)).
- **Strings.** This build is Unicode: its strings are UTF-16, and IDA takes many for 8-bit
  ones, which the decompiler shows as nonsense.
  [`tools/ida/utf16_strings.py`](tools/ida/utf16_strings.py), run after the types, redefines
  them; a function decompiled before then needs decompiling again. A preview that reads a
  string's bytes as 8-bit text still shows a UTF-16 one as nonsense: the database is right.
- **Names.** [`tools/ida/ue1_names.py`](tools/ida/ue1_names.py) names the functions a UE1 DLL
  registers its classes and natives from, which IDA leaves as `sub_...`, and the class
  object of each class the DLL does not export (`Engine.dll`'s AI events, pending levels and
  `UServerCommandlet`, `IpDrv.dll`'s two commandlets), with the name its export would have.
  A new database gets the three scripts in turn: types, strings, names. The types again
  after the names check the unexported classes too.
- **The script and the headers.** Every native class declares its fields in its script, in
  the order its C++ class has them: after `UObject`'s 0x28 bytes, bools packed 32 to a
  dword, bytes packed, the rest aligned to 4, a string 12 bytes. The SDK
  (`reference/ReleaseSDK1112f/Headers/DxHeaders.zip`) has this build's own headers:
  hand-written classes (`Engine/Inc/UnEventManager.h`, `Engine/Inc/UnRenderIterator.h`, all
  of `Extension/Inc/` and `ConSys/Inc/`) and generated ones (`Engine/Inc/EngineClasses.h`,
  `DeusEx/Inc/DeusExClasses.h`), but none of the script's structs. Where script and header
  disagree, the registered size shows which the DLL was built with: `ADeusExPlayer` has a
  field (`LastinHand`) the SDK's header lacks, and ConSys's `DConCamera` and
  `DConEventAnimation` are as their headers have them
  ([`ConSys.dll`](consys-dll.md#the-binary)).
- **Without IDA**, `objdump` reads the DLLs. `objdump -p` lists the exports under their C++
  names (`?AICanSee@APawn@@QAEMPAVAActor@@MHHHH@Z`, and `?execAICanSee@...` for its script
  entry); an `Engine.dll` export is a jump to the code, from incremental linking, to follow.
  `objdump -d -M intel --start-address=... --stop-address=...` gives a function, and its
  calls into `Core.dll` resolve through the import table (`appAtan`, `FVector::Rotation`).
- **Dialog templates** are resources, data rather than code:
  [`tools/pe/dialogs.py`](tools/pe/dialogs.py) prints a binary's (each control's class, id,
  style and rectangle, and the font) with nothing but Python. `Window.dll` has the
  launcher's wizard and its pages, `DeusEx.exe` the splash
  ([page layouts](wizard.md#page-layouts)).
- **The original launcher runs under wine.**
  [`tools/wine/wizard-capture.sh`](tools/wine/wizard-capture.sh) runs it in a 1024×768
  virtual desktop through each scenario (`-firstrun`, `-changevideo`, `-safe` to the
  relaunch, the RecoveryMode page, `-make`);
  [`tools/wine/wizard_drive.py`](tools/wine/wizard_drive.py) works each page with Win32
  messages and saves it as the screen shows it, with its controls' rectangles. The
  install's files are put back after ([what it shows](wizard.md#observed-under-wine)). It
  runs in the distrobox, never on the host, on a Proton build's `wine` (`WIZ_PROTON`,
  default `Proton-CachyOS Latest`) and a prefix with Windows Python (`WIZ_PREFIX`, default
  `umu-default`; `WIZ_PYTHON`), as `idalib-mcp.sh` does. The captures (default
  `reference/original-wizard/`) are the game's pictures: they stay out of the repositories.
- **A native's `exec` function holds the defaults of its optional parameters**: each is set
  before its argument is read. Upstream's natives take them as `std::optional`, and a
  default is not always false (`IsValidEnemy` checks the alliance unless told not to).
- **A subsystem's `Exec` runs on its `FExec` part.** It is called through the `FExec`
  vtable, with `this` 0x28 past the object, so the decompiler's field names in it are 0x28
  short (`Galaxy.dll`'s `Exec` "toggles" `UseReverb` where it toggles its stats flag).
- **MSVC reverses overload groups in the vtable.** In `FConfigCache`, `GetString(FString&)`
  sits at **+12**, *before* `GetString(TCHAR*, INT)` at **+16**. Resolve every `GConfig`
  call by argument arity and types, never by index arithmetic: blind index math silently
  produces wrong documentation here.
- **The game's UnrealScript source is embedded in `System/DeusEx.u`** (and the other `.u`
  files). Search it, a regex over the file, before guessing what the game's script does.
- **What goes in this repository** is behaviour in our own words, with addresses, offsets
  and names: never a decompiled listing or a disassembly. The repository is public, and the
  code is not ours.

## The databases

One IDA database per binary, beside it, each backed up under the same name in
`reference/idb-backup/`. `Window.dll` has none: [`tools/pe/dialogs.py`](tools/pe/dialogs.py)
reads its templates. `gamefiles/System/DeusEx.exe.i64` holds the structs of
[`types/launch.h`](types/launch.h), and the launcher's functions and vtables under the names
[`launch-flow.md`](launch-flow.md) and [`wizard.md`](wizard.md) use. Each DLL's has the
three scripts' work (the class layouts, the UTF-16 strings, the initializers' names), and:

| Database | Besides the scripts' work | One-line comments |
|---|---|---|
| `gamefiles/System/Core.dll.i64` | 246 initializers' names are the natives' inlined registrations; by hand, a name for `UObject`'s deleting destructor | most documented functions |
| `gamefiles/System/Engine.dll.i64` | by hand: the event manager's classes and enums from the SDK header; the documented functions' prototypes; names for their helpers and the event classes' vtables; for [`network.md`](network.md), the pending level's handler, the relevancy test, the priority and its sort | most documented functions, [`network.md`](network.md)'s too |
| `gamefiles/System/DeusEx.dll.i64` | by hand: the inlined `FString` and `TArray` helpers (`TArrayTCHAR_*`, `TArrayFString_*`). Unnamed: only the C runtime and small thunks | the native tick, `Browse`, the save functions, the iterators, the alliance functions |
| `gamefiles/System/Extension.dll.i64` | by hand: the list's row comparison (`XListWindow_CompareRows`), its sort keys (`GListSortCols`, `GListNumSortCols`), `Extension_RegisterNames` | most documented functions |
| `gamefiles/System/ConSys.dll.i64` | by hand: the object iterator's step (`TObjectIterator_Advance`), the two array serializers (`Serialize_TArray_FString`, `Serialize_TArray_USoundPtr`) | most documented functions |
| `gamefiles/System/DeusExText.dll.i64` | by hand: the tag names (`GDeusExTextTagNames`), the string and array helpers (`FString_*`, `TArray_FString_*`), the deleting destructors | most documented functions |
| `gamefiles/System/Render.dll.i64` | from [`tools/ida/render_types.py`](tools/ida/render_types.py): the renderer's C++ types, `URender`'s methods typed, the texture, light map and cache structures, names for the sprite's constructor and `Setup`, the light manager's methods and helpers, and the globals of the weapon triangle and the lighting (the light map and fog map being built, the effects, the light records and their counts by kind); by hand, `CoronaTest` | most documented functions |
| `gamefiles/System/D3DDrv.dll.i64` | | |
| `gamefiles/System/IpDrv.dll.i64` | by hand: the key table and the encryption's helpers (`GenerateSecretKey`, `rc4_prepare_key`, `rc4`, `trip2kwart`, `encode_ct`) | most documented functions |
| `gamefiles/System/Galaxy.dll.i64` | by hand: `UGalaxyAudioSubsystem` and its channel record `FPlayingSound` as read here; `UViewport`'s first members from the SDK's `UnCamera.h`; Galaxy's own structures and function prototypes from the SDK's `GALAXY.H` (its licence keeps them out of this repository); the library's functions named from their assertion texts; the lip sync's helpers, the music's globals, the mixer's and the reverb's SSE routines | most documented functions |
| `gamefiles/System/Fire.dll.i64` | by hand: the shared tables (`GFireSinTable`, `GFireSinTablePlus32`, `GFireSinTablePlus128`, `GFireRandTable`, `GFireRandIndex`) and `FireInitTables` | |
| `gamefiles/System/WinDrv.dll.i64` | no layouts for its two classes, which have no script (the header has them) | most documented functions |
