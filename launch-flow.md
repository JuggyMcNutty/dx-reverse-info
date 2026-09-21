# Launch flow — `DeusEx.exe`

Every claim cites the address it was read from. Imagebase `0x10900000`.

## Entry

`start` (`0x109214B6`, CRT) → `WinMain` thunk (`0x10901366`) → **`LaunchWinMain` (`0x10908A30`)**.

## 1. Single-instance forwarding (`0x10908A30`–`0x10908CD1`)

Runs **before** any engine init, and is skipped entirely if the command line contains
any of `Server`, `NewWindow`, `changevideo`, `TestRenDev` (substring match via
`appStrfind`, `0x10908A97`–`0x10908AE5`).

Otherwise:

1. Enumerate top-level windows of class **`WLog`** (`FindWindowEx`, `0x10908B31`).
2. For each, read window property **`IsBrowser`** (`GetProp`, `0x10908BC9`).
3. On the first match: skip past argv[0] in the command line, then send
   **`WM_COPYDATA` (`0x4A`)** via `SendMessageTimeoutW` (`0x10908CBE`) with
   `SMTO_ABORTIFHUNG|SMTO_BLOCK` (`3`) and a **30 000 ms** timeout.
   The `COPYDATASTRUCT` is `{ dwData = WindowMessageOpen, cbData = 4*len+4,
   lpData = <rest of command line> }`.
4. Clear `GIsStarted`, `return 0` — this process exits without starting the engine.

> The running instance opens the requested URL/map; the second process is only a messenger.

## 2. Engine bootstrap (`0x10908CDB`–`0x10909205`)

| Step | Address | Detail |
|---|---|---|
| `GIsGuarded = 1`, `GIsClient = 1` | `0x10908CE8` | |
| `appInit(...)` | `0x10908D23` | package, cmdline, `GMalloc`, `GLog`, `GError`, `GWarn`, `GFileManager`, `FConfigCacheIni_Factory` (`0x10915080`), `RequireConfig=1` |
| `-make` rejected | `0x10908D6A` | fatal: *"'DeusEx -make' is obsolete, use 'ucc make' now"* |
| `GIsServer = 1` | `0x10908D79` | always |
| `GIsClient = !ParseParam("SERVER")` | `0x10908D97` | |
| `GIsEditor = 0`, `GIsScriptable = 1` | `0x10908DC0` | |
| `GLazyLoad = !GIsClient \|\| ParseParam("LAZY")` | `0x10908E18` | |
| low-memory override | `0x10908E3B` | if `GPhysicalMemory <= 0x4000000` (64 MB) → force `GLazyLoad = 1` and log *"** Deus Ex - Low memory conditions detected - Forcing lazy loading"* |

## 3. Splash screen (`0x10908E93`–`0x10909205`)

Bitmap path: `<appPackage()>Logo.bmp`, falling back to `..\Help\Logo.bmp` if the first
does not exist (`GFileManager->FileSize`, `0x1090907F`).

Shown via `InitSplash` (`0x10901AA0`) **unless** any of: `-log`, `-server`,
or `TestRenDev` present (`0x1090917B`–`0x109091FD`). Both halves of this condition were
confirmed live — see [`live-verification.md`](live-verification.md).

> ⚠ **A missing splash bitmap is fatal.** The fallback is applied without checking that
> `..\Help\Logo.bmp` exists (`0x109090A4`). If neither bitmap is present, `InitSplash`
> asserts (`Bitmap.LoadFile(Filename)`, `Engine\Inc\UnEngineWin.h:55`) and the process
> dies before the wizard or the engine. Observed live. A port should treat this as
> non-fatal.

Then `InitWindowing()` (`0x10909205`, from `Window.dll`).

## 4. Log window (`0x10909226`–`0x109093E1`)

- `new WLog(..., FName("GameLog"))`, 660 bytes, vtable `WGameLog__vftable` (`0x10926C88`).
- Stored in the exported global `GLogWindow`.
- `OpenWindow(ShowLog = ParseParam("LOG"), 0)` (`0x109092CE`).
- Logs `LocalizeGeneral("Start", "<Package>")`.
- If `GIsClient`: sets window property **`IsBrowser`** on the log window (`0x1090934A`).
  **This is what makes the process discoverable in step 1.**

## 5. `InitEngine` (`0x1090A050`)

Returns a constructed `UGameEngine*`, or `0` to abort startup. See
[`wizard.md`](wizard.md) for the decision tree. Summary:

1. Start timing (`__rdtsc` / `appSecondsSlow`).
2. Install `GLaunchExec` (`0x1092E7B0`) as `GExec` — see §7.
3. `CreateMutex("DeusExIsRunning")`; `GetLastError() == ERROR_ALREADY_EXISTS (183)`
   records whether another instance is live (`0x1090A227`).
4. Read `[FirstRun] FirstRun` (int). `-firstrun` forces it to `0` (`0x1090A283`).
5. If `FirstRun < 220` → migrate savegames (§6).
6. `-consolecommand=<cmd>` → run through `GExec`, then **return 0** (never launches).
7. `-testrendev=<class>` → load the render-device class, write `Detected.ini`, **return 0**.
8. Otherwise run the config wizard if one is warranted.
9. Create `Running.ini` (the unclean-shutdown sentinel, `0x1090B903`).
10. Clamp `FirstRun` up to **1100** and write it back (`0x1090B997`).
11. CD check (§8).
12. `StaticLoadClass(UGameEngine, "ini:Engine.Engine.GameEngine")` (`0x1090BB2A`),
    `ConstructObject_UEngine` (`0x10920920`), then `Engine->Init()` (vtable +100).
13. Log *"Startup time: %f seconds"*.

## 6. Savegame migration (`FirstRun < 220`, `0x1090A2BA`–`0x1090A605`)

Enumerate `..\Save\*.usa`. For each, parse the slot index from the filename
(offset 4, i.e. after `Save`), then in the **`User`** ini, read
`[UnrealShare.UnrealSlotMenu] SlotNames[<i>]`; if it is empty, set it to `"Saved game"`.

## 7. Console commands — `LaunchExec__Exec` (`0x10913650`)

`GLaunchExec` is installed as the global `GExec`, so these work from the in-game console:

| Command | Effect |
|---|---|
| `ShowLog` | show the log window |
| `HideLog` | hide it |
| `TakeFocus` | bring the window forward |
| `EditActor Class=<name>` / `EditActor new` | open a `WObjectProperties` inspector; errors *"Actor not found"* / *"Missing class"* |
| `Preferences` | open `WConfigProperties`, caption `LocalizeGeneral("AdvancedOptionsTitle","Window")` |
| `MPLAYER` | `LaunchMPlayer` (`0x109142C0`) — **dead service**, see [`porting-notes.md`](porting-notes.md) |
| `HEAT` | launch `GotoHEAT.exe` on port `5193` — **dead service** |

## 8. CD check (`0x1090B9CE`–`0x1090BAFD`)

Read `[Engine.Engine] CdPath`. If it is non-empty, loop until
`<CdPath>Textures\Palettes.utx` exists; each failed pass shows a `MessageBoxW`
(`MB_OKCANCEL|MB_ICONEXCLAMATION|MB_SETFOREGROUND|MB_TASKMODAL`, `0x52001`) with
`InsertCdText` / `InsertCdTitle` from the **`Window`** localization package.
Cancel → `GIsCriticalError = 1; ExitProcess(0)`.

> Shipped `DeusEx.ini` sets `CdPath=..\`, so on a GOG/Steam install the check passes
> against the game's own `Textures\` directory and never prompts.

## 9. Main loop and shutdown (`0x109097EB` onward)

- `-EXEC=<file>` → runs `exec <file>` through the engine's client console (`0x109097E1`).
- `MainLoop(Engine)` (`0x10914630`).
- Delete `Running.ini` (`0x109098CC`) — **the clean-shutdown marker**.
- Remove the `IsBrowser` property, `appPreExit()`, `appExit()`.

> If the process dies before step 3, `Running.ini` survives and the **next** launch
> shows the recovery wizard. That is the entire crash-detection mechanism.

## Exit paths

| Path | Result |
|---|---|
| Forwarded to a running instance (§1) | returns 0, engine never starts |
| `-make` | fatal error via `GError` |
| `-consolecommand=` | command runs, returns 0 |
| `-testrendev=` | writes `Detected.ini`, returns 0 |
| Wizard cancelled (`DoModal` → 0) | returns 0 |
| SafeOptions "Next" | `ShellExecute`s a **new process** with safe flags, then ends this one |
| CD check cancelled | `ExitProcess(0)` |
| Normal | `MainLoop` → delete `Running.ini` → `appExit` |
