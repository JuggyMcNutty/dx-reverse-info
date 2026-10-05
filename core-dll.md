# Core.dll

The native half of package Core: objects and names, packages and linkers,
the property and class system, configuration, and the script interpreter
with its natives (operators, conversions, string and math functions). How it
was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 790,528 bytes |
| Imagebase | `0x10100000` |
| SHA1 | `d03a79bb13e3b5b355df1c9b71271e026c26ef28` |
| Exports | 2,005: 33 classes, 261 `exec` functions -- 256 of `UObject` (the interpreter's tokens and the natives), 4 of `UDebugInfo`, 1 of `UCommandlet` |
| Functions | 4,099, 1,808 of them the exports' jumps |

As in `Engine.dll`, each export is a five-byte jump to its code, and the
addresses here are the code's ([its binary](engine-dll.md#the-binary)).

It registers 35 classes: the 33 it exports, `ULinkerLoad` and `ULinkerSave`.
Four have a script and match its layout: `UObject`, `USubsystem`,
`UCommandlet` and `UDebugInfo`. The other 31 -- `UField`, `UStruct`,
`UFunction`, `UState`, `UClass`, the property classes, `UPackage`, the
linkers, `USystem` -- are C++ only, and the SDK's `Core/Inc/` headers have
them. The host check reads the exported ones but `UClass` from the bytes
alone.

## What Deus Ex added

The natives the script marks as Deus Ex's (`DEUS_EX`), and a class:

- `Object`'s `GetConfig` (no number), `CriticalDelete` 751, the iterator
  `AllObjects` 1001, and `clock` 1005, `unclock` 1006 and `CyclesToSeconds`
  1007;
- `DebugInfo`, Ion Storm's debug system: `AddTimingData` 4000, `Command`
  4001, `SetString` 4002, `GetString` 4003.

`Object.Sprintf`, also Deus Ex's, is script.

### GetConfig

`GetConfig(ConfigSection, ConfigKey)` (`0x1013e4e0`): the value of a key in
the system ini -- `DeusEx.ini`, or the file `-INI=` names -- as the config
cache holds it, up to 4,095 characters; an empty string when the section or
the key is not there. Section and key match in any case. Its one caller is
the Save Game screen (`MenuScreenSaveGame.GenerateNewSnapShot`), which takes
the save's picture unless `[Engine.Engine] GameRenderDevice` is
`OpenGlDrv.OpenGLRenderDevice`.

### CriticalDelete

`CriticalDelete(myObject)` (`0x1013db50`) deletes the object on the spot,
through its deleting destructor (`0x1015dd00`, the virtual at +12): it is
destroyed if it was not yet, it leaves the name hash and the object table,
where its index is free for the next object, and its state frame and memory
are freed (`~UObject`, `0x10150040`). Nothing checks for references: whatever
still points at it is left pointing at freed memory. `None` does nothing, and
the int it is declared to return is never set.

The game's 20 calls delete objects of their own -- nano keys, logs, notes,
the conversation history, text parsers, save-game pictures and save
directories -- and clear their reference on the next line.

### AllObjects

`AllObjects(BaseClass, out Object)` (`0x1013f1f0`): an iterator over the
object table in index order, over every object that is a `BaseClass`, or
every object with `None`.

### clock, unclock and CyclesToSeconds

For timing script code by hand. `clock(t)` (`0x1013ef20`) takes the CPU's
time-stamp counter (its low 32 bits) from `t`, `unclock(t)` (`0x1013eff0`)
adds it back less 34 cycles, the measurement's own cost, and
`CyclesToSeconds(t)` (`0x1013f0d0`) multiplies by the seconds per cycle
measured at startup. No script in the game calls them.

### DebugInfo

Ion Storm's debug system (the SDK's `Core/Inc/UDebugInfo.h` and
`Core/Inc/DbgInfoCpp.h`): string settings and timing data, shared by script
and C++. This build has it compiled out. `SetString` and `Command` do
nothing, `GetString` returns an empty string, and `AddTimingData`
(`0x10120100`) only writes its arguments to the log. Its only users are
`DeusExPlayer`'s debug console commands.

## Packages and linkers

- **An export for no context is never made** (`ULinkerLoad::CreateExport`,
  `0x1012e230`). An export is made only when its flags share one of the
  linker's context flags -- `RF_LoadForClient`, `RF_LoadForServer`,
  `RF_LoadForEdit` as the game runs --; a reference to any other reads as
  None. No stock package has one. Source-protected mods do: the anti-cheat
  packages the live servers send (ANNA, DXNMS) point their classes'
  `ScriptText` at exports named None, of class `Class`, with no flags and no
  data.
- **What a save writes.** Every export of the original's saves carries the
  three context flags beside those a load reads: an actor 0x2070001 --
  transactional, with a state frame --, the save info 0x70004 (public), the
  event manager's parts 0x70000 (seen, 2026-09-27).
- **A package's file** (`appFindPackageFile`, `0x10148ec0`). A name ending in
  `.dll` is none. The name as given, if a file of it exists in the working
  directory -- the game's `System` folder --; else each of
  `[Core.System]`'s `Paths`: the path up to its `*` and the name alone,
  then with the path's extension. So a file with no extension named as a
  package stands for it: a Linux binary called `DeusEx` beside `DeusEx.exe`
  is taken for the `DeusEx` package, and the game stops at its start
  ("ReadFile beyond EOF", 2026-09-27). With a GUID asked for (a net game's package), the
  cache last: `<CachePath>\<GUID>` and `CacheExt`, the GUID `%08X` of its four
  words. First exactly, then again with each folder's names compared in any
  case (logged `Case-insensitive search: <name> -> <file>`). A file found in
  the cache has its date brought up to now (`appUpdateFileModTime`), so it
  is not purged as unused. On the paths the name alone finds it, whatever
  its GUID: a different file of the same name there fails the join as a
  version mismatch ([downloads](network.md#downloads)).
- **The cache's files.** `appCreateTempFilename` (`0x10149790`): `<path>\`
  and `%04X.tmp` of a counter that runs through the session, the first that
  holds nothing (a missing or empty file). `appCleanFileCache`
  (`0x1016cb60`), which the game engine's `Init` calls: every `*.tmp` in
  `CachePath` deleted (`Deleting temporary file: %s`), then, when
  `PurgeCacheDays` is set, every `*` `CacheExt` file older than that many
  days (`Purging outdated file from cache: %s (%i days old)`). The GOG
  build's ini: `CachePath=..\Cache`, `CacheExt=.uxx`, `PurgeCacheDays=30`.

## Configuration

- **Reading** (`LoadConfig`, `0x10150d60`). A class's `config` properties are
  read, its base class's first, each from the section named after the class
  being read -- so a subclass's section overrides its base's -- and a
  `globalconfig` one from the section of the class that declares it. The file
  is the class's config: `System` the system ini, `User` `User.ini`, any
  other name that name's `.ini` in `System`. A file that is not there gives
  no values -- the properties keep their defaults -- and is made when one is
  written (`FConfigCacheIni::Find`, only a write creating one: the SDK's
  `Core/Inc/FConfigCacheIni.h`): a mod's `config(DXMTL)` classes run on a
  client with no `DXMTL.ini`. A key that is there with no value is read
  all the same: the cache finds it, and the property's `ImportText` takes
  the empty text -- a string empty, a name None, an object or class None (no
  object has an empty name: `0x10166e20`), a float 0 (`appAtof`); an int,
  byte or bool keeps what it had, its text neither a number nor a known
  word (the token reader gives an empty token, `0x10164cb0`). So a game
  ini's `ServerName=` is a server's name, empty. Of a key given twice in a
  section the last is read (seen 2026-09-27: a user ini's second, empty
  `ngWorldSecret=` won over a first with a value).
- **`ResetConfig()`** (`0x1013e8c0`, which calls `UObject::ResetConfig` at
  `0x10151ac0` with the object's class). The class's section is copied key by
  key from `Default.ini`, for a `System` class, or `DefUser.ini`, for a `User`
  one, into the live ini; keys the default file lacks keep their values. Then
  the config is read again into the class's defaults and every subclass's, and
  into every object of them, which each get `PostEditChange`. A class of any
  other config is left alone.
- **`ResetKeyboard`** ([`Engine.dll`](engine-dll.md#small)), on every level,
  is `ResetConfig` of the viewport's input class, which Deus Ex names
  `Extension.InputExt` (`[Engine.Engine] Input=`). `DefUser.ini` has no
  section of that name -- the bindings are in `[Engine.Input]` -- so nothing
  is copied, and the input objects only read their bindings from `User.ini`
  again: the player's bindings stay.
- **The console's `GET` and `SET`** (`UObject::StaticExec`, `0x101531b0`),
  which the game's menus read and write their settings with. The class is
  found by its name in any package loaded -- the menus name `DeusExMPGame`,
  `DXMapList`, `Player`, not their packages --, the property by its name.
  `GET` gives the class default's first element as the ini writes it, with
  no quotes: a string bare, an object its class and path name
  (`Texture'Engine.S_Actor'`) or `None`, a bool `True` or `False`, an enum
  byte its value's name. `SET` takes the rest of the line, spaces and all,
  as the value (`GlobalSetProperty`, `0x101523a0`): every object of the
  class or a subclass reads it, each then told of the change
  (`PostEditChange`), then the class's defaults, and the class's config is
  saved.

## The platform's start

`appPlatformInit` (`0x1016d720`), the Windows half of `appInit`
(`UnVcWin32.cpp`): `GSys`, the memory and working-set figures, the CPU's speed
(which `CPUSPEED=` overrides), the page size and processor count, and the
CPU's features by `cpuid`. MMX, KNI (SSE) and 3DNow! are each recorded
(`GIsMMX`, `GIsKatmai`, `GIs3DNow`) only when the CPU has it and the command
line lacks `-nommx`, `-nokni` and `-nok6` respectively. Galaxy's mixer picks
its routines by them ([Galaxy](galaxy-dll.md#hardware-and-the-console)); no
other DLL was checked for them.

## The script interpreter

How the original runs UnrealScript, for comparison with the fork's VM
([where a frame goes](https://github.com/JuggyMcNutty/deusex-launcher/blob/trimui-smartpro/ports/trimui-smartpro/README.md#where-a-frame-goes)).

### The code and its tokens

- **In place.** A function's code is its bytecode, loaded with every
  reference in it -- a variable's property, a function, a class, an object, a
  name -- made a pointer or index of four bytes, and run where it lies.
- **One byte at a time.** `FFrame::Step` (`0x10115890`) reads a byte and calls
  that entry of `GNatives` (`0x101f41b8`), a table of 4,096 member functions,
  on the frame's object, with a buffer for the result. The bytes below 0x39
  are expressions and statements (variables, `Let`, jumps, calls, constants,
  context), 0x39 to 0x59 conversions, 0x60 to 0x6F a native numbered 256 or
  more (the next byte holds the rest of its number), and from 0x70 on the
  native of that number.
- **Operands follow their token:** a variable's property, a constant's value,
  a jump's offset, a call's function or name.
- **The table.** Every slot starts at `execUndefined`, which stops the game
  ("Unknown code token"), and each native's registration at load fills its
  own; a number registered twice is noted (`GNativeDuplicate`). `Core.dll`'s
  own registrations store straight into the table: the compiler inlined
  `GRegisterNative` (`0x1013f480`) into them.

### Variables and calls

- **Variables.** A variable token (`LocalVariable`, `0x1012ebc0`, and the
  instance and default ones) leaves the variable's address in a global,
  `GPropAddr`, and copies its value only when given a buffer.
- **`Let`** (`0x1012fe40`) evaluates its left side with no buffer, for the
  address alone, and its right side straight into the variable: no temporary.
  Through `None` it writes to a scratch variable, with a warning.
- **Calls** (`CallFunction`, `0x1013f4e0`):
  - a native is called directly and reads its own arguments from the caller's
    code, each with a `Step`;
  - a script function gets a frame on the machine stack (`alloca`: its
    parameters and locals, zeroed), and each argument is evaluated from the
    caller's code straight into its parameter, up to `EndFunctionParms`. An
    `out` argument's address is kept and its value copied back after the call,
    and strings and arrays among the locals are freed.
- **Virtual calls** (`VirtualFunction`, `0x101301e0`) look the function up by
  name in a hash of 256 buckets, keyed on the low byte of the name's index:
  the current state's first, then the class's (`FindObjectField`,
  `0x10150b50`). A final call carries the function itself.
- **Running a function** (`ProcessInternal`, `0x1013f690`): tokens until
  `Return`, then the return value evaluated into the caller's buffer. A
  `singular` function does not run while it already is, and a 251st nested
  call stops the game ("Infinite script recursion").
- **`a.b` with `a` `None`** (`Context`, `0x101300d0`): a warning ("Accessed
  None"), `b` skipped by a size stored inline, and a zero result.

### Events and probes

- **Events** (`ProcessEvent`, `0x1013f7d0`) are the calls from C++ into
  script -- `Tick`, `Touch`, `Timer` and the rest. None is sent while scripts
  may not run, or to an object being destroyed, and a probe only when it is
  enabled. The parameters are copied into a frame on the stack and back. The
  time from entering script from C++ to leaving it is summed in
  `GScriptCycles`, the stats' script time.
- **Probes** are the 64 names from index 300 (`Core/Inc/UnNames.h`):
  `Spawned`, `Destroyed`, `Trigger`, `Timer`, `Touch`, `Bump`, `AnimEnd`,
  `Tick`, `SeePlayer`, `HearNoise` and the rest. An object's state frame has a
  64-bit mask, `ProbeMask`, with a bit for each; an event of a probe, or a
  script call of a function named after one, runs only with its bit set.
  Nothing else is checked: any other call runs.
- **The mask is set at every `GotoState`** (`0x1012e8f0`), even into the state
  the object is in: the probes that the state or the class has a function
  for, less those the state `ignores`.
- **`Disable(name)`** (`0x1013dfb0`) clears the probe's bit until then.
  **`Enable(name)`** (`0x1013de80`) sets it, if the state or the class has a
  function for the probe and the state does not ignore it. For a name that is
  not a probe, both only log a warning.
- **State code** is run by `Engine.dll`; `UObject::ProcessState` is empty.
- **A state frame saved** (`UObject::Serialize`, for an object with one):
  the node whose code runs, the state the object is in, the probe mask (8
  bytes), the latent action -- the number of the native polling it
  ([Engine's](engine-dll.md#latent-functions)) --, and with a node the
  code's offset in it, -1 for none. An object in no state has its class for
  both nodes, as `InitExecution` (`0x10150750`) starts the frame, every
  probe on; in a state, as the original's saves have it (2026-09-27), the
  state node is the most derived of its name and the code node the state
  its label was found in -- a pickup in `DeusExPickup.Pickup` runs
  `Inventory.Pickup`'s code.

## The natives

The rest are UE1's own. Where the fork differs is in
[not as the original](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/NATIVES.md#implemented-not-as-the-original); the details:

- **To a string:** a float is `%f`, a vector `%f,%f,%f`, a rotator
  `%i,%i,%i` of its values as they are, a bool the localized `True` or
  `False`, an object its path name or `None` (`0x10131f00`).
- **From a string:** a bool is true for `True`, false for `False` (in any
  case, or the localized word), and otherwise true for a number other than 0
  (`0x10132490`). A vector or rotator reads a number at the start, after the
  first comma and after the second, and a part that is missing is 0
  (`0x10136940`, `0x10136b10`).
- **Strings:** `==`, `!=` and `<` compare with case, `~=` without; `>` is
  native 116. `Mid(S, i, j)` (`0x1013bdf0`) takes up to 65,535 characters by
  default, and a negative `i` gives an empty string: it clamps as unsigned.
  Its end -- a count past the string, or a negative one (`Mid("hello", 2, -5)`
  is `"llo"`) -- is not read here but was settled by running the original, with
  VibeEngine's `MidConsole`
  ([the fork's notes](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/NATIVES.md#implemented-not-as-the-original)).
  `Chr` and `Asc` take UTF-16 code units, as this build is Unicode.
- **Math:** an integer divided by 0 is 0 (`0x10133710`), and a byte divided
  by 0 with `/=` is left as it was. `Rand(n)` is 0 for `n` of 0 or less, else
  the C library's `rand()` modulo `n`, which is below 32,768. `VRand`
  (`0x10139080`) draws points in the cube from −1 to 1 until one is inside the
  unit sphere, then scales it to length 1: a direction with none favoured.
  `Normal` of a zero vector is zero.

## Names hashed and compared

- **`appStrihash`**, UE1's inline hash with case ignored: from 0, each UTF-16
  character, upper-cased if a to z, taken low byte then high byte into
  `h = (h >> 8) ^ GCRCTable[(h ^ byte) & 0xFF]`. `GCRCTable` is the CRC table
  of the polynomial 0x04C11DB7, most significant bit first. The event
  manager's buckets and the flag base's use it
  ([events](engine-dll.md#the-manager), [flags](extension-dll.md#flags)).
- **`appStricmp`** (`0x10123560`) is the C library's `_wcsicmp`, which folds
  A to Z to lower case: an underscore sorts before the letters.

## The database

`gamefiles/System/Core.dll.i64` has the class layouts, the UTF-16 strings and
the initializers' names ([working on the binaries](README.md#working-on-the-binaries)),
246 of them the natives' inlined registrations, and by hand a name for
`UObject`'s deleting destructor and a one-line comment on each function above.
