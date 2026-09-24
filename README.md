# Reverse engineering

What was read from the original game's binaries, and how. Two efforts:

- **The launcher.** `System/DeusEx.exe` was reverse-engineered before any of
  the launcher was written, so the launcher started from known behaviour:
  [`launcher.md`](launcher.md). Complete.
- **The game's DLLs.** The original C++ behind Deus Ex's natives, read to find
  what Surreal Engine lacks or has wrong and to port it -- patch 0034 was the
  first ([what the fork changes](../ENGINE.md#what-the-fork-changes)). In
  progress. What the engine lacks, and the work that would fill it:
  [`natives.md`](natives.md).

## The binaries

All in the game's `System/`, from the GOG build of 1.112fm; the DLLs were built
in March 2001. The engine recognises the install by `DeusEx.exe`'s SHA1
([`launcher.md`](launcher.md#the-binary)).

| Binary | What it holds | Notes | Read |
|---|---|---|---|
| `DeusEx.exe` | the `Launch` module: a bootstrap shell, not the game | [`launcher.md`](launcher.md) | complete |
| `DeusEx.dll` | package DeusEx: the player, NPCs (`ScriptedPawn`), saving and the save directory, particle and laser effects | [`deusex-dll.md`](deusex-dll.md) | read |
| `Engine.dll` | package Engine: UE1's actors, pawns, levels and rendering interfaces, with Deus Ex's additions (AI senses and events, NPC movement tests, blend animations, stasis) | [`engine-dll.md`](engine-dll.md) | read |
| `Core.dll` | package Core: objects, names, packages, configuration and the script interpreter, with Deus Ex's `GetConfig`, `CriticalDelete` and debug system | [`core-dll.md`](core-dll.md) | read |
| `Extension.dll` | package Extension: the UI's windows and graphics contexts, and flags | [`extension-dll.md`](extension-dll.md) | not yet |
| `ConSys.dll` | package ConSys: conversations and their events | [`consys-dll.md`](consys-dll.md) | not yet |
| `DeusExText.dll` | package DeusExText: the parser of books, datacubes and emails | [`deusextext-dll.md`](deusextext-dll.md) | not yet |

## Working on the binaries

- **IDA runs under Proton** (Windows IDA 9.4 via umu, in-IDA HTTP server on
  `127.0.0.1:13337` plus a Linux-side proxy). `idalib` headless mode is
  impossible here. If the MCP tools go dark mid-session that bridge broke, not
  the analysis. IDA sees this tree as `X:\Documents\projects\port-ex-machina`
  and the whole filesystem as `Z:\`, so a script in any scratch directory runs
  through `py_exec_file`. `py_eval` keeps its top-level names as locals, which
  a function or comprehension defined there cannot see: put the code in a
  function, or in a file.
- **One database per binary**, beside it: `gamefiles/System/DeusEx.exe.i64`
  and the like, unpacked while open -- the `.id0`, `.id1`, `.id2`, `.nam` and
  `.til` files beside it are working files, and the `.i64` is only written on
  save. Backups in `reference/idb-backup/`. The bridge serves whichever
  database IDA has open, so one binary is worked on at a time. It picks its
  IDA when it starts: a DLL opened in a second IDA window is served on the
  next port (13338), and the bridge stays with the first window.
- **Types.** [`tools/ida/ue1_types.py`](../../tools/ida/ue1_types.py) gives a
  database the layout of every native class, struct and enum, from the
  script source in the game's packages, and checks each class against the size
  the DLL registers for it. Run it in IDA (File > Script file, or the MCP's
  `py_exec_file`), again after reopening a database without saving. On the
  host, `--check` compares a DLL's registrations without IDA, and `--layout
  <class>` prints a class's fields at their offsets -- the quickest way to name
  an offset seen in `objdump`. A class that is C++ only (`ULevel`,
  `UEventManager`, `DDeusExGameEngine`) has no script and so no layout from it;
  its SDK header has its members.
- **Strings.** This build is Unicode: its strings are UTF-16, and IDA takes
  many for 8-bit ones, which the decompiler shows as nonsense.
  [`tools/ida/utf16_strings.py`](../../tools/ida/utf16_strings.py), run after
  the types, redefines them; a function decompiled before then needs
  decompiling again.
- **Names.** [`tools/ida/ue1_names.py`](../../tools/ida/ue1_names.py) names
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
- **A native's `exec` function holds the defaults of its optional
  parameters**: each is set before its argument is read. Upstream's natives
  take them as `std::optional`, and a default is not always false
  (`IsValidEnemy` checks the alliance unless told not to).
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
| [`launcher.md`](launcher.md) | `DeusEx.exe`: anchors, struct sizes, findings, what the launcher kept and dropped |
| [`launch-flow.md`](launch-flow.md), [`wizard.md`](wizard.md), [`cli-flags.md`](cli-flags.md), [`ini-keys.md`](ini-keys.md), [`porting-notes.md`](porting-notes.md), [`types/launch.h`](types/launch.h), [`live-verification.md`](live-verification.md) | the launcher's details ([its index](launcher.md)) |
| [`deusex-dll.md`](deusex-dll.md), [`engine-dll.md`](engine-dll.md), [`core-dll.md`](core-dll.md), [`extension-dll.md`](extension-dll.md), [`consys-dll.md`](consys-dll.md), [`deusextext-dll.md`](deusextext-dll.md) | each DLL: the binary, its classes, what each function does, with addresses |
| [`natives.md`](natives.md) | what Surreal Engine lacks of the original, what the player sees of it, and the work -- from [`tools/natives_audit.py`](../../tools/natives_audit.py) and play |
