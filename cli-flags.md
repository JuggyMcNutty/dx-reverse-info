# Command-line surface

Every flag the **`Launch` module** itself reads. Engine and driver packages parse more of
the same command line; this list is only what `DeusEx.exe` acts on.

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
and `EXEC=` (`0x1090947A`).

Each `Parse` of the line reads into a buffer of its own, in UTF-16 characters, one of them
the terminator:

| Value | Read at | Buffer |
|---|---|---|
| `INI=`, `USERINI=`, `CDPATH=` | Core.dll `appInit` `0x10149A78`, `0x10149BB0`, `0x10149DA6` | 256 |
| `LOG=` | `0x10903880` | 1,024 less the base directory's length (`0x1090384E`) |
| `ABSLOG=` | `0x109038A8` | 1,024 |
| `EXEC=`, `-consolecommand=`, `-testrendev=` | `0x1090947A`, `0x1090A635`, `0x1090A756` | 4,096, `Parse`'s `FString` form (Core.dll `0x10146DC0`) |
| `MULTIHOME=` | IpDrv.dll `getlocalhostaddr` `0x10703FBD` | 256 |

`PORT=` (IpDrv.dll `0x1070AECE`) and `PktLoss=`, `PktOrder=`, `PktDup=` and `PktLag=`
(Engine.dll) are `Parse`'s int form (Core.dll `0x10147730`): `appAtoi` of the text straight
after `X=`, nothing cut, no quote taken off. `CPUSPEED=` is its float form.

## Flags

| Flag | Parser | Read at | Effect |
|---|---|---|---|
| `-SERVER` | `ParseParam` | `0x10908D97` | clears `GIsClient`; also forces `GLazyLoad` |
| `-LAZY` | `ParseParam` | `0x10908DF4` | force lazy package loading |
| `-LOG` | `ParseParam` | `0x10908E6D` | open the log window at startup; suppresses the splash |
| `-MAKE` | `ParseParam` | `0x10908D44` | **fatal**: *"'DeusEx -make' is obsolete, use 'ucc make' now"* |
| `-firstrun` | `ParseParam` | `0x1090A26D` | force `FirstRun = 0` → full first-time wizard |
| `-safe` | `ParseParam` | `0x1090ABA9` | show the SafeMode page |
| `-changevideo` | `ParseParam` | `0x1090B23E` | show the Renderer page |
| `-nodetect` | `ParseParam` | `0x1090DAC6` | skip 3D device detection on the Renderer page |
| `-EXEC=<file>` | `Parse` | `0x1090947A` | after engine init, run `exec <file>` on viewport 0, whose `Exec` takes the file's name again by `ParseToken`, 63 characters at most (Engine.dll `0x10373A60`, `0x10374241`), so `EXEC="my file.txt"` runs `my`; `ExecMacro` logs `Execing <file>` (`0x10374700`) |
| `-consolecommand=<cmd>` | `Parse` | `0x1090A635` | run `<cmd>` through `GExec`, then **exit without launching** |
| `-testrendev=<class>` | `Parse` | `0x1090A756` | load render-device class, write `Detected.ini`, **exit** |
| `-LOG=<file>` | `Parse` | `0x10903880` | log to a named file |
| `-ABSLOG=<file>` | `Parse` | `0x109038A8` | log to an absolute path |
| `MEMSTAT` | `ParseParam` | `0x10902E41` | dump allocator statistics |

## Substring-matched tokens (`appStrfind`)

| Token | Read at | Effect |
|---|---|---|
| `Server` | `0x10908A97` | skip single-instance forwarding |
| `NewWindow` | `0x10908AB1` | skip single-instance forwarding |
| `changevideo` | `0x10908ACB` | skip single-instance forwarding |
| `TestRenDev` | `0x10908AE5`, `0x109091AB` | skip forwarding; also suppresses the splash |
| `readini` | `0x1090ABD9` | show the SafeMode page (same as `-safe`) |

## Flags the launcher *emits* (safe mode)

`WConfigPageSafeOptions__GetNext` (`0x10911C00`) re-executes the binary with a subset of
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
