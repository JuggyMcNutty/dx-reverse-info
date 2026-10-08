# Engine.dll

Package Engine's native half: UE1's actors, pawns, levels, meshes, networking,
and the interfaces to rendering and audio. Deus Ex adds AI senses, an AI event
system (noises, alarms and bodies reaching NPCs), NPC movement tests, blend
animations, stasis and instant volume changes. Method:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 1,732,608 bytes |
| Imagebase | `0x10300000` |
| SHA1 | `9438119092df07046060f62b9d72914eba6a82cd` |
| Exports | 2,370: 88 classes, 168 `exec` natives (10 of them latent `Poll*` handlers) |
| Functions | 5,719, about 2,370 of them the exports' jumps |

Each export is a five-byte jump to its code (incremental linking). IDA gives the
jump the export's name and the code the same name plus `_0`
(`?AIProcess@UEventManager@@QAEXXZ_0`). Addresses here are the code's.

It registers 96 classes: the 88 it exports and 8 it does not, the AI event
classes `XAIEventType`, `XAIEvent`, `XAISenderEvent` and `XAIReceiverEvent`,
`UPendingLevel`, `UNetPendingLevel`, `UDemoPlayPendingLevel` and
`UServerCommandlet`. 57 match their script's layout; `UEventManager` and the
four event classes match the SDK's `Engine/Inc/UnEventManager.h`; 34 are C++
only (`ULevel`, `UModel`, `UMesh`, the network channels). The host check reads
the 88 exported ones from the bytes alone.

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
  `ParabolicTrace` 722, `LastRendered` 723, `GetBoundingBox` 724, `TraceTexture`
  1000, `CycleActors` 1002, `TraceVisibleActors` 1003, `GetMeshTexture` 1013.
- **Animation:** `PlayBlendAnim` 1010, `TweenBlendAnim` 1012.
- **Sound:** `PlaySound` 264 returns an ID that `StopSound` 265 takes;
  `SetInstantSoundVolume` 268, `SetInstantSpeechVolume` 269,
  `SetInstantMusicVolume` 270.
- **Changed:** `SetPhysics` 3970 takes a floor; Pawn's `StrafeTo` 504 and
  `StrafeFacing` 506 take a speed.

C++ with no native of its own (all below): the event manager, stasis and the
blend slots in the actor tick, blending in the mesh.

## The AI event system

How NPCs learn of shots, noises, alarms, bodies and the like: actors raise named
events, NPCs listen, and each frame a C++ manager works out who senses what and
calls the listeners' script.

### The manager

- **One per level.** `LevelInfo.InitEventManager` (`0x10384a90`, called by
  `LevelInfo.PreBeginPlay`) makes a `UEventManager` (0x43c bytes) in the level's
  package unless `LevelInfo.EventManager` holds one. It is saved with the level
  ([saved](#saved)), so a save keeps every listener and event.
- **Ticked by the level.** `ULevel::Tick` calls `UEventManager::Tick`
  (`0x103828f0`) after the actors, on a full tick, unpaused (`LevelInfo.Pauser`
  empty): `AIProcess`, then `CleanupEvents`.
- **Told of destroyed actors.** [`ULevel::CleanupDestroyed`](#destroyed-actors) passes each to
  `DestroyActor` (`0x10382760`): its events are marked for deletion, and it
  stops being any listener's best sender.
- **What it holds.** 256 hash buckets of event types (`XAIEventType`, a name):
  the bucket is the low byte of UE1's `appStrihash`
  ([names](core-dll.md#names-hashed-and-compared)), name order within it by
  `appStricmp` (`FindEvent`, `0x103834b0`). Each type lists its senders
  (`XAISenderEvent`, one per actor raising it) and receivers
  (`XAIReceiverEvent`, one per actor listening), each list in arrival order.
  Every receiver is also in one ring the manager walks; a new one goes in before
  the one the manager resumes at. All are objects in the level.
- **Deleting is deferred.** `SafeDelete` (`0x10383780`) marks an event;
  `CleanupEvents` (`0x10383d80`) unlinks and deletes the marked ones outside
  `AIProcess`. Event types last as long as the level.
- **The natives** find it through the level's `LevelInfo`; with none they do
  nothing.

### Listening

`AISetEventCallback(eventName, callback, scoreCallback, bCheckVisibility, bCheckDir, bCheckCylinder, bCheckLOS)`
(`0x10382990`; defaults: no score callback, true, true, false, true) makes or
finds the actor's receiver for that event (a new one at the ring's end) and sets
the callback, the score callback and the four checks.
`AIClearEventCallback(eventName)` (`0x10382b90`) marks it for deletion.

### Raising

A sender keeps a ring of the last 16 frames, each with four numbers (visual,
audio, audio radius, smell), and a current level of each: what it goes on giving
off.

- **`AISendEvent(eventName, type, Value, Radius)`** (`0x10382c60`; by default
  Value 1, Radius 800): a pulse. In this frame's slot the sense's number becomes
  at least Value, and for audio the radius at least Radius.
- **`AIStartEvent`** (`0x10382fe0`, same defaults): the pulse, and the sense's
  current level becomes Value (and Radius).
- **`AIEndEvent(eventName, type)`** (`0x103831e0`): the sense's current level
  becomes 0.
- **`AIClearEvent(eventName)`** (`0x103832c0`): all three senses' current levels
  become 0.

The type is `EAIEventType`: visual, audio or olfactory. An actor's first raise
of an event makes its sender; an actor being destroyed raises 0.

### Each frame: `AIProcess` (`0x10384080`)

1. **Whose turn.** Receivers in ring order from where the last frame stopped,
   until all have had a turn or 2 ms have passed. The clock is read only after a
   receiver that had a sender to weigh, so one such receiver has its turn each
   frame. A receiver whose actor is being destroyed is dropped.
2. **Which senders count.** The event type's, not the receiver's own. A receiver
   drawn in the last 5 s or within 1,200 units of the player
   (`DistanceFromPlayer`), and not in stasis, weighs all; any other only those
   within 400 units.
3. **Scores.** A sender's score is its distance² + 1, or what the receiver's
   `scoreCallback(receiver, sender, score)` returns (`AIComputeScore`,
   `0x10383f50`). A score ≤ 0 drops the sender. Past 256 senders a warning names
   the event and the rest are ignored.
4. **The best sender:** by score, lowest (by default the nearest) first, the
   first the receiver senses (`ComputeSenseDetection`, `0x103837b0`). Its actor,
   score and three senses go into the receiver's `XAIParams`.
5. **What a receiver senses** of a sender: each sense's highest number over the
   slots since the receiver's last turn (`0x10383bc0`), then:
   - **visibility:** a pawn's
     `AICanSee(sender, visual, bCheckVisibility, bCheckDir, bCheckCylinder, bCheckLOS)`;
     for another actor, the visual number if a trace to the sender meets no wall
     or mover;
   - **volume:** a pawn's `AICanHear(sender, audio, radius)`; for another actor,
     the audio number within the radius;
   - **smell:** a pawn's `AICanSmell` (always 0); else 0.

   For a pawn, an inventory item with an owner counts as its owner, its
   visibility × √(its collision height × radius / the owner's).
6. **The state** (`EAIEventState`) to call with. Event on: `ChangeBest` for a
   new best sender, `End` for none. Event off: `Begin` for a best sender with a
   current level in some sense (turning the event on); `Pulse` for one with
   pulses only (leaving it off).
7. **The ring moves on.** Each sender's next slot starts at its current levels
   (0 for an actor being destroyed); a sender with nothing left in its 16 slots
   is deleted. A receiver without a turn for 16 frames loses its oldest frame,
   with a warning ("Event manager not cycling quickly enough").
8. **The calls** (`0x10384980`): each receiver that had its turn and has a state
   gets its callback function (`AIEvent` when none) with the event's name, the
   state and the `XAIParams`.

In the game's script, `ScriptedPawn` listens for `WeaponDrawn`, `WeaponFire`,
`Carcass`, `LoudNoise`, `Alarm`, `Distress`, `Projectile`, `Futz` and
`MegaFutz`. Its score callbacks drop some senders (a friend's loud noise, an
enemy's drawn weapon or distress); callbacks such as `HandleShot` and
`HandleLoudNoise` react on `Begin` and `Pulse`.

### Saved

`Serialize` (`0x103825f0`), after the manager's properties: the level;
`refProcessing`, `deleteCount` and `currentSlot`, 4 bytes each (the first two
asserted 0: a save deletes the marked events first); the receiver the ring
resumes at; each bucket's first type.

Each type, sender and receiver is an object of its own, owned by the manager and
named by its class and a count (`AIReceiverEvent105`); a save imports
`Engine.AIEventType`, `Engine.AISenderEvent` and `Engine.AIReceiverEvent`. Their
fields, after their properties (none):

| Object | Fields |
|---|---|
| A type | its name; its hash (the whole `appStrihash`); its first sender and first receiver; the bucket's next type |
| A sender or receiver | its type; its actor; being destroyed (4 bytes); its list's next event |
| A sender, then | the four numbers of each of its 16 slots, then its four current levels, as floats |
| A receiver, then | callback and score callback (names); call due (4 bytes) and its state (a byte); the four checks and whether its event is on (4 bytes each); the best score (a float) and best sender; the first slot its next turn weighs (4 bytes: the slot current after its last turn); the ring's next and previous receivers (one alone is its own neighbour). Its `XAIParams` are not saved. |

## The senses

- **`AICanHear(other, Volume, Radius)`** (`0x103c7680`; by default Volume 1, and
  a radius of 800 when none above 0 is given): 0 unless `other` is `bDetectable`
  and Volume > 0. Vertical distance counts double. At or beyond the radius 0,
  else (1 − distance / radius) × Volume − the pawn's `HearingThreshold`, held to
  0..1. No script calls it; the event manager does.
- **`AICanSmell`** (`0x103c7880`): always 0; nothing smells in this build.
- **`AIGetLightLevel(Location)`** (`0x1036b980`), the light at a location, 0..1:
  - from lights, 1 for a `bUnlit` actor; otherwise half the sum, over every
    light (a light type, a brightness, not the actor itself) whose
    `WorldLightRadius` takes in the location, of its luminance × (1 − distance /
    radius), a static light only with no wall or mover between;
  - plus 2 × the luminance of the ambient light of the actor's own zone;
  - luminance = brightness / 255 × (saturation + 127.5) / 382.5.

  `AIVisibility` uses it; no script calls it.
- **`AIVisibility(bIncludeVelocity)`** (`0x1036bca0`): the actor's light, as
  `AIGetLightLevel` finds it, found again after a quarter second and eased
  between findings; up to half as much again at 30 to 200 units/s.
- **`AICanSee(other, visibility, bCheckVisibility, bCheckDir, bCheckCylinder, bCheckLOS)`**
  (`0x103c6ab0`; defaults 1.0, true, true, false, true): how well the pawn sees
  `other`, judged from its eyes by:
  - the other's apparent size, nothing under `MinAngularSize`;
  - how much of it lies inside a view `AIHorizontalFov` wide and `AspectRatio`
    times narrower up and down, turned by `AIAddViewRotation` (at least 0.75 up
    and down within 150 units);
  - how lit it is (`AIVisibility`);
  - less `VisibilityThreshold`.

  Then a line from the eyes must get past the world and any unhidden actor that
  blocks sight, `bBlockSight` (`ULevel::MultiLineCheck` with
  `NF_NotVisBlocking`): to its middle, or with `bCheckCylinder` to a player's
  eyes, top and bottom, and another pawn's top, bottom and sides.
- **`LineOfSightTo(Other, bUseLOSFlag, bIgnoreDistance)`** (`0x103beb50`): UT's,
  plus a third flag that lifts every distance limit.
  - **Reach**, beyond which the answer is no. A player looking:
    (Visibility + 16) × 0.015 (held to 1) of 5,000 units for a pawn, 4,000 for
    what is no pawn. Another pawn looking: the same of 4,000 and 3,000; or, with
    `bUseLOSFlag` and `Other` not its enemy, its `SightRadius` × Visibility /
    128, held to 4,000 for a player and 3,464 for another, nothing outside its
    `PeripheralVision`, the distance scaled up toward that edge and by the
    height between.
  - **Lines** from its eyes, each a `FastLineCheck`. Its enemy: one to the
    enemy's middle, noting where each stood. Anything else beyond 1,000 units:
    only that line; a pawn beyond half the reach not at all unless `bLOSflag` is
    set, and half the time not at all when the looker is no player. Nearer: to
    0.8 of `Other`'s height over its middle; failing that, within 500 units and
    for a pawn, to two of its cylinder's four corners at its middle's height
    (the nearest and farthest left out, both measured from the world's origin as
    UT's code measures them), and with `bUseLOSFlag` each other one tried.
  - The script's `LineOfSightTo(Other, bIgnoreDistance)` calls it without the
    LOS flag (`0x103bce10`), `CanSee(Other)` with it and no lifting
    (`0x103ba5d0`).
- **`PlayerCanSeeMe`** (`0x103ba640`): whether any local player sees the actor
  (each viewport's standalone, each pawn's in a net game; `TestCanSeeMe`,
  `0x103ba8a0`). Yes when the player's view target sees it. Else the actor must
  lie within (collision radius + 3.6) × 100,000 squared units, within 60° of the
  view's line either way along it (the cosine squared) unless the view is
  behind, and in the player's `LineOfSightTo`.

## Moving

- **A move**
  (`ULevel::MoveActor(Actor, Delta, Rotation, Hit, bTest, bIgnorePawns, bIgnoreBases, bNoFail)`,
  `0x103990e0`): the actor's cylinder is checked from its place to 2 units past
  the move's end (the delta + 2 along it). The hit is the first that blocks it.
  Passed over: with `bIgnorePawns`, a pawn or a decoration that is not `bStatic`
  (the decorations Deus Ex's, `0x103995f1`); with `bIgnoreBases`, what the actor
  stands on; always, what stands on it.
  - Unless `bNoFail`, a blocked move goes (length + 2) × hit time − 2 along the
    delta (2 short of the hit), or nowhere if that is ≤ 2; the hit's time
    becomes the distance gone / the delta's length (`0x103997c3`). So an actor
    stops 2 units off what it meets, plus the trace's backoff
    ([traces](#traces)): what falls rests 2 + (last move + 2) / 10 over the
    floor.
  - Unless a test: what stands on the actor moves with it; a non-pawn that
    encroaches on something there does not move (`CheckEncroachment`); then the
    hit's `Bump`s (Deus Ex's `BumpWall` for the level) and the touches of what
    it passed before the hit.
- **Walking over the floor** (`APawn::physWalking`, `0x103ca540`): a walking
  pawn floats. Standing still on the same base, a line 20 units down from its
  cylinder's bottom centre that finds the floor 4.1 to 4.6 away leaves it be.
  Otherwise a box trace of its cylinder, down `MaxStepHeight` + 2, measures the
  floor: with none in reach, or the same base ≤ 2.4 away, one nearer than 1.9
  lifts the pawn to 2.1; with a farther or another base, the pawn moves down
  onto it and takes what it stands on as base (the `LevelInfo` for the world).
  These are the traces' distances, short of the floor by their backoff
  ([traces](#traces)), the box trace's a tenth of its length: a pawn with
  `MaxStepHeight` 25 stands 4.8 over the floor.
- **Moving toward a spot** (`APawn::moveToward`, `0x103be250`), a tick of
  `MoveTo` or `MoveToward`:
  - reached: within 16 units across (walking, height ignored; else within the
    pawn's height, at least 48, up or down); the move's time out; or a pawn
    target within both radii and 0.8 of `MeleeRange`;
  - else the acceleration points at the spot at full `AccelRate`; a glider
    (`bCanGlide`, not `bCanStrafe`, flying or swimming) along its facing;
  - a pawn moving over 100 units/s has (its velocity's direction − the spot's) ×
    (1 − their cosine) × speed × 0.2 taken off the acceleration;
  - within 1.4 × `AvgPhysicsTime` of travel of the spot, the speed is halved
    once (`bReducedSpeed`) and held to 200 units/s over the speed;
  - an item target within the pawn's radius and height is touched;
  - falling, a pawn steers only where gravity is under 0.9 of its zone's
    default, and arrives 100 units under the spot.
- **The latent moves** (`execMoveTo` `0x103bceb0`, `execMoveToward`
  `0x103bd150`; polls `0x103bd060`, `0x103bd370`): the call clears
  `bReducedSpeed`, holds the speed to 0..`MaxDesiredSpeed`, times the move
  (`setMoveTimer`: 1 + 1.3 × distance / (the physics' speed × `DesiredSpeed`);
  0.5 with no speed; 1.2 s toward a pawn) and takes the first step at once.
  - Each tick after: the destination is the target's place (a flyer's 0.7 of a
    pawn's height higher); a walking pawn with `bAdvancedTactics` has its
    `AlterDestination` event turn it before the step (Deus Ex's NPCs walking
    around what they bumped); a pawn target's speed is kept as it was, and one
    in water is given up by a pawn that cannot swim.
  - `APawn::performPhysics` counts the move's time down and keeps
    `AvgPhysicsTime` = 0.8 × itself + 0.2 × the tick (`0x103c9c37`).
- **The speed** (`APawn::calcVelocity`, `0x103cd7a0`): an acceleration over
  `AccelRate` (over 0.3 of it for a walking player, `bIsWalking`) is cut to it;
  one under is left.
- **The next node** a pawn takes after a search: [the search](#the-search)
  ("after a search", "the second way").
- **`RandomBiasedRotation(centralYaw, yawDistribution, centralPitch, pitchDistribution)`**
  (`0x1036d030`): a random rotation about the central one, yaw up to half a turn
  (32,768) either way, pitch up to a quarter (16,384). Each distribution d, held
  to 0..1, pulls the result in: 0 spreads it evenly over the range, 1 gives the
  centre. With a = (1 + d) / 2 and x a uniform fraction of the range, the offset
  is x(1 − a)/a for x ≤ a, else (1 − a) + (x − a)a/(1 − a).
- **`AIDirectionReachable(focus, yaw, pitch, minDist, maxDist, bestDest)`**
  (`0x103c78a0`): whether the pawn can get, along a direction, to a spot whose
  distance from `focus` is between the two. It moves the pawn itself and puts it
  back:
  - in a water zone it swims (yaw and pitch); else walking, or swimming out of
    water, it walks (yaw alone); flying, it flies (both); other physics: false;
  - steps of its collision radius held to 5..25 units, at most 100, each the
    engine's own walk, fly or swim move, so walls, ledges and steps count; a
    walk stopped by a ledge tries once more with a step of `MaxStepHeight`;
  - it stops in the void, in a pain zone whose damage the pawn does not resist,
    and on entering water (leaving it, when swimming);
  - while the spot is in range it goes on, keeping the farthest; it stops on
    leaving the range, coming into it from beyond, or crossing it in one step
    (found);
  - it moves the pawn back to its start and restores its velocity. `bestDest` is
    the spot found, else the start.

  The C++ function takes a third distance, which the `exec` passes as 15 and
  nothing reads.
- **`AIPickRandomDestination(minDist, maxDist, centralYaw, yawDistribution, centralPitch, pitchDistribution, tries, multiplier, dest)`**
  (`0x103c7fc0`): up to `tries` (at least 1) directions from
  `RandomBiasedRotation` (pitch unless walking), each tried with
  `AIDirectionReachable` from the pawn, the range divided by `multiplier` (held
  to 0.0001..1). With a multiplier below 1, a direction found is tried again to
  `multiplier` of the distance reached, so the pawn stops short of what it can
  reach. `dest`: the spot, else the pawn's location.
- **`ReachablePathnodes(BaseClass, NavPoint, FromPoint, distance, bUsePrunedPaths)`**
  (`0x103c8bb0`): an iterator over up to 32 navigation points and their
  distances, nearest first, from `GetPathnodeList` (`0x103c6490`); `BaseClass`
  is read and not used. The start node: `FromPoint` if a navigation point; else
  the pawn's `MoveTarget` if one the pawn overlaps; else the first in the
  level's list the pawn overlaps. From it, the far end of each of its `Paths`
  (with `bUsePrunedPaths`, `PrunedPaths` too) whose reach spec the pawn fits
  (collision radius and height) and may use (its move flags), at the spec's
  distance. With no start node: the nearest 32 nodes within 1,000 units of
  `FromPoint`, or of the pawn, that the pawn can reach (`actorReachable`), at
  the straight distance.
- **`ComputePathnodeDistances(startActor)`** (`0x103c8910`): clears the paths,
  then sets each node's `visitedWeight` to its shortest distance over the path
  network from `GetPathnodeList`'s nodes (`0x103c8a40`). No script calls it.
- **`StrafeTo(dest, focus, speed)`** and **`StrafeFacing(dest, target, speed)`**
  (`0x103bd5f0`, `0x103bd8c0`; speed 1 by default): UE1's strafes with Deus Ex's
  speed. A player's `DesiredSpeed` is its `MaxDesiredSpeed`; an NPC's is that
  held to 0..speed. Both clear `bReducedSpeed` and time the move by its
  distance. `StrafeTo` drops the move target and looks at the focus;
  `StrafeFacing` needs a target (without one it does nothing), faces it and
  looks at where it is. The scripts give no speed: NPCs running and firing
  (`StrafeFacing`, in combat), stepping back from a door (`StrafeTo`).
- **`SetPhysics(newPhysics, newFloor)`** (`0x103c8ea0`; `AActor::setPhysics`,
  `0x103c95f0`): only a change of physics does anything. A change to none,
  walking, rolling, rotating or spider takes `newFloor` as the actor's base
  (unless it is already) through the floor's `SupportActor` event, which bases
  it (`SetSupportBase`, `0x103c9390`); with no floor it finds its base below
  (`FindBase`, `0x103c9470`: what a box of its size meets within 8 units down,
  anything colliding or the level, unless that stands on it). A change to any
  other physics leaves the base. None and rotating also stop velocity and
  acceleration, unless the floor's event changed the physics again.
  - The scripts pass the wall hit as grenades, pool balls, basketballs and
    fragments come to rest. Deus Ex's `SupportActor`s bounce a pawn or the
    player off the one it lands on and have it stomped (`ScriptedPawn`,
    `DeusExPlayer`), and push off a decoration that cannot be a base
    (`DeusExDecoration`).
- **Falling in water** (`physFalling`, `0x103d0a50`): gravity × (1 − `Buoyancy`
  / `Mass`), the mass floored at 1, so a massless actor (Deus Ex's
  `GeneratorScout`, a pawn of mass 0) falls at full gravity. Each step of at
  most 0.1 s, the mean velocity is the old one × (1 − 2 × the step ×
  `ZoneFluidFriction`) plus (that gravity + acceleration) × half the step;
  the actor moves by it, and its velocity after is twice it less the old
  when it gained downward or was rising, else the mean itself. A decoration
  with more buoyancy than mass rises to the surface and bobs there.
- **Landing** (`processLanded(HitNormal, HitActor, remaining)`, `0x103cef60`),
  from `physFalling` when its move (each a `MoveActor`, above) meets a floor
  (normal > 0.7). Any move of a decoration that hits a `PlayerPawn` first takes
  one off its `numLandings` (not under 0). The remaining time is what the tick
  has not stepped yet, and the part of this step the move did not take; unless
  `bJustTeleported`, the velocity becomes the move's own, the distance gone
  over the time it took, when the hit's time is over 0.1 and the time it took
  over 0.003 s. A floor met sliding along a wall lands with neither: no
  velocity taken, the step's time spent. Then:
  - a non-pawn in a `bBounceVelocity` zone with a velocity is thrown again: the
    zone's velocity and 80 up;
  - a pawn with nothing under 0.9 of its box within its radius × 0.2 + 8 down
    (flags 55) is fitted (`FindSpot`, 1.1 of its size) and, if that moved it,
    put there (`FarMoveActor`) with −30 to 30 units/s added at random along X
    and along Y, still falling;
  - a decoration that has landed five times in a row (`numLandings`) lands, the
    count 0. Below five, with nothing under a line from 0.8 of its height down
    to its height + radius + 8 below its middle (flags 55), it traces four boxes
    (half its radius across, its height) 8 down from its corners (flags 23).
    More than one free, one of each diagonal pair at least, sends it off the
    ledge at (x, y, ½) × 2v (x, y: each axis's free corners less the other
    side's; v: its fall speed held to 30..radius + 30) and counts the landing.
    Otherwise a `Carcass` with `bSlidingCarcass` landing on a slope (normal <
    0.9) bounces off it, 120 along the normal and 70 up, and counts the landing
    one time in five (`FRand` < 0.2); any other decoration's count goes to 0;
  - what is left lands: `Landed`; an actor still falling has `setPhysics` take
    walking (a pawn) or none, with the floor hit as its base (the `LevelInfo`
    for the world). A pawn then walking has its acceleration made unit length
    and walks out the remaining time, if over 0.01 s.

### Reaching

Whether a pawn can get somewhere is asked by moving it there and back (UT's
shape, Deus Ex's numbers):

- **`pointReachable(Dest, bKnowVisible)`** (`0x103c0d30`): no further than 1,000
  units across; not into water unless the pawn is in water or can swim; not into
  a pain zone it does not resist unless its feet are in one already; seen from
  its eye (`FastLineCheck`) unless the caller knows; the spot fitted for the
  pawn's size (`FarMoveActor` as a test, and back); then `Reachable` within 15
  units.
- **`actorReachable(Other, bKnowVisible)`** (`0x103c0630`): a non-pawn no
  further than 800 units and not in a pain zone the pawn does not resist, a pawn
  not with its feet in one; not in water unless the pawn can swim; a line from
  the eye (level and movers) that nothing but `Other` stops (unless known). A
  pawn within a blow (min(1.5 × the radius, `MeleeRange`) + both radii) is
  reached; else it is walked toward to within that reach (one over 800 units
  off, to 800 short of it), `Other` the goal. An `Inventory` or a `Trigger` is
  walked to where the cylinders touch (both radii − 2), anything else to within
  15; the goal is given only for an actor that blocks actors, or a
  `WarpZoneMarker`. The spot is fitted first, as in `pointReachable`.
- **`Reachable(Dest, Threshold, GoalActor)`** (`0x103c1000`): in a water zone
  `swimReachable`; walking or swimming `walkReachable`; flying `flyReachable`;
  other physics, nothing.
- **`walkReachable`** (`0x103c1b70`): up to 100 `walkMove`s toward the
  destination, the collision radius at a time (at least 128 for a pawn that can
  jump), each threshold 4.1.
  - It arrives within the threshold across and the pawn's height up or down (the
    goal's, when taller), or on a slope (the last floor's normal 0.7..0.95)
    within what the slope rises over the radius (46, or the goal's radius + 15).
    A climb steeper than 0.8 ((rise − height)² against (distance across)²) ends
    it.
  - A fall: a flyer flies the rest (`flyReachable`); a jumper adds `R_JUMP` and
    jumps (`FindBestJump`, the pawn moved to where it lands); another retries in
    steps of `MaxStepHeight`. Into the void, or a pain zone its feet do not
    resist, it fails; into water, a swimmer swims the rest.
  - A `WarpZoneMarker` goal is reached by being in its zone.
  - The pawn and its velocity are put back; the answer is the reach flags used.
- **`flyReachable`** (`0x103c1190`), **`swimReachable`** (`0x103c15a0`): the
  same with `flyMove` and `swimMove`, max(radius, 200) at a time, arriving
  within the threshold and the pawn's height. A flyer meeting water swims on if
  it can. A swimmer leaving the water flies on if it can fly; or, walking and
  within `MaxStepHeight` + 50 of the destination's height, climbs out (a test
  move up by its height and `MaxStepHeight`, at least the rise) and goes on as
  `flyReachable` would, its flag `R_WALK`.
- **`walkMove(Delta, Hit, GoalActor, Threshold, bAdjust)`** (`0x103c3290`):
  `ULevel::MoveActor` as a test that pawns and decorations do not stop
  (`bIgnorePawns`, [moving](#moving)), across only. Blocked: up by
  `MaxStepHeight`, across the rest, down again; a wall too steep to step (normal
  < 0.7) puts it back: 0. Then down to the floor within `MaxStepHeight` + 2:
  none, or one too steep, is -1 (put back to where it dropped from, or with
  `bAdjust` to its start). Moving less than the threshold is 0, the goal bumped
  5, else 1.
- **`flyMove`** (`0x103c3900`) moves along the whole delta, stepping up over
  what blocks it; **`swimMove`** (`0x103c3ca0`) as well, and a move that leaves
  the water is taken back to the water's edge (`findWaterLine`, `0x103d3b10`,
  halving between the two points to within a unit) and is 0.
- **`FindBestJump(Dest, Vel, Landing, bMovePawn)`** (`0x103c2f50`): the jump
  `SuggestJumpVelocity` (`0x103c2c80`) gives, landed (`jumpLanding`). That jump:
  the time in the air for its own upward speed to come down to the destination's
  height, in steps of 0.05 s under the zone's gravity (-100 where it points up),
  and the speed across that covers the distance in it, at most `GroundSpeed`. It
  counts where it lands more than 8 units nearer, less than 350 below its start,
  out of a pain zone it does not resist and out of water unless it can swim
  ("Failing FBJ" logged for a fall of 350 or more).
- **`AIDirectionReachable`**'s steps (above) are these moves, threshold 4.1, no
  goal: a walk's fall retried at `MaxStepHeight`, its range classified nearer,
  inside or beyond (`ClassifyDistanceSq`, `0x103c7f80`). `jumpReachable`
  (`0x103c2380`) has no caller.

### The search

`findPathToward(Goal, bSinglePath, &BestPath, bClearPaths)`
(`APawn::findPathToward`, `0x103db3f0`) and
`findPathTo(Dest, bSinglePath, &BestPath, bClearPaths)` (`0x103dc1d0`, the goal
a point) have UT's shape. Their execs (`0x103bc9c0`, `0x103bc800`) read the
goal, `bSinglePath` (0) and `bClearPaths` (1) (none of Deus Ex's eleven
`FindPathToward` calls nor its six `FindPathTo` calls passes either), clear
`bShootSpecial` and `SpecialPause`, hand a found node that probes
`SpecialHandling` to `HandleSpecial`, and drop `SpecialGoal` when the route is
it. **Nothing fills `RouteCache`**: Deus Ex's `SetRouteCache` (`0x103dd7e0`)
only logs "Hey, who called SetRouteCache?", and nothing calls it. The search
moves the pawn onto nodes to ask what it can reach from them, and on every way
out puts it back where it stood (`FarMoveActor` as a test, `noCheck`).

- **The goal falling.** A pawn not flying searches toward a falling pawn by
  where it will land (`jumpLanding`, with `TwoWallAdjust`), as a point.
- **Two node lists** (`0x103da210`), each sorted by squared distance and 32 long
  at most (`addPath`, `0x103dd170`, and `removePath`, `0x103dd2a0`: UT's
  `FSortedPathList`): the navigation points within 800 units of the pawn, and
  those within 800 of the goal (or the goal alone, at 0, when it is a navigation
  point). The same pass over the level's navigation list first clears each node
  when `bClearPaths` is set, as `clearPaths` does (`visitedWeight` 10,000,000,
  `bEndPoint` off, `nextOrdered` and `prevOrdered` none, `cost` from
  `SpecialCost` or `ExtraCost`), so every search Deus Ex makes starts clean, end
  points included. A pawn standing at its `MoveTarget` navigation point (height
  apart < the two collision heights together; across < its collision radius,
  squared and doubled for a player at an `InventorySpot`) is **anchored** there
  and gathers no list of its own.
- **Where the pawn starts** (`findEndPoint`, `0x103da610`, UT's): its nodes are
  dropped from the nearest until one is seen from its eye and `pointReachable`.
  Within max(its radius, 48) of it across and its height up or down, the pawn is
  anchored there; otherwise that node is **the** end point, its `bestPathWeight`
  its distance. None left: no path.
- **Anchored**, the goal may be a step away. Either test ends the search at
  once (`0x103db6ad`), the route the goal when it is a navigation point, else
  the anchor:
  - a navigation-point goal that is one of the anchor's own reach specs, which
    the pawn fits and nothing it cannot open blocks (`CanMoveTo`, `0x103dad20`);
  - any goal within 800 units of the anchor, in its line of sight and
    `pointReachable` with the pawn moved onto the anchor (`0x103da880`);
  - otherwise **`definePathsFor`** (`0x103daaa0`) marks the anchor's forward
    neighbours as the end points. The anchor's `cost` goes to 1,000,000. Each of
    its `Paths` (`0x360`), and once those end at a -1 its `PrunedPaths`
    (`0x3a0`), that fits the pawn's radius, height and move flags is traced
    between its two nodes (`ULevel::SingleLineCheck`, flags 6). Where nothing
    blocks it, or what does is not an `AMover`, or is one the pawn can open
    (`bCanOpenDoors`, and `bIsPlayer` or the mover not `bPlayerOnly`), the
    spec's **end** node becomes an end point, the spec's distance its
    `bestPathWeight`. `CanMoveTo` asks the same of one spec.
- **Where the search starts**: a navigation-point goal itself, at weight 0.
  Otherwise the goal's nodes are tried nearest first (the goal in the node's
  line of sight, the pawn moved onto the node, the goal `actorReachable` from
  there, a point `pointReachable`); the first is the start, its distance its
  weight. None: `findPathTo` fails; `findPathToward` takes the nearest anyway
  for a pawn with `bHunting`, else tries the second way (below).
- **`breadthPathFrom(Start, &EndNode, bSinglePath, MoveFlags)`** (`0x103dcd60`),
  the search: best first, from the start over the reach specs the other way
  round (`upstreamPaths`, `0x320`: the node reached is the spec's `startActor`).
  It expands the next node of its own **open list, kept sorted by what a node
  cost to reach** (`nextOrdered`, `0x430`; `prevOrdered`, `0x434`), the start
  its head with the start's weight as its `visitedWeight`:
  - an end point ends the search: the start's `previousPath` is cleared and that
    node is `EndNode`. A `bPlayerOnly` node is not expanded for a pawn that is
    not the player, the start excepted;
  - a spec is skipped where the pawn's collision radius or height is the larger,
    or the pawn lacks a flag it needs
    (`(MoveFlags & reachFlags) != reachFlags`). Reaching its node costs
    **`distance + node.cost + expanded.visitedWeight + node.bestPathWeight`**
    (the last for an end point only), taken only where less than the node's
    `visitedWeight`, with `previousPath` the node expanded;
  - the node leaves the open list if in it and goes back where its cost belongs,
    found by walking the list from a **front** node when that costs less than
    the new cost, else from the node expanded: at most 500 steps, then "Breadth
    path list overflow from %s" (the start's name) and no path. The front starts
    at the start and moves on as the list grows: each expanded node adds 1 to an
    index (a new node costing more than the front 1, one costing no more 1 less,
    a node moved in front of it 1 less), and the front steps on along the list
    until it has stepped half that index, counting a step even where the list
    ends;
  - the caps: with `bSinglePath`, no path after four nodes, silently; otherwise
    none after 1000, with "1000 navigation nodes searched from %s".

  The route is the end node's `previousPath` chain back to the start: the end
  node is where the pawn goes first.
- **After a search**, unanchored and not single-path (`0x103db0e0`): the pawn's
  other nodes are weighed against the end point, each its distance plus what the
  search found it cost. A candidate costs less than the end point's own sum,
  lies within 120 units of the pawn's height, and is on the far side of the pawn
  from the route's first node or cheaper by 15% (or 150, whichever cuts deeper).
  The cheapest candidate the pawn's eye sees and `pointReachable` finds replaces
  the route's first node.
- **The second way** (`findPathToward` only; no goal node reaching the goal, no
  `bHunting`): the lists are gathered again (the pawn's around wherever the
  goal-node tries last moved it), `definePathsFor` marks the forward neighbours
  of the pawn's nearest node, `findEndPoint` runs, and the search runs from the
  pawn's first node, its distance its weight. A route ending no farther from the
  goal than the pawn is taken, reversed (`ReverseRouteFor`, `0x103dd810`) to run
  from the pawn's node; where the next node after it is within 120 units of the
  pawn's height (or the pawn is anchored at the first), in sight and
  `pointReachable`, the route starts there instead. A route that is only the
  anchor is no path.
- **`HandleSpecial`** (`0x103c5de0`): the node's `SpecialHandling` answers. The
  same node: the route stands. None: no path. Another actor: for a pawn with
  `bCanDoSpecial` it becomes `SpecialGoal`, and the route is that actor where
  `actorReachable` (asked again when it too probes `SpecialHandling`, its own
  answer taken where reachable and not the first node), or else the way to it
  (`findPathToward`, clearing), unless that is the first node. Without
  `bCanDoSpecial`, or with nothing found: no path.
- **`clearPaths`** (`0x103da050`) does what the lists' pass does with
  `bClearPaths`; `execFindRandomDest`, `execClearPaths` and
  `execComputePathnodeDistances` call it.
- **`calcMoveFlags`** (`0x10326d10`) packs seven bits of the pawn's own flag
  word (`0x318`, `Pawn`'s bitfields) into the reach specs' seven, lowest first:
  `bCanWalk`, `bCanFly`, `bCanSwim`, `bCanJump`, `bCanOpenDoors`,
  `bCanDoSpecial` and `bIsPlayer` (the pawn word's bits 13, 15, 14, 12, 16, 17
  and 1).

### Teleporting an actor

`SetLocation` is `ULevel::FarMoveActor(actor, spot, test, noCheck)`
(`0x10398ba0`), which the engine uses for its own moves too:

- A static actor, or one not `bMovable`, stays where it is (false), except in
  the editor.
- Unless `noCheck`: an actor that collides with the world (or has
  `bCollideWhenPlacing`, off clients) is fitted in near the spot (`FindSpot`,
  `0x10398480`); no fit, false. Then, unless a test, the encroachment check at
  the spot, with touches (`CheckEncroachment`, `0x1039a350`): an actor there
  that blocks it and whose `EncroachingOn` agrees stops the move (false); those
  it no longer overlaps are untouched, and those there that do not block it
  touched.
- **`FindSpot(extent, spot, bCheckActors, bCheckFirst)`**, the extent the
  collision box's (radius, radius, height). With `bCheckFirst`, a spot where the
  box already fits is kept. Otherwise the spot is pushed out of the walls toward
  −X, −Y and −Z, then +X, +Y and +Z, each by the box's reach on that axis
  (`AdjustSpot`, `0x10398360`: a line from the spot toward a point, level and
  movers; hit at time t, the spot goes back along the wall's normal by (1.05 −
  t) × the line's length); where the box fits then, that is the spot. Else it is
  pushed the same way toward the box's eight corners, each line of
  length |extent| + 2, and kept if it moved no more than √1.5 × |extent| and the
  box fits there; otherwise no spot. `FarMoveActor` passes neither flag;
  `SpawnActor` passes `bCheckFirst`.
- **What blocks what** (`AActor::IsBlockedBy`, and the same test in
  `CheckEncroachment`): the world and brushes block an actor that collides with
  the world, by their `bBlockPlayers` for a player's pawn (a `PlayerPawn` with a
  `Player`), `bBlockActors` otherwise; two actors block each other when each
  blocks the other's kind, a projectile counting as a player.
  `CheckEncroachment` checks only an actor that collides with actors or blocks
  (or a brush); after the `EncroachingOn` questions, each actor there that
  blocks it hears `EncroachedBy`.
- **Spawning** (`ULevel::SpawnActor`, `0x10394f60`) fits the new actor the same
  way; after `PostBeginPlay`, unless `bNoCollisionFail`, it checks the actor's
  encroachment without touches: stopped, the actor is destroyed and the spawn
  fails.
- Unless a test, whatever stands on it is unbased (`SetBase(None)`, with the
  event) and it is marked `bJustTeleported`, so physics does not take the jump
  for speed.
- `Location` and `OldLocation` both become the spot, and its zone is found again
  ([below](#the-zone-an-actor-is-in)), silently for a test.

The engine's own moves: a trailer follows its owner with `noCheck`
(`physTrailer`, `0x103d7850`); `AIDirectionReachable` puts the pawn back as a
test with `noCheck`; Deus Ex's particle iterator moves its proxy with neither
([deusex-dll.md](deusex-dll.md)).

### The zone an actor is in

`SetActorZone(actor, test, forceRefresh)` (`0x1039b940`):

- A deleted actor is skipped; the level's own info is always in its own zone.
  `forceRefresh` first puts the actor (and a pawn's feet and head) in the
  level's zone, with no events.
- The zone at its location replaces the old. When they differ, unless a test, in
  order: the old zone's `ActorLeaving`; the actor's `ZoneChange`, while `Region`
  still holds the zone being left (scripts compare it with the new: a
  `Decoration` or an `Inventory` splashes only coming out of dry); `Region` set;
  the new zone's `ActorEntered`.
- A pawn's feet (its location − its collision height) and head (+ `EyeHeight`)
  the same way, each with `FootZoneChange` or `HeadZoneChange` before it is set;
  then, off clients, its `PlayerReplicationInfo`'s `PlayerZone`.

That is all; Deus Ex's scripts do the rest: pain zones' `PainTime`
(`Pawn.FootZoneChange` and `HeadZoneChange`), stray inventory in a
`bNoInventory` zone (`ZoneInfo.ActorEntered` gives it 1.5 seconds) and
`bDestructive` (decorations and fragments).

## Traces

- **Backoff** (`UModel::LineCheck`, `0x103f3c20`): a hit on the BSP (the
  level's, or a mover's brush, its normal turned by the mover's rotation) is
  given short of the surface: a line's by 0.5 units, a box's by a tenth of the
  trace's length, or by 0.1 units for a trace shorter than one; its time held to
  0..1, the rest of the move not taken. A line's hit lies on the line. A box's
  time starts at 2, so a hull the box enters within twice the trace's length is
  found; a hit the backoff brings under 1 counts (one up to a tenth of the trace
  past its end), one still at 1 is none. A script's `Trace` straight down finds
  the floor half a unit above it.
- **The box check's hulls** (`0x103f42f0`, set up at `0x103f18e0`), in each
  solid leaf the box reaches: its convex hull's planes pushed out by the box
  (|nx·ex| + |ny·ey| + |nz·ez|); for the level's hulls only, the planes of the
  hull's box, a tenth of a unit bigger at both ends in Z and toward −X and −Y,
  as much smaller at +X and +Y; then bevels at its edges. A box starting inside
  the hull is stopped at once (time 0) when, traced back along its line, it
  entered less than a trace's length back (as when its centre is still in front
  of the plane it overlaps and it heads in); otherwise it passes (as when it
  heads out of a floor it has sunk into). The walk down the tree tests both
  ends' boxes, grown by a tenth, against each node's plane.
- **An actor's cylinder** (`UPrimitive::LineCheck`, `0x103d8af0`), with the
  line's box added: hit where the line comes in, through a cap or the side,
  within the trace, a thousandth of the trace short (its time − 0.001, held to
  0..1). A line that starts inside (within its height, and its radius with a
  unit's slack: (the start's distance from the axis)² − radius² < 1) is stopped
  at once, at its start, when it heads in toward the axis (the line's run across
  · the start's offset from the axis < −0.1), and passes out freely otherwise: a
  trace straight down from inside a pawn does not hit it. An actor with a mesh
  collides the same way (`UMesh::LineCheck`, `0x103a6d10`, passes it on).
- **`FastTrace(TraceEnd, TraceStart)`** (`0x103e35e0`): whether the line is
  clear of the level's BSP, the segment itself and nothing past it
  (`UModel::FastLineCheck`, `0x103f3280`; its walk `0x103f33a0` lets a line
  through only a node flagged `NF_NotCsg`, not one flagged as not blocking
  visibility); other actors are not asked. The BSP holds the movers' polygons
  too (below), so a closed door stops it. The same check answers
  `LineOfSightTo`, `CanHear`, `pointReachable`, the path searches, network
  relevance and the mixer's sounds behind walls
  ([`Galaxy.dll`](galaxy-dll.md#sounds-behind-walls)); `actorReachable` uses a
  line check of the level and movers instead.
- **The movers in the BSP** (UE1's moving-brush tracker: `GNewBrushTracker`,
  `0x1037c860`; its update `0x1037a400`):
  - `LoadMap` makes the level one for every map but `Entry`, and `SaveGame`
    one again after it saves. It files every moving brush -- an `ABrush` with
    a brush that is not `bStatic`, so every mover, whatever its collision --
    into the level's BSP: each polygon, at the mover's place, split down the
    tree into new nodes (`0x1037c0c0`, `0x1037bb00`). A polygon's node blocks
    the line check but for a `PF_NotSolid` polygon (`NF_NotCsg`);
    `PF_Invisible` or `PF_Portal` makes it a node that does not block
    visibility, `PF_Masked` a shoot-through one.
  - Each frame drawn, `Render.dll`'s `SetupDynamics` updates it for every
    moving brush not hidden, in view or not: one that has moved or turned
    since it was filed is taken out and filed again where it is. So with
    nothing drawn (a dedicated server), and for a hidden mover, the BSP keeps
    the mover where the map's load or the last save filed it.
- **`VisibleActors(BaseClass, Actor, Radius, Loc)`** (`0x103e5260`): each actor
  in the level's list, not hidden, of the class, whose location lies strictly
  within `Radius` of `Loc` (a radius of 0, the default: no limit), with
  `FastLineCheck` clear from `Loc` to it.
- **`VisibleCollidingActors(BaseClass, Actor, Radius, Loc, bIgnoreHidden)`**
  (`0x103e55b0`): each actor the collision hash holds (movers too) whose
  location lies within `Radius` of `Loc` (`FCollisionHash::ActorRadiusCheck`,
  `0x103589e0`; a radius of 0, the default, is 1000), of the class, passed over
  when hidden only with `bIgnoreHidden`, with `FastLineCheck` clear from `Loc`
  to it, asked as the iteration comes to it. `HurtRadius` uses it; Deus Ex's own
  `bIgnoreLOS` takes `RadiusActors` instead.
- **Which surface a level hit gives**: the node the check meets the level at,
  the first of its plane's coplanar nodes, whichever of their polygons the line
  crossed.
- **What an actor collides as** (`AActor::GetPrimitive`, `0x1034c9a0`): its
  brush, else its mesh, else the engine's cylinder of its collision size; so a
  mover with no brush (`09_NYC_ShipBelow` has one) collides as a cylinder. A
  model with no BSP nodes answers every line and point check at once with no hit
  (`UModel::LineCheck`, `0x103f3c20`; `PointCheck`, `0x103f1570`).
- **The multi-hit line check** under the two iterators and `TraceActors`
  (`ULevel::MultiLineCheck`, `0x1039b220`): the level's BSP first, a hit there
  (its actor the `LevelInfo`) cutting the line to 5 units past it; then the
  actors along the cut line, each hit given short by a thousandth of the cut
  line, up to 64 hits in all, nearest first. Nothing beyond the first wall is
  listed.
- **`Trace(HitLocation, HitNormal, TraceEnd, TraceStart, bTraceActors, Extent)`**
  (`0x103e3330`): the first hit (`SingleLineCheck`, flags 55 with
  `bTraceActors`, else 6); with nothing hit the location and normal are zero.
- **`TraceActors(BaseClass, Actor, HitLoc, HitNorm, End, Start, Extent)`**
  (`0x103e4bc0`): every hit of the multi-hit check, in turn, the level's
  among them; `BaseClass` (by default `Actor`) is not tested.
- **`TraceTexture(BaseClass, Actor, texName, texGroup, flags, HitLoc, HitNorm, End, Start, Extent)`**
  (`0x1036e450`; from the actor, with no extent, by default): every hit, in turn
  (`BaseClass` read and not used). A hit on the level gives the surface's
  texture, its group (the texture's outer) and the surface's `PolyFlags`; an
  actor, no texture and flags 0. The scripts use it for the floor under a pawn
  (its footsteps), a laser beam (where it stops, and whether it reflects:
  `PF_Mirrored`), the player, weapons and turrets.
- **`TraceVisibleActors(BaseClass, Actor, HitLoc, HitNorm, End, Start, Extent)`**
  (`0x1036ec50`): the same, `BaseClass` again unused, except that the line
  passes BSP nodes that do not block visibility (node flag 4). An NPC seeking a
  spot uses it for its line of sight: the level blocks it, and an actor with
  `bBlockSight`.
- **`ParabolicTrace(finalLocation, startVelocity, startLocation, bCheckActors, cylinder, maxTime, elasticity, bBounce, landingSpeed, granularity)`**
  (`0x1036e190`, the work at `0x1036c0a0`): a thrown thing's flight, in steps.
  Defaults: the actor's velocity, location, `bCollideActors`, collision cylinder
  and `bBounce`; 5 s; elasticity 0.9; landing speed 60; steps of 0.025 s (held
  to 0.005..1).
  - Each step adds the zone's gravity to the velocity and moves by it plus the
    zone's velocity. On a hit it lands if the surface is a floor (its normal's
    Z > 0.7) and it is not bouncing or is slower than the landing speed; else it
    bounces: the velocity mirrored about the surface × the elasticity, the rest
    of the step slid along it, a second wall handled as falling handles one. The
    speed is held to the zone's terminal velocity.
  - It fails (0, its final location the start) on entering water, leaving the
    world, a step longer than about 1,580 units, or running out of time; else it
    returns the time of flight, and where it landed.

  NPCs use it for where a falling grenade will land, and whether a throw of
  their own is safe (`AISafeToThrow`).
- **`GetBoundingBox(MinVect, MaxVect, bExact, testLocation, testRotation)`**
  (`0x1036dea0`; by default the actor's own place and rotation): puts the actor
  there for the moment, takes its primitive's box (its brush's, else its mesh's,
  else the collision cylinder's; `bExact` passed on), and returns whether the
  box is valid. The scripts pass a mover's place and rotation at one of its
  keys: the HUD's highlight on a door, and a mover's area.
- **`CycleActors(BaseClass, Actor, Index)`** (`0x1036e9d0`): the level's actors
  of the class (Actor by default), from the slot `Index` names (0 when out of
  range), round once; each one found sets `Index` to the slot after it. Empty
  slots are passed over, actors being destroyed are not. NPCs keep the index
  between calls to go on where they stopped (pawns, carcasses, food).

## Blend animations

Four slots of animation over an actor's main one (`BlendAnimSequence[4]` and the
rest): head turns (`PlayTurnHead`), lip sync (`LipSynch`), blinking.

- **`PlayBlendAnim(Sequence, Rate, TweenTime, BlendSlot)`** (`0x103e0d80`; by
  default Rate 1, TweenTime −1, slot 0): `PlayAnim` for a slot (its rate, last
  frame and tween, without the main channel's notifies or loop). A slot outside
  0..3, no mesh or a sequence not in it logs and does nothing.
- **`TweenBlendAnim(Sequence, Time, BlendSlot)`** (`0x103e1300`): `TweenAnim`
  for a slot.
- **The tick.** `AActor::Tick` (`0x103a1aa0`) moves the slots after the main
  animation, as it moves that: a tween up from a negative frame, then the rate
  (or a velocity-scaled one) up to the last frame, where the slot stops. The
  loop copies the main one's conditions and shares its four iterations:
  - it runs only while the main animation plays or tweens, so with the main
    animation stopped the slots do not move;
  - each iteration moves every slot by the frame's time, and a slot that ends or
    finishes its tween leaves the rest only the time over;
  - iterations repeat until the four are spent, so in a frame whose main
    animation had no notify or end the slots move three times (up to three times
    their rate).
- **The mesh.** `ULodMesh::GetFrame` (`0x10355360`) adds each slot's pose to the
  main animation's vertices as its difference from the mesh's first frame, so a
  blend sequence moves only what it changes. A slot tweening in moves from its
  last pose, cached per actor and slot, toward the sequence's first frame.
  `UMesh::GetFrame` does not blend.
- **Its vertex count.** `GetFrame` works out only the vertices the renderer's
  budget asks for, and the special ones, at most a frame's
  ([mesh detail](render-dll.md#mesh-detail)); tweening from the actor's cached
  pose, no more than that pose holds. It reads neither `LODHysteresis` nor the
  mesh's remap of animation vertices.

## Stasis and render time

- **`LastRenderTime`**: `Engine.dll` sets it to −10 s when an actor spawns, and
  for every actor as a level starts ([a level's tick](#a-levels-tick)); the
  renderer keeps it, and a zone's ([render time](render-dll.md#render-time)).
  `LastRendered()` (`0x1036de30`) is the time since, not below 0.
- **`DistanceFromPlayer`**: `ULevel::Tick` sets it for every dynamic actor
  before they tick: the distance to the local player, in single player, not
  while paused.
- **`InStasis()`** (`0x1036bfe0`), true when all hold: not drawn for 5 s;
  `bStasis`; `bForceStasis`, or physics none or rotating; its zone not drawn for
  5 s, or more than 1,200 units from the player; single player.
- **What stasis does.** `AActor::Tick` does nothing else for an actor in stasis
  (no script tick, physics, animation or timers), and destroys one that is
  `bTransient` (the rats a container lets out). The event manager treats a
  listener in stasis as out of sight.

## Render iterators

`URenderIterator` is UE1's (`Engine/Inc/UnRenderIterator.h`): `Init` (calls the
script's `Init` and sets the observer), `First`, `Next`, `IsDone` (once `Index`
reaches `MaxItems`) and `CurrentItem`. Its constructor (`0x103d9cf0`) requires
an actor as its outer. `Engine.dll` only destroys an actor's `RenderInterface`
with it (`AActor::Destroy`); the renderer makes it from `RenderIteratorClass`,
runs it and draws its items
([render iterators](render-dll.md#render-iterators)).

## The network

The protocol (joining, packets, channels, replication, remote calls):
[`network.md`](network.md).

## Latent functions

A latent function's native starts the wait and puts in the state frame's
`LatentAction` the number of the native that polls it, which a save keeps
([a state frame saved](core-dll.md#events-and-probes)): `AActor`'s `Sleep` 384,
`FinishAnim` 385 and `FinishInterpolation` 302 (registered from `0x103e0070`
on); `APawn`'s `MoveTo` 501, `MoveToward` 503, `StrafeTo` 505, `StrafeFacing`
507, `TurnTo` 509, `TurnToward` 511 and `WaitForLanding` 528.

## A saved level

`ULevelBase::Serialize` (`0x1039c5f0`), after the level's properties: the actors
(their count, twice, then each); the URL it was loaded by (protocol, host, map,
portal, options, port, whether valid). `ULevel::Serialize` (`0x1039d560`) then
adds the BSP model, the reach specs, the level's time as a float, the first
deleted actor, 16 text blocks, and the travel info: a count, then each key and
value (package versions 61 and 62 hold the keys and the values as two lists).

## Starting the game engine

- **`UGameEngine::Init`** (`0x103891c0`): after the client, the renderer and the
  Entry level (`entry.dx`), the start URL. It is the command line's first token
  (its second if the first is `SERVER`), but only when the command line has
  `-hax0r` or `-server` and the token does not start with `-`; otherwise, and
  with no token, `FURL::DefaultLocalMap`, which Deus Ex sets to `DX.dx` here. So
  a client given a map on its command line still starts at `DX.dx` unless
  `-hax0r` comes with it. A URL that does not parse, or a level that cannot be
  loaded, is fatal. Then the input, the console (`ini:Engine.Engine.Console`),
  the viewport and the audio.
- **`UEngine::InitAudio`** (`0x1037fe50`): on a client with `UseSound` and
  without `-nosound`, creates `ini:Engine.Engine.AudioDevice` and starts it; one
  that fails to start is logged ("Audio initialization failed.") and dropped.
  With `-nosound` there is no audio subsystem at all: no sound, no music.
- **`OPEN` and `START`** (`UGameEngine::Exec`, `0x1038a030`): with a viewport,
  the URL becomes its next travel (partial for `OPEN`, absolute for `START`);
  without one, the engine browses to it at once. A failure logs "Open failed: "
  or "Start failed: " and the reason. There is no cheat check: this is what a
  line forwarded to the running game runs
  ([the receiver](launch-flow.md#1-single-instance-forwarding-0x10908a300x10908cd1)).

## A level's tick

- **A level's start** (`UGameEngine::LoadMap`, `0x1038c1f0`), for a level not
  yet begun (`bBegunPlay` unset), in order: the level's time set to 0; the
  game's `InitGame`; every actor's `PreBeginPlay` and `BeginPlay`; each actor's
  zone; every actor's `LastRenderTime` set to −10 s, whatever its map kept;
  `PostBeginPlay`; `SetInitialState`; the actors' bases. Each pass runs over
  the actor list as it grows: an actor spawned during the start takes the
  later passes too, after the same events from its spawn (a map's carcass
  spawns its items in `PostBeginPlay`, and the start's `SetInitialState`
  sends them to the `Idle2` the carcass names). A level already begun (from a
  save, or returned to) keeps its own time and render times. Then, begun or
  not, every actor's `PostPostBeginPlay`, and each viewport's player logs in
  with the load's URL (`Spawning new actor for Viewport`).
- **The player's login** (`ULevel::SpawnPlayActor`, `0x10396bd0`), a save's
  load's too: the game's `Login`, its options the URL's (a save's
  `?load?loadonly?loadgame` and the default player's, so `GameInfo.Login`
  keeps the saved player, unoccupied, and Deus Ex's leaves it as saved); the
  player's `TravelPreAccept`; its travelling items' `TravelPreAccept`, none
  for `?loadonly`; the game's `AcceptInventory`; the items'
  `TravelPostAccept`, then the player's; the game's `PostLogin`. Deus Ex's
  player spawns the level's mission script in its `TravelPostAccept` when none
  runs: a save holds none
  ([what a save writes](core-dll.md#packages-and-linkers)).
- **The game** is spawned only for a level whose `LevelInfo.Game` is None, on a
  server or standalone: a level returned to keeps the game it was saved with,
  its mutators and all.
- **The time** (`ULevel::Tick`, `0x103a51a0`): the frame's time × the level's
  `TimeDilation` is added to the level's time, paused or not. The actors, the
  players' input and the event manager get that time held to 0.005..0.4 s.
- **Unpaused** (`Pauser` empty): each dynamic actor's `DistanceFromPlayer`
  ([stasis](#stasis-and-render-time)); each dynamic actor's `Tick`, once, in the
  list's order (one whose owner has not yet ticked this frame waits in a list,
  ticked after the pass once its owner has); then the event manager
  ([each frame](#each-frame-aiprocess-0x10384080)). An actor ticked carries the
  level's mark in `bTicked`, which the level flips after each tick. The mark
  only tells whether an owner has ticked; nothing is passed over for its own
  mark, so a level's first tick ticks every actor its map loaded.
- **Paused:** the players' input, and the actors with `bAlwaysTick`.
- **An actor's tick** (`AActor::Tick`, `0x103a1aa0`), as a standalone game's
  ([by role](network.md#replication)): nothing else in stasis; its animation;
  then its script `Tick`, its state code, its timer, its `LifeSpan` and its
  physics, in that order. A player's pawn with a player (not a camera) has, in
  place of `Tick`, its player's input read, `PlayerInput` and `PlayerTick`, and
  the input read again with −1 (cleared); so its physics, later in the same
  tick, take the move `PlayerTick` makes.

## Destroyed actors

**`ULevel::DestroyActor(actor, bNetForce)`** (`0x10395ba0`):

- It refuses a `bStatic` or `bNoDelete` actor (0), and returns 1 at once for
  one already `bDeleteMe`. A client destroys only what it has authority over,
  unless forced or the actor is `bNetTemporary`; a player pawn with a live net
  connection has the connection closed instead.
- Then, any step stopping once the script has destroyed the actor itself: the
  `EndState` of its state, if it probes it; its base cleared, and every actor
  standing on it set free; out of the collision hash; `Destroyed`; every actor
  it owns loses its owner, every actor it touches is untouched; its owner's
  `LostChild`; the net and demo drivers told.
- Its slot in `Actors` becomes None, `bDeleteMe` is set, the audio subsystem is
  told (`NoteDestroy`), and the actor is destroyed (`ConditionalDestroy`: its
  strings and arrays emptied, [Core](core-dll.md#garbage-collection)). It goes
  to the head of the level's `FirstDeleted` chain, linked through its
  `Deleted`. Its memory is not freed yet.

**`ULevel::CleanupDestroyed(bForce)`** (`0x103965a0`), the last thing every
`ULevel::Tick` does (unforced):

1. Unforced, `CompactActors` (`0x103963e0`): the None slots after
   `iFirstDynamicActor` are taken out of `Actors`, the actors' order kept; an
   actor still in the list with `bDeleteMe` is logged (`Undeleted %s`) and
   taken out too.
2. With 128 or more actors on `FirstDeleted`, or forced: every live actor in
   `Actors` has its class clear its references to pending-kill actors
   ([`UStruct::CleanupDestroyed`](core-dll.md#garbage-collection)).
3. Then each actor on the chain, from its head: the event manager is told
   (`UEventManager::DestroyActor`, [the manager](#the-manager)), and the actor
   is deleted (the virtual at +12).

So below 128 a destroyed actor stays in memory, and every reference to it stays
set: the script tests `bDeleteMe`, or the reference's object, to tell. It is
forced before a level is saved: `SaveCurrentLevel`
([`DeusEx.dll`](deusex-dll.md#the-game-engine-travel-and-saving)), and the
level a map load leaves ([the map load's collection](#the-map-loads-collection)).

**A decal** leaves the surfaces it is on only through `DetachDecal`
(`execDetachDecal`, `0x103e9a30`), which the script's `Decal.Destroyed` calls.
`execAttachDecal` (`0x103e7250`) does not test `bDeleteMe`, and `ADecal`'s
destructor (`0x1030fd60`) empties only the decal's own list of surfaces. So a
decal attached again after its `Destroyed` stays on its surfaces, and once the
cleanup deletes it they point at the deleted decal.

## The map load's collection

`UGameEngine::LoadMap` (`0x1038c1f0`):

- **The old level.** Its loaders are reset, its brush tracker, net driver and
  demo driver deleted; with `?push` it is cleaned (`CleanupDestroyed(1)`) and
  saved as `Game%04i.dxs`. `GLevel` is then None; nothing flags the old
  level's objects.
- **The new level, once loaded,** unless its package is `Entry`, before its
  actors' collision, game info, `BeginPlay` and the player's login: the
  engine's `Flush(0)`; every actor inside the new level's
  package is flagged `RF_EliminateObject`, and the flag is cleared again on each
  actor in its `Actors`; then `CollectGarbage(RF_Native)` (the call at
  `0x1038d1e1`).
- So the old level goes by reachability alone, and an actor of the new
  package left out of its list (an orphan) goes too, every reference to it made
  None.

## Sounds

Who hears a sound an actor plays. What the audio subsystem then does with it:
[`Galaxy.dll`](galaxy-dll.md#playing-a-sound).

- **`PlaySound(Sound, Slot, Volume, bNoOverride, Radius, Pitch)`**
  (`0x103e1f60`; by default `SLOT_Misc`, the actor's `TransientSoundVolume` and
  `TransientSoundRadius`, pitch 1): with no sound, nothing. A radius ≤ 0 is
  800. While the level records a demo, and is not a client's, the actor's
  `DemoPlaySound` event gets the same. Deus Ex returns its ID: the actor's
  object index × 16 + the slot × 2, + 1 with `bNoOverride`. Each hearer is
  asked (`CheckHearSound`) with the volume × 100, the radius and the pitch ×
  100, and the radius squared:
  - on a client, or called from a script function marked simulated (state code
    never is), the player of each viewport in the actor's level;
  - otherwise each pawn in the level's `PawnList` with `bIsPlayer`: in single
    player, the player's.
- **`CheckHearSound(Hearer, Id, Sound, Parameters, RadiusSq)`**
  (`0x103e1b00`): the listener is a player pawn's `ViewTarget` when it has one,
  else the hearer, at its location, not its eyes. It hears within the radius ÷
  √1.3 (0.88 of it). When the level's BSP stands between the actor and the
  listener (`FastLineCheck`, [traces](#traces)), the volume is × 0.35, the
  range's square × 0.6 (the radius × 0.77) unless the hearer is the actor's
  `Instigator`, and a hearer on the range's edge hears it too. Then the
  hearer's event `ClientHearSound(Actor, Id, Sound, the actor's location,
  Parameters)`.
- **`Pawn.ClientHearSound`**, a native event, is replicated unreliably while
  the server has authority (`Engine.u`): a remote player's goes to that
  player's client ([remote functions](network.md#replication)), a local
  player's runs at once. Its native (`0x103dfc40`) plays the sound only for a
  player pawn whose `Player` is a viewport, with an audio subsystem: the volume
  and pitch ÷ 100, a radius of 0 as 1,600, an actor with `bDeleteMe` as None.
- **An event** reaches an actor only once its level has begun play
  (`AActor::ProcessEvent`, `0x10369100`).
- **`PlayOwnedSound`** (`0x103e29d0`; the same arguments and defaults): no ID
  and no 800, its range 1,600 for a radius of 0. A client's viewports hear it;
  off a client, every player pawn but the actor's own remote player, who plays
  the sound itself: the actor, if a player pawn whose `Player` is not a
  viewport, else its owner by the same test. In single player, the player.
- **`DemoPlaySound`** (`0x103e1d00`): the viewports' players, a radius of 0 as
  1,600.
- **`StopSound(Id)`** (`0x103e27d0`) hands the ID to the audio subsystem (its
  virtual at +0x78), which stops that sound.

## Small

- **`LevelInfo`'s clock** (`Year`, `Month`, `Day`, `DayOfWeek`, `Hour`,
  `Minute`, `Second`, `Millisecond` at `ALevelInfo+0x47c` to `0x49c`;
  `transient` in `Engine.u`; the script's one reader is `StatLog`'s date string)
  holds the full year and the month 1 to 12, from `GetLocalTime`. The virtual
  `ULevel::UpdateTime` (`0x103a08f0`; export
  `?UpdateTime@ULevel@@UAEXPAVALevelInfo@@@Z`, jump `0x10301b18`) passes the
  eight fields by reference to Core's `appSystemTime` (import `0x1059a05c`; in
  `Core.dll` `0x1016c6a0`, jump `0x101033be`) in that call's order (year, month,
  day of the week, day, then the time): `DayOfWeek` (`+0x488`) third, `Day`
  (`+0x484`) fourth. No store to them shows in `Engine.dll`.
- **`SetInstantSoundVolume`, `SetInstantSpeechVolume`, `SetInstantMusicVolume`**
  (`0x103e2850`, `0x103e28d0`, `0x103e2950`): hand the volume to the audio
  subsystem's own call for it (its virtuals at +0x90, +0x94, +0x98), which
  applies it at once instead of at the next tick
  ([`Galaxy.dll`](galaxy-dll.md#volume)).
- **`GetPlayerPawn()`**: the first viewport's actor.
- **`FGetHSV(hue, saturation, value)`** (`0x103ec8d0`): the colour of a light
  and of a zone's ambient light, as the renderer lights with it
  ([`Render.dll`](render-dll.md#lighting)).
- **`IsOverlapping(other)`** (`0x10369430`): collision cylinders overlap; a
  brush or the level never does.
- **`GetMeshTexture(texnum)`** (`0x103e17c0`): the actor's skin of that number
  (`GetSkin`); else, for a number above 0, the mesh's texture of that number;
  else the actor's `Skin`; else the mesh's texture.
- **`FindStairRotation(DeltaTime)`** (`0x103bb880`): UE1's own. With a frame of
  0.33 s or less, it probes the floor ahead at eye height and eases the view
  pitch toward looking down (−5,000) or up (5,400) a flight of stairs, or back
  to level.
- **`ResetKeyboard()`** (`0x103b96d0`): `UObject::ResetConfig` of the class of
  the viewport's input; `DeusExPlayer.TravelPostAccept` calls it on every level.
  What that does in Deus Ex: [configuration](core-dll.md#configuration).
