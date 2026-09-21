# Porting notes

What a cross-platform launcher must replace, and what it can drop. Based on the
documented behaviour in [`launch-flow.md`](launch-flow.md), [`wizard.md`](wizard.md),
[`cli-flags.md`](cli-flags.md) and [`ini-keys.md`](ini-keys.md).

## The shape of the problem

`DeusEx.exe` is ~250 KB of glue. It does five real jobs:

1. Decide whether to hand off to an already-running instance.
2. Set engine globals from the command line.
3. Decide whether to show a config wizard, and run it.
4. Construct `UGameEngine` from an ini-named class and call `Init()`.
5. Run the message loop, then clear the crash sentinel.

Only **(3)** is substantial, and it is almost entirely Win32 UI. Everything else is a
few hundred lines of policy.

## Load-bearing vs. incidental

### Load-bearing — a port must reproduce these

| Behaviour | Why |
|---|---|
| `Running.ini` create/delete | The **entire** crash-detection mechanism. Create after the wizard, delete on clean exit. |
| `[FirstRun] FirstRun` gates (220 / 400 / 1100) | Determines whether the first-run wizard appears, and migration. Must be read *and* written back. |
| `[Engine.Engine] GameRenderDevice` | The renderer choice is *only* communicated to the engine through this key. |
| `ini:Engine.Engine.GameEngine` indirection | The engine class is named in config, not hardcoded. |
| Safe mode = **re-exec with flags** | Settings are not applied in-process. The relaunch is the mechanism. |
| Detail auto-configuration writes | The engine expects these keys populated after a first run. |
| Flag parsing semantics | `appStrfind` tokens match anywhere — a naive `argv` parser will behave differently. |

### Incidental — safe to drop or redesign

| Behaviour | Note |
|---|---|
| `MPLAYER` / `HEAT` console commands | Both services died around 2001. `GotoHEAT.exe` is not shipped. Dead code. |
| The single registry read | Only reachable from `MPLAYER`. Nothing else uses the registry. |
| `.ICD` → `.EXE` rewrite (`InitPathnames`, `0x10901C40`) | SafeDisc copy-protection artifact. The GOG build is not SafeDisc-wrapped. |
| `-make` rejection | Points at a tool (`ucc`) that is shipped separately. |
| Glide / 3dfx / S3 MeTaL / SGL renderers | Hardware long dead; `nGlide` wraps Glide on modern systems. |
| CD check | Shipped `CdPath=..\` makes it always pass. Keep the code path only if supporting original discs. |
| The three dead safe-mode checkboxes | A bug (see [`wizard.md`](wizard.md)). Fix, do not replicate. |

## Platform seams

Each of these is a Win32 dependency that needs a replacement or a decision.

### 1. The entire GUI (`Window.dll`)

Biggest single item. The launcher constructs `WWizardDialog`, `WWizardPage`,
`WListBox`, `WButton`, `WCoolButton`, `WLabel`, `WEdit`, `WUrlButton` — all thin
wrappers over Win32 controls, with dialog templates stored as **resources inside
`Window.dll`** and loaded via `hInstanceWindow`.

None of this survives a port. The replacement needs six screens; the control inventory
and IDs are in [`wizard.md`](wizard.md), and every user-visible string is already
externalised in `System/Startup.int` and `System/Window.int` — those files can be read
directly by a new implementation rather than re-translated.

### 2. Single-instance handoff

Currently: find a window of class `WLog` with property `IsBrowser`, send `WM_COPYDATA`
with a 30 s timeout.

A port needs an equivalent IPC. On Linux the natural equivalents are an abstract unix
socket or a lock file plus D-Bus. The *protocol* is trivial — one UTF-16 string, the
tail of the command line — so only the transport changes.

Note the bypass tokens (`Server`, `NewWindow`, `changevideo`, `TestRenDev`) must still
skip the handoff, or `-changevideo` on a running game would be swallowed.

### 3. Instance detection

`CreateMutex("DeusExIsRunning")` + `ERROR_ALREADY_EXISTS`. Used *only* to decide whether
`Running.ini` indicates a crash or a concurrent instance. A pidfile or flock is enough.

### 4. Process relaunch

`ShellExecute("open", GModuleFilename, flags, appBaseDir(), SW_SHOWNORMAL)` — needs
`exec`/`posix_spawn` plus the module path and working directory.

### 5. Splash screen

`LoadFileToBitmap` on a `.bmp` from `Window.dll`. Trivial to replace; the asset is
`<Package>Logo.bmp` or `..\Help\Logo.bmp`.

### 6. ANSI/Unicode dual paths

Every Win32 call in this binary is written twice, branching on `GUnicodeOS`, because it
had to run on Windows 9x. All of it collapses to plain UTF-8 in a port. This is why the
decompiled functions look twice as long as they are.

### 7. Path separators

Backslashes are hardcoded in ini values and lookups (`..\Save\`, `Textures\Palettes.utx`,
`CdPath=..\`). A port must normalise, and must keep *writing* whatever the engine expects.

## Suggested boundary for a framework

The clean seam is `InitEngine`'s contract: **everything before `StaticLoadClass(UGameEngine)`
is launcher policy; everything after is engine.** A port can reimplement the whole
launcher as a separate process that:

1. Applies the documented flag and ini semantics.
2. Shows its own UI.
3. Writes `GameRenderDevice`, the detail keys, and `FirstRun`.
4. Creates `Running.ini`.
5. Executes the real game binary.

That requires no engine changes at all and is testable against the shipped ini files —
a strictly smaller problem than replacing `DeusEx.exe` in place.

## Verification hooks

Several of these have now been **run** — results in
[`live-verification.md`](live-verification.md). The documented behaviour is observable
without a debugger:

- Set `[FirstRun] FirstRun=0` → first-time wizard appears.
- Run with `-changevideo` → renderer page only.
- Leave a stale `Running.ini` → recovery wizard on next launch.
- `-testrendev=D3DDrv.D3DRenderDevice` → writes `Detected.ini`, exits without launching.
- Tick *"Disable 3D sound hardware"* in safe mode → observe `-nohard -noddraw -defaultres`
  on the relaunched process's command line (would confirm the shipped bug — **not yet run**).
