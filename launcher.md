# The original launcher, reverse-engineered

How the project began. Before any of the launcher was written, the game's own
`System/DeusEx.exe` was reverse-engineered, so the project started from known
behaviour and could write clean code of its own from there. This is that
record: what the original does, with the addresses it was read from.
[What the launcher kept and dropped](#what-the-launcher-kept-and-dropped) is at
the end; the launcher itself is [`../LAUNCHER.md`](../LAUNCHER.md), and how the
binaries are worked on is in [the index](README.md#working-on-the-binaries).

| File | Contents |
|---|---|
| [`launch-flow.md`](launch-flow.md) | startup→shutdown sequence, all exit paths |
| [`wizard.md`](wizard.md) | page graph, `FirstRun` gates, control inventory, the shipped bug |
| [`cli-flags.md`](cli-flags.md) | every flag, and which of the three parsers reads it |
| [`ini-keys.md`](ini-keys.md) | every read/write, files, the one registry key |
| [`porting-notes.md`](porting-notes.md) | load-bearing vs. incidental; the seven platform seams |
| [`types/launch.h`](types/launch.h) | struct definitions + size ledger |
| [`live-verification.md`](live-verification.md) | the live Proton run: confirmed, corrected, added |

Five phases, cross-verified, one live run under Proton. Complete.

## The binary

`System/DeusEx.exe` is **not the game**. It is the UE1 `Launch` module — a thin
bootstrap shell. The engine lives in `Core.dll`, `Engine.dll`, `DeusEx.dll` and
their neighbours ([the DLLs](README.md#the-binaries)).

| Property | Value |
|---|---|
| Size | 253,952 bytes |
| Imagebase | `0x10900000` |
| `GPackage` | `"Launch"` (string at `0x1092C534`) |
| Functions | 762 (367 named — mostly import thunks — / 371 unnamed) |
| MD5 | `795137104d97da1bf4282fd6979bb38d` |
| **SHA1** | **`2a933e26aa9cfb33b37f78afe21434caa031f14a`** |
| Build | Nov 2021 GOG repack of the 1112f-era binary |

That SHA1 matters twice: it identifies the build, and it is Surreal Engine's
`DEUS_EX_1112fm` database entry, so the engine recognises this install directly.

**Two things made this cheap.** `reference/ReleaseSDK1112f/Headers/DxHeaders.zip`
ships this build's own source headers (327 of them, including `LaunchPrivate.h`
and `Window/Inc/Window.h`), so struct layouts were *read*, not guessed — the
binary's assert strings name those exact paths. And `System/Startup.int` is the
launcher's own string table, naming every wizard page and control.

## Confirmed anchors

| Address | Meaning |
|---|---|
| `0x10908A30` | `WinMain` (real body; `0x10901366` is the CRT thunk) |
| `0x1090A050` | `InitEngine` — the launcher/wizard brain, 974 decompiled lines |
| `0x10914630` | `MainLoop(Engine)` |
| `0x10901320` | `FConfigCacheIni` factory passed to `appInit` |
| `0x1092E7B0` | `GExec` local exec handler (vtables `off_109270A0`, `off_1092708C`) |
| `off_10926D70` | `WConfigPageRenderer` vtable — page size 464, dialog ID 2017 |
| `off_10926E7C` | `WConfigPageSafeMode` vtable — page size 564, dialog ID 2020 |
| `off_10926F88` | Launch's `WWizardDialog` subclass vtable |

## Verified struct sizes

Transcribed from `Window/Inc/Window.h` into [`types/launch.h`](types/launch.h),
then cross-checked against real `GMalloc` sizes and field offsets:

`FName` 4 · `FString`/`FArray` 12 · `FDelegate` 12 · `WWindow` 44 ·
`WControl` 48 · `WLabel` 48 · `WListBox` 108 · `WButton` 120 ·
`WCoolButton` 128 · `WDialog` 44 · `WWizardPage` 48 · `WWizardDialog` 620

Three independent totals close exactly: `WConfigPageRenderer` = 464 == observed
`GMalloc(464)`; `WConfigPageSafeMode` = 564 == `GMalloc(564)`;
`WConfigPageSafeOptions` = 1012 == `GMalloc(1012)`.

> **Correction kept for the record.** An earlier reading put `WWizardPage` at
> 52. It is **48** — the slot at +48 is each config page's own typed `Owner`,
> declared by the derived class in addition to the inherited one. At 52 every
> derived offset is out by a slot and the totals do not close.

## Key findings

**The wizard graph:**

```
SafeMode(2020) ─Run→ launch │ ─Video→ Renderer │ ─SafeMode→ SafeOptions │ ─Web→ URL
Renderer(2017) → (D3D ? Driver(2022) → Detail(2018) : Detail(2018))
Detail(2018) → FirstTime(2019) → EndDialog(1) = launch
SafeOptions(2021) → ShellExecute(self, flags); EndDialog(0)
```

**Safe mode re-executes the binary.** `WConfigPageSafeOptions__GetNext`
(`0x10911C00`) does not apply settings in-process — it builds a flag string,
optionally deletes `<Package>.ini`, `ShellExecute`s `GModuleFilename`, and ends
the current process. The relaunch *is* the mechanism.

**Crash detection is one file.** `Running.ini` is created after the wizard and
deleted on clean exit. If it survives, the next launch shows RecoveryMode.

**⚠ Shipped bug — three safe-mode checkboxes are dead.** Of eight `BM_GETCHECK`
sites, five read the *same* control (`+0xB0`, `IDC_No3DSound`). So ticking
"Disable 3D sound hardware" silently also applies `-nohard -noddraw
-defaultres`, and `No3DVideo`, `Window` and `Res` do nothing. Static analysis
only — never observed live. Moot for the launcher now: safe mode was dropped
because Surreal Engine honours none of its flags (row 1
[below](#what-the-launcher-kept-and-dropped)).

**`appStrfind` flags match anywhere.** `readini`, `Server`, `NewWindow`,
`changevideo`, `TestRenDev` are raw substring matches needing no leading `-` —
they fire from inside a map name or URL. A naive `argv` parser behaves
differently, which is why the launcher keeps the command line as one string.

**Dead legacy paths:** `MPLAYER`/`HEAT` console commands, the single registry
read (`HKLM\software\mpath\mplayer\main`), and `.ICD`→`.EXE` rewriting in
`InitPathnames` (`0x10901C40`, a SafeDisc artifact).

**A missing splash bitmap is fatal** in the original: the fallback to
`..\Help\Logo.bmp` is applied without checking it exists (`0x109090A4`), so
`InitSplash` asserts and the process dies before the wizard. Observed live.

## Not verified against the original

- The SafeMode/RecoveryMode entry paths and the safe-mode re-exec, live.
- The three-dead-checkboxes bug, live. Well evidenced statically.
- `MainLoop` (`0x10914630`) in depth — a launcher replaces it wholesale.
- `Window.dll` dialog *templates* (geometry, styles, tab order) — out of scope;
  needed only for a pixel-faithful recreation.

## What the launcher kept and dropped

Kept as the original does it: the `FirstRun` gates (220/400/1100) and the
up-only clamp, the `Running.ini` sentinel lifecycle and its create-after-UI
ordering, the three non-equivalent command-line parsers, the single-instance
handoff. Changed or dropped:

| # | Original | The launcher | Why |
| --- | --- | --- | --- |
| 1 | Safe mode: eight checkboxes become flags (`-nosound`, `-nohard`, `-window`, ...) on a re-exec of the launcher; three of the eight were dead in the shipped binary | Dropped. The System tab (engine log, clear crash marker, resets) replaces it | Surreal Engine honours none of those flags. The corrected eight-box wiring existed (commit `254d13d`) and was removed with the page |
| 2 | Missing splash bitmap → assert → process dies before the wizard | No splash | Nothing to be missing (`0x109090A4`, [`live-verification.md`](live-verification.md)) |
| 3 | `MPLAYER` / `HEAT` console commands, one `HKLM\software\mpath` read | Dropped | Services dead since ~2001; `GotoHEAT.exe` is not shipped. [`porting-notes.md`](porting-notes.md) |
| 4 | `.ICD`→`.EXE` rewrite in `InitPathnames` | Dropped | SafeDisc artifact; the GOG build is not wrapped |
| 5 | `-make` rejected with a fatal error | Dropped | Points at `ucc`, shipped separately |
| 6 | Renderer page runs Win32 3D device detection, re-execing itself per candidate, and writes `GameRenderDevice` | Crash-isolated GPU probe (forked child); choice written to `Settings.json` `RenderDevice.Type` | Surreal Engine overrides `GameRenderDevice`. `-testrendev` is still parsed; `dxl-cli --probe` is its replacement |
| 7 | `CreateMutex` + `FindWindowEx`/`WM_COPYDATA` handoff | `flock` pidfile + abstract unix socket | Same protocol (one string, the command-line tail), different transport. The four `appStrfind` bypass tokens still skip it |
| 8 | CD check loops on `<CdPath>Textures\Palettes.utx` with a modal box | Install-validation screen | Generalises to "did the user supply the game files?", which is the actual first-run failure here |
| 9 | Driver page (2022) names the detected Direct3D card | The renderer picker's status line (GPU, API version) | The page existed to name a D3D card and point at a driver download |
| 10 | FirstTime page (2019) | Dropped; a first run opens on the Video tab with a note on Play | Its whole content was "Deus Ex is starting up for the first time" and a Run button |
| 11 | Web button `ShellExecute`s a troubleshooting URL | Dropped | No browser to hand off to, and the URL is long dead |
| 12 | Six-page modal wizard, shown only on first run, `-changevideo`, `-safe` or after a crash | Tabbed home screen on every launch; `DXL_NO_HOME=1` for the old behaviour | Settings must be reachable with a pad; a screen that appears only after a crash or a command-line flag is not |
| 13 | Detail page (sound quality, skin/world texture detail, 640×480) writes a block of `[WinDrv.WindowsClient]`/`[Galaxy...]` keys | Dropped; the Video tab carries the engine's real options | The engine's renderer and mixer read none of those keys |
| 14 | RecoveryMode page ("was not shut down properly") | Crash banner on Play quoting the engine's reported error; Troubleshoot opens System | The engine log can say *why* |
| 15 | `<Game>.ini` missing: UE1's Core creates it from `Default.ini` (before the launcher runs) | The launcher does it, and also rebuilds a stub with no `[Core.System] Paths` | [Where the settings actually live](../LAUNCHER.md#where-the-settings-actually-live) |
