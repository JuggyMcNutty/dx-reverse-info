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
