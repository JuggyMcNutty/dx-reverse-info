# HX.dll

The native half of HX, Sebastian Kaufel's (Hanfling's) co-op mod for Deus Ex, and the two
programs that ship beside it, `HX.exe` and `HCC.exe`, from its last build, 0.9.89.4 of
2019-06-04. `HX.dll` holds:

- a game engine, `UHXGameEngine`, with co-op's start, travel and saving: a `Current` folder
  for each kind of run, levels saved as numbered generations conformed to the original map,
  and the campaign's state carried from map to map by an actor, `HXSteve`;
- a patch of `Engine.dll`'s `UActorChannel::ReplicateActor`, and copies of the level's tick
  and net tick that change the distances, the relevance and what goes to a client;
- the natives of HX's actor classes: traces that answer textures, a slot's sound stopped on
  every client, spawning, calls by name, bool flags replicated to clients;
- its input, windows, text log and render iterators, its links' GameSpy answer, and its
  commandlets.

Read with: [working on the binaries](README.md#working-on-the-binaries).

## The binary

All three are in HX's `System/`, beside `HX.u` (the script of 28 of its classes, and the
natives' numbers), `HX.int`, `HXDefault.ini`, `HXDefUser.ini` and `HCC.ini`. HX ships none of
the game's binaries: it runs on the game's own DLLs.

| Property | `HX.dll` | `HX.exe` | `HCC.exe` |
|---|---|---|---|
| What | package HX's natives | the launcher: the game's `Launch` built for HX | the commandlet runner: UCC built for HX |
| Size | 638,976 bytes | 385,024 bytes | 212,992 bytes |
| Imagebase | `0x10000000` | `0x10900000` | `0x400000` |
| SHA1 | `0ecdafc3e5bfe7c5aef9abdd93c6a8520e62161e` | `ffed39ec6137a6ba1d89b1f10865b2061401f7e8` | `783da7d9ec8f8a4dde894a53bdd5b1f60525892d` |
| Exports | 761: 40 classes, 62 `exec` natives | -- | -- |
| Functions | 1,442 | -- | -- |
| Built | 2019-06-04 | 2019-06-04 (`Launch: Compiled: Jun 4 2019`) | 2019-06-04 |

An export of `HX.dll` is its code, not a linker's jump to it, as in `DeusEx.dll`.

## Classes

Each size is the one the class's registration passes to `UClass`. Natives are `exec`
exports, with their numbers in `HX.u`, which the DLL registers alike (`0x10018910` to
`0x10025000`); one with no number is bound by its name. 28 classes have a
script; 12 are C++ only. `VerifyClasses` checks 18 of the sizes against the script at every
map's load ([the checks](#the-checks)).

| Class | Base | Size | Natives |
|---|---|---|---|
| `AHXActor` | `AActor` | 0x324 | 15: `SpawnEx` 3200, `TraceTextures` 3250, `TraceSingleTexture` 3251, `StaticTraceTextures` 3252, `StaticTraceSingleTexture` 3253, `FastRepTrace` 3254, `StaticFastRepTrace` 3256, `StringToName` 3260, `Strihash` 3261, `BindConversationList` 3270, `BindConsersationEvents` 3271, `StopSoundSlot` 3281, `StopAllSoundSlots` 3282; by name `DemoStopSoundSlot`, `DemoStopAllSoundSlots` |
| `AHXEffects` | `AHXActor` | 0x334 | -- |
| `AHXInfo`, `AHXRenderProxy`, `AHXTriggers` | `AHXActor` | 0x324 each | -- |
| `AHXCoopStart`, `AHXSteve` | `AHXInfo` | 0x344, 0x43c | -- |
| `AHXTrigger` | `AHXTriggers` | 0x354 | -- |
| `AHXDecoration` | `ADeusExDecoration` | 0x440 | 8: `StopSoundSlot` 3244, `StopAllSoundSlots` 3245, `TraceTextures` 3340, `TraceSingleTexture` 3341, `FastRepTrace` 3343; by name `StringToName`, `DemoStopSoundSlot`, `DemoStopAllSoundSlots` |
| `AHXPlayerPawn` | `ADeusExPlayer` | 0x15c0 | 15: `StopSoundSlot` 3217, `StopAllSoundSlots` 3218, `TraceTextures` 3300, `TraceSingleTexture` 3301, `FastRepTrace` 3303, `ExportTravel` 3311, `CompareGameEngine` 3312, `StringToName` 3313, `AddAdditionalView` 3314, `RemoveAdditionalView` 3315, `RemoveAllAdditionalViews` 3316, `DuckCallCanBeDropped` 3317; by name `ClientStopSound`, `DemoStopSoundSlot`, `DemoStopAllSoundSlots` |
| `AHXScriptedPawn` | `AScriptedPawn` | 0xb74 | 8: `StopSoundSlot` 3225, `StopAllSoundSlots` 3226, `StringToName` 3320, `TraceTextures` 3321, `TraceSingleTexture` 3322, `FastRepTrace` 3324; by name `DemoStopSoundSlot`, `DemoStopAllSoundSlots` |
| `AHXMutator` | `AMutator` | 0x330 | 3: `StringToName` 3360, `SpawnEx` 3361, `DuckCallSucceeds` 3362 |
| `AHXFlagReplicationInfo` | `AReplicationInfo` | 0x998 | 3: `GetBoolFlagCPP` 3410, `SetBoolFlagByStringCPP` 3411, `SetClientBoolFlagByStringCPP` 3412 |
| `AHXGameReplicationInfo` | `AGameReplicationInfo` | 0x448 | -- |
| `AHXKeypoint` | `AKeypoint` | 0x324 | -- |
| `AHXTcpLink`, `AHXUdpLink` | `ATcpLink`, `AUdpLink` | 0x350, 0x338 | 1 each, by name: `Validate` |
| `UHXWindow` | `XWindow` | 0x154 | 1: `WindowScale` 3500 |
| `UHXButtonWindow` | `XButtonWindow` | 0x1ec | 1: `WindowScale` 3501 |
| `UHXToggleWindow` | `XToggleWindow` | 0x1f4 | 1: `WindowScale` 3502 |
| `UHXTextLogWindow` | `XTextLogWindow` | 0x18c | 4, by name: `AddLine`, `ClearLines`, `NumLines`, `WindowScale` |
| `UHXRenderIterator` | `URenderIterator` | 0x34 | -- |
| `UHXScriptedRenderIterator` | `UHXRenderIterator` | 0x34 | 1: `CopyRenderProperties` 3100 |
| `UHXDecorationRenderIterator` | `UHXRenderIterator` | 0x4c | -- |
| `UHXConCamera` | `DConCamera` | 0xc0 | -- |
| `UHXFlagBase` | `XFlagBase` | 0x12c | -- |
| `UHXGoal`, `UHXNanoKeyInfo` | `UObject` | 0x40, 0x3c | -- |
| `UHXGameEngine` | `DDeusExGameEngine` | 0xd0 | -- (C++ only: the ini's `GameEngine=HX.HXGameEngine`) |
| `UHXInput` | `UInput` | 0xfb0 | -- (C++ only: the ini's `Input=HX.HXInput`) |
| `UHXLevel`, `UHXModel`, `UHXActorChannel` | `ULevel`, `UModel`, `UActorChannel` | 0x1150, 0x704, 0xac | -- (C++ only) |
| `UHXServerCommandlet`, `UHXSpewCoopStartsCommandlet`, `UHXDumpNanoKeysCommandlet`, `UHXDumpDataVaultImagesCommandlet`, `UHXDumpConDataVaultImagesCommandlet` | `UCommandlet` | 0x1dc each | -- (C++ only) |
| `UHXLinkerLoad` | `ULinker` | 0x900 | -- (C++ only) |
| `UHXStructPropertyOverrides` | `UStructProperty` | 0x64 | -- (C++ only) |

The natives `AHXDecoration`, `AHXPlayerPawn`, `AHXScriptedPawn` and `AHXMutator` share with
`AHXActor` are one jump each into `AHXActor`'s, which reads and writes `Actor`'s fields alone:
`TraceTextures` `0x100214c0`, `TraceSingleTexture` `0x10022b80`, `FastRepTrace` `0x10022ba0`,
`StopSoundSlot` `0x10022bc0`, `StopAllSoundSlots` `0x1001e870`, `DemoStopSoundSlot`
`0x1001e890`, `DemoStopAllSoundSlots` `0x10022be0`, `SpawnEx` `0x1001e9f0`. Every class's
`StringToName` is a jump into Extension's ([strings](#strings)).

## The game engine

`UHXGameEngine` (registered at `0x1003a290`, its constructor `0x1003a340`, its vtable
`0x1005fc38`, its `FExec`'s `0x1005fc34`) is `DDeusExGameEngine` with co-op's start, frame,
travel and saving: 0xd0 bytes, no fields of its own, `CLASS_Config|CLASS_Transient`, config
`System`, no script. It overrides `Destroy`, `Tick`, `Init`, `Key`, `ChallengeResponse`,
`Browse`, `LoadMap`, `PaintProgress`, `BuildServerMasterMap` and `Exec`, and keeps its bases'
others (`Serialize`, `MouseDelta`, `MousePosition`, `Exit`, `Draw`, `Click`,
`SetClientTravel`, `GetMaxTickRate`, `SetProgress`, `SaveGame`, `CancelPending`,
`UpdateConnectingMessage`, `NotifyLevelChange`). Its `Destroy` (`0x1003a380`) is a copy of
`XGameEngineExt`'s (`0x10026230`).

Its section, `[HX.HXGameEngine]`, holds its bases' keys alone: `CacheSizeMegs=32`,
`UseSound=True`, the `ServerActors` `HX.HXUdpBeacon`, `HX.HXUdpServerQuery` and
`HX.HXUdpServerUplink` (to `master.333networks.com`, port 27900), and the `ServerPackages`
`DeusExConversations`, `DeusExConText`, `DeusExConAudioAIBarks`, `DeusExText`, `DeusEx` and
`HX`.

### Names

`RegisterNames` (`0x100194a0`) makes, once (its count at `0x100924f0`), 20 names
`FNAME_Intrinsic`: those by which HX's C++ calls script events and functions. `Init` and the
constructors of `AHXEffects` and `AHXPlayerPawn` call it.

| Names | For |
|---|---|
| `burnTimer`, `pushTimer` | `AHXDecoration`'s tick |
| `StyleChanged` | `UHXWindow` |
| `PruneCurrent` | the engine's `PruneCurrent` ([saving a level](#saving-a-level)) |
| `DemoStopSoundSlot`, `DemoStopAllSoundSlots`, `ClientStopSound` | the sound slots |
| `TickStuff`, `NanoVirusTimer` | `AHXPlayerPawn`'s tick |
| `LipSynchTimer` | the ticks of `AHXPlayerPawn` and `AHXScriptedPawn` |
| `EffectsTimer` | `AHXEffects`' tick |
| `Init`, `First`, `Next`, `IsDone`, `CurrentItem` | `UHXScriptedRenderIterator` |
| `Succeeds` | `DuckCallSucceeds` |
| `CanBeDropped` | `DuckCallCanBeDropped` |
| `TierOne`, `TierTwo` | nothing |

`0x100196b0` makes `HX.dll`'s own copies of the names of Extension's 53 window events, once
(its flag at `0x100868e0`), for `Init` and for `UHXInput`'s constructor.

### Starting

`Init` (`0x1003b100`) is HX's copy of `UGameEngine::Init`
([starting the game engine](engine-dll.md#starting-the-game-engine)), which calls
`UEngine::Init` itself: the `Init` of `UGameEngine`, `XGameEngineExt` and `DDeusExGameEngine`
never runs, so `JoltView` is never registered
([`DeusEx.dll`](deusex-dll.md#the-game-engine-travel-and-saving)); Extension's names come
from the constructors of `XInputExt` and `APlayerPawnExt`, and from HX's copies. In order:

1. `HX Version 0.9.89.4` (`NAME_Init`).
2. The patch of `Engine.dll`'s `ReplicateActor`
   ([taking the game's place](#taking-the-games-place)).
3. `RegisterNames`; `-CONFLICTS` read into a global (`0x100924ec`) that nothing reads.
4. The `SavePath` folder made, one level alone (`..\CoopSave` in HX's ini).
5. 21 packages' GUIDs checked ([the checks](#the-checks)).
6. A fatal error unless its class is 208 bytes.
7. Its copies of Extension's window events' names.
8. `UEngine::Init`; `GLevel` None; the file cache cleaned.
9. On a client: the viewport manager, the renderer, the player's name (below), and the Entry
   level through HX's own `LoadMap`, a failure fatal (`FailedBrowse`), kept as `GEntry`.
10. The default URL, from the user ini's `[DefaultPlayer]`.
11. The start URL and its browse (below).
12. On a client, as the game's: the input, the viewport, the console (`HX.HXConsole` in HX's
    ini), the player spawned as a simulated proxy, the input's init, the window opened,
    `DetailChange`, `InitAudio`; then `Game engine initialized`.

- **The start URL.** A client takes the command line's first token whenever there is one and
  it does not start with `-`, where the game's takes it only with `-hax0r` or `-server`
  (HX's changelog: a listen server started, or an address joined, from the command line);
  with none, `FURL::DefaultLocalMap`, the ini's `[URL] LocalMap` (`DX.dx` in HX's), where
  the game's forces `DX.dx`. A dedicated server with no log window (`HCC.exe`) passes over
  its first token, the commandlet's word (`server`), and takes the next; one with a log
  window (`HX.exe -server`) takes the first. A server with none takes `FURL::DefaultMap`,
  `[URL] Map` (`01_NYC_UNATCOIsland.dx` in HX's ini).
- **The browse**: a partial URL on the default one. One that does not parse is fatal
  (`InvalidUrl`, a key `HX.int` lacks). A browse that fails with no error's text, its map
  not the fallback already, is tried once more at the fallback: the client's
  `DefaultLocalMap`, the server's `DefaultMap`, where the game's tries `DX.dx`. Any other
  failure is fatal (`FailedBrowse`).
- **The player's name**, on a client: `[DefaultPlayer] Name`, read from the file named
  `User.ini`, which the config cache takes for the user ini, `HXUser.ini` (not confirmed by
  a run). One missing, empty or `Player` in any case, or any name with `-RANDOMDENTON` on
  the command line, is replaced by a new one, written there before the default URL is read:
  one to four letters, then `_Denton`. The count comes from a triangle from 1 to 4 peaking
  at 2 (a uniform u: 1 + √(3u) below 1/3, else 4 − √(6(1 − u))), rounded to the nearest by
  the x87, so 1 letter in 8.3% of names, 2 in 54.2%, 3 in 33.3%, 4 in 4.2%; it is asserted
  to be 1 to 5. Each letter is `A` plus `appFrand` × 25 − 0.5 rounded, held to `A`..`Z`:
  `A` to `Y` alike, never `Z`. The shares are not confirmed by a run.

### The frame

`Tick` (`0x1003c3b0`) is `XGameEngineExt::Tick` and `UGameEngine::Tick` in one
([the game engine's frame](engine-dll.md#a-levels-tick)). The same: the exit once every
window has closed (`All Windows Closed`); the mouse captured and let go as the pause, the
player's `bShowMenu` (+0x69c bit 21) and the viewport's `bShowWindowsMouse` (+0x38 bit 1)
change, against a static `WasPaused` (`0x10088810`, 1 at the start); `bDropDetail` and
`bAggressiveLOD` (the `LevelInfo`'s +0x4f0 bits 4 and 5) cleared with a client; a server's
travel by the level's `NextURL` (+0x554), `NextSwitchCountdown` (+0x564) and `bNextItems`
(+0x560), `Server switch level: %s`; `loadonly` taken off the last URL before a client's
travel; the pending join; the client's tick; the cycle counts. It differs:

- **The windows** tick first (`XRootWindow::TickWindows`).
- **The levels**: the game's, the Entry level, and the first viewport's player's (+0xac) only
  when it is neither, where the game's ticks the Entry level twice while the player waits
  there. A level whose class is exactly `ULevel` ticks through `UHXLevel::Tick`
  ([the level's tick](#the-levels-tick)), then HX's `CleanupDestroyed`, unforced and
  compacting ([destroyed actors](#destroyed-actors)); a level of another class through its
  own `Tick`.
- **A server's travel** exports the travel of each `AHXPlayerPawn` with a `Player` (+0x5d4)
  and a `PlayerReplicationInfo` (+0x558) alone, through HX's `ExportTravel`
  ([the travel info](#the-travel-info)), logging `Export server travel for: %s`; the game's
  takes any player pawn with a `Player`.
- **A client's travel** tests for `?RESTART` in the level's `NextURL`, not in the viewport's
  `TravelURL` (+0xa0): a viewport's `?RESTART` is a plain travel that exports the items, and
  the level's travel info goes to the browse only while the level's own `NextURL` is
  `?RESTART`. It looks like a bug (not confirmed by a run). The export needs `bTravelItems`
  (+0xac) and an `AHXPlayerPawn` with a `Player` and a `PlayerReplicationInfo`, and logs
  `Export client travel for: %s` (the game's `Export travel for: %s`).
- **The portal**: the last URL's (+0xa8) is kept for a client's browse, where the game's
  empties it. HX's `SwitchLevel` and `SwitchCoopLevel` add an empty portal (`#`) when given
  none, so that the travel does not take the current one.

### Console words

`Exec` (`0x1003a400`) takes these before `DDeusExGameEngine::Exec`, whose `SAVEGAME` is the
game's:

| Word | HX's | The game's |
|---|---|---|
| `FLUSH` | flushes, a precache allowed with no word after it or `True`, else as the word's `appAtoi` is not 0; logs `Flushed engine caches (%i)` to the caller | `Flush(1)`, nothing logged |
| `UPDATEGAMMA` | with a client, a first viewport and its render device: asks the device for the interface `{CB1E8908-EF4C4A4A-A5DD8D16-4F335D26}` (`0x10091550`) and calls its +0x1c, `Updated gamma using IKnowWonderRenderDevice.`; a device without it is flushed, `Updated gamma using fallback.`; with no device the engine is flushed, `Updated gamma using fallbacks fallback.` | none |
| `EDITACTOR`, `EDITOBJECT` | taken, doing nothing, while the game level's `NetMode` is not standalone | the launcher's `EditActor` ([§7](launch-flow.md#7-console-commands--launchexec__exec-0x10913650)) |
| `RELAUNCH <rest>` | `Relaunch: %s`; the config written; `<appPackage()>.exe` (`HX.exe`) opened with the rest, in the base folder; the exit asked for | Core's, which starts `deusex.exe` ([RELAUNCH](core-dll.md#relaunch)) |
| `DUMPADDVIEWS` | each player pawn's `Dumping AdditionalViews for %s`, then `AdditionalViews[%i] = %s` for its three (+0x6a8); only the first is tested for None, so a pawn whose first is set and another empty faults (not confirmed by a run) | none |
| `GSPYLITE` | taken, doing nothing | `GSpyLite.exe` launched |
| `DUMPALWAYSRELEVANT` | `Dumping bAlwaysRelevant`, then every actor with `bAlwaysRelevant` (+0x1a0 bit 4) | none |
| `DELETEGAME n` | for a text that begins with a digit or `-`: the folder of slot n, -1 to -4 included, removed with all it holds ([folders](#folders-and-missions)); below -4 a fatal assertion (`DirectoryIndex>=0`) | a digit alone, `Save%04d` ([`DeusEx.dll`](deusex-dll.md#the-game-engine-travel-and-saving)) |

Which render device answers `UPDATEGAMMA`'s interface is not confirmed by a run. HX's script
sends `UPDATEGAMMA` from the brightness choice (`HXMenuChoice_AdjustBrightness`'s
`CancelSetting`, `ResetToDefault` and `ScalePositionChanged`); `Relaunch` with a map, its
game, `-Server` and `Log=HXServer.log` from the Host screen (`HXMenuScreenHostGame.BeginHost`)
and `HXPlayerPawn.StartNewDedicatedGame`; `Relaunch -ChangeVideo` and `-ChangeAudio` from the
render device's and the audio's choices (`BoxOptionSelected`).

### Joining

- **The challenge** (`ChallengeResponse`, `0x1003d830`): the challenge shifted 16 bits left,
  XOR the challenge shifted 16 bits right with its sign, XOR 0x237c, XOR 0x6c016d31: the
  bitwise inverse of the game's answer (`0x103888c0`, 0x93fe92ce where HX has 0x6c016d31).
  The game's server refuses only a response of 0 ([joining](network.md#joining)), so the
  inverse keeps no client out.
- **The package map** (`BuildServerMasterMap`, `0x1003f0e0`): the game's
  ([joining](network.md#joining), step 4), then what HX calls its packagemap hack. While HX's
  `Browse` loads a level from a `Current` folder, a global (`0x10099420`) holds that level's
  file, `<folder>\<map>.s%02d` ([browse](#browse)), cleared after the load. The entry of the
  server's package list (68-byte entries from +0x28) whose file is that one, compared without
  case, gets in its place the map's own file (`appFindPackageFile` of the package's name, no
  GUID), that file's size (+0x24, the file manager's: a file it cannot size is not taken) and a
  `RemoteGeneration` (+0x3c) of 1; the list is not computed again. So clients are sent the
  untouched map, not the saved one (HX's changelog), whose two generations a client's load
  refuses ([packages and linkers](core-dll.md#packages-and-linkers), a package's generations);
  its `SIZE=` is the map's, its `GEN=` still the save's own (the game's `SendPackageMap`,
  `0x10401ed0`, sends the server's generation), and the server counts the level by its first
  generation, the map's, as a client with the map asks by its `HAVE`
  ([numbering](network.md#numbering)): the conformed save ([saving a level](#saving-a-level),
  step 8) keeps the map's objects and names at those numbers. It warns (`GWarn`) `Failed to
  find package %s for packagemap hack.` or `Failed to find suitable sized package %s for
  packagemap hack.`. Run (a probe on a listen server, Liberty Island left for UNATCO HQ and
  entered again, a client joining it, DXEngine on the other side): Liberty Island announced
  with the map's `SIZE=9411740` and `GEN=2`, each of its 19 movers, marked by the server
  before it left, carrying its mark on the client, and a client without the map sent
  `..\Maps\01_NYC_UNATCOIsland.dx`.

### The checks

- **`CheckPackageGuid`** (`0x10045bc0`), from `Init`, for 21 packages: Core, Engine, Editor,
  Fire, IpDrv, UWindow, UBrowser, Extension, DeusExUI, ConSys, DeusExConversations,
  DeusExSounds, DeusExItems, DeusExDeco, DeusExCharacters, DeusExConText,
  DeusExConAudioAIBarks, MPCharacters, DeusExText, IpServer, DeusEx. It loads the package's
  linker (a missing one fatal), prints its GUID (linker +0x50, four `%08X`), and compares it,
  without case, with the one HX holds, the GOG build's. A mismatch logs five warnings
  (`NAME_Warning`): `%s Package Guid: %s -- Bad`, `You are using a non standard %s package.`,
  `You will likely encounter errors and crashes.`, `Don't report any bugs when using this %s
  package.` and `If this is non intentional use the %s version instead.`, the last naming
  `DeusEx 1112fm`. Nothing reads its answer.
- **`VerifyClasses`** (`0x10046f00`), from HX's `LoadMap` (`0x1003fc6d`), unless
  `-HXNOVERIFY`: fatal checks that the script and the C++ agree, `Class %s Member %s problem:
  Script=%i C++=%i`.
  - Fields at their offsets: `Actor.Owner` 0x3c, `Actor.TimerCounter` 0x4c,
    `PlayerPawn.Player` 0x5d4, `PlayerPawn.MaxStepHeight` 0x38c, `Pawn.HealthArmRight` 0x574,
    `Pawn.lastPhoneme` 0x57c, `HXPlayerPawn.InventoryGrid` 0x1144,
    `HXFlagReplicationInfo.ClientFlagCollections` 0x558,
    `HXScriptedPawn.ClientLastConEndTime` 0xa6c, `HXScriptedPawn.HealthArmRight` 0x574,
    `HXScriptedPawn.lastPhoneme` 0x57c, `HXDecoration.ItemName` 0x3a0, `HXConCamera.Player`
    0xbc.
  - Sizes, each the one its DLL registers: 23 of the game's classes (`XRootWindow`,
    `XViewportWindow`, `XFlagBase`, `XGC`, `XTextWindow`, `XFlag`, `XModalWindow`,
    `APlayerPawnExt`, `ADeusExPlayer`, `ADeusExLevelInfo`, `AScriptedPawn`,
    `ADeusExDecoration`, `ASkillManager`, `ASkill`, `AAugmentationManager`, `AAugmentation`,
    `UParticleIterator`, `UDeusExSaveInfo`, `UDeusExLog`, `UDataVaultImageNote`,
    `XGameDirectory`, `UDumpLocation`, `ULaserIterator`;
    [`DeusEx.dll`](deusex-dll.md#classes), [`Extension.dll`](extension-dll.md#classes)) and
    18 of HX's (`AHXActor`, `AHXCoopStart`, `AHXDecoration`, `AHXEffects`,
    `AHXFlagReplicationInfo`, `AHXGameReplicationInfo`, `AHXInfo`, `AHXMutator`,
    `AHXPlayerPawn`, `AHXRenderProxy`, `AHXScriptedPawn`, `AHXSteve`, `AHXTriggers`,
    `UHXConCamera`, `UHXFlagBase`, `UHXGoal`, `UHXNanoKeyInfo`,
    `UHXDecorationRenderIterator`).

### Destroyed actors

`CleanupDestroyed(level, force, compact)` (`0x10046710`) stands in for the level's own
([destroyed actors](engine-dll.md#destroyed-actors)): the frame calls it unforced and
compacting, `CoopSaveCurrentLevel` forced and compacting.

- **Compacting** takes the None slots after `iFirstDynamicActor` (+0x110) out of `Actors`,
  with no `Undeleted` check, unlike `CompactActors`.
- **Unforced**, it frees at most 4 actors a call, from the head of the level's `FirstDeleted`
  (+0x100, chained through +0xf8). First every reference to them is made None: in every live
  actor's object and struct properties (`0x10046da0`, into structs), and in the first
  viewport's player's window tree (`rootWindow`, +0x894; `0x10046e80`, children first, the
  first child at +0x13c, the next sibling at +0x148). Then the event manager is told, and
  each is deleted, `bDeleteMe` asserted.
- **Forced**, every actor and the window tree have their references to pending-kill objects
  cleared (`UStruct::CleanupDestroyed`; `0x10046ec0` for the windows), and every destroyed
  actor is deleted.

So a reference to a destroyed actor goes None within a few frames, where the game's waits for
128 of them. Run (a probe alone on Liberty Island, both engines): six actors destroyed in one
frame, each held by a window of the root's and by an actor, the four newest None in both the
next frame, all six the frame after.

### Small

- **`PaintProgress`** (`0x10042370`) is `UGameEngine::PaintProgress` (`0x10388740`), called
  only with a client that has a viewport: the game's reads the first viewport unchecked and
  faults on a dedicated server ([the loading screen](engine-dll.md#the-loading-screen)). HX's
  `LoadMap` (`0x1003f4ee`) and `CoopSaveCurrentLevel` (`0x100432a7`) call it.
- **`MatchViewportsToActors`** (`0x10045d60`) is a copy of the game's (`0x1038bf10`): for each
  viewport `Spawning new actor for Viewport %s`, its player spawned as a simulated proxy, a
  failure fatal. HX's `Browse` (`0x1003eca4`) and `LoadMap` (`0x10041cc5`) call it.

## Travel and saving

### Browse

`Browse` (`0x1003d9a0`) replaces Deus Ex's
([`DeusEx.dll`](deusex-dll.md#the-game-engine-travel-and-saving)) and calls neither it nor
Extension's, so `XGameEngineExt` never asks for the root window after a load
([the engine and the input](extension-dll.md#the-engine-and-the-input)); it calls
`UGameEngine::Browse` only for a server's address on a client. In order:

1. The run's slot: -3 on a dedicated server, -4 with `?listen`, else -2
   ([folders](#folders-and-missions)).
2. `Browse: %s`; a URL that does not parse fails (`InvalidUrl`).
3. `?failed` and `?entry` as the game's: the brush tracker dropped, the loaders reset,
   `NotifyLevelChange`, the Entry level made the level, the viewports' players matched again
   (`MatchViewportsToActors`), the audio's viewport reset; `?failed` with no pending level
   shows `ConnectionFailed` for 6 s.
4. `?restart`: the URL becomes the `DeusExLevelInfo`'s `MapName` with the last URL's portal
   and `?loadonly`, or the last URL itself with no `DeusExLevelInfo`; slot -2 is emptied,
   on a listen or dedicated server too, whose own folder is left as it was; the map loads
   from `Maps` with the browse's travel info. HX's frame gives it the level's own only for a
   `NextURL` of `?RESTART` alone, compared without case (`0x1003c3b0`, as the game's frame,
   [server travel](network.md#server-travel)): a listen server's game appends its player's
   `?Name` and `?Class`, so its restart takes the players' travel with `bNextItems`, else
   none, and Steve begins afresh. The level, entered with no `?listen`, is no longer a
   server. Run (a probe on Liberty Island setting a flag of Steve's, UNATCO HQ setting
   another, then `?RESTART`; both engines): on a listen server UNATCO HQ again with neither
   flag, its game's options `?loadonly` alone, `Current` emptied and `ListenCurrent` left;
   on a dedicated server, whose `NextURL` is `?RESTART` alone, UNATCO HQ again with the
   first flag and not the second, `Current` emptied and `ServerCurrent` left.
5. `?loadgame=` fails: `Loadgame is not supported.`
6. Not a local map: a server's address on a client goes to `UGameEngine::Browse`; any other
   internal URL fails (`ServerOpen`); an external one goes to `appLaunchURL`.
7. A local map, with or without `?load=`: the map tested is the `?load=` value, else the
   URL's; it logs `Doing load, not loadgame.` and `Current mission number is %d, next is %d`
   ([missions](#folders-and-missions)).
   - The next mission -1, or `?loadonly`: the run's folder emptied, the map loaded from
     `Maps`; a failure loads the current level's URL's map again, as the game's.
   - Otherwise, first, Steve's export, only with the level's `bNextItems` (`LevelInfo`+0x560
     bit 0): `Adding Steve to TravelInfo.`, and every `AHXSteve` in the level's package
     writes into the copy of the travel info the load takes ([Steve](#steve)), `!!! WARNING
     !!! Found multiple Steve's` from the second on. So a travel to a map outside every
     mission takes no Steve, nor does a `?loadonly`.
   - Another mission: as -1.
   - The same mission: `PruneCurrent`, then `CoopSaveCurrentLevel` into the run's folder
     ([saving a level](#saving-a-level)). The map's name is cut at its first `dx`
     (`FURL::DefaultMapExt`, with no dot and with case, where the game's cuts at `.dx`,
     DeusEx.dll `0x100119dd`); its generation is `[Generations] <map>` of `<folder>\Save.ini`,
     and `<folder>\<map>.s%02d` of it is looked for. With none, the URL's map loads from
     `Maps`. Else that file loads, by a relative travel's URL (`TRAVEL_Relative`) with the
     URL's portal, the global `0x10099420` holding its path meanwhile for the package map
     ([joining](#joining)). A failure fails the browse, and the old level plays on, pruned
     and saved (not confirmed by a run); a success makes the level's URL, its host emptied,
     the last URL.

Unlike the game's, it does not test `bStartingNewGame`, needs no `DeusExLevelInfo` to save,
and takes no `?pop`. HX's travels come here: the frame's server travel
(`HXGameInfo.ProcessServerTravel`),
`HXMapExit`, `HXTeleporter`, `HXInterpolationDummy`, and `HXPlayerPawn`'s `SwitchLevel`
(no items, so no Steve: the campaign's state is dropped), `SwitchCoopLevel` and `Switcheroo`
(with items). The cut at `dx` relies on `HXDeusExCampaignMutator`, which runs
`HXMutator.SanitizeURL` over every `MapExit.DestMap` and `Teleporter.URL`, taking out `.dx`
and spaces; a URL that keeps its `.dx` would miss the folder's file (not confirmed by a run).

### Folders and missions

The folders are under the ini's `SavePath` (`..\CoopSave` in HX's), by slot
(`SaveDirectoryPath`, `0x10042b60`; any other negative slot asserts):

| Slot | Folder |
|---|---|
| -4 | `ListenCurrent`: a listen server's run |
| -3 | `ServerCurrent`: a dedicated server's |
| -2 | `Current`: any other run's |
| -1 | `QuickSave` |
| 0 and up | `Save%04d` |

- **`DeleteSaveGameFiles(slot)`** (`0x10042e70`) resets the level's loaders and deletes every
  file of `<folder>\*.*`, the folder named by its slot where the game's takes its name.
- **`DeleteSaveGameDirectory(slot)`** (`0x10042440`), for `DELETEGAME`, removes the folder's
  tree.
- **`GetMissionNumberFromString`** (`0x100425d0`): a map's two leading digits, else -1, as
  the game's.
- **`GetCurrentMissionNumber`** (`0x10042540`): `GetDeusExLevelInfo`'s `missionNumber`, -1
  with none.
- **`GetDeusExLevelInfo`** (`0x10042a50`): the first `DeusExLevelInfo` in the game level's
  `Actors`, where the game's takes the first among all objects
  ([`DeusEx.dll`](deusex-dll.md#the-game-engine-travel-and-saving)): HX never answers with a
  level left behind.

### Saving a level

**`PruneCurrent`** (`0x100444e0`), before each save, asserts `GLevel` and calls the script
event `PruneCurrent(out byte bTransient)` on every actor whose class has one, `bTransient`
given as the actor's `RF_Transient`; the actor's `RF_Transient` is then set or cleared as the
event left it, and a save writes no transient object
([what a save writes](core-dll.md#packages-and-linkers)). The events of `HXGameInfo`,
`HXPlayerPawn`, the game's, player's, flag's, image's and nano key's replication infos,
`HXBarkManager` and `HXDataLinkManager` all set it, so none of them is saved;
`HXPlayerPawn`'s also destroys its replication info, augmentations, skills, themes, carried
decoration and shadow. `HXActor`'s does nothing, so every other HX actor is saved.

**`CoopSaveCurrentLevel(slot)`** (`0x10043260`) is the game's `SaveCurrentLevel`
([`DeusEx.dll`](deusex-dll.md#the-game-engine-travel-and-saving)) with these steps; only
`Browse` calls it, just before `LoadMap`:

1. The level action Saving and `PaintProgress`; unless the quick save, the slow task
   `Saving` (DeusEx's text).
2. The movers' classes put back from HX's to the game's ([CoopSetupActors](#coopsetupactors)).
3. The brush tracker deleted.
4. The AI event manager (`LevelInfo.EventManager`) deleted, and every object it is the outer
   of, the reference set None; `HXGameInfo.InitGame` calls `InitEventManager` again.
5. `CleanupDestroyed`, forced and compacting ([destroyed actors](#destroyed-actors)).
6. The folder made.
7. The generation, `[Generations] <package>` of `<folder>\Save.ini`, and the file
   `<folder>\<package>.s%02d` of it plus 1: the name the level's package's, not the
   `DeusExLevelInfo`'s `MapName`, so no `DeusExLevelInfo` is needed.
8. A conformed save: a package `<package>_OLD` and a linker on the original map's file
   (`appFindPackageFile`, asserted; `LOAD_NoWarn|LOAD_NoVerify`), and `SavePackage` of the
   level's package, the level its base, no flags, to the file, with that linker to conform
   to. So the save keeps the map's names and exports in their order and its GUID, one
   generation on ([a conformed save](core-dll.md#packages-and-linkers); its saves of Liberty
   Island and UNATCO HQ read against the maps).
9. Saved: `Generations` set to the new number, and the file of the number before the old one
   deleted when there is one, so the last two stay. Not saved:
   `CoopSaveCurrentLevel: SavePackage() failed`.
10. `[Restore] LastMap=<package>` and `LastPortal=(Unknown)` written and the ini flushed;
    nothing reads them.
11. Every mover's `SavedPos` (+0x4ac) set to (-1,-1,-1).
12. A new brush tracker unless `-NoBrushTracker` (read once, `0x10098f1c`, `0x10099418`), so a
    dedicated server, whose load makes none, has one from its first save on; the slow task
    ended, the level action None, the cache flushed.

The movers are not switched back to HX's classes after the save. `CoopPruneSteve`
(`0x10045430`), exported, is an older cleanup that nothing calls.

### The travel info

`ExportTravel` (`0x100460e0`, static) is the game's travel export (`0x10391740`,
[a level's tick](engine-dll.md#a-levels-tick)) in the same format (`Class=%s Name=%s
Ptr=%08x`, CR LF, `{`, `Prop[%i]=`, newlines as `\`, a reference as `%08x %s`, `}`), but:

- the root must be an actor (an assertion);
- only an object property that holds an actor (its class `Actor` or below) is written and
  followed: the flag base, the goals, notes and keys, and classes are left out, where the
  game's follows any object; None writes nothing.

The frame's travel calls it for each `AHXPlayerPawn` with a player, keyed by its
`PlayerReplicationInfo.PlayerName`, and so does `AHXPlayerPawn`'s `ExportTravel` native
([the player](#the-player)), which keeps a leaving player's in the level's travel info, so
that a `Current` save keeps it. The arrival is the game's `ULevel::SpawnPlayActor`.

## A map's load

`LoadMap` (`0x1003f3d0`) is `UGameEngine::LoadMap` (`0x1038c1f0`;
[the map load's collection](engine-dll.md#the-map-loads-collection),
[the loading screen](engine-dll.md#the-loading-screen),
[a level's start](engine-dll.md#a-levels-tick)) with these changes:

- **Gone**: the `LoadMap: %s` line, `?push`'s save as `Game%04i.dxs`, and the hub stack's
  step (`?pop`, `?peer`, `load`): a level's `HubStackLevel` stays as its file holds it.
- **The old player**: before each viewport's actor is destroyed, a `PlayerPawnExt`'s
  `flagBase` (+0x890) is set None.
- **The old level**: after its loaders are reset and its tracker and drivers deleted,
  `ExitLevelCleanup` ([below](#exitlevelcleanup)).
- **The co-op starts**: right after the load, for a level that is a server's (`IsServer`)
  and whose `LevelInfo.Game` is None, `HX.HXCoopStart` must load (`CoopStartClass`
  asserted), then `HXSpawnCoopStarts` with the level and the URL's map, the name the level was
  loaded by ([co-op starts](#co-op-starts)). A client's level passes the test too, its net
  driver not yet hooked up to it (that comes after the package map's `HAVE GUID` lines); its
  starts go with the map's other actors that are neither static nor kept when the level
  begins.
- **`CoopSetupActors`**, after the package map's `Compute`, outside the editor, with no
  package map or one that holds package `HX`: on a client, only for an HX server
  ([below](#coopsetupactors)).
- **`VerifyClasses`**, unless `-HXNOVERIFY` ([the checks](#the-checks)).
- **`bSpawning`**: once the URL's options are read, every actor whose class has a bool
  property `bSpawning` has it set (`0x100421d0`, through `ImportText`, a public, non-const
  one alone). HX's classes declare it and clear it in `SetInitialState`;
  `HXCampaignMutator.PreBeginPlay` reads it to pass over its first `PreBeginPlay`, inside its
  own spawn.
- **The game's class** as the game's (`?game=`, `DefaultGameType`, the ini's `DefaultGame`
  or `DefaultServerGame`, `Game class is '%s'`).
- **A fresh map**: the game spawned, then `HX.HXSteve`, whose `FlagBase` (+0x324) is a new
  `UHXFlagBase` (0x12c) in the transient package, and Steve's `Init` with the travel info and
  the URL's portal ([Steve](#steve)): none for the Entry level's load, which the engine's start
  makes for a client alone, and `Browse`'s copy for every other, a dedicated server's first
  map's too (runs: `Initializing Steve.FlagBase` logged at Entry's load and where the travel
  holds Steve's flags alone, in both engines); then the game's passes over every actor, and `Bringing
  %s up for play...`, without the tick rate the game's line has.
- **A level that has begun play** (from a `Current` folder, its game and Steve not saved):
  `bBegunPlay` cleared, so the spawns send no events; the game and Steve spawned and set up as
  above; their `Touching` cleared, their execution initialised, `bBegunPlay` and `bStartup`
  set again; then, for those two alone, `InitGame`, `PreBeginPlay`, `BeginPlay`,
  `SetActorZone`, `LastRenderTime` -10, `PostBeginPlay` and `SetInitialState`; `Bringing %s
  up again for play...`.
- **The rest** as the game's: every actor's `PostPostBeginPlay`, the actor list's order,
  `MatchViewportsToActors` (HX's copy), the last URL, `SaveURLConfig`. The brush tracker only
  with a client and without `-NoBrushTracker`.

`HXGameInfo.InitGame` finds Steve by `AllActors` and takes its `FlagBase`;
`HXGameInfo.FindCoopPlayerStart` takes the co-op starts.

### The game's actors made HX's

No class is swapped as a package loads: no linker remaps one. The movers' classes are
switched in place ([CoopSetupActors](#coopsetupactors)); every other placed actor is made
destroyable there, and HX's script replaces it as it begins play. `GameInfo.IsRelevant`, as
`HXGameInfo.IsRelevant` (state `InIsRelevant`), asks the mutators' `CheckReplacement`
(`HXDeusExCampaignMutator`, `HXTailMutator`), whose `HXMutator.SpawnSuccessor` spawns the HX
class with the original's `Tag`, place, rotation and physics, no collision failure
(`SpawnEx`, [spawning](#spawning-and-calls-by-name)); `DuckCallSucceeds` calls the
successor's `Succeeds(Other)`, which copies the original's state; the original is destroyed
unless it is still static or no-delete. Later spawns go through `ModifyActorClass` and
`ModifyInventoryClass`.

### CoopSetupActors

`CoopSetupActors` (`0x10043f80`) asserts `GLevel` and loads seven classes through the
package map (`LOAD_Throw`): `Engine.Effects`, `DeusEx.DeusExMover`, `DeusEx.BreakableGlass`,
`DeusEx.BreakableWall`, `HX.HXMover`, `HX.HXBreakableGlass`, `HX.HXBreakableWall`. Then each
actor, by its class:

| Class | What it gets |
|---|---|
| `Decoration`, `Effects`, `Projectile`, `Triggers` | with a `LightType`, `bStatic` and `bNoDelete` kept, `Keeping %s as bStatic and bNoDelete due to LightType!=LT_None.` (or the line for the one it has); else both cleared. `bGameRelevant` (+0x1a0 bit 7) cleared either way |
| `DeusExLevelInfo` | `RemoteRole` None, `bNoDelete` set |
| `ZoneInfo` | `bGameRelevant` cleared |
| `CameraPoint` | `bNoDelete` set, `RemoteRole` None; the class's state `Idle` has its `StateFlags` (+0x7c) set to 0, so it is no longer auto; failing, `Failed to set state CameraPoint.Idle to 0` |
| `InterpolationPoint` | `bNoDelete` set, `RemoteRole` None; the class's `BeginPlay` made simulated (`FUNC_Simulated`, 0x100 at +0x6c), so that a client links its own paths |
| a brush with a model | its class (+0x24) swapped in place, the class exact: `DeusExMover` to `HXMover`, `BreakableGlass` to `HXBreakableGlass`, `BreakableWall` to `HXBreakableWall` |

`HXMover` declares `DeusExMover`'s 43 variables again, in their order, only `curPick`'s type
changed (`HXLockpick`), so the swap keeps every value. Runs (a private probe on a dedicated
server with a client of it): UNATCO HQ's 27 movers' `Class` `HX.HXMover` on `HCC.exe server`
and on `HX.exe`'s client; Liberty Island's client keeping no static decoration (HX's are sent)
and the map's 32 interpolation points, each linked by its own `BeginPlay`. A state's or function's flags changed
here are its class's, for the rest of the run. `HXTailMutator` keeps the
`InterpolationPoint`s and replaces the `CameraPoint`s, `MapExit`s and `Teleporter`s.

### Co-op starts

`HXSpawnCoopStarts` (`0x10025e20`) compares the map's name with 80 of the game's maps
(00_Intro to 99_Endgame4) in turn, without regard to case (`appStricmp`), and spawns the
starts of the one that matches, compiled in, through `HXSpawnSingleStart` (`0x10025cb0`):
1,268 `AHXCoopStart`s in all, 4 to 98 a map (98 in 04_NYC_Street), the output of the
`spewcoopstarts` commandlet ([commandlets](#commandlets)). The table is code, not data: each
start is a call whose sixteen arguments are constants pushed before it -- the level, the tag,
the place (three floats), the rotation (three ints), the priority, `bDefaultStart`, the team,
`bInitiallyEnabled`, the enable and disable tags, the message and the collision. The compiler
made each map's last call one shared call at the function's end (`0x1003a1c0`, the last
arguments pushed there or just before), which each map's block jumps to (the last falls into
it), so the code holds 1,189 calls for the 1,268 starts.

`HXSpawnSingleStart` spawns each through the level's `SpawnActor`, with no name, owner or
instigator and a spawn that may fail, then sets its `Tag` (its portal's name,
`ToBarFrontEntrance`, or the class's own, `HXCoopStart`), `Priority` (+0x330),
`bDefaultStart` (+0x324 bit 2), `TeamNumber` (+0x334), `bInitiallyEnabled` (bit 0),
`EnableTag` (+0x328), `DisableTag` (+0x32c) and `EnabledMessage` (+0x338), and makes it
collide with actors as its entry says, blocking nothing (`SetCollision`). Of the 1,268, 572
are default starts, 7 start disabled, 13 have an enable or a disable tag, 5 collide, all are
team 0 and carry `Enabled new CoopStart.`; 906 have priority 0, the rest 100 to 1000. A
failure logs `Failed to spawn coop start at (%f,%f,%f) with Tag '%s'`. A level from a
`Current` folder, which has no game, is loaded by its file's path ([Browse](#browse)), which
names none of the 80 maps, so none are spawned again.

### ExitLevelCleanup

`ExitLevelCleanup` (`0x10044630`, static), from `LoadMap`, goes over every object of each of
these classes, so that the old level and its Steve can be collected; eliminated is flagged
`RF_EliminateObject` (0x400):

- `ConCamera`: `cameraActor`, `conLightSpeaker`, `conLightSpeakingTo`, `firstActor`,
  `secondActor`, `lastFirstActor` and `lastSecondActor` set None; eliminated.
- `ConEventAnimation`'s and `ConEventTrade`'s `eventOwner`, `ConEventMoveCamera`'s
  `cameraActor`, `ConEventSpeech`'s `speaker` and `speakingTo`, `ConEventTransferObject`'s
  `fromActor` and `toActor`: None.
- Each `Flag`'s `flagBase` and `nextFlag`, each `FlagBase`'s 64 `hashTable` entries: None;
  all eliminated.
- `DeusExPlayer`'s `KeyList`, `conHistory`, `FirstGoal`, `LastGoal`, `FirstNote`, `LastNote`,
  `FirstLog` and `LastLog`: None.
- Every `DeusExNote`, `DeusExGoal` and `DeusExLog`: `next` None (by the property's name);
  eliminated.
- The level's game, when an `HX.HXGameInfo`: its `FirstNote`, `LastNote`, `FirstLog` and
  `LastLog` None.

With `HXGameInfo.ProcessServerTravel`'s travel, the notes are lost at every map change.

## Steve

`AHXSteve` (0x43c bytes, transient) carries the campaign's state from map to map in the
travel info. Its fields: `FlagBase` +0x324, `SkillPointsTotal` +0x328, `FirstGoal` +0x32c,
`KeyList` +0x330, `Portal` +0x334, `DataVaultImages[63]` +0x340.

- **`Init(TravelInfo, Portal)`** (`0x10022c00`) runs the reader of each key the travel info
  holds, in the table's order, and sets `Portal`; with no travel info it logs `Initializing
  Steve.FlagBase`.
- **`ExportTravel(TravelInfo)`** (`0x10023cb0`) writes each key as lines ended by CR LF
  (through an `FStringOutputDevice`):

| Key | A line | Read back |
|---|---|---|
| `__INTERNAL_Steve_Flags` | `Name=%s Type=%i Expiration=%i Value=%i`, the bool flags alone, only with a `FlagBase` | `InitFlagBase` (`0x10023150`): type 0 sets the bool, added, with its expiration, set for a value not 0; types 1 to 6 warn `Unhandled Flag: Name=%s Type=%i Expiration=%i Value=%s`; a field missing warns `Found malformed Flag line in TravelInfo.` |
| `__INTERNAL_Steve_SkillPointsTotal` | `%i` | `appAtoi` |
| `__INTERNAL_Steve_Goals` | `GoalName=%s bPrimaryGoal=%i bCompleted=%i Text="%s"` | `InitGoals` (`0x100234f0`): a new `HXGoal` (0x40, in the transient package) each, appended to `FirstGoal`; `Found malformed goal line in TravelInfo.` |
| `__INTERNAL_Steve_NanoKeys` | `KeyID=%s Description="%s"` | `InitNanoKeys` (`0x100238f0`): a new `HXNanoKeyInfo` (0x3c) each, appended to `KeyList`; `Found malformed NanoKey line in TravelInfo.` |
| `__INTERNAL_Steve_Images` | `ImageClass=<path name>` | `InitImages` (`0x10023b10`): each class loaded (`StaticLoadClass`, an `Inventory`) into slots 0 to 62 in order, `Failed to ImageClass for DataVault: %s`; `Found malformed Images line in TravelInfo.` |

The values are read with `Parse`, which takes quotes off, a line at a time (`ParseLine`), so
a text holding a quote or a line break breaks its line. Notes, and flags of any other type,
do not travel. `HXGameInfo` and the mission scripts (`RandomizeEvents`, `InitSkillPoints`)
use Steve.

## The level and the network

### Taking the game's place

HX makes no level, model or channel of its own. `UHXLevel` and `UHXModel` are registered at
`ULevel`'s and `UModel`'s sizes and never made, and none of the three classes adds a field;
their constructors (`0x1000a570`, `ULevelBase`'s default inline; `0x1000b0f0`, `UModel`'s,
`RootOutside` 1 and `EmptyModel(1, 0)`; `0x1000b920`, around `UActorChannel`'s) make the
class default objects alone.

- **The level.** The engine's frame tests each level it ticks (`0x1003c654`, `0x1003c6b2`,
  `0x1003c757`): one whose class is exactly `Engine.Level` has `UHXLevel::Tick` called on it,
  then HX's `CleanupDestroyed(level, 0, 1)`; any other its own virtual `Tick` (+0x5c).
  `UHXLevel::Tick`, by the same test, calls HX's `TickNetClient`, `TickDemoPlayback`,
  `UpdateTime`, `TickNetServer` (and from it HX's `ServerTickClient`) and `TickDemoRecord`.
- **The model.** `UHXModel`'s functions run on the level's `Model` (+0x98).
- **The channel.** `UHXActorChannel`'s static constructor (`0x10015250`) puts its class in
  `UChannel::ChannelClasses[CHTYPE_Actor]`, `ChType` 2 in its defaults; its vtable
  (`0x1005fe70`) is `UActorChannel`'s but for the destructor. What makes it count is the
  patch: `Init`, right after its version line (the call at `0x1003b15a`), runs `0x10016ad0`
  (`HXNet.cpp`, `EnginePkgUHXActorChannel`), which makes `Engine.dll`'s export
  `?ReplicateActor@UActorChannel@@QAEXXZ`, a jump to its code
  ([`Engine.dll`](engine-dll.md#the-binary)), writable (`VirtualProtect`, 0x40), writes over
  it a five-byte jump to `UHXActorChannel::ReplicateActor` (`0x10018640`), and puts its
  protection back, with no trampoline. Every `ReplicateActor` in the process is then HX's:
  the ticks', `ProcessRemoteFunction`'s first send, a demo's recording. It is the only code
  patch in `HX.dll`.

### The level's tick

`UHXLevel::Tick` (`0x10049620`) is `ULevel::Tick` (`0x103a51a0`,
[a level's tick](engine-dll.md#a-levels-tick)) but:

- the actors' time is held to 0.002..0.4 s (`0x10064004`), where the game's is held to
  0.005..0.4 s (`0x1042adcc`);
- on a net client, every dynamic actor's `DistanceFromPlayer` is its distance to the first
  viewport's player pawn, when that has a `Player`; the game's sets it in single player alone
  ([stasis and render time](engine-dll.md#stasis-and-render-time));
- standalone and on a listen or dedicated server, the pawns of `LevelInfo.PawnList` (the next
  at +0x498) with `bIsPlayer` (+0x318 bit 1) that are `HXPlayerPawn`s are listed, and each
  dynamic actor's `DistanceFromPlayer` is its distance to the nearest, 1e10 with none. An
  `HXScriptedPawn` (with `bIsPawn`) gets instead its `PlayerDistances[32]` (+0xa70, 8 bytes
  each: the player, the distance) zeroed, filled in the `PawnList`'s order up to 32, and
  sorted nearest first (`0x1004c4b0`, its compare `0x1004c6d0`), its `DistanceFromPlayer`
  the first's distance, or 1e10;
- it ends without `CleanupDestroyed(0)` (vtable +0x98): the game engine calls HX's.

HX's script relies on them: `HXScriptedPawn`'s `Tick` (its `bTickVisibleOnly` tiers), its
`GetNearestPlayer`, `GetPlayerDistance` (which `HXBarkManager` asks) and its choice of a
player; the effects a client draws by `DistanceFromPlayer` (`HXParticleGenerator`,
`HXLaserEmitter`, `HXElectricityEmitter`, `HXIncenseBurnerSmokeGenerator`); and
`HXPawnGenerator` on servers.

`TickNetServer` (`0x1004a6c0`) is the game's (`0x103a4530`). `TickNetClient`
(`0x1004a470`), `TickDemoRecord` (`0x1004ba10`), `TickDemoPlayback` (`0x1004bd30`) and
`UpdateTime` (`0x1004be90`) are copies of the game's (`0x103a2f10`, `0x103a4b90`,
`0x103a4f70`, `0x103a08f0`), the first two calling HX's `ReplicateActor`, as the patch makes
every call anyway.

### What a client is sent

`ServerTickClient` (`0x1004ad10`) is the game's (`0x103a3500`,
[replication](network.md#replication)) step for step: the view and its prediction through
`NF_NotVisBlocking`, the candidates and their 0.023 s stagger, the priority (`0x1004b860`,
the game's `0x103a4350`) and its sort (`0x1004c800`), `RelevantTimeout`, the channels,
`IsNetReady`, `ReplicateActor`. It differs:

- whether an update is due compares `LastRepTime` and the driver's `Time` as floats, the
  products truncated (`0x1004b4a0`-`0x1004b4b6`), where the game's rounds double products
  (`fistp`): the same rate, its phase off by up to half a period;
- relevance is HX's `ActorCanSee` (below);
- each of `AdditionalViews[0..2]` is tried from its own place, where the game's tries the
  first three times;
- a relevant actor's `LastRenderTime` is set to the level's `TimeSeconds`, as a drawn
  actor's is ([render time](render-dll.md#render-time)): `HXScriptedPawn`'s tick relies on
  it;
- no time is counted: the `Cull=` line prints zeros.

**`ActorCanSee`** (`0x100493b0`, static: the actor, the connection's player, the viewer, the
sight point) has the game's rules (`0x103a3120`), but a pawn's `SelectedItem` (+0x3d8) counts
as its pawn, as its `Weapon` (+0x3d0) does, and both its line checks are
`UHXModel::FastRepLineCheck`.

**`FastRepLineCheck`** (`0x100524b0`, its walk `0x100525f0`) is `UModel::FastLineCheck`
(`0x103f3280`, its walk `0x103f33a0`; [traces](engine-dll.md#traces)), but a node lets the
line through also when its own surface's `PolyFlags` hold any of 0x47 (`PF_Invisible`,
`PF_Masked`, `PF_Translucent`, `PF_Modulated`), where the game's passes `NF_NotCsg` alone:
its own surface, not its coplanar nodes', an `iSurf` of -1 not checked. Each axis's
difference is stored as a float before it is scaled, which can move the last bit.
`ActorCanSee` and the `FastRepTrace` natives use it ([traces](#traces)).

Runs (a private probe on a dedicated server, `HCC.exe server` and DXEngine's, each with the
other's client and DXEngine's with its own, on UNATCO HQ): a sprite the client's view reaches
only through glass, a line `FastTrace` stops at and `FastRepTrace` passes, is sent, one behind
a wall is not; with three extra views on the player, a sprite seen from the second alone and
one seen from the third alone are sent, one seen from none is not; a hidden item that a pawn
in view holds as its `SelectedItem` is sent, one it holds otherwise is not, nor the selected
item of a pawn out of view; each actor sent has its `LastRenderTime` the level's time, the
others keep theirs (a dedicated server draws nothing). A conversation an NPC starts as the
player comes near moves the player's view to its camera, and what is sent with it.

### The actor channel

`UHXActorChannel::ReplicateActor` (`0x100152e0`, `HXChan.cpp`, Unreal Tournament's code) is
the game's (`0x103fead0`, [replication](network.md#replication)) step for step but one: the
compare of a script property (`0x10016170`) takes a struct member by member, recursively,
and any other value by `Identical` against the copy (the channel's, the class's defaults
before its first), without the package map, where the game's first makes a reference the
client cannot resolve None (`CanSerializeObject`, vtable +0x54); a value `NetSerializeItem`
could not resolve has its copy cleared after the send. So read, a reference to an actor the
client has no channel for would go again, as None, at every update. It does not: a private
probe on a listen server, its reference set to a hidden actor no client is sent, then to
another, then None, then the first again, the original's server with its own client (in a
second Wine prefix) and with DXEngine's: no None reached either client, and the reference
did once the actor was shown and relevant, as with the game's channel. What keeps it from
going is not in the code read here. The native lists make such references None themselves.

Runs of the rest (the same probe, each engine's server with each engine's client): an
`HXScriptedPawn`'s six health values (with `bIsHuman`), its carried decoration, its
`ClientLastConEndTime` and its head turns, and the host's carried decoration (carried by
`PutCarriedDecorationInHand`), head health and head turn, reach every client alike, the turns
unpacked to the same tween rates (6.667 and 4.0 from 0.15 s and 0.25 s).

### The native lists

| Class | Its list | Against the game's ([the native lists](network.md#the-native-lists)) |
|---|---|---|
| `AHXPlayerPawn` (`0x1001ec70`) | `AActor`'s, then its own `Pawn` and `PlayerPawn` parts, not `APawn`'s or `APlayerPawn`'s | the `Pawn` part `0x10363bc0`'s, but `carriedDecoration`, `SelectedItem` and `HealthHead` to `HealthArmRight` go to every client, not the owner alone; the `PlayerPawn` part `0x103649d0`'s, its `bNeverAutoSwitch` pushing index 0 too; blend slot 3 |
| `AHXScriptedPawn` (`0x10021580`) | `AActor`'s, then its own `Pawn` part | `carriedDecoration` to all, the six `Health` values to all with `bIsHuman` (+0xa20 bit 1), the rest to the owner as the game's; blend slot 3; and, while the class has `CLASS_NativeReplication`, its own `bClientInWorld`, `bClientHostileTowardsPlayers`, `bClientIsSpeaking`, `HXSeatActor`, `HXSeatHack`, `bClientSitting`, `bClientDancing`, `ClientSimulatedAction`, the two familiar names (by `appStricmp`), `ClientLastConEndTime`, and `EMPHitPoints` with `bIsRobot` (+0xa20 bit 0): the script's statements without their `Role` test |
| `AHXDecoration` (`0x1001c990`) | `Actor`'s written again, not called | the same but with `bSpecialDesired` (+0x424 bit 3): `Rotation` in the first bunch alone, and `bFixedRotationDir`, `bRotateToDesired`, `RotationRate` and `DesiredRotation` at every change under `PHYS_Rotating`, which the game's sends in the first bunch alone; and `bClientHighlight` (+0x424 bit 0) |
| `AHXEffects` (`0x1001c750`) | `AActor`'s | and `Rotation`, with the authority and `bReplicateRotation` (+0x330 bit 1), in a first bunch of an actor that is no mesh or brush, or with a simulated remote role: a simulated mesh effect lists it twice in its first bunch |

- **Blend slot 3**: `BlendAnimSequence[3]`, `SimBlendAnim[3]` and `BlendAnimMinRate[3]`, each
  its `RepIndex` + 3, sent with the authority, a mesh, and a remote role up to simulated
  proxy, unless the client owns the actor with `bClientAnim`, or for a demo's recording. The
  game's sends no blend slot.
- **The compares**: a float by its bits, a name by its index, an object with
  `CanSerializeObject` making None what cannot go. The script keeps the statements, commented
  out (`HXScriptedPawn`, `HXDecoration`).
- **Receiving slot 3.** `PreNetReceive` and `PostNetReceive` of `AHXPlayerPawn`
  (`0x10020220`, `0x100202c0`) and `AHXScriptedPawn` (`0x10022980`, `0x10022a20`) are
  `AActor`'s (`0x10367f00`, `0x103680d0`; [replication](network.md#replication)) and slot
  3's: the first keeps `SimBlendAnim[3]` in a static both classes share; the second, when any
  of its four numbers changed, sets `BlendAnimFrame[3]` to X × 0.0001, `BlendAnimRate[3]` to
  Y × 0.0001, `BlendTweenRate[3]` to Z × 0.001 and `BlendAnimLast[3]` to W × 0.0001, each x87
  product stored as a float, unpacking what `PlayBlendAnim` packs
  ([blend animations](engine-dll.md#blend-animations)); a negative last frame is made
  positive and `BlendAnimMinRate[3]` raised to 0.5 at least; no loop flag is set. So clients
  see the head turns (`PlayTurnHead`'s slot 3).

## Traces

`HXActor`'s traces answer the texture a line meets; each runs from `TraceStart`, by default
the tracer's location, to `TraceEnd`.

**`FindTexture`** (`UHXLevel`, `0x100529a0`), under each of them, clears its four outputs,
then:

- for a hit on the level (the actor its own `LevelInfo`): `UHXModel::FindNode` (`0x100527a0`)
  on the level's model (+0x98), from the hit's node (its `Item`, +0x28) and place, walks the
  node's coplanar chain (`iPlane`, +0x28) to the first node with a surface and vertices whose
  polygon holds the point (each edge's side test, the edge crossed with the normal, agreeing;
  `Verts` +0x68, `Points` +0x88) and gives that node's surface (`iSurf`, +0x1c); -1 at either
  step gives nothing;
- for a hit on an actor with a `Brush` (a mover): the surface of the brush's node `Item`, with
  no coplanar search and no -1 check (a bounds assertion);
- its outputs: the surface's `Texture`, the texture's name (+0x20), its group (its outer's
  name, only when that outer has an outer itself: a texture straight in its package has None)
  and the surface's `PolyFlags` (+4).

The natives:

- **`TraceTextures`** (3250; `AHXDecoration` 3340, `AHXPlayerPawn` 3300, `AHXScriptedPawn`
  3321; `0x1001a900`), an iterator: `BaseClass`, then out `HitActor`, `Texture`,
  `TextureName`, `TextureGroup`, `TextureFlags`, `HitLocation`, `HitNormal`; `TraceEnd`,
  optional `TraceStart` and `TraceExtent` (0). `ULevel::MultiLineCheck` (the level's vtable
  +0xc8) with actors, its own `Level` as the `LevelInfo` and node flags 0; each hit's actor,
  place and normal (+4, +8, +0x14) and `FindTexture`'s outputs, until the loop ends
  (`IteratorNext`, `IteratorPop`); `BaseClass` read, `Actor` by default, and never tested. It
  is the game's `TraceTexture` ([traces](engine-dll.md#traces)) but:
  - it gives the `Texture` too;
  - a hit on the level gives the surface of the coplanar polygon that holds the hit, where
    the game's gives the hit node's, its plane's head; with no polygon holding it, no texture
    and flags 0 (a comment in HX's script finds so in 10_Paris_Club's vent shafts);
  - a hit on a mover gives its brush's surface, where the game's gives nothing for an actor;
  - the group is `FindTexture`'s, where the game's gives the package's name for a texture
    straight in it;
  - at its end it clears `HitActor` and the four texture outputs, where the game's clears the
    actor alone.

  Its callers: the footsteps and the floor (`HXPlayerPawn`'s and `HXScriptedPawn`'s
  `FootStepSound` and `GetFloorMaterial`), a wall (`HXPlayerPawn.GetWallMaterial`,
  `HXAutoTurret.GetWallMaterial`), the beams (`HXLaserEmitter`'s and `HXElectricityEmitter`'s
  `CalcTrace`), and the exec `TT2` (`HighlightCenterObject`'s call is dead).
- **`StaticTraceTextures`** (3252; `0x1001acf0`): `Other` first, then the same through
  `Other`'s level, `TraceStart` by default `Other`'s location, but the `LevelInfo` it passes
  is the calling context's `Level` (`0x1001af69`). HX's callers call it as a static function
  of the class `HXActor`, so in the context of the class's defaults (`UClass`+0x4d4), whose
  `Level` is None: given no `LevelInfo`, the check meets actors alone, the whole line, through
  walls.
  So `HXWeapon.GetWallMaterial`, which passes itself and stops at the level or a mover, finds
  a mover's own group and never the BSP's; `HXConCamera.ActorObstructed`'s test for an
  invisible wall never meets the BSP. With `Other` None it logs `StaticTraceTextures()
  failed: Other is None.` and returns without passing the loop's end, which no caller
  reaches.
- **`TraceSingleTexture`** (3251; 3341, 3301, 3322; `0x1001b170`): `BaseClass`, unused, then
  out `Texture`, `TextureName`, `TextureGroup`, `TextureFlags`, `HitLocation`, `HitNormal`;
  `TraceEnd`, optional `TraceStart`, `bTraceActors` (by default the tracer's
  `bCollideActors`) and `TraceExtent` (0); it returns the actor hit. `SingleLineCheck`
  (vtable +0xc0) from the tracer, flags 55 tracing actors, else 6, the result's time 1.0 and
  item -1 to begin with; the place and normal zero when nothing is hit; then `FindTexture`.
  It is the game's `Trace` ([traces](engine-dll.md#traces)) with the texture. No script of
  HX's calls it.
- **`StaticTraceSingleTexture`** (3253; `0x1001b4a0`): the same on `Other`'s level, `Other`
  the tracer; it asserts `Other`'s level (`HXActor.cpp` 338, fatal); with `Other` None it
  logs `StaticTraceSingleTexture() failed: Other is None.`, the result unset. No caller.
- **`FastRepTrace(TraceEnd, TraceStart)`** (3254; 3343, 3303, 3324; `0x1001a660`):
  `FastRepLineCheck` on the level's model, its byte the answer: `FastTrace` passing
  see-through surfaces ([what a client is sent](#what-a-client-is-sent)).
  `HXScriptedPawn.AICanShoot` calls it twice, where the game's calls `FastTrace`.
- **`StaticFastRepTrace(LevelInfo, TraceEnd, TraceStart)`** (3256; `0x1001a7a0`): the
  `LevelInfo`'s level's model; with None, `StaticFastRepTrace() failed: Level is None.`, the
  result unset. No caller.

## Strings

- **`StringToName(S)`** (3260; `AHXPlayerPawn` 3313, `AHXScriptedPawn` 3320, `AHXMutator`
  3360, `AHXDecoration` by name; `0x1001ea10`) jumps to Extension's
  `XExtensionObject::execStringToName` ([small](extension-dll.md#small)), which stops the
  game at a character other than A to Z, a to z, 0 to 9, `_` and `-`. Some 58 calls of HX's
  script make names of flags (`_Played`, `_Dead`, the missions'), nano keys, and emails' and
  files' names (`HXConPlay`, `HXGameInfo`, `HXMissionScript`, the `HXDataLink` classes,
  `HXComputerUIWindow`).
- **`Strihash(S)`** (3261; `0x1001c4d0`; the string coerced, an int answered): `appStrihash`
  ([names hashed and compared](core-dll.md#names-hashed-and-compared)). `HXGameInfo`'s
  JCDenton mode takes the hash, its top bit cleared, scaled to one of five player classes.

## Conversations

- **`BindConversationList(ConvListClass, Target)`** (3270; `0x1001ba40`): loads the
  `ConversationList` object of that name (`LOAD_NoWarn`) and, when it loads, gives the target
  its conversations with ConSys's `DConversationList::BindConversations` (`0x10010b70`,
  [an actor's conversations](consys-dll.md#an-actors-conversations)), answering true; else
  false. It is the game's `ConBindEvents` ([`DeusEx.dll`](deusex-dll.md#conversations))
  without its look for the `DeusExLevelInfo`: for any actor, with the caller's list.
  `HXPlayerPawn.ClientStartDataLinkTransmission` calls it for itself,
  `HXDataLinkManager.StartDataLinkTransmission` for the game.
- **`BindConsersationEvents(Con, ConBoundActors[10], InvokeActor, Scope)`** (3271, its name
  so spelt; `0x1001bbc0`): asserts `Con` and the level `Scope` (`HXActor.cpp` 431, 432);
  empties the ten slots of the caller's array (through `GPropAddr`, as the game's
  `BindEvents`); then offers each actor of `Scope`'s `Actors`, in their order, passing over
  None and `bDeleteMe`, once, when it has `bIsPawn` or is a `Decoration`, to ConSys's
  `BindEventsToActor` (`0x100100f0`: the `BindName` and invoker tests, `AddBoundActor`). The
  game's `BindEvents` (`0x1000fec0`,
  [a conversation's actors](consys-dll.md#a-conversations-actors)) offers every `Pawn`, then
  `Decoration`, then `PlayerPawn` in memory: a player twice, other
  levels' and deleted actors too, an event keeping the last actor offered. HX's binds none of
  another level, the Entry level's among them, whose binding crashed now and then (HX's
  changelog). Its callers: `HXConPlay.StartCoopConversation` and `JumpToConversation`,
  `HXCinematicPlay.StartCinematic`, `HXClientDataLinkPlay`, `HXDataLinkDryRunner`.

## Sound slots

The game stops a sound by its ID alone, on the machine that played it
([sounds](engine-dll.md#sounds)). HX stops an actor's slot on every client that hears it:

- **`StopSoundSlot(Slot)`** (3281; `AHXDecoration` 3244, `AHXPlayerPawn` 3217,
  `AHXScriptedPawn` 3225; `0x1001bdd0`) picks its hearers as `PlaySound` does:
  1. while the level records a demo (its `DemoRecDriver`, +0x88, has no `ServerConnection`,
     +0x38) and is not a client's, the actor's `DemoStopSoundSlot` event;
  2. on a client, or called from a simulated function (the frame's node, its flags +0x6c
     holding 0x100; state code never is), each viewport (the engine's client's `Viewports`)
     whose player's actor (+0x30) is in this level and an `HXPlayerPawn` gets
     `ClientStopSound` with the actor's object index and the slot's bit;
  3. else each `HXPlayerPawn` with `bIsPlayer` in `Level.PawnList` gets the call: reliably to
     a remote one, at once for a local one.

  No distance is tested.
- **`StopAllSoundSlots()`** (3282; 3245, 3218, 3226; `0x1001c010`): the same, with
  `DemoStopAllSoundSlots` and the mask -1.
- **`DemoStopSoundSlot(Slot)`** and **`DemoStopAllSoundSlots()`** (`0x1001c230`,
  `0x1001c390`; simulated native events, replicated reliably while `bDemoRecording`): the
  viewports' `HXPlayerPawn` players in the level get `ClientStopSound`, as `DemoPlaySound`
  plays (`0x103e1d00`). So a demo's playback seen by a spectator that is no `HXPlayerPawn`
  stops nothing (not confirmed by a run).
- **`ClientStopSound(ActorIndex, SlotMask)`** (`AHXPlayerPawn`, by name; `0x100211b0`; a
  simulated native event, replicated reliably on `ClientHearSound`'s condition): only for a
  pawn whose `Player` is a viewport, with an audio subsystem (the engine's +0x4c), for each
  of bits 0 to 6 set, the audio's `StopSoundId` (vtable +0x78,
  [`Galaxy.dll`](galaxy-dll.md#playing-a-sound)) with the ID `ActorIndex` × 16 + the slot
  × 2. The index is the server's object index, as in the IDs `ClientHearSound` plays by; a
  client's own simulated sounds carry its own index, which the client's branch (2 above)
  sends.

Its callers stop `SLOT_Misc`: `HXDecoration.StopPushSound`, `HXPhone`'s `BeginState`s,
`HXValve`'s state code, `HXWHPiano.StopPianoSound`. Nothing calls `StopAllSoundSlots`.

## Spawning and calls by name

- **`SpawnEx(SpawnClass, SpawnOwner, SpawnTag, SpawnLocation, SpawnRotation,
  bSpawnNoCollisionFail, SpawnPhysics)`** (3200; `AHXMutator` 3361; `0x1001b850`), all but
  the class optional: the place and rotation by default the caller's own,
  `bSpawnNoCollisionFail` false, `SpawnPhysics` the `Physics` of the class's defaults
  (`PHYS_None` for no class or one that is no actor). For the spawn the class's default actor
  takes `SpawnPhysics` as its `Physics`. `ULevel::SpawnActor` (vtable +0x9c) gets the class,
  no name, the owner, the caller's own `Instigator`, the place, the rotation, the default
  actor as its template (which the spawn takes as it takes none, Engine.dll
  `0x103950bb`-`0x103950e0`), `bNoCollisionFail` and no remote owner; then the new actor's
  `Tag` is set to `SpawnTag` and the default's `Physics` put back. The class is not tested for
  None (the spawn refuses it). It is the game's `Spawn` with two more: `bNoCollisionFail`,
  which passes over the encroachment check after `PostBeginPlay`, and a start physics, which
  the spawn's own events see as `Default.Physics`. Its callers:
  `HXMutator.SpawnSuccessor` (the original's `Tag`, place and rotation, true, and its
  `Physics`), `HXCampaignMutator.SpawnModifiedActor` and `SpawnModifiedInventory`. HX's
  changelog: renamed from `SpawnExt`, the physics added.
- **`DuckCallSucceeds(Successor, Other)`** (3362; `0x1001e8b0`): declared bool, its result
  never set. It finds the successor's `Succeeds`, its state's first, then its class's, and
  calls it with `Other` only when it returns nothing and takes exactly one parameter, an
  object property whose class is exactly `Actor`. `HXMutator.SpawnSuccessor` calls it.
- **`DuckCallCanBeDropped(Item, bSilent)`** (`AHXPlayerPawn`, 3317; `0x10021360`; `bSilent`
  true by default): true, unless the item's `CanBeDropped` returns a bool and takes two
  parameters, the first a bool: then its answer. `bSilent` is read and never passed: the item
  is asked with False. `HXPlayerPawn.DropItem` calls it with False.

## The player

`AHXPlayerPawn`'s other C++:

- **No flag base.** Its constructor (`0x1001ea30`) runs `RegisterNames`, deletes the flag base
  `APlayerPawnExt`'s constructor made ([flags](extension-dll.md#flags)), through its deleting
  destructor (+0xc), and clears `flagBase` (+0x890): an HX player has none; Steve's holds the
  flags.
- **`AddAdditionalView(AddMe)`** (3314; `0x100204e0`, its virtual `0x10020420`, slot 43):
  None counts as added (true); the actor goes in the first empty slot of `AdditionalViews`
  (+0x6a8), false when all three are full; one there already is not looked for: the game's
  `APlayerPawn::AddAdditionalView` (`0x103ba540`).
- **`RemoveAdditionalView(RemoveMe)`** (3315; `0x100205c0`, its virtual `0x10020460`, slot
  44): clears every slot that holds the actor and packs the rest to the front, in their
  order, where the game's (`0x103ba4c0`, [Deus Ex's additions](network.md#deus-exs-additions))
  clears the first alone and moves the rest down, the last left as it was. As the virtual, it
  serves Extension's viewport windows too (`SetViewportActor`,
  [a viewport window](extension-dll.md#a-viewport-window)).
- **`RemoveAllAdditionalViews()`** (3316; `0x10020690`): clears all three.
  `HXMapExit.PlayTransitionPath` empties each player's and adds the server's camera dummy.
- **`CompareGameEngine(EngineClass)`** (3312; `0x10020cb0`): whether the class is exactly that
  of the level's engine (`ULevelBase`+0x40). The server's `HXGameInfo.ClientPlayerPossessed`
  runs `CheckPlayerGameEngine`, which has the client's `HXPlayerPawn.VerifyGameEngine` ask it
  of `HX.HXGameEngine`; a false sends
  `FailGameEngineCheck`, and the server disconnects the player, `Invalid GameEngine class,
  disconnecting`, as the game checks the console's and the root window's classes
  ([Deus Ex's additions](network.md#deus-exs-additions)).
- **`ExportTravel()`** (3311; `0x10020d90`): declared bool, its result never set. With a level
  and a `PlayerReplicationInfo` (+0x558) whose `PlayerName` (+0x318) is not empty: `Export
  travel for: %s`, the engine's `ExportTravel` ([the travel info](#the-travel-info)), and the
  text stored in the level's `TravelInfo` (+0xe4) under the player's name, its keys without
  case. `HXPlayerPawn.Destroyed` calls it on the server before the inventory goes, so a player
  who leaves gets his items back at a later login under the same name.
- **`ScriptConsoleExec`** (`0x1001ebf0`) is `UObject`'s.

## Flags

`AHXFlagReplicationInfo` replicates bool flags by their names' hashes:

- **The server's**: `FlagCollections0` to `FlagCollections15`, from +0x318, nine ints each:
  the bits, then eight hashes, a bit for each: 128 flags.
- **The client's**: `ClientFlagCollections[16]` (+0x558), 17 ints each, of which the natives
  use nine hashes and their nine bits: 144 flags.
- **A flag's key** is its name's `appStrihash` alone
  ([names hashed and compared](core-dll.md#names-hashed-and-compared)): two names of one hash
  are one flag.

| Native | Does |
|---|---|
| `GetBoolFlagCPP(FlagName, bSkipClientFlags)` (3410; `0x10025020`) | the bit of the first server slot of the name's hash; else, unless skipped, the first client slot's; else false |
| `SetBoolFlagByStringCPP(FlagName, Value)` (3411; `0x100252e0`) | sets or clears the bit of the name's slot (true); else takes the first empty slot (true); with none, `ERROR: No empty flag slot in HHXFlagReplicationInfo. REPORT THIS AS A BUG.` and false |
| `SetClientBoolFlagByStringCPP(FlagName, Value)` (3412; `0x100255a0`) | the same on the client's collections, nothing logged |

The script wraps them (`GetBoolFlag`, `SetBoolFlagByString`, `SetClientBoolFlagByString`). On
the server `HXGameInfo.InitFlagReplicationInfo` (every bool flag of Steve's), `HXConPlay`,
`HXFlagTrigger`, `HXMissionScript` and `HXScriptedPawn`'s deaths set them; on a client
`CheckFlagRefs`, `GetActiveDataLink` and `HXClientDataLinkPlay` (`SetPlayedFlag`).

## The actors' ticks

Each override calls its base's tick first, and does HX's work only when that answers true and
the tick is a full one (`LEVELTICK_All`). `AActor::Tick` answers true in stasis too, false
only for an actor put off behind its owner ([a level's tick](engine-dll.md#a-levels-tick);
`0x103a1aed`, `0x103a1b55`), so HX's countdowns run in stasis. A countdown takes the tick's
time off a positive field and, below 0.001, sets it to 0 and sends its event.

| Class | Tick | Its base's | HX's work |
|---|---|---|---|
| `AHXPlayerPawn` | `0x10020080` | `AActor::Tick` | `TickStuff(DeltaTime)` when the engine is a `UGameEngine` and the level is not its Entry level (+0x6c), at every role, a simulated proxy's too; `LipSynchTime` (+0xd78) to `LipSynchTimer`; `NanoVirusTime` (+0x1598) to `NanoVirusTimer` |
| `AHXScriptedPawn` | `0x10022880` | `AScriptedPawn::Tick` | `LipSynchTime` (+0xa1c) to `LipSynchTimer`; dead, nothing sets it |
| `AHXDecoration` | `0x1001e6f0` | `AActor::Tick` | every full tick, put off or not: `SwimAlpha` (+0x42c) toward 1 while `bFloating` (+0x350 bit 0), else toward 0, at 1 a second. Ticked only: `BurnTime` (+0x3b8) to `burnTimer` (state `Burning`), `PushTime` (+0x3bc, 0.2 from `Bump`) to `pushTimer` (`StopPushSound`), where the game's decorations use `Timer` |
| `AHXEffects` | `0x1001c890` | `AActor::Tick` | `EffectsTime` (+0x324) to `EffectsTimer` (`HXTrashGenerator` 0.1, `HXWaterRing` 0.2) |

- **`TickStuff`** (`HXPlayerPawn`, overridden in state `Conversation`): the speech's and the
  credits' sync, the item in hand, a client's lip sync; on the server the breath, energy,
  poison, fire and drone.
- **A slip**: the store at `0x1002019a` zeroes `LipSynchTime` where `NanoVirusTime` is meant.
  It does no harm: `NanoVirusTimer` sets its time again, no script sets `LipSynchTime`, and
  `LipSynchTimer` is empty.

## Windows

- **`PreRenderWindows`** (`0x100206e0`, the virtual's slot 45, which `APlayerPawnExt`'s native
  1050 calls): HX's `ResizeWindows`, then the game's `XRootWindow::PreRender` (`0x1003a760`,
  [the root window](extension-dll.md#the-root-window)): the frame saved on a stack 20 deep of
  HX's own (`0x10093580`, its count `0x10098a0c`), the render viewport cut into the frame,
  or a frame of no size with rendering off
  ([the raw background](extension-dll.md#the-raw-background)), the render size worked out,
  the canvas's size and clip set. HX's counts up only when it saved, the game's always.
- **`PostRenderWindows`** (`0x10020920`, slot 46): the game's `PostRender` (`0x1003a960`),
  then the render size worked out again (`ComputeRenderSize`) after the frame is put back.
- **`ResizeWindows`** (`0x10020ae0`): the root's multiplier is the smaller of the clip's width
  over 639.9 and its height over 479.9 (449.9 with `WindowScale` -1), each truncated, at
  least 1, and lowered to `WindowScale` when that is above 0 and below it. The game's
  `ResizeRoot` (`0x1003adf0`) divides by 640 and 480. `HXPlayerPawn.WindowScale`, a
  `globalconfig` with no menu, caps the UI's scale; -1 gives 1600x900 a scale of 2. Run (a
  private probe at 1600x900, the player's `WindowScale` changed in play): the root 1600x900
  with 1, 2 and 3, 800x450 with -1, from the next frame.
- **`UHXWindow`**'s `Init` (`0x10014e30`) runs `XWindow::Init`, asserts a root (`HXWindow.cpp`
  29), keeps it in `RootWindow` (+0x150), and keeps the root's `parentPawn` in `PlayerPawn`
  (+0x14c), which must be an `HXPlayerPawn`: None or another class stops the game (`GError`,
  `Cast of %s to %s failed`). It runs inside `CreateNewWindow`, before the script's
  `InitWindow` ([showing and hiding](extension-dll.md#showing-and-hiding)), so the
  `StyleChanged` handlers that read `PlayerPawn.ThemeManager` have it (`HXMenuUITitleWindow`,
  `HXMenuUIClientWindow`, `HXComputerUIWindow`, `HXPersonaInventoryObjectBelt`). Its
  `eventStyleChanged` (`0x10008ef0`) is a thunk no C++ calls.
- **`WindowScale()`** (`UHXWindow` 3500, `0x10014fe0`; `UHXButtonWindow` 3501,
  `UHXToggleWindow` 3502 and `UHXTextLogWindow`'s by name sharing `0x10014b50`, a jump to the
  first): the root's `hMultiplier` (+0x730, `ResizeRoot`'s), or 1 without a root. HX's script
  never calls it. `UHXButtonWindow` and `UHXToggleWindow` have no other C++ and no fields.
- **`UHXTextLogWindow`** (its lines at +0x178, 20 bytes each: the time, the text and the
  colour; its bits at +0x184, `bTooTall` 0 and `bPaused` 2; `TextColor` at +0x188; white and
  a `textTimeout` of 5.0 by default) is the game's log window
  ([text](extension-dll.md#text)) with a colour for each line:
  - `Init` (`0x100143b0`) is `XTextLogWindow::Init` (`0x100474b0`) made again over
    `XTextWindow::Init`: left and top aligned, 5 s, no lines, `bTooTall` clear.
  - `AddLine(Text, Color, Timeout)` (`0x100146d0`, its native `0x10014860`): a line timed to
    `GetTickOffset` + its timeout, with its text and colour, and the text made again; the
    colour by default `TextColor`, the timeout `textTimeout`. The game's `AddLog`
    (`0x100476a0`) needs a colour and always takes `textTimeout`.
  - Its tick (`0x10014460`), unless `bPaused`, counts every line's time down by the tick's;
    when any is at 0 or below, the lines still above 0 are kept, in their order, and the text
    made again. The game's (`0x10047c30`) drops only the run of lines at the start whose time
    is out.
  - `ClearLines()` (`0x100147e0`, its native `0x10014980`) is `ClearLog`; `NumLines()`
    (`0x10014a40`) the count of lines.
  - `Serialize`, `CleanUp`, `ConfigurationChanged` and `Draw` are the game's, each line drawn
    in its colour.

  `HXHUDLogDisplay.ClientMessage` passes a colour and a timeout (`ChatTimeout` for `Say` and
  `TeamSay`, `LogTimeout` for the rest, 0.5 s at least); `HasTimedOut` reads `NumLines`.

## Input

`UHXInput` (`Input=HX.HXInput`; 0xfb0 bytes, `CLASS_Transient|CLASS_Config`, config `User`,
`UInput`'s static constructor) is Extension's `XInputExt` made again on `UInput`
([the engine and the input](extension-dll.md#the-engine-and-the-input)): its `Process`
(`0x1002d0b0`), `PreProcess` (`0x1001c680`), `Key` (`0x1002d2b0`) and constructor
(`0x1002cfb0`) step for step, only its class, package and config name differing.

- **Its constructor** (`0x10048c50`), outside the editor, loads the class defaults' config,
  then its own, then the names of Extension's window events, once (`0x100196b0`).
- **`PreProcess`** (`0x10048d20`): always true.
- **`Process`** (`0x10048d30`) asserts a key below `IK_MAX` (`HXInput.cpp` 51). When the
  viewport's actor is a `PlayerPawnExt` with a root window (+0x894) and the root takes the
  key, every key held is let go: its mark in `KeyDownTable` (+0xeb0) cleared, its binding,
  if it has one, run with action Release (3) and delta 0 (`ExecInputCommands`, vtable slot
  31); true. Otherwise a press is taken once a hold and a release only after a press, and a
  non-empty `Bindings[key]` (+0x2ac, 12 bytes each) runs with the key's action and delta,
  which it sets in `Action` (+0xea8) and `Delta` (+0xeac) and then resets.
- **`Key`** (`0x10049080`): true when the viewport actor's root window takes the character
  (`XRootWindow::Key`).
- **The engine's `Key`** (`UHXGameEngine`, `0x1003d8b0`) is `XGameEngineExt::Key` (Extension
  `0x10026650`), a typed character to the console first (`UEngine::Key`), but one the console
  leaves goes to the viewport's input (+0x60) as `UHXInput::Key` when it is one, else as
  `XInputExt::Key`: Extension's knows only its own input.

The Customize Keys screen sets a binding with `SET ini:Engine.Engine.Input <key> <value>`
(`HXMenuScreenCustomizeKeys`): the class's config saved whole into the user ini's own section,
`[HX.HXInput]`, every key's binding and the aliases, `[Engine.Input]` left as it was; at the
next start the constructor's `LoadConfig` reads `[Engine.Input]`, then `[HX.HXInput]` over it.
Runs (a private probe, HX alone): F9 bound to `ShowScores` so lands in a new `[HX.HXInput]`,
every key's binding from the last key down, key 0 as `StrProperty0`, then the 40 aliases, and
is read again after a restart; with F9 bound otherwise in each section, `[HX.HXInput]`'s is
taken.

## Render iterators

- **`CopyRenderProperties(Dest, Source)`** (`UHXScriptedRenderIterator`, 3100; `0x10051680`,
  its native `0x100523c0`), both set, copies what draws an actor: the flags `bAnimFinished`,
  `bAnimLoop`, `bAnimNotify`, `bAnimByOwner`, `bLightChanged` and `bDynamicLight`;
  `AnimSequence`, `AnimFrame`, `AnimRate`, `TweenRate` and the four blend slots' sequence,
  frame, rate and tween; `Location`, `Rotation`, `DrawType`, `Style`, `Sprite`, `Texture`,
  `Skin`, `Mesh`, `DrawScale`, `PrePivot`, `ScaleGlow`, `AmbientGlow`, `Fatness`; `bUnlit`,
  `bNoSmooth`, `bParticles`, `bRandomFrame`, `bMeshEnviroMap`, `bMeshCurvy`;
  `VisibilityRadius`, `VisibilityHeight`, `bShadowCast`, `MultiSkins[8]`; every `Light*` and
  `Volume*` byte, `bSpecialLit`, `bActorShadows`, `bCorona`, `bLensFlare`; `AnimLast`,
  `AnimMinRate`, `OldAnimRate`, `SimAnim`, and the blend slots' last frame, minimum rate, old
  rate and `SimBlendAnim`. Not `bHidden`, the collision or the sound.
- **`UHXScriptedRenderIterator`** (`0x100520c0`-`0x10052320`): `Init(Camera)`, `First`,
  `Next`, `IsDone` and `CurrentItem` each call the script function of that name
  (`FindFunctionChecked`, fatal when it is missing). The game's `URenderIterator`
  (`0x103d9e20`-`0x103d9f70`, [render iterators](engine-dll.md#render-iterators)) calls the
  script from `Init` alone, then sets the observer, answers `First`, `Next` and `IsDone` in
  C++, and its outer for `CurrentItem`; HX's `Init` sets no observer, its script's does. No
  HX class extends it: it is for mods.
- **`UHXDecorationRenderIterator`** (`SavedLocation` +0x34, `SavedRotation` +0x40): its
  constructor asserts an `HXDecoration` outer (`HXRenderIterator.cpp` 128). `HXDecoration`'s
  default `RenderIteratorClass` is it, so every HX decoration is drawn through it
  ([render iterators](render-dll.md#render-iterators)), one item a frame:
  - `Init` (`0x10051b20`) sets the observer and saves the decoration's place and rotation;
    `First` sets `Index` 0 and `Next` adds one; `IsDone` (`0x10051b90`) is false at 0, then
    puts the place and rotation back and is true.
  - `CurrentItem` (`0x10051be0`), for a decoration carried (`Physics` none, its `Base` a pawn
    whose `carriedDecoration`, +0x4e0, is it): when the carrier is a player and the level's
    client's first viewport's actor, the local carrier, the item is the decoration's
    `RenderProxy` (+0x3c0). A live one gets its `LifeSpan` back to its class's default; else
    `HX.HXRenderProxy` is spawned (`LOAD_NoFail`), owned by the decoration, at the origin,
    collision ignored (`Failed to spawn RenderProxy for %s.`, a warning). The decoration's
    `LastRenderTime` is stamped with `TimeSeconds`, its render properties copied onto the
    proxy, and the proxy made translucent, `ScaleGlow` 1 and unlit. For anyone else the item
    is the decoration itself. Either is put at the carrier's place, half its
    `CollisionHeight` up, and along its facing, made level and of unit length, by half the
    carrier's `CollisionRadius` plus the decoration's, the `Location` written straight.
  - Not carried, with `SwimAlpha` above 0: the angle is `TimeSeconds` × `SwimOmega` +
    `SwimPhi`; `Pitch` and `Yaw` each gain their part of `SwimAmp` (a rotator) × `SwimAlpha`
    × the angle's sine, `Roll` its part × `SwimAlpha` × its cosine, truncated; the item the
    decoration (`SwimPhi`, `SwimAlpha`, `SwimOmega`, `SwimAmp` at +0x428 to +0x434).

  So swimming and carrying are drawn alone, and only the carrier sees his load translucent:
  `HXPlayerPawn.PutCarriedDecorationInHand` no longer restyles it, `HXDecoration` sets
  `SwimPhi` and `SwimAlpha` and destroys its `RenderProxy`. Not confirmed by a run: that the
  hidden proxy is drawn as an item, what the carrier and the others see, the swim's
  amplitude.
- **`AHXRenderProxy`** (transient) has no C++ but its destructor. Its defaults: hidden,
  `RemoteRole` None, `LifeSpan` 100, `DrawType` None, `bGameRelevant`, no collision.

## Links

`Validate(ValidationString, BeaconProduct)` (`AHXTcpLink` `0x10017b80`, `AHXUdpLink`
`0x10018110`; by name) answers a master server's challenge as IpDrv's does
([the master server](ipdrv-dll.md#the-master-server)), GameSpy's RC4 variant (`0x10016e30`,
`0x10016c80`) written in eight characters of base 64 (`0x10016ed0`), but (`0x10017610`):

- it answers only a challenge of exactly six characters, else empty;
- it finds the key by the product in any case (`0x10017920`): `hx` gives `5YKJVt`; `gmtest`,
  `gmtestam`, `gmtestcd` and `gmtestcdam` give `HA6zkS`; any other six spaces. IpDrv's
  (`0x107034c0`, its keys `0x107017f0`) tests no length and finds its keys with case.

HX's ini has `[Beacon] Product=hx`, and `HXMasterServerLink`, `HXUdpServerQuery` and
`HXUdpServerUplink` call it.

## Commandlets

**`UHXServerCommandlet`** (`hxserver`; registered at `0x10057140`, its code `0x10056900` to
`0x10056de0`; `UCommandlet`'s size, no fields, `CLASS_Transient`) is the dedicated server;
`HCC.ini` makes `server` its alias ([`HCC.exe`](#hccexe)). HX's changelog: an ad hoc
replacement for the old `ServerCommandlet`, with the improvements made in `Launch`.

- **Its static constructor** (`0x10056940`) sets its flags (+0x1d8) to `LogToStdout`,
  `IsServer` and `LazyLoad` alone (0x13), clearing `IsClient`, `IsEditor`, `ShowErrorCount`
  and `ShowBanner`; the game's (Engine.dll `0x10381850`) sets 0x13 too, and leaves bits 5 to
  7 as they were.
- **`Main`** (`0x10056960`) reads none of its parameters: `InitEngine`, then `MainLoop` while
  there is an engine and no exit has been asked for; it returns 0.
- **`InitEngine`** (`0x100569f0`) times the start; loads `ini:Engine.Engine.GameEngine` as a
  class that must derive from `UHXGameEngine`, fatal else, with no-fail alone, where the
  game's takes any `UEngine`, with no-fail and not from the file (0x41); makes it in the
  transient package (`0x100571f0`) and `Init`s it; logs `Startup time: %f seconds`.
- **`MainLoop`** (`0x10056b60`) times frames by `rdtsc`, ticks the engine with the seconds
  since the last frame began, and past each second sets `CurrentTickRate` (+0x64) to the
  frames a second. It takes `GetMaxTickRate` (the game's: `NetServerMaxTickRate`, or
  `LanServerMaxTickRate` with `-lanplay`, held to 10..120, 0 with no net driver), holds it to
  2.5..200, a rate below 0.0001 taken for 200, and waits out the frame's 1 / rate: while 0
  to 1 s is left, a 1 ms sleep while more than 1.5 ms is left, else a spin. The game's
  (`0x103818b0`) sleeps the rest at once (`appSleep`), not at all at a rate of 0; Windows'
  coarse sleep makes that one sleep too long for the 90 frames a second HX's ini asks of a
  server (`NetServerMaxTickRate=90`). Run (a probe on `HCC.exe server`): `GETMAXTICKRATE`
  90, 901 frames in 10.0004 s, each 11.111 to 11.123 ms.

**The other four**, for HX's developers (their help is `HX.int`'s); play needs none, and the
mission scripts' hand-made tables come from their output:

| Commandlet | Class | Writes |
|---|---|---|
| `spewcoopstarts <path> <outfile>` | `UHXSpewCoopStartsCommandlet` (`0x10057390`) | C++: for each map a block that tests its name, with an `HXSpawnSingleStart` for each `HXCoopStart` placed in it, under a header saying it is generated and that the `.dx` files are to be edited instead; `Successfully wrote %i HXCoopStarts for %i maps to file %s.` Its output is the table `HXSpawnCoopStarts` holds ([co-op starts](#co-op-starts)) |
| `dumpnanokeys <path> <outfile>` | `UHXDumpNanoKeysCommandlet` (`0x100554e0`) | a CSV of `Map`, `KeyID`, `Description`, `SkinColor`, `Actor`, `Notes`: the `NanoKey`s, and the `PickupDistributor`s' `NanoKeyData` (`Notes` `ScriptedPawnTag=%s`) |
| `dumpdatavaultimages <path> <outfile>` | `UHXDumpDataVaultImagesCommandlet` (`0x10053b60`) | a CSV of `Map`, `Image`, `Actor`: the placed `DataVaultImage`s, `InformationDevices.ImageClass`, the `ScriptedPawn`s' `InitialInventory`, the carcasses |
| `dumpcondatavaultimages <conpkg> <outfile>` | `UHXDumpConDataVaultImagesCommandlet` (`0x10052c20`) | a CSV of `Mission`, `Image`, `BindName`, `Conversation`: each `ConEventTransferObject` of `ConList_Mission00` to `ConList_Mission99` that gives a `DataVaultImage` |

## Classes with no code of their own

- **`UHXConCamera`, `UHXFlagBase`, `UHXGoal`, `UHXNanoKeyInfo`**: no C++ beyond their
  constructors and destructors. HX's script makes them: `HXGameInfo` its goals and keys,
  `HXConPlay` its camera.
- **Plain constructors**: `AHXActor` (`0x10006050`), `AHXDecoration` (`0x10005440`),
  `AHXScriptedPawn` (`0x100214e0`), `AHXMutator` (`0x10001f90`), `AHXFlagReplicationInfo`
  (`0x1000bce0`), `AHXGameReplicationInfo` (`0x100013d0`), `AHXCoopStart` (`0x100070c0`),
  `AHXTrigger` (`0x10006570`), `AHXTriggers` (`0x100062d0`), `AHXKeypoint` (`0x100050c0`),
  `AHXInfo` (`0x10006a00`), `AHXRenderProxy` (`0x10007490`), `AHXSteve` (`0x10006ca0`).
  `AHXEffects`' (`0x1001c660`) also runs `RegisterNames`.
- **The event wrappers** (`0x100021b0` to `0x10004460`), generated, are called nowhere in
  `HX.dll`.
- **`UHXLinkerLoad`** (registered at `0x1004ca10`, its constructor `0x1004ca80`): a C++
  subclass of `ULinkerLoad` (`Inc\HXLinker.h`), registered under `ULinker`, whose overrides
  are the game's code renamed, with no constructor that opens a file. Nothing makes one:
  Core's `GetPackageLinker` makes the game's `ULinkerLoad` (not confirmed by a run).
- **`UHXStructPropertyOverrides`** (registered at `0x10016930`, its constructor
  `0x10016990`): its vtable (`0x10061a94`) is `UStructProperty`'s but for the destructor;
  nothing uses it.

Neither of the last two changes how a package loads.

## HX.exe

`HX.exe` is the game's `Launch` module ([`launcher.md`](launcher.md),
[the launch](launch-flow.md)) built again for HX (its own `appInit`, `appInitI`,
`0x10933e70`; its config cache's `Find`, `0x1090a510`). What differs:

- **Its name.** The game's name is the program's, `HX`: its inis are `HX.ini`, `HXUser.ini`,
  `HXDefault.ini` and `HXDefUser.ini`, and a program named `DeusEx` gets the game's. With no
  `HXDefault.ini` or `HXDefUser.ini`, it takes `Default.ini` and `DefUser.ini`. A missing
  `HX.ini` is copied from the default ini, `HXUser.ini` from the default user ini; a default
  that cannot be read is fatal, `Missing .ini file: Default.ini` (or `DefUser.ini`), those
  names whatever the files were.
- **The command line** ([the parsers](cli-flags.md)): `INI=`, `USERINI=`, `DEFAULTINI=`,
  `DEFUSERINI=` and `PACKAGEINI=`, each a value that must end in `.ini`, fatal else
  (`Malformed system ini commandline parameter: %s` and the like). The config cache
  resolves `System`, `User`, `Default`, `DefUser` and `Package`, and `ResetConfig` copies
  from `HXDefault.ini` and `HXDefUser.ini` ([configuration](core-dll.md#configuration)).
- **The log** (`0x10905810`) is `<program>.log`, `HX.log`; `LOG=` and `ABSLOG=` lose a `.log`
  and have it added again; `-TIMESTAMPLOG` adds a date. The log window is `GameLog`,
  `ServerLog` or `EditorLog`, a server's with a tray icon.
- **Forwarding** ([§1](launch-flow.md#1-single-instance-forwarding-0x10908a300x10908cd1)):
  the log window's class is `<program>UnrealWLaunchLog`; forwarding is skipped for
  `ChangeAudio`, `FirstTime` and `Editor`.
- **The splash** is `..\Help\<program>Logo.bmp`, else `..\Help\Logo.bmp`, shown only when it
  is there, where the game's asserts
  ([§3](launch-flow.md#3-splash-screen-0x10908e930x10909205)); HX ships neither. The texts
  and dialogs are `HX.int`'s and its own resources'.
- **The wizard** (`0x10932020`;
  [the entry tree](wizard.md#entry-decision-tree-initengine-0x1090aab60x1090b7f6)): `-safe`;
  `FirstRun` below 1100 for the first-time pages, where the game's is below 400
  ([the gates](wizard.md#the-firstrun-version-gates)); `-changevideo`; `-changeaudio`, new;
  the recovery; no `readini`. The pages run Renderer, Resolution (new: DirectDraw's modes,
  into `FullscreenViewportX`, `FullscreenViewportY` and `FullscreenColorBits`),
  AudioSubsystem (new: `[Engine.Engine] AudioDevice`, only with more than one registered),
  FirstTime; Detail and Driver are never reached ([the pages](wizard.md#page-graph)).
  SafeMode gains an Audio button; SafeOptions keeps the game's dead checkboxes
  ([the bug](wizard.md#-shipped-bug-three-safe-mode-checkboxes-are-dead)), its Reset deleting
  `HX.ini`. There is no savegame migration, CD check, low-memory override or `-make` check.
  At the first run a `<program>Story.txt` shows in a dialog, when it is there.
- **The run** ([§7](launch-flow.md#7-console-commands--launchexec__exec-0x10913650),
  [§9](launch-flow.md#9-main-loop-and-shutdown-0x10909443-onward)):
  - an `-EDITOR` mode;
  - the console words lose `MPLAYER` and `HEAT`, and `EditActor` takes `Name=` too
    (`0x10914630`);
  - DEP turned off (`0x10935ab0`), the player asked before the exit where it cannot be;
  - frames timed by the time-stamp counter when it keeps within 0.25% of
    `QueryPerformanceCounter`, else by the latter;
  - the main loop (`0x10923a90`) holds the tick rate to 2.5..200, a rate of 0 (no cap) taken
    for 200, and waits each frame out as `MainLoop` does (below): 1 ms sleeps while 1.5 ms or
    more is left, then a spin, only while under a second is left; the game's has no cap;
  - 21 functions of Core and Engine rewritten by five-byte jumps (`RedirectCall`,
    `0x109047d0`): varargs and the string pool hardened (`0x10933d90`); `Logf` passing over
    suppressed names; `SafeLoadError`, `StaticLoadClass` (`%s is not a child class of %s`)
    and `ExitProperties` (passing over a property still `RF_NeedLoad`) replaced;
    `UCommandlet::execMain` a no-op that takes its argument; `UControlChannel::ReceivedBunch`
    passing text only while the connection is open or pending; all 16 `StatLog` and
    `StatLogFile` natives no-ops, `GetMapFileName` and `GetGMTRef` empty;
  - `-SIMHDD`, a slow disk, for debugging.

## HCC.exe

`HCC.exe` is UCC built again for HX (its `main` `0x40be80`), with `HX.exe`'s patches, DEP
setting, timing and log naming (`HCC.log`), and UCC's banner, help, closing count of errors
and warnings with the seconds taken, and Y/N prompt, which `-SILENT` answers (`0x408870`).

- **Its ini** is `HCC.ini`, or `PACKAGEINI=`'s, whose `[General] Game=HX` selects HX's inis,
  where the SDK's UCC names the game's alone.
- **`[CommandletAliases]`** rewrites the first word: `server` becomes `hxserver`
  ([commandlets](#commandlets)).
- **A commandlet** is found by its class's path; by its name with `Commandlet`; among the
  registered commandlets by their short name, with or without `Commandlet`; then by each
  `[General] CommandletPrefixes` with the name and `Commandlet` (commented out in `HCC.ini`).
- **`Make` and `Build`** load with flag 0x40 (`0x411cd0`).
