# Render.dll

The native half of package Render: `URender`, UE1's scene renderer --
occlusion through the BSP, which actors are drawn and how, dynamic lighting,
meshes, sprites, decals and coronas. Read where a feature's drawing lives
there -- render iterators, the render time the engine and the scripts read,
coronas -- and, in a second pass for the handheld's frame, mesh detail and
lighting. How it was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 233,472 bytes |
| Imagebase | `0x10b00000` |
| SHA1 | `2299e6ae7f28ddcda10e65a49957af609b3f2891` |
| Exports | 97: 1 class, no natives |
| Functions | 434 |

It registers one class, `URender` (244 bytes), which is C++ only, as is all
it works on: the scene node, sprites, span buffers, BSP nodes and zones. The
SDK has their headers (`Engine/Inc/UnRender.h`, and Render's own
`RenderPrivate.h` and `UnSpan.h`), and
[`tools/ida/render_types.py`](../../tools/ida/render_types.py) declares them
in the database. As in `Engine.dll`, an export is a jump to the code.

The SDK's header marks one Deus Ex change: each sprite keeps its actor's
glow, draw scale, location and rotation, for render iterators (below).

## A frame

`DrawWorld` (`0x10b1cb90`) runs `OccludeFrame` (`0x10b19fc0`), then
`DrawFrame` (`0x10b1a2d0`); both recurse into the frame's children: mirrors,
warp zones and the sky.

- **`OccludeFrame`** calls `SetupDynamics` (`0x10b22d90`), which makes a
  sprite for each actor to draw and a dynamic light for each light in view,
  then `OccludeBsp` (`0x10b173d0`), which walks the BSP front to back and
  keeps each sprite some part of which is left visible.
- **`DrawFrame`** draws the world's surfaces with their decals, then the
  sprites that were kept, translucent ones last, then the coronas.

## Which actors are drawn

`SetupDynamics` goes through every actor of the level, each frame. It passes
over one that is:

- hidden (`bHidden`; `bHiddenEd` in the editor);
- in first person in the main frame, the actor the view is from: the
  viewer's pawn, or its view target when it has one;
- `bOnlyOwnerSee`, unless it is the viewer's (anywhere up its `Owner` chain)
  in first person; or `bOwnerNoSee` and the viewer's, in first person;
- `bHighDetail` while the render device's `HighDetailActors` is off. Of the
  game's classes only `Decal` sets it, and a decal is drawn with its surface,
  not here;
- a brush: a mover goes to the level's brush tracker, the rest is the world.

Each other actor gets one sprite. A light with a type, brightness and radius
that is neither `bStatic` nor `bNoDelete`, or is `bDynamicLight`, becomes a
dynamic light when its radius reaches into the view.

## Render iterators

An actor with a `RenderIteratorClass`, while the game runs, is drawn as the
items its iterator gives, and gets no sprite of its own:

- **The interface.** Without a `RenderInterface`, or with one that is no
  longer valid, `SetupDynamics` makes one: an object of that class with the
  actor as its outer. With the class cleared, it destroys the one there is.
- **Each frame**, for each scene frame: `Init` with the viewer, `First`, then
  until `IsDone`, a sprite for the actor `CurrentItem` gives, and `Next`.
- **Each item's state.** The iterators move one proxy actor from item to item
  ([particles and lasers](deusex-dll.md#particles-and-lasers)), so each
  sprite keeps what the proxy was as it was made (`FDynamicSprite::Setup`,
  `0x10b23910`): its glow, draw scale, location and rotation.
  `DrawActorSprite` (`0x10b25080`) draws a sprite item at its own screen
  place, glow and scale, and a mesh item with the proxy put back to that
  state for the draw and restored after.

## Render time

The renderer keeps it; the engine and the scripts read it
([stasis and render time](engine-dll.md#stasis-and-render-time)):

- **An actor's `LastRenderTime`** is the level's `TimeSeconds` each time it
  is drawn (`DrawActorSprite`): as a sprite the occlusion kept, or on its own
  through `DrawActor` (`0x10b262c0`), which `GC.DrawActor` calls
  ([actors in a window](extension-dll.md#actors-in-a-window)). For an
  iterator that is its proxy, which is what `ParticleGenerator` and
  `LaserEmitter` ask (`proxy.LastRendered()`).
- **A zone's** (`Zones[i].LastRenderTime` in the level's model) is stamped by
  `OccludeBsp`: the frame's first zone, and each zone seen through a portal.
  `InStasis` reads it.
- **A decal's own `LastRenderedTime`** is stamped when `DrawFrame` puts it on
  a surface it draws. `LastRendered()` does not read it: it reads
  `LastRenderTime`, which a decal never gets. So a decal, and Deus Ex's
  `Shadow`, never counts as drawn: when an NPC moves, its shadow is laid
  again only if the NPC was drawn in the last second, and otherwise taken
  off. The script always lays the player's.

## A pawn's attachments

After a pawn's mesh, `DrawActorSprite` draws:

- when the mesh has a weapon triangle (`DrawMesh` and `DrawLodMesh` note its
  place, `GWeaponCoords`): the pawn's `Weapon` in its third-person mesh and
  scale at the triangle, in the pawn's style and lit as the pawn; with a
  muzzle flash, the weapon's `MuzzleFlashMesh`, which no Deus Ex weapon has;
  the flag its `PlayerReplicationInfo` carries (`HasFlag`, a multiplayer
  game's); and it sends its `Shadow` an `Update`, which does nothing in Deus
  Ex;
- when it has none: its `SelectedItem` in its third-person mesh, where the
  item is.

## Coronas

`DrawFrame` keeps up to 32 coronas from frame to frame, each with a
brightness from 0 to 1:

- **Which lights:** those shining into the viewer's own leaf of the BSP -- the
  static lights that reach it (its `iPermeating` list) and the dynamic lights
  in it -- with `bCorona` and a `Skin` texture.
- **Seen** (`CoronaTest`, `0x10b1bc00`) when the line from the eye to the
  light meets no level geometry or mover, and no pawn or other actor but the
  viewer's own pawn.
- **Fading**, on real time: each frame every corona loses three times the
  seconds elapsed, and each one seen gains twice that. So a corona comes up,
  or goes, in about a third of a second, and is dropped at 0.
- **Drawn** at the light's place on screen, if in front of the eye: a square
  a fifth of the view's width times the light's `DrawScale`, whatever the
  distance, translucent, in the colour of its hue and saturation times the
  brightness.

## Mesh detail

Every mesh of the game's characters, decorations and items is a LOD mesh --
431 in `DeusExCharacters.u`, `DeusExDeco.u` and `DeusExItems.u` -- with tables
for dropping detail: its vertices in the order they collapse, the vertex each
collapses to (`CollapsePointThus`), the same for the texture corners
(`CollapseWedgeThus`), and the vertex count below which each face goes
(`FaceLevel`). `DrawLodMesh` (`0x10b0ea80`) works out a vertex budget each
time it draws one:

- **The budget** is the mesh's vertex count (`ModelVerts`) times a factor, at
  least `LODMinVerts` and at most the whole mesh. The factor is 430 × a
  resolution term (0.3 + 0.7 × the view's width in pixels / 640) × the
  actor's `DrawScale` × its `LODBias` × the mesh's `MeshScaleMax`, divided by
  the mesh's `LODStrength` × the renderer's shape LOD (0.25) × the tangent of
  half the field of view × the actor's depth in the view less the mesh's
  `LODZDisplace` (at least 1) × a complexity term (0.25 + 0.003 ×
  `ModelVerts`). So the budget falls as one over the depth, sooner for a
  complex mesh and a wide view (zoomed in, it keeps more). A mesh with
  `LODStrength` 0 or without the tables is drawn whole.
- **What it drops.** It asks `ULodMesh::GetFrame` (`Engine.dll`) for the
  budget's vertices only, and the special ones (the weapon triangle's); draws
  only the faces whose `FaceLevel` is within the budget; and moves each corner
  of those down its collapse list until its vertex is within the budget too.
  Only the vertices of faces turned to the eye get lit.
- **Morphing.** With `LODMorph` above 0, the vertices in that top fraction of
  the budget slide toward the vertex they collapse to, the nearer the top the
  further, their texture coordinates with them: detail fades rather than
  pops, beginning before the first vertex goes.
- **The settings** are `URender`'s. `Init` sets the shape LOD to 0.25, its
  adjustment to 1 (nothing changes it), the mode to 1 and the fixed factor to
  1. Console commands set them (`URender::Exec`): `MLOD` the shape LOD,
  `MLMODE` the mode (0: the fixed factor, `MLFIX`, whatever the distance; 1:
  normal; 2: no morphing; 3: the field of view ignored; 4: both), and `TLOD`
  a texture LOD distance.
- **The game's meshes.** Every one has `LODMinVerts` 10, `LODMorph` 0.3, and
  no `LODZDisplace` or `LODHysteresis`; no actor's `LODBias` differs from 1. A
  character has 310 to 380 vertices and `LODStrength` 0.5, its carcass 1; a
  decoration has 38 as a median (up to 482) and an item 30, at 1. So a
  trooper (`GM_Jumpsuit`, 370 vertices) at the default 75° is whole to about
  2,700 units deep at 853 pixels wide (3,700 at 1280), and has about 200
  vertices at 5,000 and 100 at 10,000.

## Lighting

`FLightManager` (its vtable at `0x10b2a93c`, in `FLightManagerBase`'s order;
one object, `GLightManager`) lights the world's surfaces through light maps,
and meshes vertex by vertex. Each light it takes gets a record for the draw
(`SetupLight`, `0x10b05fa0`): its place, radius, and brightness and colour
at this moment (`URender::GlobalLighting` gives a pulsing or flickering light
its brightness now), and its effect's entry in `GLightEffects`
(`0x10b2a0f0`): the function that shapes it, whether that shape changes over
time (searchlight, slow and fast wave, cloud cast, shock, disco,
interference, rotor), and whether its brightness wavers from texel to texel
(torch and fire waver, watery shimmer).

### Light maps

`SetupForSurf` (`0x10b06c90`) gives each surface drawn its light map.

- **Three kinds of light** (`AddLight`, `0x10b08b30`), from the surface's list
  of the level's lights, each with its shadow bits (a bit a texel, stored
  with the level), and the moving lights over it:
  - *static*: `bStatic`, `LT_Steady`, and an effect whose shape and
    brightness hold still;
  - *animated*: any other `bStatic` or `bNoDelete` light that is not
    `bDynamicLight`;
  - *moving*: `bDynamicLight`, or neither `bStatic` nor `bNoDelete`. It casts
    no shadow.

  With the client's `NoDynamicLights` on (an ini setting, off by default),
  animated lights count as static and moving ones are left out.
- **The static map**: the zone's ambient light, and each static light through
  its shadow bits (smoothed as they are unpacked, `0x10b02650`). It is kept
  in the global cache (`GCache`) under the model, the light map and the zone,
  and built again only when it is not there, when one of its lights has
  `bLightChanged`, or, for a mover's surface, when the mover has moved,
  turned or changed leaf since.
- **The dynamic map**, only when an animated or moving light reaches the
  surface: the static map copied and those lights added, every frame --
  cached with the frame's time, so a surface drawn twice in a frame is lit
  once. An animated light whose shape holds still is kept in the cache as its
  shadowed light on that surface, and only scaled by its brightness now; one
  whose shape changes keeps its unpacked shadows there and has its shape run
  again; a moving light is run without shadows. As a light is added
  (`MergeLight`, `0x10b03040`), a torch waver dims each texel by a random
  amount of up to 5%, and a fire waver up to 20%.
- **To the device.** A map holds a byte a channel, up to 127. The render
  device gets the static map, which it holds already, or the dynamic map,
  marked changed (`bRealtimeChanged`) for it to upload whole.

### Meshes

`SetupForActor` (`0x10b08c70`) picks an actor's lights once a draw, and
`Light` (`0x10b027f0`) lights each vertex with them.

- **The candidates**: the static lights that reach into the actor's leaf of
  the BSP, the moving lights in it, and the lights it had last frame (kept in
  the cache under the actor, up to 16). Each counts once a frame, and only
  if its `bSpecialLit` is the actor's. Its strength at the actor's centre is
  (1 − distance / radius) × its brightness (a cylinder light counts with
  three quarters of its brightness and radius).
- **The pick**, strongest first: static lights until 8 are taken, the others
  while fewer than 8 lights in all are, and none below an eighth of the
  strongest taken.
- **Shadowed or not**: a line from the light to the actor through the
  level's BSP, checked again for each light every 16 frames (by the frame
  count and the light's object index), except for a `bMovable` light that is
  not static, which is always taken. A light fades in when found and out when
  shadowed or dropped, over about a third of a second, and lights as it
  fades.
- **Per vertex**, for each light: a diffuse term, (cos + 1)² − 1.5 of the
  angle to the light (nothing beyond about 77°, 2.5 facing it), and a
  highlight, 6 × cos² of the angle between the eye and the light's reflection
  at the vertex when the reflection heads toward the eye, both times
  (1 − distance / radius) and the light's colour. The sum is scaled by 1.4 ×
  `ScaleGlow`, and the zone's ambient light and the actor's `AmbientGlow`
  (255 pulses) added, each channel at most 1. An unlit draw (`PF_Unlit`) is
  mid-grey.

## The database

`gamefiles/System/Render.dll.i64` has the script types, the UTF-16 strings,
the initializers' names and the renderer's C++ types from
[`tools/ida/render_types.py`](../../tools/ida/render_types.py), which also
types `URender`'s methods; declares the texture, light map and cache
structures; and names the sprite's constructor and `Setup`, the light
manager's methods and helpers, and the globals of the weapon triangle and of
the lighting (the light map and fog map being built, the effects, the light
records and their counts by kind). By hand it has `CoronaTest`. Each function
above carries a one-line comment.
