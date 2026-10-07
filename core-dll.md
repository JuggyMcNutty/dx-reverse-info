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

## Garbage collection

An object stays while it is reachable from the root set; everything else is
destroyed, then deleted. Nothing is reference-counted. The game engine
collects at each map load but Entry's ([`Engine.dll`](engine-dll.md#the-map-loads-collection));
the console's `OBJ GARBAGE` collects at once, keeping what is native (and, in
the editor, what is standalone), even under `-NOGC`.

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

**The purge** (`PurgeGarbage`, `0x101581f0`), unless `-NOGC` (`Not purging
garbage`); it logs `Purging garbage`, with `GObjInGarbageCollection` set:

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
  - Of a key given twice in a section the last is read, even empty: a user
    ini's second, empty `ngWorldSecret=` beats a first with a value.
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
([Galaxy](galaxy-dll.md#hardware-and-the-console)). Whether another DLL
reads them is not checked.

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
  the current state's first, then the class's (`FindObjectField`,
  `0x10150b50`). A final call carries the function itself.
- **Running a function** (`ProcessInternal`, `0x1013f690`): tokens up to
  `Return`, then the return value evaluated into the caller's buffer. A
  `singular` function does not run while it already is. A 251st nested call
  stops the game ("Infinite script recursion").
- **`a.b` with `a` `None`** (`Context`, `0x101300d0`): a warning ("Accessed
  None"), `b` skipped by a size stored inline, and a zero result.

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
- **The mask is set at every `GotoState`** (`0x1012e8f0`), even into the
  state the object is in: the probes that the state or the class has a
  function for, less those the state `ignores`.
- **`Disable(name)`** (`0x1013dfb0`) clears the probe's bit until the next
  `GotoState`. **`Enable(name)`** (`0x1013de80`) sets it, if the state or the
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
  - `Chr` and `Asc` take UTF-16 code units, as this build is Unicode.
- **Math:**
  - an integer divided by 0 is 0 (`0x10133710`); a byte divided by 0 with
    `/=` is left as it was;
  - `Rand(n)` is 0 for `n` of 0 or less, else the C library's `rand()`
    modulo `n`, which is below 32,768;
  - `VRand` (`0x10139080`) draws points in the cube from −1 to 1 and takes
    the first inside the unit sphere, scaled to length 1: a direction with
    none favoured;
  - `Normal` of a zero vector is zero.
- **Rotators:**
  - `rotator(v)` (`FVector::Rotation`, `0x10144390`): yaw `atan2(Y, X)` and
    pitch `atan2(Z, √(X² + Y²))`, each × 65535 / 2π, truncated and not
    wrapped (straight down is −16383); roll 0.
  - `vector(r)` (`FRotator::Vector`, `0x1011d1c0`), `GetAxes` and `GetUnAxes`
    take a sine table of 16384 steps round the turn (an angle's index its
    value >> 2, so its low 2 bits are dropped), a cosine the same table a
    quarter turn (0x4000) on. `GetUnAxes` gives `GetAxes`' axes transposed.

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
