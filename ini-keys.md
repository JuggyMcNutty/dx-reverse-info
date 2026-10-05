# Configuration surface

Every ini read and write of `DeusEx.exe`, resolved from `GConfig` vtable call sites against
the `FConfigCache` interface in `Core/Inc/Core.h:195`. Each entry was confirmed by argument
arity and types at the call site, not by index arithmetic: MSVC reverses overload groups in
the vtable ([the rule](README.md#working-on-the-binaries)).

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

Written as the Detail page opens, from the renderer and the hardware. "When" is the line
the page shows ([`wizard.md`](wizard.md#detail-2018)).

| Section | Key | Value | When | Address |
|---|---|---|---|---|
| `WinDrv.WindowsClient` | `MinDesiredFrameRate` | `1` | below | `0x1090ED2C`, `0x1090ED9E` |
| `Galaxy.GalaxyAudioSubsystem` | `UseReverb` | `False` | `SoundLow` | `0x1090EF28` |
| `Galaxy.GalaxyAudioSubsystem` | `OutputRate` | `11025Hz` | `SoundLow` | `0x1090EF4E` |
| `Galaxy.GalaxyAudioSubsystem` | `UseSpatial` | `False` | `SoundLow` | `0x1090EF73` |
| `Galaxy.GalaxyAudioSubsystem` | `UseFilter` | `False` | `SoundLow` | `0x1090EF98` |
| `Galaxy.GalaxyAudioSubsystem` | `LowSoundQuality` | `1` (SetBool) | `SoundLow` | `0x1090EFBA` |
| `WinDrv.WindowsClient` | `SkinDetail` | `Medium` | `SkinsLow` | `0x1090F23B` |
| `WinDrv.WindowsClient` | `TextureDetail` | `Medium` | `WorldLow` | `0x1090F4D8` |
| `WinDrv.WindowsClient` | `WindowedViewportX` / `Y` | `640` / `480` | always | `0x1090F59C`, `0x1090F5C2` |
| `WinDrv.WindowsClient` | `WindowedColorBits` | `16` | always | `0x1090F5E7` |
| `WinDrv.WindowsClient` | `FullscreenViewportX` / `Y` | `640` / `480` | always | `0x1090F60C`, `0x1090F631` |
| `WinDrv.WindowsClient` | `FullscreenColorBits` | `16` | always | `0x1090F656` |

`MinDesiredFrameRate` has two call sites and one value: both pass the string `"1"` (read at
`0x1090ED0C` and `0x1090ED7E`). The first runs when the renderer is
`SoftDrv.SoftwareRenderDevice` or the CPU is slow (`GSecondsPerCycle × 280,000,000 > 1`:
under about 280 MHz); the second, otherwise, when it is `D3DDrv.D3DRenderDevice`. The SDK's
source notes both changed for Deus Ex, from 20 and 28. `Default.ini` ships `1.0`, the same
value. Besides it, only the skins' and the world's lines depend on the renderer, through its
`DescFlags`. `SoundLow` is chosen when `GIsMMX == 0 || GPhysicalMemory <= 0x4000000`
(64 MB), at `0x1090EDA1`.

The shipped `System/DeusEx.ini` has `[FirstRun] FirstRun=0`, `[Engine.Engine] CdPath=..\`
and `GameRenderDevice=GlideDrv.GlideRenderDevice`, and the `[WinDrv.WindowsClient]` and
`[Galaxy.GalaxyAudioSubsystem]` sections. Every key above is in both `DeusEx.ini` and
`Default.ini` **except three**: `DescFlags` and `Description` (below), and `SlotNames[%i]`,
a key of the `User` file that no shipped ini has (the savegame migration writes it).

### `DescFlags` and `Description` are runtime values, not shipped defaults

Neither is in `DeusEx.ini`, `Default.ini` or any other shipped `.ini`. The render device
writes them during detection, and the launcher reads them back:

- `-testrendev=<class>` sets `[<class>] DescFlags=2` and flushes (`0x1090A86D`,
  `0x1090A886`), then writes `Detected.ini`, which is also absent from a fresh install.
- `WConfigPageRenderer__RefreshList` (`0x1090CFC3`) reads `DescFlags` back for its flag 1,
  certified, which gives a device its place in the compatible list; the Detail page
  (`0x1090ECA1`) reads the chosen renderer's for its flags 4 and 8, low-detail world and
  skins ([`wizard.md`](wizard.md#detail-2018)).
- `[D3DDrv.D3DRenderDevice] Description` (`0x109103D7`) is the card's name on the Driver
  page. The shipped `[D3DDrv.D3DRenderDevice]` section holds only static rendering options,
  no `Description`.

So these keys carry device detection's results into the wizard, through the config.

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
| `Detected.ini` | create | `0x1090A9DB` | output of `-testrendev=`, **also written during first-run renderer detection**, which runs the game once more through `ShellExecute` (`0x1090DB18`) as `testrendev=D3DDrv.D3DRenderDevice log=Detected.log` ([`wizard.md`](wizard.md#renderer-2017)) |
| `<appPackage()>.ini` | delete | `0x10912508` | SafeOptions "Reset all configuration options" |
| `..\Save\*.usa` | enumerate | `0x1090A2BA` | savegame migration |
| `..\Help\<Package>Logo.bmp`, `..\Help\Logo.bmp` | read | `0x1090907F` | splash bitmap |
| `..\Help\LogoSmall.bmp` | read | `0x1090C780` | the wizard's logo |
| `<CdPath>Textures\Palettes.utx` | probe | `0x1090BA75` | CD check |

## Written by the log window

Not part of the config contract, but the launcher writes it (`WWindow::Serialize`, on
close), seen under wine:

```
[WindowPositions]
GameLog=(X=0,Y=0,XL=512,YL=256)
```

## Registry

Exactly one key, and it is dead:

| Hive | Subkey | Value | Address |
|---|---|---|---|
| `HKEY_LOCAL_MACHINE` | `software\mpath\mplayer\main` | `root directory` | `0x10914370` |

Read only by `LaunchMPlayer` (`0x109142C0`), reachable only through the `MPLAYER` console
command. The launcher touches **no other registry state**: all persistence is ini files.
