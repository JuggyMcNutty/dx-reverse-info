# Command-line surface

Every flag the **`Launch` module** itself reads. Engine/driver packages parse more from
the same command line; this list is only what `DeusEx.exe` acts on.

Three different parsers are used, and they are **not** equivalent:

| Helper | Form | Matching |
|---|---|---|
| `ParseParam(cmdline, "X")` | `-X` | flag present, leading `-` required |
| `Parse(cmdline, "X=", out)` | `-X=value` | value extraction |
| `appStrfind(cmdline, "X")` | anywhere | **raw substring, no `-` required** |

The `appStrfind` cases are the surprising ones: `readini` and the four
single-instance bypass tokens match *anywhere in the command line*, including inside
a map name or URL.

Most checks read the command line `appInit` keeps, without the program's path. Three
read the one Windows gives, path and all: the four bypass tokens, and the splash's
`-log`, `-server` and `TestRenDev` ([`launch-flow.md`](launch-flow.md#1-single-instance-forwarding-0x10908a300x10908cd1)).

## Flags

| Flag | Parser | Read at | Effect |
|---|---|---|---|
| `-SERVER` | `ParseParam` | `0x10908D97` | `GIsClient = 0`; also forces `GLazyLoad` |
| `-LAZY` | `ParseParam` | `0x10908DF4` | force lazy package loading |
| `-LOG` | `ParseParam` | `0x10908E6D` | open the log window at startup; suppresses the splash |
| `-MAKE` | `ParseParam` | `0x10908D44` | **fatal** — *"'DeusEx -make' is obsolete, use 'ucc make' now"* |
| `-firstrun` | `ParseParam` | `0x1090A26D` | force `FirstRun = 0` → full first-time wizard |
| `-safe` | `ParseParam` | `0x1090ABA9` | show the SafeMode page |
| `-changevideo` | `ParseParam` | `0x1090B23E` | show the Renderer page |
| `-nodetect` | `ParseParam` | `0x1090DAC6` | skip 3D device detection on the Renderer page |
| `-EXEC=<file>` | `Parse` | `0x1090947A` | after engine init, run `exec <file>` in the client console |
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

`WConfigPageSafeOptions__GetNext` (`0x10911C00`) re-executes the binary with a
subset of these. They are consumed by the engine and drivers, not by `Launch`:

| Flag | Read by | Effect |
|---|---|---|
| `-nosound` | `Engine.dll`, `UEngine::InitAudio` | no audio subsystem: no sound, no music ([`engine-dll.md`](engine-dll.md#starting-the-game-engine)) |
| `-no3dsound` | `Galaxy.dll`, `Init` | no A3D or EAX sound hardware ([`galaxy-dll.md`](galaxy-dll.md#settings)) |
| `-nohard` | `WinDrv.dll`, `UWindowsViewport::OpenWindow` | the software renderer instead of `GameRenderDevice` ([`windrv-dll.md`](windrv-dll.md#the-flags)) |
| `-noddraw` | `WinDrv.dll`, `UWindowsClient::Init` | no DirectDraw: the software renderer, when it is the one used, has no fullscreen mode and runs in a window |
| `-defaultres` | `WinDrv.dll`, `UWindowsClient::Init` | 640×480, windowed and fullscreen |
| `-nommx`, `-nokni`, `-nok6` | `Core.dll`, `appPlatformInit` | the CPU's MMX, KNI (SSE) and 3DNow! left unused ([`core-dll.md`](core-dll.md#the-platforms-start)) |
| `-nojoy` | `WinDrv.dll`, `UWindowsClient::PostEditChange` | no joystick |

See the shipped-bug note in [`wizard.md`](wizard.md) — in the original, only
`-nosound`, `-nommx -nokni -nok6` and `-nojoy` are driven by their own checkbox.

A run the SafeMode page's Run button starts keeps `-safe` on its command line,
and `WinDrv.dll` reads that too: no DirectInput ([`windrv-dll.md`](windrv-dll.md#the-flags)).
