# Core.dll

The native half of package Core: objects and names, packages and linkers,
the property and class system, configuration, and the script interpreter
with its natives (operators, conversions, string and math functions). Read with:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 790,528 bytes |
| Imagebase | `0x10100000` |
| SHA1 | `d03a79bb13e3b5b355df1c9b71271e026c26ef28` |
| Exports | 2,005: 33 classes; 261 `exec` functions: 256 of `UObject` (the interpreter's tokens and the natives), 4 of `UDebugInfo`, 1 of `UCommandlet` |
| Functions | 4,099, 1,808 of them the exports' jumps |

- Each export is a five-byte jump to its code, as in `Engine.dll`
  ([its binary](engine-dll.md#the-binary)). The addresses here are the
  code's.
- It registers 35 classes: the 33 it exports, `ULinkerLoad` and
  `ULinkerSave`.
  - Four have a script and match its layout: `UObject`, `USubsystem`,
    `UCommandlet` and `UDebugInfo`.
  - The other 31 are C++ only; the SDK's `Core/Inc/` headers have them:
    `UField`, `UStruct`, `UFunction`, `UState`, `UClass`, the property
    classes, `UPackage`, the linkers, `USystem`.
  - The host check reads the exported ones but `UClass` from the bytes
    alone.

## What Deus Ex added

The natives the script marks as Deus Ex's (`DEUS_EX`), and a class:

| Class | Natives |
|---|---|
| `Object` | `GetConfig` (no number), `CriticalDelete` 751, the iterator `AllObjects` 1001, `clock` 1005, `unclock` 1006, `CyclesToSeconds` 1007 |
| `DebugInfo`, Ion Storm's debug system | `AddTimingData` 4000, `Command` 4001, `SetString` 4002, `GetString` 4003 |

`Object.Sprintf`, also Deus Ex's, is script.

### GetConfig

`GetConfig(ConfigSection, ConfigKey)` (`0x1013e4e0`):

- the value of a key in the system ini (`DeusEx.ini`, or the file `-INI=`
  names), as the config cache holds it, up to 4,095 characters;
- an empty string when the section or the key is not there;
- section and key match in any case.

Its one caller is the Save Game screen
(`MenuScreenSaveGame.GenerateNewSnapShot`), for its save picture
([save pictures](extension-dll.md#save-pictures)).

### CriticalDelete

`CriticalDelete(myObject)` (`0x1013db50`) deletes the object on the spot,
through its deleting destructor (`0x1015dd00`, the virtual at +12):

- the object is destroyed, if it is not already;
- it leaves the name hash and the object table, where its index is free for
  the next object;
- its state frame and memory are freed (`~UObject`, `0x10150040`).

Nothing checks for references: whatever still points at it is left pointing
at freed memory. `None` does nothing. The int it is declared to return is
never set.

The game's 20 calls, all in `DeusEx.u`, delete objects of their own:

| What | Callers |
|---|---|
| a nano key | `NanoKeyRing.RemoveKey`, `RemoveAllKeys` |
| an image's note | `DataVaultImage.DeleteNote` |
| the log, the conversation history | `DeusExPlayer.ClearLog`, `ResetConversationHistory` |
| the player's debug object | `DeusExPlayer.Destroyed` |
| a dump location | `DeusExGameInfo.Login`, `DeusExPlayer.DXDumpInfo`, `DumpLocationBaseWindow.DestroyDumpLoc`, `BehindTheCurtain.ViewDumps` |
| a text parser | `InformationDevices.CreateInfoWindow`, `CreditsScrollWindow.ProcessText`, `ComputerUIWindow.ProcessDeusExText` |
| a save-game picture | `MenuScreenSaveGame.DestroyWindow`, `DeusExRootWindow.ShowSnapshot` |
| a save or map directory | `MenuScreenSaveGame.NewSaveGame`; `MenuScreenLoadGame`'s `UpdateSaveInfo`, `PopulateGames`, `UpdateFreeDiskSpace`; `LoadMapWindow.DestroyWindow` |

Most drop their reference on the next line. `RemoveAllKeys` reads the deleted
key's `NextKey` to go on, from freed memory.

### AllObjects

`AllObjects(BaseClass, out Object)` (`0x1013f1f0`): an iterator over the
object table in index order, over every object that is a `BaseClass`, or
every object with `None`.

### clock, unclock and CyclesToSeconds

For timing script code by hand. No script in the game calls them.

- `clock(t)` (`0x1013ef20`) takes the CPU's time-stamp counter (its low 32
  bits) from `t`.
- `unclock(t)` (`0x1013eff0`) adds it back less 34 cycles, the
  measurement's own cost.
- `CyclesToSeconds(t)` (`0x1013f0d0`) multiplies by the seconds per cycle
  measured at startup.

### DebugInfo

Ion Storm's debug system (the SDK's `Core/Inc/UDebugInfo.h` and
`Core/Inc/DbgInfoCpp.h`): string settings and timing data, shared by script
and C++. This build has it compiled out:

- `SetString` and `Command` do nothing;
- `GetString` returns an empty string;
- `AddTimingData` (`0x10120100`) only writes its arguments to the log.

Its only users are `DeusExPlayer`'s debug console commands.

## Packages and linkers

- **An export for no context is never made** (`ULinkerLoad::CreateExport`,
  `0x1012e230`). An export is made only when its flags share one of the
  linker's context flags: `RF_LoadForClient`, `RF_LoadForServer`,
  `RF_LoadForEdit` as the game runs. A reference to any other reads as None.
  No stock package has one. Source-protected mods do: the anti-cheat
  packages the live servers send (ANNA, DXNMS) point their classes'
  `ScriptText` at exports named None, of class `Class`, with no flags and no
  data.
- **What a save writes.** Every export in a save carries the three context
  flags beside those a load reads:

  | Export | Flags |
  |---|---|
  | an actor | 0x2070001: transactional, with a state frame |
  | the save info | 0x70004 (public) |
  | the event manager's parts | 0x70000 |

  No object flagged `RF_Transient` is written (`SavePackage`, `0x10155980`),
  and `StaticAllocateObject` (`0x101579c0`) flags so every object of a class
  with `CLASS_Transient`: a reference to one reads as None. A level's mission
  script (`MissionScript` is transient) is in no save.

- **A package's file** (`appFindPackageFile`, `0x10148ec0`). A name ending in
  `.dll` finds none. The search:
  1. the name as given, if a file of it exists in the working directory
     (the game's `System` folder);
  2. each of `[Core.System]`'s `Paths`: the path up to its `*` and the name
     alone, then with the path's extension;
  3. with a GUID asked for (a net game's package), the cache last:
     `<CachePath>\<GUID>` and `CacheExt`, the GUID `%08X` of its four words.

  It runs first exactly, then again with each folder's names compared in any
  case (logged `Case-insensitive search: <name> -> <file>`).
  - So a file with no extension named as a package stands for it: a Linux
    binary called `DeusEx` beside `DeusEx.exe` is taken for the `DeusEx`
    package, and the game stops at its start ("ReadFile beyond EOF").
  - A file found in the cache has its date set to the current time
    (`appUpdateFileModTime`), so it is not purged as unused.
  - On the paths the name alone finds it, whatever its GUID: a different
    file of the same name there fails the join as a version mismatch
    ([downloads](network.md#downloads)).
- **The cache's files.**
  - `appCreateTempFilename` (`0x10149790`): `<path>\` and `%04X.tmp` of a
    counter that runs through the session, the first that holds nothing (a
    missing or empty file).
  - `appCleanFileCache` (`0x1016cb60`), which the game engine's `Init`
    calls: every `*.tmp` in `CachePath` deleted
    (`Deleting temporary file: %s`); then, when `PurgeCacheDays` is set,
    every `*` `CacheExt` file older than that many days
    (`Purging outdated file from cache: %s (%i days old)`).
  - The GOG build's ini: `CachePath=..\Cache`, `CacheExt=.uxx`,
    `PurgeCacheDays=30`.

- **A tagged property the class cannot take** (`UStruct::SerializeTaggedProperties`,
  `0x10126730`) is logged and its bytes skipped, the object loading on: a name no property
  has (`Property %s of %s not found`), another type (`Type mismatch in %s of %s: file %i,
  class %i`), an element past the static array (`Array bounds in %s of %s: %i/%i`), another
  struct (`Property %s of %s struct type mismatch %s/%s`), a native or, on a persistent
  archive, transient property (`Property %s of %s is not serialiable`, sic); each skip logs
  `Skipping %i bytes of type %i`, but for `XLevel`. A struct's binary (`UStruct::SerializeBin`,
  `0x10126610`) is every member of it and the structs it extends, native members left out
  and transient ones on a persistent archive, every element of a static array member;
  a dynamic array's (`UArrayProperty::SerializeItem`, `0x10168520`) its count then each
  element's.

## Garbage collection

An object stays while it is reachable from the root set; everything else is
destroyed, then deleted. Nothing is reference-counted. The game engine
collects at each map load but Entry's
([`Engine.dll`](engine-dll.md#the-map-loads-collection)); the console's
`OBJ GARBAGE` collects at once, keeping what is native (and, in the editor, what
is standalone), even under `-NOGC`.

**`CollectGarbage(KeepFlags)`** (`0x10158500`) logs `Collecting garbage`, makes
the tag archive, marks from the root set (`SerializeRootSet`) and purges
(`PurgeGarbage`).

**The tag archive** (made at `0x1015eac0`):

- It tags every object `RF_TagGarbage | RF_Unreachable` and every name
  `RF_Unreachable`.
- **A reference** (`operator<<(UObject*&)`, `0x1015ec90`) counts one. A target
  flagged `RF_EliminateObject` (0x400) is set to None there, in the holder's
  own memory, and is not followed. An unreachable target loses
  `RF_Unreachable`; the first time (it still has `RF_TagGarbage`) it loses that
  too and is serialized into the archive, so its own references are followed.
  A serialize that does not reach `UObject::Serialize` is fatal
  (`%s failed to route Serialize`).
- **A name** reached loses `RF_Unreachable`.

**The root set** (`SerializeRootSet`, `0x101580b0`): `GObjRoot` (the objects
`AddToRoot` keeps), then every object that has one of `KeepFlags` and still
carries `RF_TagGarbage`. Script classes are not native: a class nothing uses
goes with its package and is loaded again when next asked for.

**What an object marks** (`UObject::Serialize`, `0x10150210`, as the archive
neither loads nor saves):

- its class, name, outer and linker (so an object keeps its package and its
  linker);
- with a state frame (`RF_HasStack`), the frame's node and state;
- its properties, by its class's `SerializeBin`: every object property, each
  element of a static array, the objects inside structs and dynamic arrays;
- a native class adds its own members in its `Serialize`. A linker
  (`ULinker::Serialize`, `0x1011df90`) marks its root and each import's object,
  never its exports: a loaded package's objects stay only while something
  reaches them.

**The purge** (`PurgeGarbage`, `0x101581f0`), unless `-NOGC`
(`Not purging garbage`); it logs `Purging garbage`, with
`GObjInGarbageCollection` set:

1. Every object still `RF_Unreachable` is destroyed (`ConditionalDestroy`,
   `0x1014fdb0`: once only, `RF_Destroyed`; `Destroy` frees its properties'
   strings and arrays, `UObject::Destroy` at `0x1014fa50`) -- natives only in
   the exit purge, every object then.
2. Every unreachable non-native object is deleted (the virtual at +12, as
   `CriticalDelete`'s).
3. Every unreachable name that is not native is deleted
   (`FName::DeleteEntry`, `0x1014e0b0`; [names](#names-hashed-and-compared)).

It ends with `Garbage: objects: %i->%i; refs: %i`: the objects before, after,
and the references counted.

**`UStruct::CleanupDestroyed(Data)`** (`0x10127170`), which a level calls on
each live actor ([destroyed actors](engine-dll.md#destroyed-actors)): through
the struct's `RefLink`, every element of every object property that points at
an object that `IsPendingKill` (an actor with `bDeleteMe`) becomes None; through
`StructLink`, each element of a struct property is cleaned the same way. Dynamic
arrays are left alone. A reference to an invalid object is fatal. In the editor
it walks every property instead and calls `Modify` before each change.


## Configuration

- **Reading** (`LoadConfig`, `0x10150d60`):
  - A class's `config` properties are read, its base class's first, each
    from the section named after the class being read: a subclass's section
    overrides its base's. A `globalconfig` one is read from the section of
    the class that declares it.
  - The file is the class's config: `System` the system ini, `User`
    `User.ini`, any other name that name's `.ini` in `System`.
  - A file that is not there gives no values: the properties keep their
    defaults. It is made when one is written (`FConfigCacheIni::Find`, only
    a write creating one: the SDK's `Core/Inc/FConfigCacheIni.h`). So a mod's
    `config(DXMTL)` classes run on a client with no `DXMTL.ini`.
  - A key that is there with no value is read all the same: the cache finds
    it, and the property's `ImportText` takes the empty text.

    | Property | Empty text gives |
    |---|---|
    | string | empty |
    | name | None |
    | object or class | None (no object has an empty name: `0x10166e20`) |
    | float | 0 (`appAtof`) |
    | int, byte or bool | what it had: its text is neither a number nor a known word (the token reader gives an empty token, `0x10164cb0`) |

    So a game ini's `ServerName=` is a server's name, empty.

    The token reader (`0x10164cb0`, UE1's `ReadToken`) gives: a quoted
    string to its closing quote, with `\\` and `\xx` (two hex digits, one
    that is none counting 0) escapes, no token when the quote is left open
    ("ReadToken: Bad quoted string"); else, from a letter or digit, the run
    of letters, digits, `_` and `-` (and `.` where dots are allowed); else
    the first character alone. A name's import (`UNameProperty::ImportText`)
    is its first token, dots not allowed: `-7` names `-`, `a b` names `a`,
    `"a b"` names `a b`.
  - Of a key given twice in a section the last is read, even empty: a user
    ini's second, empty `ngWorldSecret=` beats a first with a value.
- **`StaticSaveConfig()`** (`0x1013e7c0`): `SaveConfig` of the context's
  class's defaults (`UClass::Defaults`), from an object's call as from the
  class's; the object's own values are never written.
- **`ResetConfig()`** (`0x1013e8c0`; it calls `UObject::ResetConfig`,
  `0x10151ac0`, with the object's class):
  1. The class's section is copied key by key into the live ini from
     `Default.ini`, for a `System` class, or `DefUser.ini`, for a `User` one.
     Keys the default file lacks keep their values.
  2. The config is read again into the class's defaults and every
     subclass's, and into every object of them, which each get
     `PostEditChange`.

  A class of any other config is left alone.
- **`ResetKeyboard`** ([`Engine.dll`](engine-dll.md#small)), on every level, is
  `ResetConfig` of the viewport's input class, which Deus Ex names
  `Extension.InputExt` (`[Engine.Engine] Input=`). `DefUser.ini` has no
  section of that name (the bindings are in `[Engine.Input]`), so nothing is
  copied: the input objects only read their bindings from `User.ini` again,
  and the player's bindings stay.
- **`GetPropertyText(PropName)` and `SetPropertyText(PropName, Value)`**
  (`0x1013e0b0`, `0x1013e320`): a property of the object's class by its
  name, read only when it is public (a script's `private` one is not), its
  first element as `GET` writes it, and set only when it is public and not
  const; any other name reads empty and sets nothing. The server's query
  answerer (`IpServer`'s `UdpServerQuery`) reads the level's, the game's
  and the players' properties a remote names through it.
- **The console's `GET` and `SET`** (`UObject::StaticExec`, `0x10153110`),
  with which the game's menus read and write their settings:
  - The class is found by its name in any package loaded (the menus name
    `DeusExMPGame`, `DXMapList`, `Player`, not their packages); the property
    by its name.
  - `GET` gives the class default's first element as the ini writes it,
    with no quotes: a string bare; an object its class and path name
    (`Texture'Engine.S_Actor'`) or `None`; a bool `True` or `False`; an enum
    byte its value's name.
  - `SET` takes the rest of the line, spaces and all, as the value
    (`GlobalSetProperty`, `0x101523a0`). Every object of the class or a
    subclass reads it, each then told of the change (`PostEditChange`); then
    the class's defaults; then the class's config is saved.

### A property's text

The text a property is read from and written to -- an ini's value, a `.int` file's, `SET`
and `GET`, `SetPropertyText` and `GetPropertyText`, a travel's -- by each property class's
`ImportText` and `ExportTextItem`:

- **A struct** (`UStructProperty::ImportText`, `0x101698b0`): `(key=value,key[i]=value,...)`;
  a key up to 63 characters, an element index in brackets, `=` (`Illegal or missing key
  name`); the member found by name among the struct's and the structs it extends, within its
  dimension, and given the text to import delimited; a key
  no member has is skipped to the next `,` or `)` at depth 0, a quoted string whole (`Bad
  quoted string`), nested parentheses counted (`Bad parenthesised struct`, `Incomplete
  parenthesised struct`); then `,` or `)` (`Bad termination`). Members not named keep their
  values. The index reader is broken: it starts on the `[` itself, finds no `]` there, logs
  `ImportText: Illegal array element` and fails the import at that key (the members before it
  set), so `N[1]=7` is never read -- though the export writes it (TextConsole, 2026-10-26).
  Out (`ExportTextItem`, `0x10169710`): `(` + each portable member, the struct's own first,
  then the extended struct's (a Plane's W before X, Y, Z), each element of a static array as
  `Name[i]=`, joined by `,`, + `)` -- nothing at all when no member prints.
- **A string** (`UStrProperty::ImportText`, `0x10167980`): delimited, one token by the
  token reader (`0x10164cb0`): a quoted string's content, `\\` a backslash and `\xx` a hex
  byte, or a bare run of letters, digits, `_` and `-`, else one character; undelimited, the
  text whole. Out (`0x101678a0`): quoted when delimited, bare otherwise.
- **A dynamic array** (`UArrayProperty::ImportText`, `0x10168830`): `(a,b,...)`, the array
  emptied and each element's delimited text imported; out (`0x10168720`) the elements'
  text joined by `,` in parentheses.
- **An object** (`UObjectProperty::ImportText`, `0x10166e20`): `None`; `Type'Name'`, the
  class `Type` found among the loaded (`StaticFindObject` in any package) and the object by
  `Name` among its loaded instances, a path or a bare name; else the name among the
  property class's loaded objects. Nothing found leaves None. Out (`0x10166d40`):
  `Type'Package.Group.Name'` or `None`. **A class** (`UClassProperty::ImportText`,
  `0x10167110`): the object's import, then None unless a class deriving from the metaclass;
  out as an object's.
- **A bool** (`0x10166380`): `1`, `True` or the localized true word; `0`, `False` or the
  localized false; anything else fails, the value kept.
- **`SaveConfig`** (`UObject::SaveConfig`, `0x10151540`): for each property with the flags
  asked, under the class's path as its section (the declaring class's for a `globalconfig`
  one, the object's name for a per-object config class): a dynamic array has the section's
  lines of its name removed and one `Name=element` line written per element; a map's lines
  are removed; anything else is one key, `Name` or `Name[i]`, its text exported undelimited
  (a string bare, a struct's members quoted within); the config cache is flushed to disk at
  once, and every class deriving from the config class re-reads its defaults.

### The .int files

Both readers take them from `System` alone, whatever the paths say: a mod's
must be put there.

- **A package's text** (`Localize`, `0x10148430`). The key is read from
  `<Package>.<language>`, then from `<Package>.int` (the game's language is
  `int`). Each is read through the config cache by that name alone, so it
  comes from the working directory, `System`, never along the paths. A key
  there with no value gives empty text. For a key in neither file:
  - the script's `Localize` (`execLocalize`, `0x1013ce00`) logs
    `No localization: <Package>.<Section>.<Key> (int)` and gives
    `<?int?<Package>.<Section>.<Key>?>`;
  - a class's localized properties (`LoadLocalized`, `0x10151390`) take an
    empty text, and a property given empty text keeps its default.
- **The objects they register** (`UObject::CacheDrivers`, `0x10158900`),
  which `GetRegistryObjects` (`0x101591c0`) calls before it reads them. It
  reads the files once, and again when the language changes.
  - Each path's folder is searched for `*.int`. The path is taken relative
    to Core.dll's own folder (`appBaseDir`, `0x1016d0e0`, `System`), so an
    absolute path finds nothing.
  - Each file found is read by its name from `System`, not from the folder
    it was found in: its `[Public]` section, from `<name>.<language>` else
    `<name>.int`. `Object=` lines register objects, and `Preferences=` lines
    the Advanced Options' pages.
  - So only `System`'s files register anything. A file found in another
    path's folder registers `System`'s file of that name, if there is one,
    a second time.
  - Each `Core.<ext>` in `System`, but for `dll`, `u` and `ilk`, then
    registers a language.

## RELAUNCH

`USystem::Exec` (`0x1016b790`), beside `EXIT` and `QUIT`, takes `RELAUNCH`
with the rest of the line:

1. It logs `Relaunch: <rest>`.
2. It writes the configuration back to its files.
3. It starts `deusex.exe` -- that name, relative, not the running module's
   path, which it asks for and only logs -- with the rest as its command
   line, in the base directory (`ShellExecute`, `open`).
4. It asks the engine to exit (`appRequestExit(0)`), and the process ends
   through its main loop as any clean exit does. It does not wait for the new
   one.

Deus Ex's scripts send it twice. The Display screen's Rendering Device sends
`RELAUNCH -changevideo`, after saving the menu's settings: the launcher's
renderer page ([the wizard](wizard.md)). The Host screen's dedicated server
sends `Relaunch <map>?game=<class>?-server?log=server.log`: `ParseParam`
finds `-server` in the URL, as it checks nothing after a flag's name
([the parsers](cli-flags.md)). The `deusex.exe` it starts does not forward
either line to the instance still ending: both hold one of the words that
keep a launch from forwarding ([the launch](launch-flow.md)).

## The platform's start

`appPlatformInit` (`0x1016d720`), the Windows half of `appInit`
(`UnVcWin32.cpp`), sets `GSys`, the memory and working-set figures, the CPU's
speed (which `CPUSPEED=` overrides), the page size and processor count, and
the CPU's features by `cpuid`. Each feature is recorded only when the CPU
has it and the command line lacks its switch:

| Feature | Recorded in | Switch |
|---|---|---|
| MMX | `GIsMMX` | `-nommx` |
| KNI (SSE) | `GIsKatmai` | `-nokni` |
| 3DNow! | `GIs3DNow` | `-nok6` |

Galaxy's mixer picks its routines by them
([Galaxy](galaxy-dll.md#hardware-and-the-console)), `Render.dll` its
surface clip by `GIs3DNow` ([a frame](render-dll.md#a-frame)), and the
launcher the Detail page's sound by `GIsMMX`
([the wizard](wizard.md#detail-2018)). `Engine.dll` imports `GIs3DNow` too,
and `SoftDrv.dll` `GIsMMX`: neither use is read here.

It seeds the C library's `rand` from the clock (`srand(time(0))`), once, so
every number drawn from it differs from run to run: the script's `Rand`,
`FRand`, `VRand` and `RotRand` ([the natives](#the-natives)) and the fractal
textures' random bytes ([`Fire.dll`](fire-dll.md#the-shared-tables)).

## The script interpreter

How the original runs UnrealScript.

### The code and its tokens

- **In place.** A function's code is its bytecode, run where it lies. It is
  loaded with every reference in it (a variable's property, a function, a
  class, an object, a name) made a pointer or index of four bytes.
- **One byte at a time.** `FFrame::Step` (`0x10115890`) reads a byte and
  calls that entry of `GNatives` (`0x101f41b8`), a table of 4,096 member
  functions, on the frame's object, with a buffer for the result:

  | Byte | Token |
  |---|---|
  | below 0x39 | expressions and statements (variables, `Let`, jumps, calls, constants, context) |
  | 0x39 to 0x59 | conversions |
  | 0x60 to 0x6F | a native numbered 256 or more; the next byte holds the rest of its number |
  | 0x70 and up | the native of that number |

- **Operands follow their token:** a variable's property, a constant's value,
  a jump's offset, a call's function or name.
- **A runaway loop.** Each `Jump` (`0x1012faf0`) and `JumpIfNot`
  (`0x1012fbc0`) run, taken or not, adds one to a count. Past 10,000,000 the
  frame logs "Runaway loop detected (over 10000000 iterations)" as a
  critical error, which stops the game, unless the command line has
  `-norunaway`; either way the count starts again. `GInitRunaway`
  (`0x1012e7d0`) zeroes it and the call depth below: `Engine.dll` calls it at
  the start of each level's tick (`ULevel::Tick`) and early in a map's load
  (`UGameEngine::LoadMap`), before the level is loaded.
- **The table.** Every slot starts at `execUndefined`, which stops the game
  ("Unknown code token"). Each native's registration at load fills its own;
  a number registered twice is noted (`GNativeDuplicate`). `Core.dll`'s own
  registrations, 246 of its initializers, store straight into the table:
  the compiler inlined `GRegisterNative` (`0x1013f480`) into them.

### Variables and calls

- **Variables.** A variable token (`LocalVariable`, `0x1012ebc0`, and the
  instance and default ones) leaves the variable's address in a global,
  `GPropAddr`, and copies its value only when given a buffer.
- **`Let`** (`0x1012fe40`) evaluates its left side with no buffer, for the
  address alone, and its right side straight into the variable: no
  temporary. Through `None` it writes to a scratch variable, with a warning.
- **Calls** (`CallFunction`, `0x1013f4e0`):
  - a native is called directly and reads its own arguments from the
    caller's code, each with a `Step`;
  - a script function gets a frame on the machine stack (`alloca`: its
    parameters and locals, zeroed). Each argument is evaluated from the
    caller's code straight into its parameter, up to `EndFunctionParms`. An
    `out` argument's address is kept and its value copied back after the
    call. Strings and arrays among the locals are freed.
- **Virtual calls** (`VirtualFunction`, `0x101301e0`) look the function up by
  name in a hash of 256 buckets, keyed on the low byte of the name's index:
  the current state's first (its own, then the state it extends or
  overrides, up that chain), then the class's (`FindObjectField`,
  `0x10150b50`). A final call carries the function itself.
- **Running a function** (`ProcessInternal`, `0x1013f690`): tokens up to
  `Return`, then the return value evaluated into the caller's buffer. A
  `singular` function does not run while any singular function of its
  object does: the object holds one flag, bit `0x20` of its `ObjectFlags`
  (`FUNC_Singular`'s own value; the SDK's `RF_InSingularFunc`, `0x800`, goes
  unused). A call held off writes nothing: a variable assigned from it keeps
  its value. A 251st nested script function stops the game ("Infinite
  script recursion (250 calls) detected"), the events called from C++
  counted with the rest.
- **`a.b` with `a` `None`** (`Context`, `0x101300d0`): a warning ("Accessed
  None"), `b` skipped by a size stored inline, and a zero result.
- **`switch`** (`execSwitch`, `0x1012f850`): the condition kept, then each
  case's value compared with it -- a string by `appStricmp`, without regard
  to case; any other type by `appMemcmp` over the switch's size, so a float
  by its bits (−0.0 is not 0.0).
- **A dynamic array's element** (`execDynArrayElement`, `0x1012f190`)
  asserts, `Array` (UnCorSc.cpp 325), on every access: its array pointer is
  a null the source left (`//!!`). Deus Ex's scripts declare `array<>`
  properties and never index one.

### Events and probes

- **Events** (`ProcessEvent`, `0x1013f7d0`) are the calls from C++ into
  script: `Tick`, `Touch`, `Timer` and the rest.
  - None is sent while scripts may not run, or to an object being
    destroyed; a probe only when it is enabled.
  - The parameters are copied into a frame on the stack and back.
  - The time from entering script from C++ to leaving it is summed in
    `GScriptCycles`, the stats' script time.
- **Probes** are the 64 names from index 300 (`Core/Inc/UnNames.h`):
  `Spawned`, `Destroyed`, `Trigger`, `Timer`, `Touch`, `Bump`, `AnimEnd`,
  `Tick`, `SeePlayer`, `HearNoise` and the rest. An object's state frame has
  a 64-bit mask, `ProbeMask`, with a bit for each. An event of a probe, or a
  script call of a function named after one, runs only with its bit set.
  Nothing else is checked: any other call runs.
- **The mask is set at every `UObject::GotoState`** (`0x1012e8f0`), even
  into the state the object is in: the probes that the state or the class
  has a function for, less those the state `ignores`. Into another state it
  first sends `EndState` under `RF_InEndState` (`0x2000`; not from within
  one), `RF_StateChanged` (`0x1000`) cleared before and tested after: a
  `GotoState` finished during it sets the flag, and this one then returns
  preempted (2), its state and label never taken. The state set, `BeginState`
  the same way. A finished `GotoState` sets `RF_StateChanged` and returns 1;
  the script's goes to its label only then.
- **A script's `GotoState`** (`execGotoState`, `0x1013dd00`) calls it only
  for another state than the object's (one left out is the object's own),
  then goes to the label if the change was not preempted by a `GotoState` in
  `EndState` or `BeginState`. Into the state the object is in (None for no
  state) it only goes to the label: no `EndState` or `BeginState`, and the
  probes as they are, so a `Disable` in `BeginState` holds. The label is
  `Begin` when none is given; `GotoLabel` (`0x1012eb10`) clears the latent
  action, looks for the label in the state and the states above it, and
  stops the state code when none has it, logged for a named label
  (`Label not found`).
- **`Disable(name)`** (`0x1013dfb0`) clears the probe's bit until the mask
  is next set. **`Enable(name)`** (`0x1013de80`) sets it, if the state or the
  class has a function for the probe and the state does not ignore it. For
  a name that is not a probe, both only log a warning.
- **State code** is run by `Engine.dll`; `UObject::ProcessState` is empty.
- **A state frame saved** (`UObject::Serialize`, for an object with one):
  - the node whose code runs;
  - the state the object is in;
  - the probe mask (8 bytes);
  - the latent action: the number of the native polling it
    ([Engine's](engine-dll.md#latent-functions));
  - with a node, the code's offset in it; -1 for none.

  An object in no state has its class for both nodes, as `InitExecution`
  (`0x10150750`) starts the frame, every probe on. In a state (observed in
  saves), the state node is the most derived of its name, and the code node
  the state its label was found in: a pickup in `DeusExPickup.Pickup` runs
  `Inventory.Pickup`'s code.

## The natives

The rest are UE1's own. The details:

- **To a string:** a float is `%f`, a vector `%f,%f,%f`, a rotator
  `%i,%i,%i` of its parts each wrapped to 0..65535 (`0x10137550`: a pitch of
  −5691 prints as 59845), a bool the localized `True` or `False`, an object
  its path name or `None` (`0x10131f00`).
- **From a string:**
  - a bool is true for `True`, false for `False` (in any case, or the
    localized word), and otherwise true for a number other than 0
    (`0x10132490`);
  - a vector or rotator reads a number at the start, after the first comma
    and after the second; a part that is missing is 0 (`0x10136940`,
    `0x10136b10`).
- **Strings:**
  - `==`, `!=` and `<` compare with case, `~=` without; `>` is native 116.
  - `Mid(S, i, j)` (`0x1013bdf0`) takes up to 65,535 characters by default.
    A negative `i` gives an empty string: it clamps as unsigned. Its end, a
    count past the string or a negative one, is observed, not read:
    `Mid("hello", 2, -5)` is `"llo"`.
  - `Chr` and `Asc` take UTF-16 code units, as this build is Unicode;
    `Chr(0)` is the empty string (`0x1013c520`).
- **Math:**
  - an integer divided by 0 is 0 (`0x10133710`; INT_MIN / −1 is unguarded:
    the x86 divide error, a crash); a shift takes its count's low 5 bits,
    the x86 instruction's; a byte divided by 0 with
    `/=` is left as it was;
  - `Rand(n)` is 0 for `n` of 0 or less, else the C library's `rand()`
    modulo `n`, which is below 32,768;
  - `VRand` (`0x10139080`) draws points in the cube from −1 to 1 and takes
    the first inside the unit sphere, scaled to length 1: a direction with
    none favoured;
  - `Normal` (`0x10138de0`, `FVector::SafeNormal` `0x10144be0`) is zero
    under a squared length of 1e-8, a length of 0.0001; otherwise the vector
    times one over the root, in double.
- **A float made an int** -- `int(f)` (`0x10131b40`), `byte(f)`
  (`0x10131aa0`, the int's low 8 bits) and a rotator scaled by a float
  (`0x101395e0`, each angle times the float rounded to a float first) -- by
  MSVCRT's `_ftol`: truncated to 64 bits and the low 32 kept, so past an
  int's range it wraps (3e9 is −1,294,967,296); NaN, or past 64 bits, 0. An
  int scaled in place by a float, `*=` 159 (`0x10134280`) and `/=` 160
  (`0x10134370`), is `_ftol` of the product or quotient, which the x87, at
  the game's 24-bit precision, rounds to a float first (7 *= 3e9 is
  −474,836,992, 512 under the exact product's low bits); `/=` by 0.0 makes
  it 0.
- **`IsInState(S)`** (`0x1013ece0`): true for the object's state or any
  state it extends.
- **Rotators:**
  - `rotator(v)` (`FVector::Rotation`, `0x10144390`): yaw `atan2(Y, X)` and
    pitch `atan2(Z, √(X² + Y²))`, each × 65535 / 2π, truncated and not
    wrapped (straight down is −16383); roll 0.
  - `vector(r)` (`FRotator::Vector`, `0x1011d1c0`), `GetAxes` and `GetUnAxes`
    take a sine table of 16384 steps round the turn (an angle's index its
    value >> 2, so its low 2 bits are dropped), a cosine the same table a
    quarter turn (0x4000) on. `GetUnAxes` gives `GetAxes`' axes transposed.
  - `v >> r` 276 and `v << r` 275 (`0x101380e0`, `0x10137d90`) turn a
    vector by the rotator and back, by the same table: the unit coords
    turned step by step (`FCoords::operator*=`, each axis taken to its dots
    with the step's), for `<<` by the roll, then the pitch, then the yaw,
    for `>>` the yaw undone, then the pitch, then the roll; the vector then
    dotted with the coords' axes. `>>` is no inverse of a whole matrix, and
    its last float digits are its own.
  - `==` 142 and `!=` 203 (`0x10139400`, `0x101394f0`) compare every bit of
    each angle: rotators a whole turn apart are not equal.
  - `bool(r)` (`execRotatorToBool`, `0x10137060`) is true when any angle has
    a bit in its low 16: `rot(65536,0,0)` is false.
  - `OrthoRotation(X, Y, Z)` (`execOrthoRotation`, `0x1013a700`;
    `FCoords::OrthoRotation`, `0x10144830`): yaw `atan2(X.Y, X.X)` and pitch
    `atan2(X.Z, √(X.X² + X.Y²))`, each × 32768 / π made an int by `_ftol`;
    then the unit coords turned by that pitch and yaw (`FCoords /= FRotator`)
    and the roll `atan2(Z · their Y axis, Y · their Y axis)` the same way.
- **`DynamicLoadObject(ObjectName, ObjectClass, MayFail)`** (`0x1013eb30`):
  `StaticLoadObject` (`0x10154d50`), a failure logged as a warning unless
  `MayFail`. Whatever groups the name gives, the object is looked for in the
  package its first part names: that package's export of the name after the
  last `.`, of exactly the class asked for (a `Mesh` finds a `LodMesh` too),
  in any group (`ULinkerLoad::Create`, `0x10161cc0`); else an object already
  loaded of that name and class, a subclass too, right in that package. So
  `Effects.Laser.LaserBeam1`, `Effects.LaserBeam1` and
  `Effects.Wrong.LaserBeam1` are the one `FireTexture`, which a `Texture`
  asked for does not find.
- **`new(Outer, Name, Flags) Class`** (`UObject::execNew`, `0x1013d9f0`):
  `StaticConstructObject` (`0x10157ff0`) of the class under that name, in the
  outer given, or, with none, in the transient package (`GetTransientPackage`,
  `0x101573e0`): `new(Self)` on the player makes the object in its level's
  package. A flag outside the script's own (`RF_ScriptMask`, `0x704005`) is
  logged, `new: Flags %08X not allowed`, and left out. An Object of a config
  class made so (`new class'X'`, `X` with a `config` variable) hangs the game
  at exit, saved or not; one of a plain class does not (seen with the
  harness's probes, 2026-10-26; the cause unread).

## Names hashed and compared

- **`appStrihash`**, UE1's inline hash with case ignored: from 0, each UTF-16
  character, upper-cased if a to z, taken low byte then high byte into
  `h = (h >> 8) ^ GCRCTable[(h ^ byte) & 0xFF]`. `GCRCTable` is the CRC table
  of the polynomial 0x04C11DB7, most significant bit first. The event
  manager's buckets and the flag base's use it
  ([events](engine-dll.md#the-manager), [flags](extension-dll.md#flags)).
- **`appStricmp`** (`0x10123560`) is the C library's `_wcsicmp`, which folds
  A to Z to lower case: an underscore sorts before the letters.
- **The name table** (`FName::FName(Name, FindType)`, `0x1014b950`): a name is
  found in 4,096 buckets by `appStrihash`, compared with `appStricmp`, so one
  entry holds every spelling of a name, spelt as it was first made. With
  `FNAME_Find` a name not there is None; otherwise it is made, in the slot a
  deleted name left last (`FName::Available`), else in a new one at the end.
  `FNAME_Intrinsic` flags it `RF_Native`.
- **Hard-coded names** (`FName::StaticInit`, `0x1014bbc0`): None, the property
  types, the probes and the rest of `UnNames.h`, each in its fixed slot
  (`Hardcode`, `0x1014b7f0`) and `RF_Native`.
- **A name deleted** (`DeleteEntry`, `0x1014e0b0`, from the collection's
  purge): never a native one (an assert); it leaves its bucket, is freed, and
  its slot goes to `Available`.
- **An object's own name** when none is given (`MakeUniqueObjectName`,
  `0x101575b0`, from `StaticAllocateObject` and `Rename`): its class's name
  without trailing digits, then the class's count (`ClassUnique`, at +1160 in
  a `UClass`), counted up past any number an object of the same outer
  already has.
