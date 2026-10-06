# Launch flow — `DeusEx.exe`

Every claim cites the address it was read from. Imagebase `0x10900000`.

## Entry

`start` (`0x109214B6`, CRT) → `WinMain` thunk (`0x10901366`) → **`WinMain` (`0x10908A30`)**.

## 1. Single-instance forwarding (`0x10908A30`–`0x10908CD1`)

Runs **before** any engine init. Skipped when the command line contains any of `Server`,
`NewWindow`, `changevideo`, `TestRenDev` (`appStrfind`, a substring match,
`0x10908A97`–`0x10908AE5`). This check reads the command line as Windows gives it, the
program's path included: an install path holding one of the four words skips forwarding too.

Otherwise:

1. Enumerate top-level windows of class **`WLog`** (`FindWindowEx`, `0x10908B31`).
2. For each, read the window property **`IsBrowser`** (`GetProp`, `0x10908BC9`).
3. On the first match, skip past argv[0] and send the rest as **`WM_COPYDATA` (`0x4A`)**:
   `SendMessageTimeoutW` (`0x10908CBE`), `SMTO_ABORTIFHUNG|SMTO_BLOCK` (`3`), a
   **30 000 ms** timeout. The `COPYDATASTRUCT` is
   `{ dwData = WindowMessageOpen, cbData = 4*len+4, lpData = <rest of command line> }`.
4. Clear `GIsStarted`, `return 0`: this process exits without starting the engine. The
   running instance opens the requested URL or map.

"Past argv[0]" is past the first space: a quoted program path holding spaces is cut inside
itself, and what is sent starts with the rest of the path.

**The receiver** is the running instance's log window (`WLog`, Window.dll; the SDK's
`Window/Inc/Window.h`). On `WM_COPYDATA` it logs `WM_COPYDATA: <line>`, runs `TakeFocus`
(the game's window to the front, [§7](#7-console-commands--launchexec__exec-0x10913650)),
then `Open <first token>` unless that token starts with `-`
([`OPEN`](engine-dll.md#starting-the-game-engine)). It runs them on the engine, which the
log window gets only when the main loop starts (`MainLoop`, `0x10914630`): a line that
arrives before then, during the wizard, does nothing.

## 2. Engine bootstrap (`0x10908CDB`–`0x10908E92`)

| Step | Address | Detail |
|---|---|---|
| `GIsGuarded = 1`, `GIsClient = 1` | `0x10908CE8` | |
| `appInit(...)` | `0x10908D23` | package, cmdline, `GMalloc`, `GLog`, `GError`, `GWarn`, `GFileManager`, `FConfigCacheIni_Factory` (`0x10915080`), `RequireConfig=1` |
| `-make` rejected | `0x10908D6A` | fatal: *"'DeusEx -make' is obsolete, use 'ucc make' now"* in the error handler's box, titled Window.int `[Errors] Critical`: the message, a blank line, "History: ". The process ends with 1. The GOG build has no `ucc` |
| `GIsServer = 1` | `0x10908D79` | always |
| `GIsClient = !ParseParam("SERVER")` | `0x10908D97` | |
| `GIsEditor = 0`, `GIsScriptable = 1` | `0x10908DC0` | |
| `GLazyLoad = !GIsClient \|\| ParseParam("LAZY")` | `0x10908E18` | |
| low-memory override | `0x10908E3B` | `GPhysicalMemory <= 0x4000000` (64 MB) → `GLazyLoad = 1`, and log *"** Deus Ex - Low memory conditions detected - Forcing lazy loading"* |

## 3. Splash screen (`0x10908E93`–`0x10909205`)

Bitmap: `..\Help\<Package>Logo.bmp` (`..\Help\DeusExLogo.bmp`), built as `..\Help` + the
package name + `Logo.bmp` (`0x10908F4F`–`0x10908F7D`); if that file does not exist,
`FileSize(<Package>Logo.bmp) < 0` (`GFileManager->FileSize`, `0x1090907F`), `..\Help\Logo.bmp`.

Shown by `InitSplash` (`0x10901AA0`) **unless** the command line holds `-log`, `-server` or
`TestRenDev` (`0x1090917B`–`0x109091FD`). Like forwarding, these checks read the whole
command line, the program's path included.

The splash is `DeusEx.exe`'s own dialog 119, opened on a thread of its own: a popup with a
dialog frame, kept off the taskbar (a tool window), holding one bitmap control. Its
template's image is the exe's bitmap #101, a 583×70 "DEUS EX" banner, which the file's
bitmap replaces. In the SDK's source the window is sized to the bitmap, centred on the
screen and put on top once, then released. It closes while the wizard shows and reopens
after ([§5](#5-initengine-0x1090a050)), and closes for good once there is an engine
([§9](#9-main-loop-and-shutdown-0x10909443-onward)).

> ⚠ **A missing splash bitmap is fatal.** The fallback to `..\Help\Logo.bmp` is taken
> without checking that it exists (`0x109090A4`). With neither bitmap present, `InitSplash`
> asserts (`Bitmap.LoadFile(Filename)`, `Engine\Inc\UnEngineWin.h:55`) and the process dies
> before the wizard or the engine ([seen under wine](wizard.md#observed-under-wine)).

Then `InitWindowing()` (`0x10909205`, from `Window.dll`).

## 4. Log window (`0x10909226`–`0x109093E1`)

- `new WLog(..., FName("GameLog"))`, 660 bytes, vtable `WGameLog__vftable` (`0x10926C88`),
  stored in the exported global `GLogWindow`. Created on every launch.
- `OpenWindow(ShowLog = ParseParam("LOG"), 0)` (`0x109092CE`).
- Logs `LocalizeGeneral("Start", "<Package>")`.
- If `GIsClient`: sets the window property **`IsBrowser`** on the log window
  (`0x1090934A`). This is what §1 finds.

## 5. `InitEngine` (`0x1090A050`)

Returns a constructed `UGameEngine*`, or `0` to abort startup. The wizard's decision tree:
[`wizard.md`](wizard.md).

1. Start timing (`__rdtsc` / `appSecondsSlow`).
2. Install `GLaunchExec` (`0x1092E7B0`) as `GExec` (§7).
3. `CreateMutex("DeusExIsRunning")`; `GetLastError() == ERROR_ALREADY_EXISTS (183)` records
   whether another instance is live (`0x1090A227`).
4. Read `[FirstRun] FirstRun` (int). `-firstrun` forces it to `0` (`0x1090A283`).
5. `FirstRun < 220` → migrate savegames (§6).
6. `-consolecommand=<cmd>` → run it through `GExec`, then **return 0** (never launches).
7. `-testrendev=<class>` → load the render-device class, write `Detected.ini`, **return 0**.
   Before trying the device it sets `[<class>] DescFlags=2` (incompatible) and flushes the
   configuration (`0x1090A86D`, `0x1090A886`); a device that starts writes its own.
8. Otherwise run the config wizard if one is warranted. The splash closes while it shows
   (`0x1090B7FC`) and reopens after (`0x1090B885`); a cancelled wizard returns 0.
9. Create `Running.ini`, the unclean-shutdown sentinel (`0x1090B903`).
10. Clamp `FirstRun` up to **1100** and write it back (`0x1090B997`), every time, also when
    it is already 1100 or more.
11. CD check (§8).
12. `StaticLoadClass(UGameEngine, "ini:Engine.Engine.GameEngine")` (`0x1090BB2A`),
    `ConstructObject_UEngine` (`0x10920920`), then `Engine->Init()` (vtable +100).
13. Log *"Startup time: %f seconds"*.

Before the wizard's entry tree, `InitPathnames` (`0x10901C40`, called at `0x1090AB7E`)
rewrites `.ICD` to `.EXE`: a SafeDisc artifact. The GOG build is not SafeDisc-wrapped.

## 6. Savegame migration (`FirstRun < 220`, `0x1090A2BA`–`0x1090A605`)

Enumerate `..\Save\*.usa`. For each, parse the slot index from the file name (offset 4,
after `Save`); in the **`User`** ini, read `[UnrealShare.UnrealSlotMenu] SlotNames[<i>]`, and
set it to `"Saved game"` if it is empty.

## 7. Console commands — `LaunchExec__Exec` (`0x10913650`)

`GLaunchExec` is the global `GExec`, so these work from the in-game console:

| Command | Effect |
|---|---|
| `ShowLog` | show the log window |
| `HideLog` | hide it |
| `TakeFocus` | bring the window forward |
| `EditActor Class=<name>` / `EditActor new` | open a `WObjectProperties` inspector; errors *"Actor not found"* / *"Missing class"* |
| `Preferences` | open `WConfigProperties`, caption `LocalizeGeneral("AdvancedOptionsTitle","Window")` |
| `MPLAYER` | `LaunchMPlayer` (`0x109142C0`), which holds the binary's only registry read, `HKLM\software\mpath\mplayer\main` ([`ini-keys.md`](ini-keys.md#registry)) — **dead service** |
| `HEAT` | launch `GotoHEAT.exe` on port `5193` — **dead service**; `GotoHEAT.exe` is not shipped |

## 8. CD check (`0x1090B9CE`–`0x1090BAFD`)

Read `[Engine.Engine] CdPath`. If it is non-empty, loop until `<CdPath>Textures\Palettes.utx`
(joined with a backslash where `CdPath` lacks one) is **larger than 0 bytes**
(`0x1090BA82`). Each failed pass shows a `MessageBoxW`
(`MB_OKCANCEL|MB_TASKMODAL|MB_SETFOREGROUND|MB_TOPMOST`, `0x52001`, no icon) with
`InsertCdText` / `InsertCdTitle` from the **`Window`** localization package.
Cancel → `GIsCriticalError = 1; ExitProcess(0)` (`0x1090BAE8`). That is after step 9 of §5,
so `Running.ini` stays and the next launch opens in RecoveryMode.

The shipped `DeusEx.ini` sets `CdPath=..\`, so on a GOG or Steam install the check passes
against the game's own `Textures\` and never prompts.

## 9. Main loop and shutdown (`0x10909443` onward)

With an engine from `InitEngine`:

- Log `LocalizeGeneral("Run")`, close the splash (`0x10909443`).
- `-EXEC=<file>` → run `exec <file>` on the client's first viewport, if it has one
  (`0x109097E1`).
- `MainLoop(Engine)` (`0x10914630`), unless an exit is already requested.

Then, whatever `InitEngine` returned:

- Delete `Running.ini` (`0x109098CC`), **the clean-shutdown marker**. It is the only
  deletion: a cancelled wizard, `-consolecommand=`, `-testrendev=` and the safe-mode relaunch
  end here too; a crash (through the error handler) and the CD prompt's `ExitProcess` never
  reach it.
- Remove the `IsBrowser` property, log `LocalizeGeneral("Exit")`, close the log window,
  `appPreExit()`, `appExit()`.

> If the process dies before this, `Running.ini` survives and the **next** launch shows the
> recovery wizard. That is the entire crash-detection mechanism.

## Exit paths

| Path | Result |
|---|---|
| Forwarded to a running instance (§1) | returns 0, engine never starts |
| `-make` | fatal error via `GError`; exit code 1 |
| `-consolecommand=` | command runs; `Running.ini` deleted; returns 0 |
| `-testrendev=` | writes `Detected.ini`; `Running.ini` deleted; returns 0 |
| Wizard cancelled (`DoModal` → 0) | `Running.ini` deleted; returns 0 |
| SafeOptions "Next" | `ShellExecute`s a **new process** with safe flags; `Running.ini` deleted; this one ends |
| SafeMode "Web" | opens the web page; `Running.ini` deleted; returns 0 |
| CD check cancelled | `ExitProcess(0)`; `Running.ini` stays |
| Normal | `MainLoop` → delete `Running.ini` → `appExit` |
| Crash | the error handler; `Running.ini` stays |

## Platform seams

The original's seven Win32 dependencies, and how it meets each:

1. **The GUI.** `Window.dll`'s classes (`WWizardDialog`, `WWizardPage`, `WListBox`,
   `WButton`, `WCoolButton`, `WLabel`, `WEdit`, `WUrlButton`) are thin wrappers over Win32
   controls. The dialog templates are resources inside `Window.dll`, loaded through
   `hInstanceWindow` ([page layouts](wizard.md#page-layouts)). Every string the user sees is
   in `System/Startup.int` and `System/Window.int`.
2. **Single-instance handoff.** A `WLog` window with the property `IsBrowser`;
   `WM_COPYDATA` carrying the command line's tail as one UTF-16 string; a 30 s timeout. The
   bypass tokens `Server`, `NewWindow`, `changevideo`, `TestRenDev` skip it
   ([§1](#1-single-instance-forwarding-0x10908a300x10908cd1)).
3. **Instance detection.** `CreateMutex("DeusExIsRunning")` + `ERROR_ALREADY_EXISTS`, used
   only to tell a crash from a concurrent instance when `Running.ini` survives
   ([§5](#5-initengine-0x1090a050), [the entry tree](wizard.md#entry-decision-tree-initengine-0x1090aab60x1090b7f6)).
4. **Relaunch.** `ShellExecute("open", GModuleFilename, flags, appBaseDir(), SW_SHOWNORMAL)`
   ([SafeOptions](wizard.md#safeoptions-2021--eight-checkboxes)).
5. **The splash.** Window.dll's `LoadFileToBitmap` of `..\Help\<Package>Logo.bmp` or
   `..\Help\Logo.bmp`, shown in dialog 119 ([§3](#3-splash-screen-0x10908e930x10909205)).
6. **ANSI/Unicode dual paths.** Every Win32 call is written twice, branching on
   `GUnicodeOS`, for Windows 9x. This is why decompiled functions look twice as long as
   they are.
7. **Path separators.** Backslashes are hard-coded in ini values and lookups: `..\Save\`,
   `Textures\Palettes.utx`, `CdPath=..\` ([§6](#6-savegame-migration-firstrun--220-0x1090a2ba0x1090a605),
   [§8](#8-cd-check-0x1090b9ce0x1090bafd)).
