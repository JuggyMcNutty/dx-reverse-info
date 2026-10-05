# The original launcher, reverse-engineered

`System/DeusEx.exe`, read in full: what the original does, with the addresses it was read
from. [deusex-launcher](https://github.com/JuggyMcNutty/deusex-launcher)'s `main` recreates
it almost 1:1; its port branches depart from it
([what it changes from the original](https://github.com/JuggyMcNutty/deusex-launcher/blob/linux-x86_64/docs/LAUNCHER.md#what-it-changes-from-the-original)).
Method: [working on the binaries](README.md#working-on-the-binaries).

| File | Contents |
|---|---|
| [`launch-flow.md`](launch-flow.md) | startup→shutdown sequence, all exit paths, the seven platform seams |
| [`wizard.md`](wizard.md) | page graph, `FirstRun` gates, control inventory, the shipped bug, what it shows under wine |
| [`cli-flags.md`](cli-flags.md) | every flag, and which of the three parsers reads it |
| [`ini-keys.md`](ini-keys.md) | every read/write, files, the one registry key |
| [`types/launch.h`](types/launch.h) | struct definitions + size ledger |

## The binary

`System/DeusEx.exe` is **not the game**. It is the UE1 `Launch` module, a thin bootstrap
shell. The engine lives in `Core.dll`, `Engine.dll`, `DeusEx.dll` and their neighbours
([the DLLs](README.md#the-binaries)); of them, the launcher imports `Core.dll`, `Engine.dll`
and `Window.dll`.

| Property | Value |
|---|---|
| Size | 253,952 bytes |
| Imagebase | `0x10900000` |
| `GPackage` | `"Launch"` (string at `0x1092C534`) |
| Functions | 762 (367 named — mostly import thunks — / 371 unnamed) |
| MD5 | `795137104d97da1bf4282fd6979bb38d` |
| **SHA1** | **`2a933e26aa9cfb33b37f78afe21434caa031f14a`** |
| Build | Nov 2021 GOG repack of the 1112f-era binary |

The SHA1 identifies the build, and it is Surreal Engine's `DEUS_EX_1112fm` database entry:
the engine recognises this install by it.

Sources beside the binary: `reference/ReleaseSDK1112f/Headers/DxHeaders.zip` ships this
build's own headers (327, including `LaunchPrivate.h`, `Window/Inc/Window.h` and
`Engine/Inc/UnEngineWin.h`, the source of `InitEngine`, the splash and all six pages); the
binary's assert strings name those paths. `System/Startup.int` is the launcher's string
table, naming every wizard page and control. The pages' layouts are `Window.dll`'s dialog
templates ([`wizard.md`](wizard.md#page-layouts)).

## Confirmed anchors

| Address | Meaning |
|---|---|
| `0x10908A30` | `WinMain` (real body; `0x10901366` is the CRT thunk) |
| `0x1090A050` | `InitEngine` — the launcher/wizard brain, 974 decompiled lines |
| `0x10914630` | `MainLoop(Engine)` |
| `0x10901320` | `FConfigCacheIni` factory passed to `appInit` (a jump to `0x10915080`) |
| `0x1092E7B0` | `GExec` local exec handler (vtables `off_109270A0`, `off_1092708C`) |
| `off_10926D70` | `WConfigPageRenderer` vtable — page size 464, dialog ID 2017 |
| `off_10926E7C` | `WConfigPageSafeMode` vtable — page size 564, dialog ID 2020 |
| `off_10926F88` | Launch's `WWizardDialog` subclass vtable |

## Verified struct sizes

From `Window/Inc/Window.h` into [`types/launch.h`](types/launch.h), checked against real
`GMalloc` sizes and field offsets:

`FName` 4 · `FString`/`FArray` 12 · `FDelegate` 12 · `WWindow` 44 ·
`WControl` 48 · `WLabel` 48 · `WListBox` 108 · `WButton` 120 ·
`WCoolButton` 128 · `WDialog` 44 · `WWizardPage` 48 · `WWizardDialog` 620

`WWizardPage` is 48 bytes; +48 is each page's own typed `Owner`, so a page's members start
at +52. Three totals close exactly: `WConfigPageRenderer` = 464 == `GMalloc(464)`;
`WConfigPageSafeMode` = 564 == `GMalloc(564)`; `WConfigPageSafeOptions` = 1012 ==
`GMalloc(1012)`.
