# DeusEx.dll

The native half of package DeusEx: the player, the NPCs' native tick and
alliances, saving and the save directory, the particle and laser iterators
behind `ParticleGenerator` and `LaserEmitter`, and a QA tool that records bug
locations. How it was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 245,760 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `b31ec4613068a88843cebe6057f84913644cbf50` |
| Exports | 372: 16 classes, 57 `exec` natives |
| Functions | 834 |

## Classes

Every class's size is the one its registration passes to `UClass`, and each
matches the layout of its script (`tools/ida/ue1_types.py`) but
`DDeusExGameEngine`, which has no script. Natives are `exec` exports, with
their script numbers.

| Class | Base | Size | Natives |
|---|---|---|---|
| `AScriptedPawn` | `APawn` | 0xa10 | 6: `IsValidEnemy` 2105, `GetAllianceType` 2106, `GetPawnAllianceType` 2107, `HaveSeenCarcass` 2108, `AddCarcass` 2109, `ConBindEvents` 2102 |
| `ADeusExPlayer` | `APlayerPawnExt` | 0xd64 | 12: `SetBoolFlagFromString` 3001, `CreateHistoryObject` 3002, `CreateHistoryEvent` 3003, `CreateLogObject` 3010, `SaveGame` 3011, `DeleteSaveGameFiles` 3012, `CreateGameDirectoryObject` 3013, `CreateDataVaultImageNoteObject` 3014, `CreateDumpLocationObject` 3015, `UnloadTexture` 3016, `GetDeusExVersion` 1099, `ConBindEvents` 2100 |
| `ADeusExDecoration` | `ADecoration` | 0x3ac | 1: `ConBindEvents` 2101 |
| `ADeusExLevelInfo` | `AInfo` | 0x388 | -- |
| `AAugmentation`, `AAugmentationManager` | `AActor` | 0x470, 0x3fc | -- |
| `ASkill`, `ASkillManager` | `AActor` | 0x3a0, 0x38c | -- |
| `UParticleIterator` | `URenderIterator` | 0xd50 | 1: `UpdateParticles` 3017 |
| `ULaserIterator` | `URenderIterator` | 0x190 | -- |
| `UDeusExSaveInfo` | `UObject` | 0x78 | 1: `UpdateTimeStamp` 3075 |
| `XGameDirectory` | `UObject` | 0x54 | 15, 3080--3094 |
| `UDumpLocation` | `UObject` | 0xa8 | 21, 3020--3040 |
| `UDeusExLog`, `UDataVaultImageNote` | `UObject` | 0x38, 0x44 | -- |
| `DDeusExGameEngine` | `XGameEngineExt` | 0xd0 | -- (C++ only: the game engine, the ini's `GameEngine=DeusEx.DeusExGameEngine`) |

## The native tick

`AScriptedPawn::Tick` (`0x100195a0`) overrides `AActor::Tick` for every
`ScriptedPawn` and ends by calling it, which runs the script's `Tick`. Its own
work runs where the pawn is simulated here: not controlled by a remote client
(`RemoteRole` not `ROLE_AutonomousProxy`), `Role` at least
`ROLE_SimulatedProxy`, and not a viewports-only tick -- or with
`bSimulatedPawn`. In single player that is every tick. In order:

1. **Disappearing.** With `bDisappear`, a pawn in stasis, or not rendered for
   more than 5 s (`Level.TimeSeconds` less `LastRenderTime`), is destroyed, and
   the tick ends there.
2. **Pivot.** While `PrePivotTime` is above 0, `PrePivot` moves toward
   `DesiredPrePivot` in a straight line, reaching it as `PrePivotTime` runs
   out.
3. **Agitation and fear.** `UpdateAgitation` (`0x10019e30`) and `UpdateFear`
   (`0x10019f60`) with the frame's time. The script has versions of both that
   nothing calls.
4. **Timers.**
   - Counted down to 0: `AlarmTimer`, `FireTimer`, `SpecialTimer`,
     `AvoidWallTimer`, `AvoidBumpTimer`, `ObstacleTimer`, `CloakEMPTimer`,
     `TakeHitTimer`, `CarcassCheckTimer`, `BeamCheckTimer`, `FutzTimer`,
     `PlayerAgitationTimer`.
   - `ReloadTimer`: counted down only while the pawn has a weapon; set to 0
     without one.
   - `PotentialEnemyTimer`: counted down, and when it runs out
     `PotentialEnemyAlliance` is cleared.
   - Counted up: `WeaponTimer` while the pawn has a weapon (0 without);
     `DistressTimer` while it is not negative, until it passes
     `FearSustainTime`, when it becomes -1.
5. **Cloak.** With `bHasCloak`, the script's `EnableCloak(Health <=
   CloakThreshold)`, every tick.
6. **Avoidance.** With `bAdvancedTactics`, once the pawn stops accelerating,
   leaves walking or has no `TurnDirection`, the manoeuvre ends:
   - `bAdvancedTactics` is cleared;
   - `MoveTimer` loses 4 s if the pawn was turning;
   - `ActorAvoiding`, `NextDirection` and `TurnDirection` are cleared;
   - `bClearedObstacle` is set and `ObstacleTimer` zeroed.
7. **Burning.** While `bOnFire`, `burnTimer` grows; past `BurnPeriod`, the
   script's `ExtinguishFire`.
8. **Bleeding.** With `bCanBleed` and `BleedRate` above 0 -- and, with
   `bTickVisibleOnly`, only within 1,200 units of the player:
   - a `SpurtBlood` event each time `DropCounter` passes the period
     `(1.1 - BleedRate) / f`, where `f` is the pawn's speed over 512 held
     between 0.05 and 1, so a pawn drips faster the harder it bleeds and the
     faster it moves;
   - `BleedRate` falls by the frame's time over `ClotPeriod`, and at 0 both
     are reset.

## Alliances, fear and carcasses

`AScriptedPawn`'s other natives. Each `exec` wrapper only reads the arguments
and calls the function named here.

- **`GetAllianceType(name)`** (`0x10019420`): looks the name up among the 16
  `AlliancesEx`; `None`, or a name not there, is Neutral.
  - Found: Hostile if its `AllianceLevel` is below 0 or its `AgitationLevel`
    at least 1, Friendly if the level is above 0, else Neutral.
  - With `bLikesNeutral`, Neutral becomes Friendly.
  - With `bReverseAlliances`, Friendly and Hostile swap.
- **`GetPawnAllianceType(pawn)`** (`0x100194d0`): Hostile if the other pawn is
  a `ScriptedPawn` that holds this one's alliance hostile, else what this pawn
  makes of the other's alliance. `None` is Neutral.
- **`IsValidEnemy(pawn, bCheckAlliance)`** (`0x10019300`): ported by patch
  0034 ([its message](../../engine-patches/0034-deusex-ai-sight.patch)).
- **`UpdateAgitation(dt)`** (`0x10019e30`) and **`UpdateFear(dt)`**
  (`0x10019f60`), called only from the native tick. They do exactly what the
  script's own `UpdateAgitation` and `UpdateFear` do, which nothing calls:
  - `AgitationCheckTimer` counts down;
  - after `AgitationTimer` (or `FearTimer`) has run out, the decay is the
    decay rate times the time, less the part of the frame the timer still
    covered;
  - that decay comes off each non-permanent alliance's `AgitationLevel`
    (only while `bAlliancesChanged`, which stays set while any is above 0) and
    off `FearLevel`, none below 0.
- **`HaveSeenCarcass(name)`** (`0x1001a010`) and **`AddCarcass(name)`**
  (`0x1001a040`): the first `NumCarcasses` of `Carcasses`; a new name is added
  while there are fewer than 4.

## Conversations

`ConBindEvents` (`AScriptedPawn` `0x10019140`, `ADeusExPlayer` `0x10014320`,
`ADeusExDecoration` `0x1000ea50`, the same code three times):

- It finds the level's `DeusExLevelInfo`, and does nothing for a mission
  below 0.
- It loads the conversation list `<package>Text.ConList_MissionNN`, where
  `<package>` is the level's `ConversationPackage`, `DeusExConversations`
  becoming `DeusExCon`, so `DeusExConText.ConList_Mission02` in the game
  itself.
- The list binds the actor's conversations in ConSys's
  `DConversationList::BindConversations`.
- With no `DeusExLevelInfo` it logs that conversations cannot be bound.

## The player

`ADeusExPlayer`'s natives:

- **`SaveGame(index, optional desc)`** (`0x10014830`): the game engine's
  `SaveGame`, with `""` as the default description.
- **`DeleteSaveGameFiles(optional dir)`** (`0x100149f0`): the engine's, with
  `""` -- which means `Save\Current`.
- **`SetBoolFlagFromString(name, value)`** (`0x100144e0`): sets that bool
  flag, adding it with no expiry, and returns the name. No script calls it.
- **New objects.** `CreateHistoryObject`, `CreateHistoryEvent`,
  `CreateLogObject`, `CreateDataVaultImageNoteObject` and
  `CreateDumpLocationObject` make a new object each call in the player's own
  package, the level, so a saved level keeps the player's history, log and
  notes. `CreateGameDirectoryObject` makes a new `XGameDirectory` in the
  transient package each call.
- **`UnloadTexture(tex)`** (`0x10014c90`): unloads each mip's data.
- **`GetDeusExVersion()`** (`0x10014270`): `"Mon Mar 19 12:06:14 2001
  v1.112fm"`, the build date and version.

## The game engine: travel and saving

`DDeusExGameEngine` is `XGameEngineExt` with Deus Ex's travel and saves.
Saves live under the ini's `SavePath`:

- `Save\Current` holds the maps of the mission in progress as the player
  left them.
- `Save\SaveNNNN` is a slot and `Save\QuickSave` the quick save, each a copy
  of `Current` plus the level saved in, and `SaveInfo.<ext>`.
- A map's mission number is its name's two leading digits
  (`GetNextMissionNumber`, `0x10011ef0`: `02_NYC_Street` is 2, anything else
  -1). The current one is the loaded level's `DeusExLevelInfo.missionNumber`
  (`GetCurrentMissionNumber`, `0x10011ed0`).

**`Browse(url)`** (`0x10010b90`), after `XGameEngineExt::Browse` has had its
turn:

- **`?restart`:** reloads the current map (`?loadonly`) after emptying
  `Current`.
- **`?loadgame=N`** (-1 for the quick save): reads the slot's `SaveInfo`,
  empties `Current`, copies the slot into it, and loads
  `Current\<MapName>.<ext>?load?loadonly?loadgame`.
- **Any other map:** it compares the mission numbers. Within one mission,
  unless `?loadonly`:
  - `PruneTravelActors`, then `SaveCurrentLevel` into `Current`;
  - the destination is loaded from `Current` if it was saved there, else from
    `Maps`.

  A new mission, a map outside any, or a player with `bStartingNewGame` set
  (which it then clears) empties `Current` first, and the destination loads
  from `Maps`.

**`SaveCurrentLevel(slot)`** (`0x1000fac0`):

- The directory: `Current` for -2, `QuickSave` for -1, else `Save%04d`.
- It marks the level as saving (`LevelInfo.LevelAction` 2), shows "Saving"
  (not for the quick save), and drops the brush tracker and destroyed
  actors.
- It saves the level package as `<MapName>.<ext>`.
- It sets every mover's `SavedPos` to (-1,-1,-1), then restores the tracker
  and the level action and flushes the cache.

**`PruneTravelActors`** (`0x1000f9b0`): before the level is saved, destroys
what travels with the player so it is not saved twice:

- the augmentations and their manager;
- the skills and theirs;
- the flag base, after `DeleteAllFlags`;
- any carried decoration.

**`SaveGame(slot, desc)`** (`0x1000ef10`), for the `SaveGame` native and the
`SAVEGAME` console command. It fills a `DeusExSaveInfo`:

- **Text:** the map name, and the description, or the level's `Title` when
  none is given.
- **Numbers:** the directory index, the player's incremented `saveCount`,
  its play time `saveTime`, the time stamp, and `bCheatsEnabled`.
- **Place:** the level's `MissionLocation`.
- **Picture:** a 160×120 snapshot from the root window, skipped when the
  ini's `GameRenderDevice` is `OpenGLDrv.OpenGLRenderDevice`.

Slot 0 means a new slot: the highest existing `SaveNNNN` plus 1. It then empties
the slot, copies `Current` into it, saves the `SaveInfo` there and the level
with `SaveCurrentLevel`.

**The others:**

- **`CopySaveGameFiles(from, to)`** (`0x10010000`): every file of one
  directory into another.
- **`DeleteSaveGameFiles(dir)`** (`0x10010360`): every file of `dir`, or of
  `Current` for `""`, after resetting the level's loaders.
- **`DeleteGame(slot)`** (`0x10010710`): removes `Save%04d` with its
  contents.
- **`LoadSaveInfo(slot)`** (`0x100108a0`): reads a slot's `SaveInfo`, -2 for
  `Current` and -1 for the quick save.
- **`GetSaveInfo(pkg)`** (`0x10010850`): `Current`'s, or a new one in `pkg`.
- **`GetDeusExLevelInfo`** (`0x100120a0`): the first `DeusExLevelInfo` among
  all objects.
- **`Exec`** (`0x1000ed70`): adds the console commands `SAVEGAME n` and
  `DELETEGAME n`. The Load and Save Game screens delete a save with the
  second.
- **`Init`** (`0x1000ecf0`): registers the name `JoltView`, then
  `XGameEngineExt::Init`.

## The save directory

`XGameDirectory`, the script's `GameDirectory`, lists maps or saves for the
menus. Each native's `exec` only unpacks its arguments.

- **Listing.** `GetGameDirectory` (`0x100171e0`) lists by `SetDirType`:
  - maps (`GetMapsDirectory`, `0x10017200`): the map files on every path;
  - saves (`GetSaveGamesDirectory`, `0x10017520`): the `Save*` directories.

  `GetDirCount` and `GetDirFilename(i)` (`0x10017e80`) read that list.
- **Save info.** `GetSaveInfo(slot)` (`0x10017eb0`, -1 for the quick save) and
  `GetSaveInfoFromDirectoryIndex(i)` (`0x10018000`, the list's i-th directory)
  load that slot's `MyDeusExSaveInfo` and keep it. `DeleteSaveInfo(info)`
  (`0x10018170`) only lets go of one so kept: it releases its file and
  destroys the object, and deletes nothing on disk. `PurgeAllSaveInfo`
  (`0x10018240`) lets go of all of them.
- **New slots.** `GetNewSaveFileIndex` (`0x10017cc0`) is the highest `SaveNNNN`
  listed plus 1, never a gap. `GenerateSaveFilename(n)` (`0x10017d60`) is
  `SaveNNNN.<ext>`, and `GenerateNewSaveFilename(n)` (`0x10017e30`) lists the
  saves first and takes a new index for -1.
- **Other.** `GetTempSaveInfo` (`0x10018120`) makes one transient
  `DeusExSaveInfo` and keeps it. `GetSaveFreeSpace` (`0x10017770`) is the
  save drive's free space in KB. `GetSaveDirectorySize(slot)`
  (`0x100179d0`) is the slot's files' total in KB.

`UDeusExSaveInfo::UpdateTimeStamp` (`0x10014df0`) stores the local time as
the system gives it: the full year, the month from 1 to 12, the day, hour,
minute and second. `CreateTexture` (`0x10014e20`) makes the snapshot's
texture beside it.

## Particles and lasers

Both are render iterators: the engine draws an actor with a
`RenderIteratorClass` once for each item its iterator gives from
`CurrentItem` (the protocol is `Engine/Inc/UnRenderIterator.h`). Both draw
one proxy actor many times, moving it before each.

**`UParticleIterator`** holds 64 particles (`FsParticle` in
`DeusEx/Inc/uparticle.h`). The script adds them from `ParticleGenerator`.

`UpdateParticles(dt)` (`0x1001ac50`) ages each live particle, and one whose
life has run out is deleted (`DeleteParticle`, `0x1001aaf0`). A living one:

- **drifts:** its horizontal velocity is its initial one plus a new random
  offset each frame, from -3 to +2;
- **rises or falls:** under zone gravity when the generator asks for it,
  else faster with age at the generator's rise rate;
- **grows** with age, from 0.01 to 3 times the draw scale, when asked;
- **fades** with its remaining life, when asked;
- **moves** by its velocity.

The proxy is hidden while no particle lives. `CurrentItem` (`0x1001ab20`)
moves the proxy to the current particle (`FarMoveActor`) with its scale and
glow, and deletes a particle that cannot be moved to.

**`ULaserIterator`** holds 8 beams (`ULaserIterator.h`), each drawn as a run
of segments. `CurrentItem` (`0x1001a1a0`):

- finds the beam and segment of the current item;
- moves and turns the proxy (a `LaserProxy`) onto that stretch of the beam;
- with `bRandomBeam`, jitters each segment's end by a random unit vector and
  aims the segment along the result: the electricity of
  `ElectricityEmitter`;
- after the last item, leaves the proxy at a segment chosen at random.

## Bug locations

`UDumpLocation` is Ion Storm's QA tool, not read in detail: its 21 natives
(3020--3040) keep bug locations -- map, position, view, game version, title
and description, the script's `DumpLocationStruct` -- in dump files per
user, to list, add, delete and go back to. `DeusExGameInfo.Login` asks
`HasLocationBeenSaved` on every map; nothing a player uses depends on it.

## The database

`gamefiles/System/DeusEx.dll.i64` has the class layouts, the UTF-16 strings
and the initializers' names ([working on the binaries](README.md#working-on-the-binaries)),
and by hand the inlined `FString` and `TArray` helpers (`TArrayTCHAR_*`,
`TArrayFString_*`).

The functions above carry a one-line comment. What is left unnamed is the C
runtime and small thunks.
