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

- **`Identical`**, each property class's own (vtable `+0x6C`), is how two
  values are taken for the same, a missing second one counting as zero: by a
  save, against the class's defaults (`UObject::Serialize` `0x10150210`,
  `SerializeTaggedProperties` `0x10126730`: a value `Identical` to its
  default is not written, and loads as the default); by the travel's export
  (`UProperty::ExportText` `0x10165440`, which writes nothing for one);
  by replication ([network.md](network.md#replication)); by a struct's `==`
  and `!=` (`0x101303a0`, `0x101305a0`), member by member. By type: a string
  (`0x101676f0`) by `appStricmp`, an empty or missing one `""`, so strings
  apart in case alone are the same, where the script's `==` is `appStrcmp`
  (`0x1013b560`); a struct (`0x101690d0`) each member; a fixed array
  (`0x10167d30`) and a dynamic one (`0x10168480`, the counts first) each
  element; a map (`0x10168d80`) always the same.
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

- **A string's bytes** (`FString`'s `<<`, `0x101459b0`): a compact count
  with the terminator, then the characters; on a save, negative and 16-bit
  characters when one before the terminator is past 0xFF, else positive and
  a byte each (Latin-1); on a load, the count's sign says which, and a string
  of the terminator alone is made empty. So a note typed past Latin-1 is
  saved wide and every other string of a save as 8-bit.
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
  - A name's trailing spaces and dots are dropped by Windows' file system as
    it opens the file, not by the search: Mission 14's five travels with a
    space before their `#` (`14_OceanLab_Lab.dx #Sunkenlab`) look for
    `14_OceanLab_Lab.dx ` and open `14_OceanLab_Lab.dx`.
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

- **A tagged property the class cannot take**
  (`UStruct::SerializeTaggedProperties`, `0x10126730`) is logged and its bytes
  skipped, the object loading on: a name no property has (`Property %s of %s not
  found`), another type (`Type mismatch in %s of %s: file %i, class %i`), an
  element past the static array (`Array bounds in %s of %s: %i/%i`), another
  struct (`Property %s of %s struct type mismatch %s/%s`), a native or, on a
  persistent archive, transient property (`Property %s of %s is not
  serialiable`, sic); each skip logs `Skipping %i bytes of type %i`, but for
  `XLevel`. A struct's binary (`UStruct::SerializeBin`, `0x10126610`) is every
  member of it, its own first, then those of the structs it extends (no Plane
  case in `SerializeItem`, `0x101691b0`: a Plane's W, X, Y, Z), native members
  left out and transient ones on a persistent archive, every element of a static
  array member; a dynamic array's (`UArrayProperty::SerializeItem`,
  `0x10168520`) its count then each element's.

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
  - Of a key given twice in a section the last is read, even empty: a user ini's
    second, empty `ngWorldSecret=` beats a first with a value. A line
    (`FConfigFile::Read`, DeusEx.exe `0x10916780`) is its key up to the first
    `=`, nothing trimmed, a value's quotes taken off as it is read.
  - The file's bytes (`appLoadFileToString`, `0x101488c0`): a file of even
    size beginning `FF FE` is UTF-16 little-endian, one beginning `FE FF`
    big-endian, each unit a character and the byte-order mark dropped; any
    other file is read byte by byte, each byte a character (Latin-1). So an
    ini Notepad saved as "Unicode" reads as the 8-bit one does.
  - A file written (`appSaveStringToFile`, `0x10148c40`): a byte a character, as
    `ToAnsi` narrows one, when every character is below 0x100; else UTF-16
    little-endian, the byte-order mark `FF FE` first. So an ini or `.int`
    holding a character past Latin-1 is saved as UTF-16, every other as 8-bit;
    an ini is written whole, CR LF.
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
  (`0x1013e0b0`, `0x1013e320`): a property of the object's class by its name,
  the class's own before its base's, so one a subclass names again is the
  subclass's (`0x10143fd0`), read only when it is public (a script's `private`
  one is not), its first element as `GET` writes it, and set only when it is
  public and not const; any other name reads empty and sets nothing. The
  server's query answerer (`IpServer`'s `UdpServerQuery`) reads the level's, the
  game's and the players' properties a remote names through it.
- **The console's `GET` and `SET`** (`UObject::StaticExec`, `0x10153110`),
  with which the game's menus read and write their settings:
  - The class is found by its name in any package loaded (the menus name
    `DeusExMPGame`, `DXMapList`, `Player`, not their packages); the property
    by its name, once, on that class, its own before its base's
    (`0x10143fd0`), else `Unrecognized class/property` is logged.
  - `GET` gives the class default's first element as the ini writes it,
    with no quotes: a string bare; an object its class and path name
    (`Texture'Engine.S_Actor'`) or `None`; a bool `True` or `False`; an enum
    byte its value's name.
  - `SET` takes the rest of the line, spaces and all, as the value
    (`GlobalSetProperty`, `0x101523a0`). Every object of the class or a
    subclass reads it at that property's place, each then told of the change
    (`PostEditChange`); then the class's defaults; then the class's config is
    saved. So `SET Actor bSinglePlayer` sets `Actor`'s in a `PlayerPawn` too,
    and `SET PlayerPawn bSinglePlayer` the player's own.

### A property's text

The text a property is read from and written to -- an ini's value, a `.int`
file's, `SET` and `GET`, `SetPropertyText` and `GetPropertyText`, a travel's --
by each property class's `ImportText` and `ExportTextItem`:

- **A struct** (`UStructProperty::ImportText`, `0x101698b0`):
  `(key=value,key[i]=value,...)`; a key up to 63 characters, an element index in
  brackets, `=` (`Illegal or missing key name`); the member found by name among
  the struct's and the structs it extends, within its dimension, and given the
  text to import delimited; a key no member has is skipped to the next `,` or
  `)` at depth 0, a quoted string whole (`Bad quoted string`), nested
  parentheses counted (`Bad parenthesised struct`,
  `Incomplete parenthesised struct`); then `,` or `)` (`Bad termination`).
  Members not named keep their values. The index reader is broken: it starts on
  the `[` itself, finds no `]` there, logs `ImportText: Illegal array element`
  and fails the import at that key (the members before it set), so `N[1]=7` is
  never read -- though the export writes it (DXEngine's `TextConsole`). Out
  (`ExportTextItem`, `0x10169710`): `(` + each portable member, the struct's own
  first, then the extended struct's (a Plane's W before X, Y, Z), each element
  of a static array as `Name[i]=`, joined by `,`, + `)` -- nothing at all when
  no member prints.
- **A string** (`UStrProperty::ImportText`, `0x10167980`): delimited, one token
  by the token reader (`0x10164cb0`): a quoted string's content, `\\` a
  backslash and `\xx` a hex byte, or a bare run of letters, digits, `_` and `-`,
  else one character; undelimited, the text whole. Out (`0x101678a0`): quoted
  when delimited, bare otherwise.
- **A dynamic array** (`UArrayProperty::ImportText`, `0x10168830`): `(a,b,...)`,
  the array emptied and each element's delimited text imported; out
  (`0x10168720`) the elements' text joined by `,` in parentheses.
- **An object** (`UObjectProperty::ImportText`, `0x10166e20`): `None`;
  `Type'Name'`, the class `Type` found among the loaded (`StaticFindObject` in
  any package) and the object by `Name` among its loaded instances, a path or a
  bare name; else the name among the property class's loaded objects. Nothing
  found leaves None. Out (`0x10166d40`): `Type'Package.Group.Name'` or `None`.
  **A class** (`UClassProperty::ImportText`, `0x10167110`): the object's import,
  then None unless a class deriving from the metaclass; out as an object's.
- **A bool** (`0x10166380`): `1`, `True` or the localized true word; `0`,
  `False` or the localized false, as its first token (the token reader, above),
  so `True,`, `1.0` and a quoted `"True"` are true; any other fails, the value
  kept. **An enum** (`0x10165aa0`): its first token, by the enum's names alone,
  never a number. **An int** (`0x10165f00`): from a `-` or a digit alone, so
  `+5` sets nothing.
- **`SaveConfig`** (`UObject::SaveConfig`, `0x10151540`): for each property with
  the flags asked, under the class's path as its section (the declaring class's
  for a `globalconfig` one, the object's name for a per-object config class): a
  dynamic array has the section's lines of its name removed and one
  `Name=element` line written per element; a map's lines are removed; anything
  else is one key, `Name` or `Name[i]`, its text exported undelimited (a string
  bare, a struct's members quoted within); the config cache is flushed to disk
  at once, and every class deriving from the config class re-reads its defaults.

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
- **A string constant** (`execStringConst`, `0x10130890`) is 8-bit text, each
  byte widened to a character (`appFromAnsi`, `0x1014a0c0`, into a ring of
  256 buffers of 1,024, `0x10145c60`), at most 1,023 of them; a Unicode one
  (`0x10130990`) is taken as it is. The compiler writes 8-bit when every
  character is below 0x100 (`appIsPureAnsi`, `0x10145b30`). 0x5A has no
  handler.
- **A cast** (`DynamicCast`, `0x10130ed0`) and `UObject::IsA`
  (`0x101155f0`) compare the very class up its `SuperField` chain, a null
  class passing any object, so a class of another's name in another package
  is not it; the script's `IsA(name)` (`0x1013ee60`) compares by name.
  `AllObjects` (`0x1013f1f0`), `Engine.dll`'s iterators, `StaticFindObject`
  (`0x10151de0`) and a spawn's notifications test a class the same way.
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
  instance and default ones, `0x1012ec60`, `0x1012ed00`) leaves the
  variable's address in a global, `GPropAddr`, and copies its value only
  when given a buffer, whole, each element of a static array
  (`CopyCompleteValue`, vtable `+0x90`). An element (`ArrayElement`,
  `0x1012ef90`) steps its index first and copies one (`CopySingleValue`,
  `+0x8C`); a member (`StructMember`, `0x1012f3d0`) copies the struct into a
  zeroed buffer of its own and takes the member from there.
- **`Let`** (`0x1012fe40`) evaluates its left side with no buffer, for the
  address alone, and its right side straight into the variable: no
  temporary. Through `None` it writes to a scratch variable, with a warning.
  It takes every type but bool. **`LetBool`** (`0x1012ff30`) evaluates the
  value into a zeroed int of its own and sets or clears the bit by it.
- **Calls** (`CallFunction`, `0x1013f4e0`) take each argument as they come
  to it, a later one that changes a variable leaving the earlier copy as it
  was:
  - a native is called directly and reads its own arguments from the
    caller's code, each with a `Step` into a value of its own
    (`execAdd_IntInt` `0x101337f0`, `execConcat_StringString` `0x1013aa70`:
    `I + Bump(I)`, `Bump` setting its `out` `I` to 10, is 1); an `out` one is
    read and written through `GPropAddr` once every argument is stepped
    (`execAddEqual_IntInt` `0x10134480`: `I += Bump(I)` is 10);
  - a script function gets a frame on the machine stack (`alloca`: its
    parameters and locals, zeroed). Each argument is evaluated from the
    caller's code straight into its parameter, up to `EndFunctionParms`, an
    `out` one's value too, so the function starts with the variable as it
    was then. An `out` argument's address is kept and its value copied back
    after the call, after the return value is written, the last first: an `out`
    argument that is also the variable assigned ends with the parameter's
    value, through a `return` of the call too (the return steps the call
    into its caller's buffer), and of two `out` arguments given one variable
    the first's. A native writes its `out` arguments through their addresses
    in its own order: the post-increment and post-decrement natives
    (`0x101347e0`, `0x101348a0`, the byte ones `0x10133290`, `0x10133350`)
    write their result before they step the variable, so `I = I++` ends
    stepped. Strings and arrays among the locals are freed.
- **Virtual calls** (`VirtualFunction`, `0x101301e0`) look the function up by
  name in a hash of 256 buckets, keyed on the low byte of the name's index:
  the current state's first (its own, then the state it extends or
  overrides, up that chain), then the class's (`FindObjectField`,
  `0x10150b50`). A final call carries the function itself.
- **Running a function** (`ProcessInternal`, `0x1013f690`): tokens up to
  `Return`, then the return value evaluated into the caller's buffer. Every
  function's code ends in a `Return` with `Nothing`, which writes nothing
  (`execNothing`, `0x10102095`), so a function with a return value that
  runs off its end leaves the caller's buffer as it was. A `singular`
  function does not run while any singular function of its object does:
  the object holds one flag, bit `0x20` of its `ObjectFlags`
  (`FUNC_Singular`'s own value; the SDK's `RF_InSingularFunc`, `0x800`, goes
  unused). A call of a function named after a probe whose bit is clear, and
  one sent to the other side of a net game, are held off too. A call held
  off, or ended without a value, writes nothing: a variable assigned from
  it keeps its value, but a bool, which `LetBool` clears. What else takes a
  result has set its buffer first: a condition, a context's object, a
  cast, a conversion, a struct's member and a script function's parameter
  to zero, so they read zero; a native's optional parameter to its
  default, so it takes that as though left out (`Spawn`'s place the
  spawner's, `Trace`'s start the tracer's); a native's vector or struct
  parameter not at all, so it reads what the stack held. A `return f()`
  hands the caller's buffer on. A 251st nested script function stops the
  game ("Infinite script recursion (250 calls) detected"), the events
  called from C++ counted with the rest.
- **`a.b` with `a` `None`** (`Context`, `0x101300d0`): a warning ("Accessed
  None"), `b` skipped by a size stored inline, and a zero result.
- **`switch`** (`execSwitch`, `0x1012f850`): the condition stepped once into
  a buffer of its own, so a case's call that changes its variable leaves it
  as it was, then each case's value compared with it -- a string by `appStricmp`, without regard
  to case; any other type by `appMemcmp` over the switch's size, so a float
  by its bits (−0.0 is not 0.0).
- **A struct's `==` and `!=`** (`0x101303a0`, `0x101305a0`): each struct
  stepped into a zeroed buffer of its own, then each member compared by its
  [`Identical`](#packages-and-linkers).
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
- **The mask is set at every `UObject::GotoState`** (`0x1012e8f0`), even into
  the state the object is in: the probes that the state or the class has a
  function for, less those the state `ignores`. With no state frame it does
  nothing; else it first clears the latent action. The state is found by
  `FindState` (`0x10150c80`), in the state's fields and the class's, a
  class's own name never one; none found is no state, the class the node.
  Into another state, its name compared, it first sends `EndState`, if its
  probe is on, under `RF_InEndState` (`0x2000`; not from within one),
  `RF_StateChanged` (`0x1000`) cleared before and tested after: a `GotoState`
  finished during it sets the flag, and this one then returns preempted (2),
  its state and label never taken. The node set, its code cleared, the mask
  that of the node and the class. One to no state, or to a state the class
  has not, then returns 0 without the flag, so made during an `EndState` it
  preempts nothing and the outer one goes on into its state. Into a state,
  `BeginState` is sent the same way; then `RF_StateChanged` is set, and it
  returns 1.
- **A script's `GotoState`** (`execGotoState`, `0x1013dd00`) calls it only
  for another state than the object's (one left out is the object's own),
  the object's here None in no state; then goes to the label only for the
  object's own state or a return of 1, never one preempted or not found. Into
  the state the object is in it only goes to the label: no `EndState` or
  `BeginState`, and the probes as they are, so a `Disable` in `BeginState`
  holds. The label is `Begin` when none is given; `GotoLabel` (`0x1012eb10`)
  clears the latent action, looks for the label in the state and the states
  above it, and stops the state code when none has it. `execGotoState` logs
  `GotoState (<state> <label>): State not found` for a return of 0 to a name
  not None or `Auto`, and `Label not found` for a named label not found.
- **`GetStateName()`** (native 284, `0x1013edb0`) is the state frame's node's
  name: in no state the class's, None for an object with no frame.
  **`IsInState(S)`** (`0x1013ece0`) walks that node and the ones above it,
  in no state the class and its supers. Every actor has a frame, and the
  console: `InitExecution` (`0x10150750`) makes one, in no state, every probe
  on, from `Engine.dll`'s map load, `SpawnActor` and the console's
  initialization; an object made by `new` has none.
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

- **To a string:** a float is `%f`, a vector `%f,%f,%f` -- the MSVC
  runtime's `%f`: every digit exact to six decimals, a tie at the sixth
  rounding up (813.1953125 is `813.195313`), 2 to the 70th written whole,
  infinity `1.#INF00` --, a rotator
  `%i,%i,%i` of its parts each wrapped to 0..65535 (`0x10137550`: a pitch of
  −5691 prints as 59845), a bool the localized `True` or `False`, an object
  its path name or `None` (`0x10131f00`).
- **From a string:**
  - a bool is true for `True`, false for `False` (in any case, or the localized
    word), and otherwise true for an int other than 0, by `appAtoi`
    (`0x10132490`), so `0.5`, `-0.5` and `0x1` are false;
  - an int, a byte (the int's low 8 bits: `300` is 44) and a rotator's three
    angles are `appAtoi`'s too (`0x10132320`, `0x101321b0`, `0x10136b10`).
    `appAtoi` (`0x101235b0`) is MSVCRT's `_wtoi`: blanks and a sign first,
    then the digits up to the first that is not one, 0 without any; under
    Proton a number past an int's range is held to its ends (`2147483648` is
    2147483647, `-2147483649` is −2147483648: DXEngine's `SweepVmConsole`);
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
  - `VSize` (`0x10138d10`) and `Dot` (`0x10138630`) sum Z's and Y's terms
    first, then X's, at the tick's precision; `Dot` stores once as a float,
    `VSize` the sum as a double for `appSqrt` (`0x10123290`, an `fsqrt` at
    that precision) and the root as a float. `Lerp` (`0x10136610`) is
    (B − A) × Alpha + A, stored once;
  - `Normal` (`0x10138de0`, `FVector::SafeNormal` `0x10144be0`) is zero
    under a squared length of 1e-8, a length of 0.0001; otherwise the vector
    times one over the root, at the x87's precision (24 bits in a console's
    tick: [render-dll.md](render-dll.md#lighting), in floats), each axis
    stored as a float: the squares summed X's and Y's first, then Z's, the
    sum stored as a double for `appSqrt`'s `fsqrt`, one over it an `fdivr`.
    In a console's tick two of three normals stand a last bit from a
    double's (DXEngine's `SweepVmConsole`).
- **A float made an int** -- `int(f)` (`0x10131b40`), `byte(f)`
  (`0x10131aa0`, the int's low 8 bits) and a rotator times a float
  (`0x101395e0`, `0x101396d0`, `*=` `0x101398b0`: each angle times the float
  at the x87's precision, rounded to 24 bits in a console's tick, whole in
  the level's) or over one (`0x101397c0`, `/=` `0x101399c0`: each angle
  times one over the float, `fdivr` of 1.0, so at 64 bits a whole quotient
  can come out one under: rot(90, 0, 0) / 90 is (0, 0, 0) in the level's
  tick) -- by
  MSVCRT's `_ftol`: truncated to 64 bits and the low 32 kept, so past an
  int's range it wraps (3e9 is −1,294,967,296); NaN, or past 64 bits, 0. An
  int scaled in place by a float, `*=` 159 (`0x10134280`) and `/=` 160
  (`0x10134370`), is `_ftol` of the product or quotient as the x87 holds
  it: at 24 bits, in a console's tick ([render-dll.md](render-dll.md#lighting),
  in floats), rounded to a float first (7 *= 3e9 is −474,836,992, 512 under
  the exact product's low bits: DXEngine's `OpsConsole`); in the level's
  tick, at 64, exact (−474,836,480: DXEngine's `PrecisionConsole`, an actor's own tick);
  `/=` by 0.0 makes it 0.
- **`IsInState(S)`** (`0x1013ece0`): true for the object's state or any
  state it extends; in no state, for its class or any class above it.
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
  `StaticConstructObject` (`0x10157ff0`) of the class under that name, in its
  outer: the calling object, which the outer given, None too, takes the place
  of, the transient package for None or a caller outside the object table (a
  class's defaults; `GetTransientPackage`, `0x101573e0`). So `new class'X'`
  makes the object in the caller and `new(None)` in the transient package:
  `new(Self)` on the player makes the object in its level's package. A flag outside the script's own (`RF_ScriptMask`, `0x704005`) is
  logged, `new: Flags %08X not allowed`, and left out. An Object of a config
  class made so (`new class'X'`, `X` with a `config` variable) hangs the game
  at exit, saved or not; one of a plain class does not (seen with the
  harness's probes; the cause unread).

## Names hashed and compared

- **`appStrihash`**, UE1's inline hash with case ignored: from 0, each UTF-16
  character, upper-cased if a to z, taken low byte then high byte into
  `h = (h >> 8) ^ GCRCTable[(h ^ byte) & 0xFF]`. `GCRCTable` is the CRC table
  of the polynomial 0x04C11DB7, most significant bit first. The event
  manager's buckets and the flag base's use it
  ([events](engine-dll.md#the-manager), [flags](extension-dll.md#flags)).
- **`appStricmp`** (`0x10123560`) is the C library's `_wcsicmp`, which folds
  A to Z to lower case: an underscore sorts before the letters. No module of
  the game sets a locale (none imports `setlocale`), so A to Z alone fold,
  every other character as it is.
- **The name table** (`FName::FName(Name, FindType)`, `0x1014b950`): a name is
  found in 4,096 buckets by `appStrihash`, compared with `appStricmp`, so one
  entry holds every spelling of a name, spelt as it was first made. A
  package's linker makes every name of its table at its load (`0x10160553`),
  so the first package loaded fixes a name's text: DeusEx.u's `annadies` for
  the conversations' `AnnaDies`; `string(name)` (`execNameToString`,
  `0x101320b0`) gives the entry's. With
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
