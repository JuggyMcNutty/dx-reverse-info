# Live verification run

Static analysis checked against the real binary running under Proton, 2026-09-21.

**Setup.** `umu-run` into the existing `umu-default` prefix
(`Proton-CachyOS Latest`). The install was restored to its shipped state afterwards;
`DeusEx.ini` is byte-identical to the backup in `.ini-backup/`.

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
> `Help/Logo.bmp` has been restored from `ReleaseSDK1112f/Help/Logo.bmp`.
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

## Not verified

- The SafeMode / RecoveryMode entry paths (`-safe`, stale `Running.ini`).
- The safe-mode re-exec and its flag string — **including the three-dead-checkboxes bug**,
  which remains a static-analysis finding only. It is well evidenced (eight
  `BM_GETCHECK` sites, five reading `+0xB0`, struct size confirmed by `GMalloc(1012)`),
  but has not been observed live.
- `GetNext` chain past the Renderer page (Driver / Detail / FirstTime).
