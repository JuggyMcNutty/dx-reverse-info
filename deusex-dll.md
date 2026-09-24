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
| Functions | 834 in IDA; 261 unnamed |

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
