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
blend slots in the actor tick, blending in the mesh. All of it is read,
below.

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
  in the bucket of its hash's low byte -- UE1's `appStrihash`
  ([names](core-dll.md#names-hashed-and-compared)) -- and kept in name order
  within it by `appStricmp`; `FindEvent`, `0x103834b0`). Each type lists its
  senders (`XAISenderEvent`, one per actor raising it) and its receivers
  (`XAIReceiverEvent`, one per actor listening), each list in the order its
  events came, and every receiver is also in one ring the manager walks: a
  circle, a new receiver put before the one the manager resumes at. All are
  objects in the level.
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

### Saved

`Serialize` (`0x103825f0`), after the manager's properties: the level;
`refProcessing`, `deleteCount` and `currentSlot`, 4 bytes each (the first
two asserted 0, a save deleting the marked events first); the receiver the
ring resumes at; then each bucket's first type. Each type, sender and
receiver is an object of its own -- `Engine.AIEventType`,
`Engine.AISenderEvent` and `Engine.AIReceiverEvent` in a save's imports --
owned by the manager and named by its class and a count
(`AIReceiverEvent105`). Their fields, after their properties (they have
none):

- **A type:** its name; its hash, the whole `appStrihash`; its first sender
  and first receiver; the bucket's next type.
- **A sender or receiver:** its type, its actor, whether it is being
  destroyed (4 bytes), and its list's next event.
- **A sender,** then: the four numbers of each of its 16 slots, then its four
  current levels, as floats.
- **A receiver,** then: its callback and score callback (names); whether a
  call is due (4 bytes) and the state for it (a byte); the four checks and
  whether its event is on (4 bytes each); the best score (a float) and the
  best sender; the first slot its next turn weighs (4 bytes: the slot that
  became current after its last turn); the ring's next and previous
  receivers, one alone its own neighbour. Its `XAIParams` are not saved.

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
  by patch 0034 ([its message](https://github.com/JuggyMcNutty/VibeEngine/commit/b5d08853dbf4e24894d56942c07a5a743438e824)).
- **`LineOfSightTo(Other, bUseLOSFlag, bIgnoreDistance)`** (`0x103beb50`):
  UT's, with a third flag that lifts every distance limit. Beyond a reach
  it answers no: for a player looking, (Visibility + 16) × 0.015 of 5,000
  units for a pawn (the factor held to 1) and 4,000 for what is none; for
  another pawn, the same of 4,000 and 3,000 -- or, with `bUseLOSFlag` and
  `Other` not its enemy, its `SightRadius` times Visibility / 128, held to
  4,000 for a player and 3,464 for another, nothing outside its
  `PeripheralVision`, and the distance scaled up toward that edge and by
  the height between.
  Then lines from its eyes, each a `FastLineCheck`: its enemy it sees
  along one to the enemy's middle, noting where each stood; anything else
  beyond 1,000 units only along that line -- a pawn beyond half the reach
  not at all, unless `bLOSflag` is set, and half the time not at all when
  the looker is no player; nearer, to 0.8 of `Other`'s height over its
  middle, and failing that, within 500 units and for a pawn, to two of its
  cylinder's four corners at its middle's height -- the nearest and the
  farthest left out, both measured from the world's origin, as UT's code
  measures them, and with `bUseLOSFlag` each other one tried. The script's
  `LineOfSightTo(Other, bIgnoreDistance)` calls it without the LOS flag
  (`0x103bce10`), `CanSee(Other)` with it and no lifting (`0x103ba5d0`).
- **`PlayerCanSeeMe`** (`0x103ba640`): whether any local player -- each
  viewport's, standalone; each pawn's in a net game -- sees the actor
  (`TestCanSeeMe`, `0x103ba8a0`): the player's view target sees it; else
  it must lie within (collision radius + 3.6) × 100,000 squared units, and
  -- unless the view is behind -- within 60 degrees of the view's line,
  either way along it (the cosine squared), and then the player's
  `LineOfSightTo` it.

## Moving

- **Walking over the floor** (`APawn::physWalking`, `0x103ca540`): a
  walking pawn floats. Standing still on the same base, a line 20 units
  down from the middle of its cylinder's bottom that finds the floor 4.1 to
  4.6 away leaves it be. Otherwise a box trace of its cylinder, down
  `MaxStepHeight` + 2, measures the floor: with none in reach, or the same
  base 2.4 or nearer, one nearer than 1.9 lifts the pawn to 2.1; with a
  farther or another base it moves down onto it and takes what it stands
  on for its base -- for the world the `LevelInfo`. Those distances are the
  traces' own, short of the floor by their backoff ([traces](#traces)):
  the box trace's a tenth of its length, so a pawn with `MaxStepHeight` 25
  stands 4.8 over the floor -- measured 4.75 at Liberty Island's start.
- **Moving toward a spot** (`APawn::moveToward`, `0x103be250`), a tick of
  `MoveTo` or `MoveToward`: the spot is reached within 16 units across
  (walking, the height ignored; else within the pawn's height, at least 48,
  up or down), when the move's time is out, or for a pawn target within
  both radii and 0.8 of `MeleeRange`. Else the acceleration is set straight
  at the spot at the full `AccelRate` -- a glider (`bCanGlide`, not
  `bCanStrafe`, flying or swimming) along its facing --; a pawn moving over
  100 units a second has it steered by (its velocity's direction − the
  spot's) × (1 − their cosine) × speed × 0.2 taken off; within 1.4 of
  `AvgPhysicsTime` of travel of the spot the speed is halved once
  (`bReducedSpeed`) and held to 200 units a second over the speed. An item
  target within the pawn's radius and height is touched. Falling, a pawn
  steers only where gravity is under 0.9 of its zone's default, and
  arrives 100 units under the spot.
- **The latent moves** (`execMoveTo` `0x103bceb0`, `execMoveToward`
  `0x103bd150`; their polls `0x103bd060`, `0x103bd370`): the call clears
  `bReducedSpeed`, takes the speed held to 0 to `MaxDesiredSpeed`, times
  the move (`setMoveTimer`: 1 + 1.3 × distance over the physics' speed
  times `DesiredSpeed`, 0.5 with no speed; 1.2 s toward a pawn), and takes
  the first step at once. Each tick after, the destination is the
  target's place (a flyer's 0.7 of a pawn's height higher), and a pawn
  with `bAdvancedTactics` walking has its `AlterDestination` event turn it
  before the step -- Deus Ex's NPCs walking around what they bumped; a
  pawn target's speed is kept as it was, and one in water is given up by
  a pawn that cannot swim. `APawn::performPhysics` counts the move's time
  down and keeps `AvgPhysicsTime` at 0.8 of itself and 0.2 of the tick
  (`0x103c9c37`).
- **The speed** (`APawn::calcVelocity`, `0x103cd7a0`): an acceleration
  over `AccelRate` -- over 0.3 of it for a player walking (`bIsWalking`) --
  is cut to it; one under it is left.
- **The next node** (`APawn::findPathToward`, `0x103db3f0`): once the
  route is found, the node after its first is taken instead when it lies
  within 120 units up or down (or the pawn stands at the first), clear of
  the level from the eyes, and reachable.
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
- **`StrafeTo(dest, focus, speed)`** and **`StrafeFacing(dest, target,
  speed)`** (`0x103bd5f0`, `0x103bd8c0`), speed 1 by default: UE1's strafes
  with Deus Ex's speed. A player's `DesiredSpeed` is its `MaxDesiredSpeed`;
  an NPC's is that held to at most the speed and at least 0. Both clear
  `bReducedSpeed` and time the move by its distance. `StrafeTo` drops the move
  target and looks at the focus; `StrafeFacing` needs a target (without one it
  does nothing), faces it and looks at where it is. The scripts give no speed:
  NPCs running and firing (`StrafeFacing`, in combat) and stepping back from a
  door (`StrafeTo`).
- **`SetPhysics(newPhysics, newFloor)`** (`0x103c8ea0`; `AActor::setPhysics`,
  `0x103c95f0`): when the physics changes to none, walking, rolling, rotating
  or spider, the actor takes `newFloor` as its base -- through the floor's
  `SupportActor` event, which bases it -- or, with none, finds its base below;
  to any other, it leaves its base. None and rotating also stop its velocity
  and acceleration. The scripts pass the wall hit as grenades, pool balls,
  basketballs and fragments come to rest.
- **Falling in water** (`physFalling`, `0x103d0a50`): gravity is scaled by
  1 − `Buoyancy` / `Mass`, the mass floored at 1, so a massless actor
  (Deus Ex's `GeneratorScout`, a pawn of mass 0) falls at full gravity.

### The search

`findPathToward` (`0x103db3f0`, `AActor* findPathToward(AActor* Goal, INT MaxNodes, ANavigationPoint** EndNode, INT bSinglePath)`)
finds the node the goal is in or nearest (`GetPathnodeList`, `0x103c6490`),
asks whether the goal itself can be walked to (`CanMoveTo` for a navigation
point, `pointReachable` for a spot), and only then searches. `execFindPathToward`
(`0x103bc9c0`) reads the goal, then `MaxNodes` (0 by default), then `bSinglePath`
(1), and seeds the start node's `visitedWeight` with the node's own weight from
the goal before the search (`0x103db875`, `0x103db980`). None of Deus Ex's eleven
calls passes `MaxNodes`, so it is 0.

- **`breadthPathFrom(StartNode, EndNode, MaxNodes, MoveFlags)`** (`0x103dcd60`),
  the search itself. It walks **the level's navigation point list in order** from
  the start node -- `Node = Node->nextNavigationPoint`, the same list
  `clearPaths` walks -- expanding each, and gives up when a node it reaches is
  marked as an end point:
  - the cost of reaching a node over a reach spec (`LevelReachSpec::distance` at
    its first dword, its `startActor` the second, `collisionRadius` the fourth,
    `collisionHeight` the fifth, `reachFlags` the sixth) is
    **`distance + nextNode->cost + node->visitedWeight + nextNode->bestPathWeight * (nextNode->bEndPoint ? 1 : 0)`**,
    where `upstreamPaths` (the 16 ints at `0x320`) is the reverse travel
    direction, so the node reached is the spec's `startActor`. A spec is skipped
    where the pawn's collision radius or height is the larger, or where the
    flags it needs are not all in the spec's (`(MoveFlags & spec.reachFlags) !=
    spec.reachFlags`);
  - a node is taken only when the cost is **less than** what it last cost;
  - an open list of the nodes not yet expanded is kept sorted by that cost, out
    of the nodes' own `nextOrdered` (`0x430`) and `prevOrdered` (`0x434`): a node
    already in it is taken out first, then put back where the cost belongs,
    found by walking the list (at most 500 steps -- "Breadth path list overflow
    from %s", naming the **start** node -- after which the search gives up). The
    list's front walks on as far as half the index the list has grown to. **No
    node is ever taken off the open list to be expanded**: the walk is the
    level's own list, so this bookkeeping is kept and never read;
  - the caps: `MaxNodes` given, the search gives up after four nodes, silently;
    otherwise after 1000, logging "1000 Navigation nodes". Both names the start
    node;
  - the route is the end node's `previousPath` (`0x43c`) back, the start node's
    cleared (`StartNode->previousPath = 0`), and `ReverseRouteFor` (`0x10302ffe`)
    reverses it.
- **`clearPaths`** (`0x103da050`) resets what the search keeps in the nodes: for
  every navigation point, `visitedWeight = 10000000`, `bEndPoint` off,
  `nextOrdered = prevOrdered = 0`, and `cost` from the `SpecialCost` event with
  the pawn given, or `ExtraCost`. Nothing else calls it: `execFindRandomDest`,
  `execClearPaths` and `execComputePathnodeDistances` do, and no Deus Ex script
  calls `ClearPaths`. **So a search does not clear the end points, and neither
  does anything else between searches** except an NPC wandering (which runs
  `FindRandomDest`): the marks in a level are whatever the last flood left, of
  whatever nodes it was run from, and the search stops at the first of them it
  meets walking the list. The fork clears them before every search and marks
  its own fresh set each time; that, and not the marking itself, is what a port
  of `definePathsFor` in place of `MarkReachableNavEndPoints` gets wrong.
- **`calcMoveFlags`** (`0x10326d10`) packs seven bits of the pawn's own flag
  word (`0x318`, `Pawn`'s bitfields) into the seven bits the reach specs carry,
  lowest first: `bCanWalk`, `bCanFly`, `bCanSwim`, `bCanJump`, `bCanOpenDoors`,
  `bCanDoSpecial` and `bIsPlayer` (the pawn word's bits 13, 15, 14, 12, 16, 17
  and 1).
- **`definePathsFor(&Node, Pawn)`** (`0x103daaa0`, called through a thunk at
  `0x10302522`) marks the end points. With no node, nothing. It sets that node's
  `cost` to 1,000,000, then walks its `Paths` (`0x360`) and `PrunedPaths`
  (`0x3a0`), 16 each, `-1` ending either: a spec that fits the pawn's radius,
  height and move flags is traced between its two nodes
  (`ULevel::LineCheck` through the virtual at vtable slot `0x30`, flags 6), and
  where nothing blocks it -- or where what does is not an `AMover`, or is one
  and the pawn can open doors (`bCanOpenDoors`) and is either the player
  (`bIsPlayer`) or the mover is not the player's alone (`AMover`'s `bPlayerOnly`,
  bit 3 of its flag word at `0x4ec`) -- the spec's **end** actor is marked as an
  end point and given the spec's distance as its `bestPathWeight`. `findPathToward`
  calls it before searching.
- **Which node `definePathsFor` is given** is not settled: `findPathToward` takes
  its node from `GetPathnodeList` on the **goal's** location
  (`0x103db600`, `0x103db932`), which would make the end points the goal's own
  forward neighbours -- and the search walks the level's list **backwards** from
  the goal, so it would never meet one. Marking instead from the node the pawn
  stands on (the reading that suits a backward search stopping at what the pawn
  can walk to) is what the fork tried, and neither reading reproduced the
  original's routes (MoveConsole, 47 of Liberty Island's 52 pawns' distance
  moved against the original's, where the fork's own marking gives 50). What is
  missing is therefore something in `GetPathnodeList`'s node list or in the
  goal-side `findPathToward` flow between the two calls, not the marking itself.

### Teleporting an actor

`SetLocation` is `ULevel::FarMoveActor(actor, spot, test, noCheck)`
(`0x10398ba0`), which the engine uses for its own moves too:

- A static actor, or one not `bMovable`, stays where it is (false), except in
  the editor.
- Unless `noCheck`: an actor that collides with the world -- or has
  `bCollideWhenPlacing`, off clients -- is fitted in near the spot
  (`FindSpot`, `0x10398480`: in the captures it moved the player 7 to 15
  units, clear of a ceiling or a floor); no fit, false. Then, unless a test,
  the encroachment check at the spot, with touches (`CheckEncroachment`,
  `0x1039a350`): an actor there that blocks it and whose `EncroachingOn`
  agrees stops the move (false); those it no longer overlaps are untouched,
  and those there that do not block it touched.
- **`FindSpot(extent, spot, bCheckActors, bCheckFirst)`**, the extent the
  collision box's (radius, radius, height): with `bCheckFirst`, a spot where
  the box fits already is kept. Otherwise the spot is pushed out of the
  walls (`AdjustSpot`, `0x10398360`: a line from the spot toward a point,
  level and movers; hit at time t, the spot goes back along the wall's
  normal by (1.05 − t) times the line's length) toward −X, −Y and −Z,
  then +X, +Y and +Z, each by the box's reach on that axis; where the box
  fits then, that is the spot. Else it is pushed the
  same way toward the box's eight corners, each line |extent| + 2 long, and
  kept if it moved no more than √1.5 times |extent| and the box fits there;
  otherwise no spot. `FarMoveActor` passes neither flag; `SpawnActor`
  passes `bCheckFirst`.
- **What blocks what** (`AActor::IsBlockedBy`, and the same test in
  `CheckEncroachment`): the world and brushes block an actor that collides
  with the world, by their `bBlockPlayers` for a player's pawn (a
  `PlayerPawn` with a `Player`) and `bBlockActors` otherwise; two actors
  block each other when each blocks the other's kind, a projectile counting
  as a player. `CheckEncroachment` checks only an actor that collides with
  actors or blocks (or a brush); after the `EncroachingOn` questions, each
  actor there that blocks it hears `EncroachedBy`.
- **Spawning** (`ULevel::SpawnActor`, `0x10394f60`) fits the new actor in the
  same way, then, after `PostBeginPlay` and unless `bNoCollisionFail`, checks
  its encroachment without touches: stopped, it is destroyed and the spawn
  fails.
- Unless a test, whatever stands on it is unbased (`SetBase(None)`, with the
  event) and it is marked `bJustTeleported`, so physics does not take the
  jump for speed.
- `Location` and `OldLocation` both become the spot, and its zone is found
  again ([below](#the-zone-an-actor-is-in)) -- silently for a test.

The engine's own moves: a trailer follows its owner with `noCheck`
(`physTrailer`, `0x103d7850`); `AIDirectionReachable` puts the pawn back as a
test with `noCheck`; Deus Ex's particle iterator moves its proxy with neither
([deusex-dll.md](deusex-dll.md)).

### The zone an actor is in

`SetActorZone(actor, test, forceRefresh)` (`0x1039b940`):

- A deleted actor is skipped; the level's own info is always in its own
  zone. `forceRefresh` first puts the actor -- and a pawn's feet and head --
  in the level's zone, with no events.
- The zone at its location replaces the old. When they differ, unless a
  test: the old zone's `ActorLeaving`, then the actor's `ZoneChange` -- while
  `Region` still holds the zone being left, which scripts compare with the
  new (a `Decoration` or an `Inventory` splashes only coming out of dry) --
  then `Region` is set, then the new zone's `ActorEntered`.
- A pawn's feet (its location less its collision height) and head (plus
  `EyeHeight`) the same way, each with `FootZoneChange` or `HeadZoneChange`
  before it is set; then, off clients, its `PlayerReplicationInfo`'s
  `PlayerZone`.

That is all: Deus Ex's scripts do the rest -- pain zones' `PainTime`
(`Pawn.FootZoneChange` and `HeadZoneChange`), stray inventory in a
`bNoInventory` zone (`ZoneInfo.ActorEntered` gives it 1.5 seconds) and
`bDestructive` (decorations and fragments).

## Traces

- **Backoff** (`UModel::LineCheck`, `0x103f3c20`): a hit on the BSP -- the
  level's, or a mover's brush, its normal turned by the mover's rotation --
  is given short of the surface -- a line's 0.5 units, a box's a tenth of
  the trace's length, or 0.1 units for a trace shorter than one --, its
  time held to 0 to 1, the rest of the move not taken. A line's hit lies
  on the line; a box's time starts at 2, so a hull the box enters up to
  twice the trace's length is found, and a hit the backoff brings under 1
  counts -- one up to a tenth of the trace past its end -- where one still
  at 1 is none. A script's `Trace` straight down finds the floor half a
  unit above it.
- **The box check's hulls** (`0x103f42f0`, set up at `0x103f18e0`): in each
  solid leaf the box reaches, its convex hull's planes pushed out by the
  box (|nx·ex| + |ny·ey| + |nz·ez|); then, for the level's hulls only, the
  planes of the hull's box -- a tenth of a unit bigger at both ends in Z
  and toward −X and −Y, and as much smaller at +X and +Y --; then bevels
  at its edges. A box that starts inside the hull is stopped at once (time
  0) when, traced back along its line, it entered less than a trace's
  length back -- as when its centre is still in front of the plane it
  overlaps and it heads in -- and otherwise passes, as when it heads out of
  a floor it has sunk into. The walk down the tree tests both ends' boxes
  grown by a tenth against each node's plane.
- **An actor's cylinder** (`UPrimitive::LineCheck`, `0x103d8af0`), the
  line's box added to it: hit where the line comes in, through a cap or
  the side, within the trace, the hit given a thousandth of the trace
  short (its time less 0.001, held to 0 to 1). A line that starts inside --
  within its height, and its radius with a unit's slack (the start's
  distance from the axis squared, less the radius squared, under 1) -- is
  stopped at once, at its start, when it heads in toward the axis (the
  line's run across, dotted with the start's offset from the axis, under
  −0.1), and passes out freely otherwise: a trace straight down from
  inside a pawn does not hit it. An actor with a mesh collides the same
  way (`UMesh::LineCheck`, `0x103a6d10`, passes it on).
- **`FastTrace(TraceEnd, TraceStart)`** (`0x103e35e0`): whether the line is
  clear of the level's BSP, the segment itself and nothing past it
  (`UModel::FastLineCheck`, `0x103f3280`), other actors not asked. The BSP
  holds the movers' polygons too while the level runs -- UE1's moving-brush
  tracker files them in (`GNewBrushTracker`, `0x1037c860`) --, so a closed
  door stops it: seen at 16 of Liberty Island's doors (2026-09-28). The
  same check answers `LineOfSightTo`, `CanHear`, `pointReachable`, the path
  searches and network relevance; `actorReachable` looks with a line check
  of the level and movers instead.
- **`VisibleActors(BaseClass, Actor, Radius, Loc)`** (`0x103e5260`): each
  actor in the level's list, not hidden, of the class, whose location lies
  within `Radius` of `Loc` (strictly; a radius of 0, the default, no
  limit), with `FastLineCheck` clear from `Loc` to it.
- **`VisibleCollidingActors(BaseClass, Actor, Radius, Loc,
  bIgnoreHidden)`** (`0x103e55b0`): each actor the collision hash holds --
  movers too -- whose location lies within `Radius` of `Loc`
  (`FCollisionHash::ActorRadiusCheck`, `0x103589e0`; a radius of 0, the
  default, is 1000), of the class, passed over when hidden only if
  `bIgnoreHidden`, with `FastLineCheck` clear from `Loc` to it, asked as
  the iteration comes to it. `HurtRadius` uses it, and Deus Ex's own
  `bIgnoreLOS` takes `RadiusActors` instead.
- **Which surface a level hit gives**: the node the check meets the level
  at -- the first of its plane's coplanar nodes, whichever of their
  polygons the line crossed (seen: `TraceTexture`'s textures along 107
  lines on Liberty Island, 2026-09-28).
- **What an actor collides as** (`AActor::GetPrimitive`, `0x1034c9a0`): its
  brush, else its mesh, else the engine's cylinder of its collision size --
  so a mover with no brush (`09_NYC_ShipBelow` has one) collides as a
  cylinder. A model with no BSP nodes answers every line and point check at
  once with no hit (`UModel::LineCheck`, `0x103f3c20`; `PointCheck`,
  `0x103f1570`).
- **The multi-hit line check** under the two iterators
  (`ULevel::MultiLineCheck`, `0x1039b220`): the level's BSP first; a hit there
  (its actor the `LevelInfo`) shortens the line to 5 units past it; then the
  actors along what is left, up to 64 hits in all, nearest first. Nothing
  beyond the first wall is listed.
- **`TraceTexture(BaseClass, Actor, texName, texGroup, flags, HitLoc,
  HitNorm, End, Start, Extent)`** (`0x1036e450`), from the actor by default,
  with no extent: every hit, in turn -- `BaseClass` is read and not used. A
  hit on the level gives the texture of the surface hit, its group (the
  texture's outer) and the surface's `PolyFlags`; an actor, no texture and
  flags 0. The scripts use it for the floor under a pawn (its footsteps), a
  laser beam (where it stops, and whether it reflects: `PF_Mirrored`), the
  player, weapons and turrets.
- **`TraceVisibleActors(BaseClass, Actor, HitLoc, HitNorm, End, Start,
  Extent)`** (`0x1036ec50`): the same, `BaseClass` again unused, except that
  the line passes BSP nodes that do not block visibility (node flag 4). An NPC
  seeking a spot uses it for its line of sight: the level blocks it, and an
  actor with `bBlockSight`.
- **`ParabolicTrace(finalLocation, startVelocity, startLocation,
  bCheckActors, cylinder, maxTime, elasticity, bBounce, landingSpeed,
  granularity)`** (`0x1036e190`, the work at `0x1036c0a0`): a thrown thing's
  flight, in steps. By default the actor's velocity, location,
  `bCollideActors`, collision cylinder and `bBounce`, 5 s, an elasticity of
  0.9, a landing speed of 60, and steps of 0.025 s (held between 0.005 and
  1).
  - Each step adds the zone's gravity to the velocity and moves by it and the
    zone's velocity. On a hit it lands if the surface is a floor (normal Z
    above 0.7) and it is not bouncing or is slower than the landing speed;
    else it bounces: the velocity mirrored about the surface and times the
    elasticity, the rest of the step slid along it, a second wall handled as
    falling handles one. It holds the speed to the zone's terminal velocity.
  - It fails -- 0, the start its final location -- on entering water, leaving
    the world, a step longer than about 1,580 units, or running out of time;
    else it returns the time of flight, and where it landed.

  NPCs use it for where a falling grenade will land, and whether a throw of
  their own is safe (`AISafeToThrow`).
- **`GetBoundingBox(MinVect, MaxVect, bExact, testLocation, testRotation)`**
  (`0x1036dea0`), at the actor's own place and rotation by default: puts the
  actor there for the moment and takes its primitive's box -- its brush's,
  else its mesh's, else the collision cylinder's (`bExact` passed on) -- and
  returns whether the box is valid. The scripts pass a mover's place and
  rotation at one of its keys: the HUD's highlight on a door, and a mover's
  area.
- **`CycleActors(BaseClass, Actor, Index)`** (`0x1036e9d0`): the level's
  actors of the class (Actor by default), from the slot `Index` names (0 when
  out of range) and round once; each one found sets `Index` to the slot after
  it. Empty slots are passed over, actors being destroyed are not. NPCs keep
  the index between calls to go on where they stopped (pawns, carcasses,
  food).

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
- **Its vertex count.** `GetFrame` works out only the vertices the renderer's
  budget asks for, and the special ones, at most a frame's
  ([mesh detail](render-dll.md#mesh-detail)); tweening from the actor's cached
  pose, no more than that pose holds. It reads neither `LODHysteresis` nor the
  mesh's remap of animation vertices.

## Stasis and render time

- **`LastRenderTime`**: `Engine.dll` sets it to −10 s when an actor spawns,
  and for every actor as a level starts ([a level's tick](#a-levels-tick));
  the renderer keeps it, and a zone's
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

## The network

The protocol -- joining, packets, channels, replication and remote calls --
is in [`network.md`](network.md).

## Latent functions

A latent function's native starts the wait and puts in the state frame's
`LatentAction` the number of the native that polls it, which a save keeps
([a state frame saved](core-dll.md#events-and-probes)): `AActor`'s `Sleep`
384, `FinishAnim` 385 and `FinishInterpolation` 302 (registered at
`0x103e0070` and on), `APawn`'s `MoveTo` 501, `MoveToward` 503, `StrafeTo`
505, `StrafeFacing` 507, `TurnTo` 509, `TurnToward` 511 and `WaitForLanding`
528.

## A saved level

`ULevelBase::Serialize` (`0x1039c5f0`), after the level's properties: the
actors -- their count, twice, then each -- and the URL it was loaded by:
protocol, host, map, portal, options, port and whether it is valid.
`ULevel::Serialize` (`0x1039d560`) then adds the BSP model, the reach specs,
the level's time as a float, the first deleted actor, 16 text blocks, and
the travel info: a count, then each key and value (package versions 61 and
62 wrote the keys and the values as two lists).

## Starting the game engine

- **`UGameEngine::Init`** (`0x103891c0`): after the client, the renderer and
  the Entry level (`entry.dx`), the start URL. It is the command line's first
  token -- or its second, if the first is `SERVER` -- but only when the
  command line has `-hax0r` or `-server`, and not when the token starts with
  `-`. Otherwise, and when there is no token, it is `FURL::DefaultLocalMap`,
  which Deus Ex sets to `DX.dx` here. So a client given a map on its command
  line still starts at `DX.dx` unless `-hax0r` comes with it. A URL that does
  not parse, or a level that cannot be loaded, is fatal. Then the input, the
  console (`ini:Engine.Engine.Console`), the viewport and the audio.
- **`UEngine::InitAudio`** (`0x1037fe50`): on a client with `UseSound`, and
  without `-nosound`, creates `ini:Engine.Engine.AudioDevice` and starts it;
  one that fails to start is logged ("Audio initialization failed.") and
  dropped. With `-nosound` there is no audio subsystem at all: no sound, no
  music.
- **`OPEN` and `START`** (`UGameEngine::Exec`, `0x1038a030`): with a
  viewport, the URL becomes its next travel -- partial for `OPEN`, absolute for
  `START`; without one, the engine browses to it at once. A failure logs "Open
  failed: " or "Start failed: " and the reason. There is no cheat check: this
  is what a line forwarded to the running game runs
  ([the receiver](launch-flow.md#1-single-instance-forwarding-0x10908a300x10908cd1)).

## A level's tick

- **A level's start** (`UGameEngine::LoadMap`, `0x1038c1f0`), for a level
  not yet begun (`bBegunPlay` unset): the level's time set to 0, then the
  game's `InitGame`, every actor's `PreBeginPlay` and `BeginPlay`, each
  actor's zone, every actor's `LastRenderTime` set to −10 s -- whatever its
  map kept --, then `PostBeginPlay`, `SetInitialState` and the actors'
  bases. A level already begun -- from a save, or returned to -- keeps its
  own time and render times.
- **The time** (`ULevel::Tick`, `0x103a51a0`): the frame's time, times the
  level's `TimeDilation`, is added to the level's time, paused or not.
  The actors -- and the players' input and the event manager -- are given
  that time held between 0.005 and 0.4 s.
- **Unpaused** (`Pauser` empty): each dynamic actor's `DistanceFromPlayer`
  ([below](#stasis-and-render-time)), then each dynamic actor's `Tick`,
  once, in the list's order; one whose owner has not yet ticked this frame
  waits in a list, ticked after the pass once its owner has. Then the event
  manager ([each frame](#each-frame-aiprocess-0x10384080)). An actor
  ticked carries the level's mark in `bTicked`, which the level flips after
  each tick; the mark only tells whether an owner has ticked, and nothing is
  passed over for its own mark -- a level's first tick ticks every actor
  its map loaded.
- **Paused:** the players' input, and the actors with `bAlwaysTick`.
- **An actor's tick** (`AActor::Tick`, `0x103a1aa0`), ticking as a
  standalone game's ([by role](network.md#replication)): nothing
  else in stasis; its animation; then its script `Tick`, its state code,
  its timer, its `LifeSpan` and its physics, in that order. A player's
  pawn with a player (not a camera) has, in place of `Tick`, its player's
  input read, `PlayerInput` and `PlayerTick`, and the input read again
  with −1 (cleared) -- so its physics, later in the same tick, take the
  move `PlayerTick` makes.

## Small

- **`SetInstantSoundVolume`, `SetInstantSpeechVolume`,
  `SetInstantMusicVolume`** (`0x103e2850`, `0x103e28d0`, `0x103e2950`): hand
  the volume to the audio subsystem's own call for it (its virtuals at +0x90,
  +0x94, +0x98), which applies it at once instead of at the next tick
  ([`Galaxy.dll`](galaxy-dll.md#volume)).
- **`GetPlayerPawn()`**: the first viewport's actor.
- **`FGetHSV(hue, saturation, value)`** (`0x103ec8d0`): the colour of a
  light and of a zone's ambient light, as the renderer lights with it
  ([`Render.dll`](render-dll.md#lighting)).
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
- **`PlaySound(Sound, Slot, Volume, bNoOverride, Radius, Pitch)`**
  (`0x103e1f60`), by default `SLOT_Misc`, the actor's `TransientSoundVolume`
  and `TransientSoundRadius`, and pitch 1; a radius of 0 or less is 800. Each
  player pawn hears it (`CheckHearSound`). Deus Ex returns its ID: the
  actor's object index × 16 + the slot × 2, + 1 with `bNoOverride`.
  **`StopSound(Id)`** (`0x103e27d0`) hands the ID to the audio subsystem (its
  virtual at +0x78), which stops that sound. What the audio subsystem does
  with both: [`Galaxy.dll`](galaxy-dll.md#playing-a-sound).

## The database

`gamefiles/System/Engine.dll.i64` has the class layouts, the UTF-16 strings
and the initializers' names ([working on the binaries](README.md#working-on-the-binaries)),
and by hand the event manager's classes and enums from the SDK header, the
prototypes of the functions above, and names for their helpers and the event
classes' vtables. Each function above carries a one-line comment.
