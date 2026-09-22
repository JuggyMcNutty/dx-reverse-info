# Configuration surface

Every ini read/write performed by `DeusEx.exe`. Resolved from `GConfig` vtable call
sites against the `FConfigCache` interface in `Core/Inc/Core.h:195`.

> **Vtable caveat.** MSVC emits overload *groups* in reverse declaration order, so
> `GetString(FString&)` sits at **+12** and `GetString(TCHAR*, INT)` at **+16** — the
> opposite of the header. Every entry below was confirmed by argument arity and types
> at the call site, not by index arithmetic.

Offsets: `+0 GetBool`, `+4 GetInt`, `+8 GetFloat`, `+12 GetString(FString&)`,
`+16 GetString(buf)`, `+20 GetStr`, `+24 GetSection`, `+32 EmptySection`,
`+36 SetBool`, `+40 SetInt`, `+48 SetString`, `+52 Flush`.

## Read

| Section | Key | Op | Address | Purpose |
|---|---|---|---|---|
| `FirstRun` | `FirstRun` | GetInt | `0x1090A252` | version gate: 220 / 400 / 1100 |
| `Engine.Engine` | `CdPath` | GetString | `0x1090B9CE` | CD presence check |
| `Engine.Engine` | `GameRenderDevice` | GetStr | `0x1090EBB7` | current renderer, for detail tuning |
| *(render class)* | `DescFlags` | GetInt | `0x1090CFC3`, `0x1090ECA1` | device capability bits |
| `D3DDrv.D3DRenderDevice` | `Description` | GetStr | `0x109103D7` | card name on the Driver page |
| `UnrealShare.UnrealSlotMenu` | `SlotNames[%i]` | GetStr (file `User`) | `0x1090A4AB` | savegame migration |

## Write

| Section | Key | Value | Address |
|---|---|---|---|
| `FirstRun` | `FirstRun` | clamped up to `1100` | `0x1090B997` |
| `Engine.Engine` | `GameRenderDevice` | chosen renderer class | `0x1090E671` |
| *(render class)* | `DescFlags` | `2` | `0x1090A86D` (then `Flush`, `0x1090A886`) |
| `UnrealShare.UnrealSlotMenu` | `SlotNames[%i]` | `"Saved game"` (file `User`) | `0x1090A560` |

### Detail auto-configuration — `WConfigPageDetail__OnInitDialog` (`0x1090EB50`)

Written when the Detail page initialises, based on detected renderer and hardware:

| Section | Key | Value | Address |
|---|---|---|---|
| `WinDrv.WindowsClient` | `MinDesiredFrameRate` | `1` — two call sites, same value (see below) | `0x1090ED2C`, `0x1090ED9E` |
| `Galaxy.GalaxyAudioSubsystem` | `UseReverb` | `False` | `0x1090EF28` |
| `Galaxy.GalaxyAudioSubsystem` | `OutputRate` | `11025Hz` | `0x1090EF4E` |
| `Galaxy.GalaxyAudioSubsystem` | `UseSpatial` | `False` | `0x1090EF73` |
| `Galaxy.GalaxyAudioSubsystem` | `UseFilter` | `False` | `0x1090EF98` |
| `Galaxy.GalaxyAudioSubsystem` | `LowSoundQuality` | SetBool | `0x1090EFBA` |
| `WinDrv.WindowsClient` | `SkinDetail` | `Medium` | `0x1090F23B` |
| `WinDrv.WindowsClient` | `TextureDetail` | `Medium` | `0x1090F4D8` |
| `WinDrv.WindowsClient` | `WindowedViewportX` / `Y` | `640` / `480` | `0x1090F59C`, `0x1090F5C2` |
| `WinDrv.WindowsClient` | `WindowedColorBits` | `16` | `0x1090F5E7` |
| `WinDrv.WindowsClient` | `FullscreenViewportX` / `Y` | `640` / `480` | `0x1090F60C`, `0x1090F631` |
| `WinDrv.WindowsClient` | `FullscreenColorBits` | `16` | `0x1090F656` |

> **Correction.** This table previously described `MinDesiredFrameRate` as
> *per-renderer*, on the strength of there being two call sites. There are two
> call sites but only one value: both `push offset a1` where `a1` is the string
> `"1"`. Read from the disassembly at `0x1090ED0C` and `0x1090ED7E`.
>
> The condition, from `WConfigPageDetail__OnInitDialog`, is a single `if` with
> three alternatives — software renderer, a slow CPU, or Direct3D:
>
> ```c
> if (renderer == "SoftDrv.SoftwareRenderDevice"
>     || 280000000.0 * GSecondsPerCycle > 1.0      /* below ~280 MHz */
>     || renderer == "D3DDrv.D3DRenderDevice")
>     GConfig->SetString("WinDrv.WindowsClient", "MinDesiredFrameRate", "1");
> ```
>
> The shipped default is `1.0`, so the write is still a real change. Nothing
> else in the detail block is renderer-dependent.
>
> The audio branch alongside it selects `SoundLow` over `SoundHigh` when
> `GIsMMX == 0 || GPhysicalMemory <= 0x4000000` (64 MB), at `0x1090EDA1`.

Cross-checks against the shipped `System/DeusEx.ini`: `[FirstRun] FirstRun=0`,
`[Engine.Engine] CdPath=..\`, `GameRenderDevice=GlideDrv.GlideRenderDevice`,
and the `[WinDrv.WindowsClient]` / `[Galaxy.GalaxyAudioSubsystem]` sections all exist.
Every key above is present in both `DeusEx.ini` and `Default.ini` — **except two**.

### `DescFlags` and `Description` are runtime values, not shipped defaults

Neither appears in `DeusEx.ini`, `Default.ini`, or any other shipped `.ini`. (Grepping
`Description` hits hundreds of lines in `DeusEx.int`, but those are item descriptions in
the localization file — a different key in a different namespace. Not related.)

Both are **written by the render device during detection and read back by the launcher**:

- `-testrendev=<class>` sets `[<class>] DescFlags=2` and flushes (`0x1090A86D`, `0x1090A886`),
  then writes `Detected.ini`. `Detected.ini` is likewise absent from a fresh install.
- `WConfigPageRenderer__RefreshList` (`0x1090CFC3`) and the detail tuner (`0x1090ECA1`)
  read `DescFlags` back to decide which devices are "certified/compatible" vs. "all".
- `[D3DDrv.D3DRenderDevice] Description` (`0x109103D7`) is the human-readable card name
  shown on the Driver page; the shipped `[D3DDrv.D3DRenderDevice]` section contains only
  static rendering options, no `Description`.

**Implication for a port:** these keys are an output channel from device detection into
the wizard. A reimplementation that queries the GPU directly does not need them, but
anything that shells out to the original drivers must round-trip them through config.

## Class names resolved through ini indirection

`StaticLoadClass` with an `ini:` URL reads the class name from config at load time:

| Indirection | Resolves via | Address |
|---|---|---|
| `ini:Engine.Engine.GameEngine` | `[Engine.Engine] GameEngine` | `0x1090BB2A` |
| `ini:Engine.Engine.EditorEngine` | `[Engine.Engine] EditorEngine` | `0x1090BB57` (editor only) |

Shipped value: `GameEngine=DeusEx.DeusExGameEngine`.

## Files

| File | Operation | Address | Meaning |
|---|---|---|---|
| `Running.ini` | create | `0x1090B903` | unclean-shutdown sentinel |
| `Running.ini` | probe | `0x1090B569` | triggers RecoveryMode wizard |
| `Running.ini` | delete | `0x109098CC` | clean-shutdown marker |
| `Detected.ini` | create | `0x1090A9DB` | output of `-testrendev=` — **also written during first-run renderer detection**, which spawns `-testrendev=` children via `ShellExecute` (`0x1090DB18`) |
| `<appPackage()>.ini` | delete | `0x10912508` | SafeOptions "Reset all configuration options" |
| `..\Save\*.usa` | enumerate | `0x1090A2BA` | savegame migration |
| `<Package>Logo.bmp`, `..\Help\Logo.bmp` | read | `0x1090907F` | splash bitmap |
| `<CdPath>Textures\Palettes.utx` | probe | `0x1090BA75` | CD check |

## Written by the log window

Not part of the config contract, but the launcher does write it
(`WWindow::Serialize`, on close):

```
[WindowPositions]
GameLog=(X=0,Y=0,XL=512,YL=256)
```

Confirmed live. A port keeping a log window should honour or deliberately drop this.

## Registry

Exactly one key, and it is dead:

| Hive | Subkey | Value | Address |
|---|---|---|---|
| `HKEY_LOCAL_MACHINE` | `software\mpath\mplayer\main` | `root directory` | `0x10914370` |

Read only by `LaunchMPlayer` (`0x109142C0`), reachable only via the `MPLAYER` console
command. The launcher touches **no other registry state** — all persistence is ini files.
