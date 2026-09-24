# ConSys.dll

The native half of package ConSys: conversations -- their events (speech,
choices, flags, animations, trades, camera moves), the camera, the history
the player's log keeps, and the lists that bind them to actors. How it was
read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 135,168 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `18c6b7ff257561d8f3d755503b2f9d9b00434790` |
| Exports | 495: 34 classes, 10 `exec` natives |
| Functions | 624 |

As in `DeusEx.dll`, an export is its code. Identical functions share an
address: `DConEventTrade::BindActor` is `DConEventAnimation`'s too.

It registers the 34 classes it exports; the package's `ConLight` and
`ConCameraWindow` are script only. 31 match the layout of their script, and
`DConImport` is C++ only. Two are as their SDK headers declare them:

- `DConCamera` registers 0x84 bytes (`ConSys/Inc/ConCamera.h`), where its
  script declares 0xbc. The script does not declare the class native, and
  only the script reads its fields: the C++ constructor clears only
  `cameraActor`, which both put first.
- `DConEventAnimation` registers 0x60 (`ConSys/Inc/ConEventAnimation.h`: a
  play mode and a play length where the script has `bLoopAnim`), where its
  script declares 0x58. The game's conversations have no animation events.

`DeusEx.dll` uses its C++ in two places: `ConBindEvents` calls
`DConversationList::BindConversations`
([`DeusEx.dll`](deusex-dll.md#conversations)), and the player's
`CreateHistoryObject` and `CreateHistoryEvent` make its history objects. The
rest is the natives and the importer.

## Classes

Every size is the one the class's registration passes to `UClass`. Natives
are `exec` exports.

| Class | Base | Size | Natives |
|---|---|---|---|
| `DConObject` | `UObject` | 0x28 | -- |
| `DConversation` | `DConObject` | 0x78 | 7: `CreateFlagRef` 2050, `CreateConCamera` 2051, `BindEvents` 2052, `BindActorEvents` 2053, `ClearBindEvents` 2054, `GetSpeechAudio` 2055, `GetSpeechLength` 2056 |
| `DConEvent` | `DConObject` | 0x40 | -- |
| `DConEventRandomLabel` | `DConEvent` | 0x58 | 3: `GetLabelCount` 2060, `GetLabel` 2061, `GetRandomLabel` 2062 |
| `DConEventSpeech`, `DConEventTransferObject`, `DConEventMoveCamera`, `DConEventCheckObject` | `DConEvent` | 0x6c, 0x80, 0x78, 0x5c | -- |
| `DConEventChoice`, `DConEventSetFlag`, `DConEventCheckFlag`, `DConEventCheckPersona`, `DConEventJump` | `DConEvent` | 0x48, 0x44, 0x50, 0x54, 0x54 | -- |
| `DConEventTrigger`, `DConEventAddGoal`, `DConEventAddNote`, `DConEventAddSkillPoints`, `DConEventAddCredits` | `DConEvent` | 0x44, 0x58, 0x50, 0x50, 0x44 | -- |
| `DConEventAnimation`, `DConEventTrade`, `DConEventComment`, `DConEventEnd` | `DConEvent` | 0x60, 0x50, 0x4c, 0x40 | -- |
| `DConSpeech`, `DConChoice`, `DConFlagRef` | `DConObject` | 0x38, 0x58, 0x38 | -- |
| `DConItem`, `DConListItem` | `DConObject` | 0x30 | -- |
| `DConversationList`, `DConversationMissionList` | `DConObject` | 0x3c, 0x2c | -- |
| `DConAudioList` | `DConObject` | 0x38 | -- |
| `DConCamera` | `DConObject` | 0x84 | -- |
| `DConHistory`, `DConHistoryEvent` | `DConObject` | 0x5c, 0x48 | -- |
| `DConImport` | `DConObject` | 0xb4 | -- (C++ only: the importer) |

The script also gives `ConEvent.GetSoundLength` native 2054, which is
`ClearBindEvents`'s; the DLL has no code for it, and no script calls it.

## The game's conversations

`DeusExConText.u` holds all 1,955 in 18 lists under one `ConMissionList`:
`ConList_Mission00` to `ConList_Mission16` but 13, then 98 and 99. 397 are
barks, with `_Bark` in their name. Their 10,079 lines of speech are in
`DeusExConAudio<name>.u`, one package for each conversation's
`audioPackageName`: all MP3s (MPEG-1 Layer III, 44.1 kHz, 48 kbps but for four
at 128).

## An actor's conversations

`DConversationList::BindConversations(actor)` (`0x10010b70`) gives an actor
the conversations of a mission list; `ConBindEvents` calls it with the
level's list.

- **First** it deletes the actor's old list (`PurgeBoundConversations`,
  `0x10010cf0`), taking one off each conversation's `ownerRefCount`.
- **Then** each conversation of the list, in order, goes to the front of the
  actor's `ConListItems` when its owner is:
  - for a bark (`_Bark` in its name, case sensitive): the actor's
    `BarkBindName`, or its `BindName` when it has no bark name;
  - for any other: the actor's `BindName`. Never its bark name.

  Names compare without case. Each item adds one to the conversation's
  `ownerRefCount`, the number of actors that have it.
- So an actor's list runs from the mission list's last conversation to its
  first, and the script starts the first in it that qualifies
  (`DeusExPlayer.GetActiveConversation`).

`DConversationMissionList::BindConversations(actor, mission)` (`0x10011040`)
does the same from the list with that number. Nothing in the game calls it.

## A conversation's actors

**`BindEvents(actors[10], invokeActor)`** (`0x1000fec0`), called as a
conversation starts and as it jumps to another:

- It empties the 10 slots.
- It offers every `Pawn`, every `Decoration` and every `PlayerPawn` in memory
  to each event (`BindEventsToActor`, `0x100100f0`): a player twice, no other
  actor. It passes over an actor whose `BindName` is empty, or the same as
  the invoker's while it is not the invoker. So of several actors with one
  name, the one that started the conversation is bound.
- An actor that any event took goes in the first free slot
  (`AddBoundActor`, `0x100101a0`), up to 10. The script ends the conversation
  when one of them is destroyed: `ScriptedPawn.Destroyed` and
  `DeusExDecoration.Destroyed` tell `ConPlayBase.ActorDestroyed`.

**`BindActorEvents(actor)`** (`0x100101d0`) offers one actor to each event, as
the invoker too. The script calls it after `BindEvents` when `ownerRefCount`
is above 1, so a conversation several actors have binds the one that
started it.

**`ClearBindEvents`** (`0x10010200`) does nothing: it walks the events and
calls nothing. So an event keeps the last actor bound to it, and a name no
actor has leaves it as it was.

### What each event binds

The actor's "name" is its `BindName`, its "bark name" its `BarkBindName`;
both compare without case.

- **Speech** (`0x1000b070`): the speaker, and the one spoken to, when its
  name matches, or when it is the invoker and its bark name matches.
- **Transfer object** (`0x1000bc40`): the giver and the receiver by name, or
  by bark name in a `bFirstPerson` conversation. Each bind also loads the
  item's class, `DeusEx.<objectName>`.
- **Trade** and **animation** (one function, `0x100071b0`): the event's
  owner, the same way.
- **Check object** (`0x10007bf0`) binds no actor. It loads the class
  `DeusEx.<objectName>`, or none for a name starting `NK_`: a nano key, which
  the script looks for on the key ring.
- **Move camera** (`0x100098f0`) binds nothing: `cameraActor` is never set.
  None of the game's camera events names an actor.
- The other events bind nothing.

The conversation package stores neither item class, only the names, so both
are loaded here.

## Speech audio

- **`GetSpeechAudio(id)`** (`0x10010210`): none for -1. Otherwise it loads
  one sound, by name: `ConAudio<audioPackageName>_<id>` from
  `..\System\<package>Audio<audioPackageName>.u`, where `<package>` is the
  conversation's own package less a final `Text`: a conversation in
  `DeusExConText` with `audioPackageName` `Mission01` speaks from
  `DeusExConAudioMission01.u`.
- **`GetSpeechLength(id)`** (`0x10010430`): 0 for -1 or no sound. Otherwise
  the length read from the sound's header (`GetSoundLength`, `0x10010460`):
  - a WAV's data bytes over its bytes a second;
  - an MP3's bits over the first frame's bit rate;
  - for anything else, a warning and 0.

  The script waits that long for each line.
- **The audio list.** Each audio package also has a `ConAudioList_<name>`
  (`DConAudioList`, its sounds serialized after its properties) that the
  code here does not read. Its entry N is the sound numbered N, for all
  10,079.

## Random labels

`ConEventRandomLabel` is a list of labels. Each time the conversation
reaches it, it jumps to one of them.

- **`GetRandomLabel()`** (`0x1000a270`):
  - with `bCycleEvents` off, a random label;
  - with it on, the labels in turn, from `cycleIndex`;
  - with `bCycleOnce` too, the last label once it is reached, from then on;
  - with `bCycleRandom` instead, random once every label has had its turn.
- **`GetLabel(i)`** (`0x1000a110`) is empty out of range.
  **`GetLabelCount()`** (`0x1000a0c0`) is the number of labels, which are
  serialized after the event's properties (`0x1000a090`).
- **The game's 1,241**: 561 random, 15 in turn forever, 496 in turn and then
  random, and 169 in turn once. 164 of those 169 are in first-person
  conversations, what an NPC says when the player walks up or frobs it.

## Small

- **`CreateConCamera()`** (`0x100106f0`) makes a new camera in package
  `DeusEx`; `ConPlay` makes one for a third-person conversation.
  **`CreateFlagRef(name, value)`** (`0x10010600`) does the same for a flag
  reference, and only `Conversation.AddFlagRef` calls it, which nothing calls.
- **The history.** `DConHistory::Destroy` (`0x1000ca20`) deletes its events,
  then itself.
- **The importer.** `ImportConversationFile(package, file)` (`0x1000cc50`), a
  plain C export, reads a conversation editor `.con` file into the text and
  audio packages through a transient `DConImport`. It is the editor's; the
  game never runs it.

## The database

`gamefiles/System/ConSys.dll.i64` has the class layouts, the UTF-16 strings
and the initializers' names ([working on the binaries](README.md#working-on-the-binaries)).
By hand it has the object iterator's step (`TObjectIterator_Advance`) and the
two array serializers (`Serialize_TArray_FString`, `Serialize_TArray_USoundPtr`).
Each function above carries a one-line comment.
