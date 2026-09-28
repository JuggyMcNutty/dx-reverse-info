# The original launcher, reverse-engineered

How the project began. Before any of the launcher was written, the game's own
`System/DeusEx.exe` was reverse-engineered, so the project started from known
behaviour and could write clean code of its own from there. This is that
record: what the original does, with the addresses it was read from.
[deusex-launcher](https://github.com/JuggyMcNutty/deusex-launcher)'s `main`
recreates it almost 1:1; its port branches carry the launcher as it grew,
which kept only part of it
([what it changes from the original](https://github.com/JuggyMcNutty/deusex-launcher/blob/linux-x86_64/docs/LAUNCHER.md#what-it-changes-from-the-original)).
How the binaries are worked on is in [the index](README.md#working-on-the-binaries).

| File | Contents |
|---|---|
| [`launch-flow.md`](launch-flow.md) | startup→shutdown sequence, all exit paths |
| [`wizard.md`](wizard.md) | page graph, `FirstRun` gates, control inventory, the shipped bug |
| [`cli-flags.md`](cli-flags.md) | every flag, and which of the three parsers reads it |
| [`ini-keys.md`](ini-keys.md) | every read/write, files, the one registry key |
| [`porting-notes.md`](porting-notes.md) | load-bearing vs. incidental; the seven platform seams |
| [`types/launch.h`](types/launch.h) | struct definitions + size ledger |
| [`live-verification.md`](live-verification.md) | the live Proton run: confirmed, corrected, added |

Five phases, cross-verified, two live runs under Proton -- the second through every page
([`live-verification.md`](live-verification.md)). Complete.

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

Two more came later, for `main` of the launcher, which recreates this almost
1:1. One of those headers, `Engine/Inc/UnEngineWin.h`, is the source of
`InitEngine`, the splash and all six pages, and matches the binary wherever the
two were compared ([`wizard.md`](wizard.md)). And the pages' layouts are data,
`Window.dll`'s dialog templates ([`wizard.md`](wizard.md#page-layouts)).

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
-defaultres`, and `No3DVideo`, `Window` and `Res` do nothing. Observed live
too ([`live-verification.md`](live-verification.md#the-second-run-every-page-2026-09-27)).
A recreation wires all eight correctly; the port
branches' launcher dropped safe mode, because Surreal Engine honours none of
its flags (row 1 of
[what it changes](https://github.com/JuggyMcNutty/deusex-launcher/blob/linux-x86_64/docs/LAUNCHER.md#what-it-changes-from-the-original)).

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
