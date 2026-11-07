# Command-line surface

Every flag the **`Launch` module** itself reads, and how Core's parsers read a value, the
engine's and the drivers' too; the flag tables are only what `DeusEx.exe` acts on.

Three parsers, **not** equivalent:

| Helper | Form | Matching |
|---|---|---|
| `ParseParam(cmdline, "X")` | `-X` or `/X` | flag present: the name anywhere after the line's first character with `-` or `/` just before it (Core.dll `0x10146d4f`, `0x10146d55`); nothing after it is checked, so `-log` also matches `-LOG=<file>` |
| `Parse(cmdline, "X=", out)` | `X=value` | value extraction: `X=` found as `appStrfind` finds it (`0x10146bee`), no `-` needed, so `LOG=` is not found in `ABSLOG=`; true whenever it is found, the value empty or not. The value is copied first, its buffer's length less one at most (`appStrncpy`, `0x101233c0`), past the quote of one that begins with `"`, then cut: a quoted one at its next `"`, running to the line's end with none, no escapes; any other at a space, tab, CR, LF or comma (`0x10146bc0`, `0x10146c2b`, `0x10146c4e` to `0x10146c96`); what the buffer has no room for is dropped (below) |
| `appStrfind(cmdline, "X")` | anywhere | **a substring in any case, but not straight after an ASCII letter or digit (Core.dll `0x10145ca0`); no `-` required** |

The `appStrfind` cases are the surprising ones: `readini` and the four single-instance
bypass tokens match *anywhere in the command line* not straight after an ASCII letter or
digit, inside a map name or URL too. Matching the line's `argv` words one by one does not
reproduce them.

Most checks read the command line `appInit` keeps, without the program's path. Three read
the one Windows gives, path and all: the single-instance bypass, with its four tokens, the
splash's, with `-log`, `-server` and `TestRenDev`
([`launch-flow.md`](launch-flow.md#1-single-instance-forwarding-0x10908a300x10908cd1)),
and `EXEC=` (`0x1090947a`).

Each `Parse` of the line reads into a buffer of its own, in UTF-16 characters, one of them
the terminator:

| Value | Read at | Buffer |
|---|---|---|
| `INI=`, `USERINI=`, `CDPATH=` | Core.dll `appInit` `0x10149a78`, `0x10149bb0`, `0x10149da6` | 256 |
| `LOG=` | `0x10903880` | 1,024 less the base directory's length (`0x1090384e`) |
| `ABSLOG=` | `0x109038a8` | 1,024 |
| `EXEC=`, `-consolecommand=`, `-testrendev=` | `0x1090947a`, `0x1090a635`, `0x1090a756` | 4,096, `Parse`'s `FString` form (Core.dll `0x10146dc0`) |
| `MULTIHOME=` | IpDrv.dll `getlocalhostaddr` `0x10703fbd` | 256 |

An `INI=` or `USERINI=` found empty is used as it is, the file's name empty (`appInit`), which
no file is: the file manager opens a name as given (`CreateFileW`, `DeusEx.exe` `0x10905d40`,
`0x10907000`), so `appInit`'s copy of `Default.ini` or `DefUser.ini` to it writes nothing, its
failure unchecked (Core.dll `0x10149b35`, `0x10149c66`), and the config cache reads nothing
from it and writes nothing back ([configuration](core-dll.md#configuration)). Its `Find`
(`DeusEx.exe` `0x10915e30`) adds `.ini` to a name under five characters, or with no `.` fourth
or fifth from its end, before it takes `System.ini` and `User.ini` for the two inis' names as
given, so an `INI=` of such a name is two files: `System`, the class configs' and `ini:` names'
(`ResolveName`, Core.dll `0x10154be0`), the name as given; a read or write naming no file the
name and `.ini`, an empty value where that file is not there: the launcher's own keys
(`FirstRun`, the wizard's renderer, detail and sound settings, `DescFlags`, the device's
`Description`, `CdPath`), `appInit`'s `Language` and `CdPath`, the `[URL]` section
(`FURL::StaticInit`, Engine.dll `0x103f6c50`: the protocol, the default and local maps, the
host, the portal, the map and save extensions, the port), the script's `GetConfig` (Core.dll
`0x1013e4e0`), the save's snapshot check of `GameRenderDevice` (`DDeusExGameEngine::SaveGame`,
DeusEx.dll `0x1000f3e3`), WinDrv's before DirectDraw (`UWindowsClient::Init`, WinDrv.dll
`0x11101d20`) and D3DDrv's `DescFlags` for Glide (D3DDrv.dll `0x1000afcb`); the game's start
forces its local map to `DX.dx` all the same ([starting the game
engine](engine-dll.md#starting-the-game-engine)). In Core, Engine, WinDrv, D3DDrv, IpDrv,
DeusEx.dll and `DeusEx.exe` every other read of the config cache names a file: a class's
config, `System` or `User` (`User.ini` itself names the user ini as given), a `.int`, or
IpDrv's commandlets' own; OpenGlDrv, Window and Editor, which import the cache too, are not
read here. An empty `INI=`'s are the empty name and `System\.ini`; `INI=MyMod`'s `MyMod` and
`MyMod.ini`. So an empty `USERINI=` plays with no key bindings and the classes' defaults for
the player's settings, none saved; an empty `INI=` reads no paths and no game engine class, and
`InitEngine`'s load of `ini:Engine.Engine.GameEngine` (`0x1090bb21`) ends in a critical error,
Core.int's `ConfigNotFound`, "Can't find 'ini:Engine.Engine.GameEngine' in configuration file"
(`StaticLoadClass`, Core.dll `0x10155229`), `.ini` written at the exit that follows (`appExit`,
Core.dll `0x10149f20`) when the run set a key in it. A `LOG=` found empty names
the base directory itself, an `ABSLOG=` nothing: the log's writer is not made, the device
goes dead (`0x10903971`) and the game runs without a log; a `LOG=` found decides, an
`ABSLOG=` after it unread.

`PORT=` (IpDrv.dll `0x1070aece`) and `PktLoss=`, `PktOrder=`, `PktDup=` and `PktLag=`
(Engine.dll) are `Parse`'s int form (Core.dll `0x10147730`): `appAtoi` of the text straight
after `X=`, nothing cut, no quote taken off. `CPUSPEED=` is its float form.

## Flags

| Flag | Parser | Read at | Effect |
|---|---|---|---|
| `-SERVER` | `ParseParam` | `0x10908d97` | clears `GIsClient`; also forces `GLazyLoad` |
| `-LAZY` | `ParseParam` | `0x10908df4` | force lazy package loading |
| `-LOG` | `ParseParam` | `0x10908e6d` | open the log window at startup; suppresses the splash |
| `-MAKE` | `ParseParam` | `0x10908d44` | **fatal**: *"'DeusEx -make' is obsolete, use 'ucc make' now"* |
| `-firstrun` | `ParseParam` | `0x1090a26d` | force `FirstRun = 0` → full first-time wizard |
| `-safe` | `ParseParam` | `0x1090aba9` | show the SafeMode page |
| `-changevideo` | `ParseParam` | `0x1090b23e` | show the Renderer page |
| `-nodetect` | `ParseParam` | `0x1090dac6` | skip 3D device detection on the Renderer page |
| `-EXEC=<file>` | `Parse` | `0x1090947a` | after engine init, run `exec <file>` on viewport 0, whose `Exec` takes the file's name again by `ParseToken`, 63 characters at most (Engine.dll `0x10373a60`, `0x10374241`), so `EXEC="my file.txt"` runs `my`; `ExecMacro` logs `Execing <file>` (`0x10374700`) and runs the file's lines as `ParseLine` cuts them ([a key's binding](engine-dll.md#a-keys-binding)) |
| `-consolecommand=<cmd>` | `Parse` | `0x1090a635` | run `<cmd>` through `GExec`, then **exit without launching** |
| `-testrendev=<class>` | `Parse` | `0x1090a756` | load render-device class, write `Detected.ini`, **exit** |
| `-LOG=<file>` | `Parse` | `0x10903880` | log to a named file |
| `-ABSLOG=<file>` | `Parse` | `0x109038a8` | log to an absolute path |
| `MEMSTAT` | `ParseParam` | `0x10902e41` | dump allocator statistics |

## Substring-matched tokens (`appStrfind`)

| Token | Read at | Effect |
|---|---|---|
| `Server` | `0x10908a97` | skip single-instance forwarding |
| `NewWindow` | `0x10908ab1` | skip single-instance forwarding |
| `changevideo` | `0x10908acb` | skip single-instance forwarding |
| `TestRenDev` | `0x10908ae5`, `0x109091ab` | skip forwarding; also suppresses the splash |
| `readini` | `0x1090abd9` | show the SafeMode page (same as `-safe`) |

## Flags the launcher *emits* (safe mode)

`WConfigPageSafeOptions__GetNext` (`0x10911c00`) re-executes the binary with a subset of
these. The engine and drivers read them, not `Launch`:

| Flag | Read by | Effect |
|---|---|---|
| `-nosound` | `Engine.dll`, `UEngine::InitAudio` | no audio subsystem: no sound, no music ([`engine-dll.md`](engine-dll.md#starting-the-game-engine)) |
| `-no3dsound` | `Galaxy.dll`, `Init` | no A3D or EAX sound hardware ([`galaxy-dll.md`](galaxy-dll.md#settings)) |
| `-nohard` | `WinDrv.dll`, `UWindowsViewport::OpenWindow` | the software renderer instead of `GameRenderDevice` ([`windrv-dll.md`](windrv-dll.md#the-flags)) |
| `-noddraw` | `WinDrv.dll`, `UWindowsClient::Init` | no DirectDraw: the software renderer, when it is the one used, has no fullscreen mode and runs in a window ([`windrv-dll.md`](windrv-dll.md#the-flags)) |
| `-defaultres` | `WinDrv.dll`, `UWindowsClient::Init` | 640×480, windowed and fullscreen ([`windrv-dll.md`](windrv-dll.md#the-flags)) |
| `-nommx`, `-nokni`, `-nok6` | `Core.dll`, `appPlatformInit` | the CPU's MMX, KNI (SSE) and 3DNow! left unused ([`core-dll.md`](core-dll.md#the-platforms-start)) |
| `-nojoy` | `WinDrv.dll`, `UWindowsClient::PostEditChange` | no joystick ([`windrv-dll.md`](windrv-dll.md#the-flags)) |

Which checkbox drives which flag, and the three that drive none:
[the shipped bug](wizard.md#-shipped-bug-three-safe-mode-checkboxes-are-dead).

The SafeMode page's Run goes on with the command line the run was given. When `-safe` opened
the page, that keeps `-safe`, which `WinDrv.dll` reads too: no DirectInput
([`windrv-dll.md`](windrv-dll.md#the-flags)). Opened by a stale `Running.ini` (RecoveryMode)
or by `readini`, the run has no `-safe`.
