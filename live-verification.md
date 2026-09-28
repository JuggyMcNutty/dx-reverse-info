# Live verification runs

Static analysis checked against the real binary running under Proton: the first run,
2026-09-21, below, and the second, every page of the wizard, 2026-09-27
([below](#the-second-run-every-page-2026-09-27)).

**Setup (the first run).** `umu-run` into the existing `umu-default` prefix
(`Proton-CachyOS Latest`). The install was restored to its shipped state afterwards;
`DeusEx.ini` is byte-identical to the backup in `reference/ini-backup/`.

## Runs

| # | Command | Result |
|---|---|---|
| 1 | `DeusEx.exe -testrendev=D3DDrv.D3DRenderDevice` | reached log-window creation, died there (environment, see below) |
| 2 | `explorer /desktop=dxtest,1024x768 DeusEx.exe -firstrun` | splash assert — `Logo.bmp` had been deleted from this install |
| 3 | same, after restoring `Help/Logo.bmp` | **first-time wizard opened and ran device detection** |

## Confirmed

Run 1's `DeusEx.log`, verbatim in part:

```
Init: Version: 1100
Init: Command line: -testrendev=D3DDrv.D3DRenderDevice
Init: Base directory: X:\Documents\projects\deusex-launcher\System\
Init: Character set: Unicode
Log: Bound to Engine.dll
Log: Bound to Core.dll
Log: Bound to Window.dll
Log: Cd Path: ..\
```

| Claim | Where documented | Evidence |
|---|---|---|
| `FirstRun` clamps to **1100** because that is the engine version | `wizard.md` | `Init: Version: 1100` |
| Launcher binds exactly `Core` / `Engine` / `Window` | `porting-notes.md` | the three `Bound to` lines — no others |
| `[Engine.Engine] CdPath` is read at startup | `ini-keys.md` | `Log: Cd Path: ..\` |
| Unicode branches taken when `GUnicodeOS` | `porting-notes.md` §6 | `Init: Character set: Unicode` |
| `FirstRun (0) < 400` → first-time wizard | `wizard.md` entry tree | run 3 opened the wizard |
| Renderer page performs device detection | `wizard.md` | run 3 wrote detection results (below) |
| `DescFlags` / `Description` are **runtime** values, absent from shipped ini | `ini-keys.md` | see diff below |
| `[D3DDrv.D3DRenderDevice] Description` is the card name | `ini-keys.md` | `Description=ATI Radeon HD 5600 Series` |
| `Running.ini` is created **after** the wizard, not before | `launch-flow.md` §5 | wizard sat open 2m47s with `Running.ini` **absent** |

Detection wrote this into `[D3DDrv.D3DRenderDevice]` — none of it present in the
shipped `DeusEx.ini`:

```
DescFlags=1
dwDeviceId=26840
dwVendorId=4098
UseVertexFog=False
UseAGPTextures=False
UseVideoMemoryVB=False
UseVSync=False
Description=ATI Radeon HD 5600 Series
```

### The splash condition, confirmed from both sides

`launch-flow.md` §3 says the splash is shown *unless* `-log`, `-server` or `TestRenDev`
is present. Both halves were exercised by accident:

- Run 1 (`-testrendev=…`) never touched the splash — it got as far as the log window.
- Run 2 (`-firstrun`) **did** attempt it, and asserted:

```
Assertion failed: Bitmap.LoadFile(Filename)
[File:..\..\Engine\Inc\UnEngineWin.h] [Line: 55]
```

That is `InitSplash`, and the assert fires on exactly the documented fallback chain:
`<Package>Logo.bmp` → `..\Help\Logo.bmp`.

## Corrections and additions to the spec

**1. The splash fallback has no existence check — a missing bitmap is fatal.**
`InitEngine` tests `FileSize(<Package>Logo.bmp) < 0` and then substitutes
`..\Help\Logo.bmp` *without testing that it exists* (`0x109090A4`). If neither is
present, `InitSplash` asserts and the process dies before the wizard or the engine.
Any launch not carrying `-log`, `-server` or `TestRenDev` is affected.

> This install had both bitmaps deleted, which is how the behaviour surfaced.
> `Help/Logo.bmp` has been restored from `reference/ReleaseSDK1112f/Help/Logo.bmp`.
> **A port should treat a missing splash as non-fatal.**

**2. `Detected.ini` is not only produced by an explicit `-testrendev=`.** It also
appears during first-run renderer detection: the Renderer page `ShellExecute`s the game
recursively (`0x1090DB18`) with `-testrendev=<class>` per candidate, so a crashing
driver kills only a child. `ini-keys.md` previously attributed the file solely to the
explicit flag.

**3. `[WindowPositions]` is written by the log window** — not previously documented:

```
[WindowPositions]
GameLog=(X=0,Y=0,XL=512,YL=256)
```

Written by `WLog`/`WWindow::Serialize` on close. A port that keeps a log window should
either honour or deliberately drop this.

## Environment note (not a game defect)

Under plain Proton, `WLog::OpenWindow` fails at the child `EDIT` control:

```
Critical: CreateWindowEx failed: Success.
Critical: Windows GetLastError: Success. (0)
Critical: PerformCreateWindowEx / WEdit::OpenWindow / WTerminal::OnCreate
```

`CreateWindowEx` returns NULL with `GetLastError() == 0`. Running inside a Wine virtual
desktop (`explorer /desktop=…`) avoids it entirely. This is a Proton/Wine window-station
quirk, not launcher behaviour — but it is worth knowing, because **the log window is
created unconditionally on every launch** (`launch-flow.md` §4), so when it fails the
game cannot start at all.

## The second run: every page (2026-09-27)

For deusex-launcher's `main`, which is compared against these captures. Inside the
distrobox, with the Proton build's own `wine` in the IDA prefix and a 1024×768 virtual
desktop: [`tools/wine/wizard-capture.sh`](tools/wine/wizard-capture.sh) runs
`DeusEx.exe` with `-firstrun`, `-changevideo` and `-safe`, then with no flags, then with
`-make`, and
[`tools/wine/wizard_drive.py`](tools/wine/wizard_drive.py), inside the same desktop, works
each page by Win32 messages to its controls and saves the window as the screen shows it
with its controls' rectangles. The install's files the runs write are put back after.
The captures stay outside the repositories, in `reference/original-wizard/`.

| Claim | Where documented | Evidence |
|---|---|---|
| `-safe` opens SafeMode, captioned "Deus Ex Safe Mode" | `wizard.md` entry tree | the page, with Cancel alone at the bottom |
| A stale `Running.ini` with nothing running opens RecoveryMode | `wizard.md` entry tree | "Deus Ex Recovery Mode", after the CD prompt's Cancel below had left one |
| SafeMode says "…it was not shut down properly…" for `-safe` too | `wizard.md` SafeMode | the same prompt on both pages |
| SafeOptions opens with every box ticked but Reset | `wizard.md` SafeOptions | the boxes' states |
| **The three dead checkboxes** | `wizard.md` shipped bug | with "Disable 3D sound hardware" cleared and the next three ticked, the relaunch ran as `DeusEx.exe -nosound -nommx -nokni -nok6 -nojoy`: no `-nohard`, `-noddraw` or `-defaultres` |
| The relaunch carries only the safe flags | `wizard.md` SafeOptions | the same command line |
| A cancelled wizard deletes `Running.ini` | `launch-flow.md` §9 | the file was gone after `-firstrun` and `-changevideo` were cancelled |
| The CD prompt: title, text, OK and Cancel, no icon; Cancel leaves `Running.ini` | `launch-flow.md` §8 | with `CdPath` pointed at a missing folder for the run |
| The splash is `..\Help\Logo.bmp` at its own size, centred, until the engine is up | `launch-flow.md` §3 | a 512×410 window at the desktop's centre, behind the CD prompt, its frame over the bitmap's edges; with a wizard to show it closes within a second. Wine shows the picture colour-reduced: many pixels a step of 8 off the file's |
| The Renderer list: certified and software devices, or all five sorted; the certified one chosen | `wizard.md` Renderer | Direct3D (detection certified it under wine) and Software Rendering; with "Show all devices", 3dfx Glide, Direct3D, OpenGL, S3 MeTaL, Software, Direct3D still chosen |
| Driver shows the detected card | `wizard.md` Driver | "AMD Radeon RX 6700 XT", with the web link as a blue underlined button, in Arial at 12 pixels rather than the page's MS Sans Serif |
| Detail's lines | `wizard.md` Detail | High sound quality, High detail player skins, High detail textures (its quotes stripped), Standard video resolution |
| The frame's buttons | `wizard.md` the frame | Back from the second page on, Finish never, "Run!" on FirstTime and SafeOptions, no Next on SafeMode |
| The templates' layout, scaled | `wizard.md` page layouts | every control at its dialog units × (1.5, 1.625), each of x, y, width and height rounded on its own: the window 530×436 with a 524×411 client area; Next at 183, 384, 75 × 23 |
| `-make` is fatal | `launch-flow.md` §2 | a "Critical Error" box, the error icon, the message, a blank line and "History: " with nothing after, OK alone; the process ended with 1 |

## Not verified

- The forwarding receiver: a second launch handing a running game its command line.
- `MainLoop` (`0x10914630`), and the splash staying up through a real start of the engine.
