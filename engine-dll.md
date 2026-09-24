# Engine.dll

The native half of package Engine: UE1's actors, pawns, levels, meshes,
networking and the interfaces to rendering and audio, with what Deus Ex added
to them -- AI senses, the AI event system that carries noises, alarms and
bodies to NPCs, NPC movement tests, blend animations, stasis and instant
volume changes. How it was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 1,732,608 bytes |
| Imagebase | `0x10300000` |
| SHA1 | `9438119092df07046060f62b9d72914eba6a82cd` |
| Exports | 2,370: 88 classes, 168 `exec` natives (10 of them latent `Poll*` handlers) |
| Functions | 5,719, about 2,370 of them the exports' jumps |

Each export is a five-byte jump to its code, from incremental linking. IDA
gives the jump the export's name and the code the same name with `_0`
(`?AIProcess@UEventManager@@QAEXXZ_0`); the addresses here are the code's.

It registers 96 classes: the 88 it exports and 8 it does not -- the AI event
classes `XAIEventType`, `XAIEvent`, `XAISenderEvent` and `XAIReceiverEvent`,
`UPendingLevel`, `UNetPendingLevel`, `UDemoPlayPendingLevel` and
`UServerCommandlet`. 57 match their script's layout, and `UEventManager` and
the four event classes the SDK's `Engine/Inc/UnEventManager.h`; the other 34
are C++ only (`ULevel`, `UModel`, `UMesh`, the network channels). The host
check reads the 88 exported ones from the bytes alone.

## What Deus Ex added

The natives the script marks as Deus Ex's (`DEUS_EX`), with their numbers:

- **AI:** Actor's `AIGetLightLevel` 700, `AIVisibility` 701,
  `AISetEventCallback` 710, `AIClearEventCallback` 711, `AISendEvent` 713,
  `AIStartEvent` 714, `AIEndEvent` 715, `AIClearEvent` 716 and
  `RandomBiasedRotation` 717; Pawn's `AICanSee` 705, `AICanHear` 706,
  `AICanSmell` 707, `AIDirectionReachable` 708, `AIPickRandomDestination` 709,
  `ReachablePathnodes` 1004 and `ComputePathnodeDistances` 1020; LevelInfo's
  `InitEventManager` 650.
- **Actors:** `IsOverlapping` 718, `GetPlayerPawn` 720, `InStasis` 721,
  `ParabolicTrace` 722, `LastRendered` 723, `GetBoundingBox` 724,
  `TraceTexture` 1000, `CycleActors` 1002, `TraceVisibleActors` 1003,
  `GetMeshTexture` 1013.
- **Animation:** `PlayBlendAnim` 1010, `TweenBlendAnim` 1012.
- **Sound:** `PlaySound` 264 returns an ID that `StopSound` 265 takes;
  `SetInstantSoundVolume` 268, `SetInstantSpeechVolume` 269,
  `SetInstantMusicVolume` 270.
- **Changed:** `SetPhysics` 3970 takes a floor; Pawn's `StrafeTo` 504 and
  `StrafeFacing` 506 take a speed.

Beside them, C++ with no native of its own: the event manager, stasis and the
blend slots in the actor tick, blending in the mesh. What is read is below;
`ParabolicTrace`, `GetBoundingBox`, `TraceTexture`, `CycleActors`,
`TraceVisibleActors`, the sound IDs and the changed natives are not yet.

## The AI event system

How NPCs learn of shots, noises, alarms, bodies and the like: actors raise
named events, NPCs listen for them, and each frame a C++ manager works out
who senses what and calls the listeners' script.

### The manager

- **One per level.** `LevelInfo.InitEventManager` (`0x10384a90`), which
  `LevelInfo.PreBeginPlay` calls, makes a `UEventManager` (0x43c bytes) in the
  level's package unless `LevelInfo.EventManager` holds one. It is saved with
  the level (`Serialize`, `0x103825f0`, deletes the events marked for deletion
  first), so a save keeps every listener and event.
- **Ticked by the level.** `ULevel::Tick` calls `UEventManager::Tick`
  (`0x103828f0`) after the actors, on a full tick with the game not paused
  (`LevelInfo.Pauser` empty): `AIProcess`, then `CleanupEvents`.
- **Told of destroyed actors.** `ULevel::CleanupDestroyed` passes each to
  `DestroyActor` (`0x10382760`): the actor's events are marked for deletion,
  and it stops being any listener's best sender.
- **What it holds.** 256 hash buckets of event types (`XAIEventType`: a name,
  kept in name order within its bucket). Each type lists its senders
  (`XAISenderEvent`, one per actor raising it) and its receivers
  (`XAIReceiverEvent`, one per actor listening), and every receiver is also in
  one ring the manager walks. All are objects in the level.
- **Deleting is deferred.** An event is marked (`SafeDelete`, `0x10383780`),
  and `CleanupEvents` (`0x10383d80`) unlinks and deletes the marked ones
  outside `AIProcess`. Event types stay for the level's life.
- **The natives** find it through the level's `LevelInfo`; with none they do
  nothing.

### Listening

`AISetEventCallback(eventName, callback, scoreCallback, bCheckVisibility,
bCheckDir, bCheckCylinder, bCheckLOS)` (`0x10382990`) defaults to no score
callback and true, true, false, true. It makes the actor's receiver for that
event (at the ring's end), or finds it, and sets the callback, the score
callback and the four checks. `AIClearEventCallback(eventName)`
(`0x10382b90`) marks it for deletion.

### Raising

A sender keeps four numbers for each of the last 16 frames, in a ring --
visual, audio, audio radius, smell -- and a current level of each: what it
goes on giving off.

- **`AISendEvent(eventName, type, Value, Radius)`** (`0x10382c60`), Value 1
  and Radius 800 by default: a pulse. In this frame's slot, the sense's number
  becomes at least Value, and for audio the radius at least Radius.
- **`AIStartEvent`** (`0x10382fe0`), the same defaults: the pulse, and the
  sense's current level becomes Value (and Radius).
- **`AIEndEvent(eventName, type)`** (`0x103831e0`): the sense's current level
  becomes 0.
- **`AIClearEvent(eventName)`** (`0x103832c0`): all three senses' current
  levels become 0.

The type is `EAIEventType`: visual, audio or olfactory. An actor's first raise
of an event makes its sender; an actor being destroyed raises 0.

### Each frame: `AIProcess` (`0x10384080`)

1. **Whose turn.** The receivers in ring order, from where the last frame
   stopped, until each has had a turn or 2 ms have passed. The clock is read
   only after a receiver that had a sender to weigh, so one such receiver has
   its turn each frame. A receiver whose actor is being destroyed is dropped.
2. **Which senders count.** Those of the event type, not the receiver's own.
   A receiver drawn in the last 5 s or within 1,200 units of the player
   (`DistanceFromPlayer`), and not in stasis, weighs every sender; any other
   only those within 400 units.
3. **Scores.** A sender's score is its distance squared plus 1, or what the
   receiver's `scoreCallback(receiver, sender, score)` returns
   (`AIComputeScore`, `0x10383f50`). A score of 0 or less drops the sender.
   Past 256 senders a warning names the event and the rest are ignored.
4. **The best sender.** In order of score, lowest first -- the nearest, by
   default -- the first the receiver senses (`ComputeSenseDetection`,
   `0x103837b0`). Its actor, score and three senses go in the receiver's
   `XAIParams`.
5. **What a receiver senses** of a sender: each sense's highest number over
   the slots since the receiver's last turn (`0x10383bc0`), then:
   - **visibility:** for a pawn, `AICanSee(sender, visual, bCheckVisibility,
     bCheckDir, bCheckCylinder, bCheckLOS)`; for another actor, the visual
     number if a trace to the sender meets no wall or mover;
   - **volume:** for a pawn, `AICanHear(sender, audio, radius)`; for another
     actor, the audio number within the radius;
   - **smell:** for a pawn, `AICanSmell` (always 0); else 0.

   An inventory item with an owner counts as its owner for a pawn, and its
   visibility is scaled by the square root of its collision size (height
   times radius) over the owner's.
6. **The state** (`EAIEventState`) for which the receiver is called:
   - an event already on: `ChangeBest` for a new best sender, `End` for none;
   - an event off: `Begin` for a best sender with a current level in some
     sense, turning the event on; `Pulse` for one with pulses only, leaving it
     off.
7. **The ring moves on.** Each sender's next slot starts at its current levels
   (0 for an actor being destroyed), and a sender with nothing left in its 16
   slots is deleted. A receiver that has not had a turn in 16 frames loses its
   oldest frame, with a warning ("Event manager not cycling quickly enough").
8. **The calls.** Each receiver that had its turn and a state to report is
   called: its callback function (`AIEvent` when none) with the event's name,
   the state and the `XAIParams` (`0x10384980`).

In the game's script, `ScriptedPawn` listens for `WeaponDrawn`, `WeaponFire`,
`Carcass`, `LoudNoise`, `Alarm`, `Distress`, `Projectile`, `Futz` and
`MegaFutz`. Its score callbacks drop some senders (a friend's loud noise, an
enemy's drawn weapon or distress), and callbacks such as `HandleShot` and
`HandleLoudNoise` react on `Begin` and `Pulse`.

## The senses

- **`AICanHear(other, Volume, Radius)`** (`0x103c7680`), Volume 1 and a
  radius of 800 when none above 0 is given: 0 unless `other` is `bDetectable`
  and Volume above 0. Vertical distance counts double; at or beyond the
  radius it is 0, else (1 − distance / radius) × Volume less the pawn's
  `HearingThreshold`, held between 0 and 1. No script calls it; the event
  manager does.
- **`AICanSmell`** (`0x103c7880`) always returns 0: nothing smells in this
  build.
- **`AIGetLightLevel(Location)`** (`0x1036b980`), the light at a location, 0
  to 1:
  - from lights: 1 for a `bUnlit` actor; otherwise half the sum over every
    light (a light type, a brightness, not the actor itself) whose
    `WorldLightRadius` takes in the location, each its luminance times
    (1 − distance / radius) -- a static light only with no wall or mover
    between;
  - plus twice the luminance of the ambient light of the actor's own zone;
  - a luminance is brightness / 255 × (saturation + 127.5) / 382.5.

  `AIVisibility` uses it, and no script calls it.
- **`AICanSee`** (`0x103c6ab0`) and **`AIVisibility`** (`0x1036bca0`): ported
  by patch 0034 ([its message](../../engine-patches/0034-deusex-ai-sight.patch)).

## Moving

- **`RandomBiasedRotation(centralYaw, yawDistribution, centralPitch,
  pitchDistribution)`** (`0x1036d030`): a random rotation about the central
  one, yaw up to half a turn (32,768) either way and pitch up to a quarter
  (16,384). Each distribution, held between 0 and 1, pulls the result in: 0
  spreads it evenly over the range, 1 gives the centre. With a = (1 + d) / 2
  and a uniform fraction x of the range, the offset is x(1 − a)/a up to a, and
  (1 − a) + (x − a)a/(1 − a) above.
- **`AIDirectionReachable(focus, yaw, pitch, minDist, maxDist, bestDest)`**
  (`0x103c78a0`): whether the pawn can get, along a direction, to a spot whose
  distance from `focus` is between the two. It moves the pawn itself and puts
  it back:
  - in a water zone it swims, along yaw and pitch; otherwise walking (or
    swimming out of water) it walks, along the yaw alone, and flying it flies,
    along both; in any other physics it returns false;
  - steps of its collision radius, held between 5 and 25 units, at most 100,
    each the engine's own walk, fly or swim move, so walls, ledges and steps
    count; a walk stopped by a ledge tries once more with a step of
    `MaxStepHeight`;
  - it stops in the void, in a pain zone whose damage the pawn does not
    resist, and on entering water (leaving it, when swimming);
  - while the spot is in range it goes on, keeping the farthest. It stops on
    leaving the range, on coming into it from beyond, or on crossing it in one
    step, which counts as found;
  - it moves the pawn back to its start and restores its velocity. `bestDest`
    is the spot found, else the start.

  The C++ function takes a third distance, which the `exec` passes as 15 and
  nothing reads.
- **`AIPickRandomDestination(minDist, maxDist, centralYaw, yawDistribution,
  centralPitch, pitchDistribution, tries, multiplier, dest)`**
  (`0x103c7fc0`): up to `tries` (at least 1) directions from
  `RandomBiasedRotation`, pitch unless walking. Each is tried with
  `AIDirectionReachable` from the pawn with the range divided by `multiplier`
  (held between 0.0001 and 1). With a multiplier below 1, a direction found is
  tried again to `multiplier` of the distance reached, so the pawn stops short
  of what it can reach. `dest` is the spot, else the pawn's location.
- **`ReachablePathnodes(BaseClass, NavPoint, FromPoint, distance,
  bUsePrunedPaths)`** (`0x103c8bb0`): an iterator over up to 32 navigation
  points and their distances, nearest first, from `GetPathnodeList`
  (`0x103c6490`). `BaseClass` is read and not used. The list starts from a
  node:
  - `FromPoint` when it is a navigation point; else the pawn's `MoveTarget`
    when that is one the pawn overlaps; else the first in the level's list the
    pawn overlaps;
  - from it, the far end of each of its `Paths` (and, with `bUsePrunedPaths`,
    `PrunedPaths`) whose reach spec the pawn fits (collision radius and height)
    and may use (its move flags), at the spec's distance;
  - with no start node, the nearest 32 nodes within 1,000 units of
    `FromPoint`, or of the pawn, that the pawn can reach (`actorReachable`), at
    the straight distance.
- **`ComputePathnodeDistances(startActor)`** (`0x103c8910`): clears the
  paths, then sets each node's `visitedWeight` to its shortest distance over
  the path network from `GetPathnodeList`'s nodes (`0x103c8a40`). No script
  calls it.

## Blend animations

Four slots of animation over an actor's main one (`BlendAnimSequence[4]` and
the rest): head turns (`PlayTurnHead`), lip sync (`LipSynch`), blinking.

- **`PlayBlendAnim(Sequence, Rate, TweenTime, BlendSlot)`** (`0x103e0d80`),
  Rate 1, TweenTime −1 and slot 0 by default: `PlayAnim` for a slot -- its
  rate, last frame and tween, without the main channel's notifies or loop. A
  slot outside 0 to 3, no mesh or a sequence not in it logs and does nothing.
- **`TweenBlendAnim(Sequence, Time, BlendSlot)`** (`0x103e1300`): `TweenAnim`
  for a slot.
- **The tick.** `AActor::Tick` (`0x103a1aa0`) moves the slots after the main
  animation, the way it moves that: a tween up from a negative frame, then the
  rate (or a velocity-scaled one) up to the last frame, where the slot stops.
  The loop copies the main one's conditions and shares its four iterations:
  - it runs only while the main animation plays or tweens, so with the main
    animation stopped the slots do not move;
  - each iteration moves every slot by the frame's time, and a slot that ends
    or finishes its tween leaves the rest only the time over;
  - iterations repeat until the four are spent, so in a frame whose main
    animation had no notify or end the slots move three times -- up to three
    times their rate.
- **The mesh.** `ULodMesh::GetFrame` (`0x10355360`) adds each slot's pose to
  the main animation's vertices as its difference from the mesh's first frame,
  so a blend sequence moves only what it changes. A slot tweening in moves from
  its last pose, cached per actor and slot, toward the sequence's first frame.
  `UMesh::GetFrame` does not blend.

## Stasis and render time

- **`LastRenderTime`**: `Engine.dll` sets it only when an actor spawns, to
  −10 s; the renderer keeps it, and a zone's
  ([render time](render-dll.md#render-time)). `LastRendered()` (`0x1036de30`)
  is the time since, not below 0.
- **`DistanceFromPlayer`**: `ULevel::Tick` sets it for every dynamic actor
  before they tick, the distance to the local player, in single player and not
  while paused.
- **`InStasis()`** (`0x1036bfe0`): true when all hold -- not drawn for 5 s;
  `bStasis`; `bForceStasis`, or physics none or rotating; its zone not drawn
  for 5 s, or more than 1,200 units from the player; single player.
- **What stasis does.** `AActor::Tick` does nothing else for an actor in
  stasis -- no script tick, physics, animation or timers -- and destroys one
  that is `bTransient` (the rats a container lets out). The event manager
  treats a listener in stasis as out of sight.

## Render iterators

`URenderIterator` is UE1's (`Engine/Inc/UnRenderIterator.h`): `Init` (which
calls the script's `Init` and sets the observer), `First`, `Next`, `IsDone`
(once `Index` reaches `MaxItems`) and `CurrentItem`. Its constructor
(`0x103d9cf0`) requires an actor as its outer. `Engine.dll` only destroys an
actor's `RenderInterface` with it (`AActor::Destroy`); the renderer makes it
from `RenderIteratorClass`, runs it and draws its items
([render iterators](render-dll.md#render-iterators)).

## Small

- **`SetInstantSoundVolume`, `SetInstantSpeechVolume`,
  `SetInstantMusicVolume`** (`0x103e2850`, `0x103e28d0`, `0x103e2950`): hand
  the volume to the audio subsystem's own call for it (its virtuals at +0x90,
  +0x94, +0x98), which applies it at once instead of at the next tick.
- **`GetPlayerPawn()`**: the first viewport's actor.
- **`IsOverlapping(other)`** (`0x10369430`): collision cylinders overlap; a
  brush or the level never does.
- **`GetMeshTexture(texnum)`** (`0x103e17c0`): the actor's skin of that
  number (`GetSkin`); else, for a number above 0, the mesh's texture of that
  number; else the actor's `Skin`; else the mesh's texture.
- **`FindStairRotation(DeltaTime)`** (`0x103bb880`): UE1's own. With a frame
  of 0.33 s or less, it probes the floor ahead at eye height and eases the
  view pitch toward looking down (−5,000) or up (5,400) a flight of stairs, or
  back to level.
- **`ResetKeyboard()`** (`0x103b96d0`): `UObject::ResetConfig` of the class of
  the viewport's input, which `DeusExPlayer.TravelPostAccept` calls on every
  level. What that does in Deus Ex: [configuration](core-dll.md#configuration).

## The database

`gamefiles/System/Engine.dll.i64` has the class layouts, the UTF-16 strings
and the initializers' names ([working on the binaries](README.md#working-on-the-binaries)),
and by hand the event manager's classes and enums from the SDK header, the
prototypes of the functions above, and names for their helpers and the event
classes' vtables. Each function above carries a one-line comment.
