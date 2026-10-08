# Render.dll

The native half of package Render: `URender`, UE1's scene renderer. It
occludes through the BSP, picks which actors are drawn and how, and draws
dynamic lighting, meshes, sprites, decals and coronas. How it was read:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 233,472 bytes |
| Imagebase | `0x10b00000` |
| SHA1 | `2299e6ae7f28ddcda10e65a49957af609b3f2891` |
| Exports | 97: 1 class, no natives |
| Functions | 434 |

- One class, `URender` (244 bytes), C++ only. So is all it works on: the
  scene node, sprites, span buffers, BSP nodes and zones.
- Their headers: the SDK's `Engine/Inc/UnRender.h`, and Render's own
  `RenderPrivate.h` and `UnSpan.h`.
  [`tools/ida/render_types.py`](tools/ida/render_types.py) declares them in
  the database.
- An export is a jump to the code, as in `Engine.dll`.
- One Deus Ex change, marked in the SDK's header: each sprite keeps its
  actor's glow, draw scale, location and rotation, for
  [render iterators](#render-iterators).

## A frame

`DrawWorld` (`0x10b1cb90`) runs `OccludeFrame` (`0x10b19fc0`), then
`DrawFrame` (`0x10b1a2d0`). Both recurse into the frame's children: mirrors,
warp zones and the sky.

- **`OccludeFrame`** calls `SetupDynamics` (`0x10b22d90`), then `OccludeBsp`
  (`0x10b173d0`).
  - `SetupDynamics` makes a sprite for each actor to draw, and a dynamic
    light for each light in view.
  - `OccludeBsp` walks the BSP front to back and keeps each sprite with some
    part left visible ([which actors are drawn](#which-actors-are-drawn)).
    It passes over a surface seen from behind, but for a zone portal or a
    two-sided one. A portal passes what shows through it to the span buffer
    of the zone beyond.
- **`DrawFrame`** draws the world's surfaces with their decals, then the
  sprites kept (translucent ones last), then the coronas.
- **The sky's frame** looks out from the zone's `SkyZone`, turned as the
  viewer is and by the inverse of the sky zone's rotation (observed, not
  read). Liberty Island's sky zone is turned 5,080 (28°).

## Which actors are drawn

`SetupDynamics` goes through every actor of the level, each frame. It passes
over one that is:

- hidden (`bHidden`; `bHiddenEd` in the editor);
- the actor the view is from, in first person in the main frame: the
  viewer's pawn, or its view target when it has one;
- `bOnlyOwnerSee`, unless it is the viewer's (anywhere up its `Owner` chain)
  in first person; or `bOwnerNoSee` and the viewer's, in first person;
- `bHighDetail` while the render device's `HighDetailActors` is off. Of the
  game's classes only `Decal` sets it, and a decal is drawn with its
  surface, not here;
- a brush: a mover goes to the level's brush tracker, the rest is the world.

Each other actor gets one sprite. A light, hidden or not, with a type,
brightness and radius, that is `bDynamicLight` or neither `bStatic` nor
`bNoDelete`, becomes one of the frame's dynamic lights when its sphere is not
wholly outside one of the view's four sides: 25 × (`LightRadius` + 1), or
25 × (`VolumeRadius` + 1) when that is larger. As the occlusion walk visits
each node, a dynamic light goes on to each side of the node's plane its
sphere, 25 × (`LightRadius` + 1), reaches (`FDynamicLight_Filter`,
`0x10b24a10`): into that side's leaf when it is one (`URender::LeafLights`),
and onto the node's lit surfaces (`SurfLights`). `OccludeFrame` (`0x10b19fc0`)
then gives each surface its lights and each sprite its leaf's
(`FDynamicSprite.LeafLights`), and empties every list.

**A sprite kept** (`FDynamicSprite`, `0x10b233c0`; its `Setup`,
`0x10b23910`):

- **Its rectangle** on screen, in whole pixels, at least a row tall, at the
  depth of the actor's location: a sprite's texture at its size and place,
  or a mesh's render box through `BoundVisible`. That rectangle, set back in
  the world at that depth, is its proxy.
- **The walk.** It starts at the BSP's root as a raster of the rectangle's
  rows. At each node it comes to (`0x10b23e30`), the part on each side of
  the node's plane goes on to that child, the raster cut along the line
  where the plane crosses the proxy.
- **An empty leaf** (UE1's `ChildOutside`): a part that comes to one waits in
  the node's list for that side, in order of depth. It is tested there
  (`0x10b24740`) against that leaf's zone's span buffer: what of the zone
  shows through the portals seen so far, less what the walk has drawn in
  front of it. The test comes before the node's surfaces on the viewer's
  side, after them on the far side.
- **Dropped:** a part in a solid leaf, and all that came down into a subtree
  whose bounds are hidden.
- **Drawn:** a sprite with a part showing keeps those spans and is drawn,
  which stamps its [render time](#render-time).
- **A mesh's render box** (`UMesh::GetRenderBoundingBox`, `Engine.dll`
  `0x103a6850`): the boxes of its animation's frame and the next, the frame
  `⌊(AnimFrame + 1) × n⌋ mod n` of the sequence's n frames; or the whole
  mesh's box while `AnimFrame` is below 0 or the sequence is not the mesh's.
  Then: less the mesh's origin; times its scale and the draw scale (1.5 for
  a `bParticles` actor); grown by a unit; turned by the mesh's `RotOrigin`
  and the actor's rotation; set at its location plus `PrePivot`.
- **`BoundVisible`** (`0x10b162e0`) makes the box a rectangle:
  - with the viewer inside the box, the whole frame;
  - otherwise the corners' projections, running to the frame's edge on each
    side some corner is beyond;
  - none when every corner is behind the viewer or beyond one side.

  Each edge is the pixel it falls in; the right and bottom ones are left
  out. A mesh whose location is behind the viewer gets no sprite at all.
- **A sprite's rectangle:** its texture's size times the draw scale, round
  where its location lands, rounded up; none nearer than a unit.

## Render iterators

An actor with a `RenderIteratorClass`, while the game runs, is drawn as the
items its iterator gives. It gets no sprite of its own.

- **The interface.** Without a valid `RenderInterface`, `SetupDynamics`
  makes one: an object of that class, the actor its outer. With the class
  cleared, it destroys the one there is.
- **Each frame**, for each scene frame: `Init` with the viewer, `First`,
  then, while not `IsDone`, a sprite for the actor `CurrentItem` gives, and
  `Next`.
- **Each item's state.** The iterators move one proxy actor from item to item
  ([particles and lasers](deusex-dll.md#particles-and-lasers)). So each
  sprite keeps the proxy's glow, draw scale, location and rotation as they
  are when it is made (`FDynamicSprite::Setup`, `0x10b23910`).
  `DrawActorSprite` (`0x10b25080`) draws a sprite item at its own screen
  place, glow and scale; a mesh item with the proxy put back to that state
  for the draw, and restored after.

## Render time

The renderer keeps it; the engine and the scripts read it
([stasis and render time](engine-dll.md#stasis-and-render-time)).

- **An actor's `LastRenderTime`** is the level's `TimeSeconds` each time it
  is drawn (`DrawActorSprite`, first thing): as a sprite the occlusion kept,
  or on its own through `DrawActor` (`0x10b262c0`). For an iterator the
  actor stamped is its proxy, which is what `ParticleGenerator` and
  `LaserEmitter` ask (`proxy.LastRendered()`).
- **`DrawActor`** draws, and so stamps, whenever the sprite's `Setup` gives
  the actor a rectangle on the frame
  ([which actors are drawn](#which-actors-are-drawn)): a mesh whose location
  is not behind the viewer and whose render box `BoundVisible` puts on the
  frame; a sprite whose texture's rectangle lands on it. No span buffer is
  asked, so walls in front do not matter.
  - `GC.DrawActor` calls it on the scene's frame, narrowed to the window with
    `bConstrain` ([actors in a window](extension-dll.md#actors-in-a-window)):
    an NPC the vision augmentation draws through a wall counts as drawn.
  - `Canvas.DrawActor` (`UCanvas::execDrawActor`, `Engine.dll` `0x10377ed0`;
    the first-person weapons) calls it too, clearing `bHidden` for the call
    and setting it after, whatever it was.
- **A zone's** (`Zones[i].LastRenderTime` in the level's model) is stamped by
  `OccludeBsp`: the frame's first zone, and each zone seen through a portal.
  `InStasis` reads it.
- **A decal's own `LastRenderedTime`** is stamped when `DrawFrame` puts the
  decal on a surface it draws. `LastRendered()` does not read it: it reads
  `LastRenderTime`, which a decal never gets. So a decal, and Deus Ex's
  `Shadow`, never counts as drawn. When an NPC moves, its shadow is laid
  again only if the NPC was drawn in the last second, else taken off. The
  script always lays the player's.

## A pawn's attachments

After a pawn's mesh, `DrawActorSprite` draws what it holds, only where the
mesh has a weapon triangle. `DrawMesh` and `DrawLodMesh` note its place
(`GWeaponCoords`) and that they found one (`GMeshHadWeaponTriangle`). A mesh
without one draws nothing more.

- **With a `Weapon`:**
  - the weapon at the triangle in its third-person mesh and scale, its own
    rotation zeroed for the draw, its style the pawn's, lit as the pawn. A
    weapon with no third-person mesh draws nothing, and nothing else is
    drawn in its place;
  - with a muzzle flash, the weapon's `MuzzleFlashMesh` (no Deus Ex weapon
    has one);
  - the flag its `PlayerReplicationInfo` carries (`HasFlag`, a multiplayer
    game's);
  - and the pawn's `Shadow` is sent an `Update`, which does nothing in Deus
    Ex.
- **With none:** its `SelectedItem`, the same way (third-person mesh and
  scale at the triangle, rotation zeroed, the pawn's style, lit as the
  pawn): the player's multitool or lockpick in his hand, in third person.

Each is drawn by swapping its third-person mesh and scale into its `Mesh`
and `DrawScale`, and the pawn's style into its `Style`, for the draw, then
back.

## Coronas

`DrawFrame` keeps up to 32 coronas from frame to frame, each with a
brightness from 0 to 1.

- **Which lights:** those with `bCorona` and a `Skin` texture, shining into
  the BSP leaf the viewport's actor stands in (its `Region.iLeaf`, not the
  eye's): the static lights that reach it (its `iPermeating` list). The pass
  reads the leaf's dynamic lights too (`URender::LeafLights`), but
  `DrawWorld` runs `OccludeFrame` before `DrawFrame`, and `OccludeFrame` has
  emptied every leaf's list by then
  ([which actors are drawn](#which-actors-are-drawn)): no dynamic light gets
  a corona. A spawned movable light with a corona shows none, in the
  viewer's leaf or out of it.
- **Seen** (`CoronaTest`, `0x10b1bc00`) when the line from the eye to the
  light meets no level geometry or mover, and no pawn or other actor but the
  viewer's own pawn.
- **Fading**, in real time: each frame every corona loses `3 × dt` (dt the
  seconds elapsed), and each one seen gains `6 × dt`. So a corona comes up,
  or goes, in about a third of a second. At 0 it is dropped.
- **Drawn**, if in front of the eye, at the light's place on screen:
  - a square a fifth of the view's width times the light's `DrawScale`,
    whatever the distance: `UCanvas::DrawIcon` of the whole `Skin`,
    translucent;
  - in its hue's colour whitened by its saturation, times the brightness.
    The hue's colour comes from its sector of 85 (red to green, green to
    blue, blue to red, the last over 84); then `LightSaturation` / 255 of
    what it lacks of white is added.

  The colour is worked out in `DrawFrame` itself (`0x10b1a2d0`), not by
  `FGetHSV`, whose light colour is dimmer.

## Mesh detail

Every mesh of the game's characters, decorations and items is a LOD mesh
(431 in `DeusExCharacters.u`, `DeusExDeco.u` and `DeusExItems.u`), with
tables for dropping detail:

- its vertices in the order they collapse;
- the vertex each collapses to (`CollapsePointThus`), and the same for the
  texture corners (`CollapseWedgeThus`);
- the vertex count below which each face goes (`FaceLevel`).

`DrawLodMesh` (`0x10b0ea80`) works out a vertex budget each time it draws
one, at least `LODMinVerts` and at most the whole mesh:

```
budget = ModelVerts × factor
factor = 430 × (0.3 + 0.7 × width / 640) × DrawScale × LODBias × MeshScaleMax
       / (LODStrength × shapeLOD × tan(fov / 2) × max(1, depth − LODZDisplace)
          × (0.25 + 0.003 × ModelVerts))
```

- **The terms.** `ModelVerts` is the mesh's vertex count; width the view's,
  in pixels; `DrawScale`, `LODBias` and depth (in the view) the actor's;
  `MeshScaleMax`, `LODStrength` and `LODZDisplace` the mesh's; shapeLOD the
  renderer's shape LOD (0.25); fov the field of view. So the budget falls as
  one over the depth, sooner for a complex mesh and a wide view (zoomed in,
  it keeps more). A mesh with `LODStrength` 0 or without the tables is drawn
  whole.
- **What it drops.** It asks `ULodMesh::GetFrame` (`Engine.dll`) for the
  budget's vertices only, and the special ones (the weapon triangle's). It
  draws only the faces whose `FaceLevel` is within the budget, and moves
  each corner of those down its collapse list to a vertex within the budget
  too. Only the vertices of faces turned to the eye get lit.
- **Morphing.** With `LODMorph` above 0, the vertices in that top fraction of
  the budget slide toward the vertex they collapse to, the nearer the top
  the further, their texture coordinates with them. Detail fades rather than
  pops, beginning before the first vertex goes.

**The settings** are `URender`'s. `Init` sets the shape LOD to 0.25, its
adjustment to 1 (nothing changes it), the mode to 1 and the fixed factor
to 1. Console commands set them (`URender::Exec`):

| Command | Sets |
|---|---|
| `MLOD` | the shape LOD |
| `MLMODE` | the mode: 0 the fixed factor (`MLFIX`) whatever the distance; 1 normal; 2 no morphing; 3 the field of view ignored; 4 both |
| `TLOD` | a texture LOD distance |

**The game's meshes.** Every one has `LODMinVerts` 10, `LODMorph` 0.3, and no
`LODZDisplace` or `LODHysteresis`. No actor's `LODBias` differs from 1.

| Mesh | Vertices | `LODStrength` |
|---|---|---|
| a character | 310 to 380 | 0.5 |
| its carcass | | 1 |
| a decoration | 38 as a median, up to 482 | 1 |
| an item | 30 | 1 |

So a trooper (`GM_Jumpsuit`, 370 vertices) at the default 75° is whole to
about 2,700 units deep at 853 pixels wide (3,700 at 1280). It has about 200
vertices at 5,000 and 100 at 10,000.

## Mesh textures

Which texture each face of a mesh draws:

- **A slot's texture**, for each of the mesh's texture slots: the actor's
  `MultiSkins` entry; else the mesh's own texture; else the actor's `Skin`.
  Slot 0 takes the `Skin` before the mesh's texture. `UMesh::GetTexture`
  (`Engine.dll`) picks between the mesh's texture and the `Skin`.
- **Animated.** Each slot's texture is brought up to date and shown at its
  animation's current frame, so an animated texture plays (a fractal one
  steps as in [stepping](fire-dll.md#stepping)).
- **The environment map:** the actor's `Texture`; else its zone's
  `EnvironmentMap`; else the level's; else the texture of the last slot
  that has one. A face whose slot has no texture draws it, and so does an
  environment-mapped face (the actor's `bMeshEnviroMap`, or the face's own
  flags).
- **Masked.** A masked texture is drawn masked (`PF_Masked`,
  [blending](d3ddrv-dll.md#blending)) whatever the face's own flags.
- **The viewer's `Sprite`**, when set, stands in for every slot's texture and
  for the environment map: every mesh is drawn in it. It is Deus Ex's Matrix
  easter egg: `DeusExPlayer.Matrix` sets the player's `Sprite` to
  `Extras.Matrix_A00`, or back to `None`.

## Lighting

`FLightManager` (its vtable at `0x10b2a93c`, in `FLightManagerBase`'s order;
one object, `GLightManager`) lights the world's surfaces through light maps,
and meshes vertex by vertex.

Each light it takes gets a record for the draw (`SetupLight`,
`0x10b05fa0`):

- its place and radius;
- its brightness and colour at this moment (`URender::GlobalLighting` gives a
  pulsing or flickering light its current brightness);
- its effect's entry in `GLightEffects` (`0x10b2a0f0`): the function that
  shapes it; whether that shape changes over time (searchlight, slow and
  fast wave, cloud cast, shock, disco, interference, rotor); whether its
  brightness wavers from texel to texel (torch and fire waver, watery
  shimmer).

The plain shape, `LE_None`'s, is also that of the torch and fire wavers, the
watery shimmer, warp, the omni bump map and the unused slot. The cloud cast
has it too: its function (`0x10b04380`) only calls `SpatialPlain`, though the
table counts its shape as changing.

- **The colour** is Engine.dll's `FGetHSV` (`0x103ec8d0`) at full value:
  - the value makes a brightness `min(1, 0.7 b / (√b + 0.01))`,
    `b = 1.4 × value ÷ 255` (0.82 at 255);
  - the hue is two neighbouring primaries mixed, 85 steps apart round the
    wheel;
  - the saturation mixes it toward white, 255 all white.

  A palette light (`LT_TexturePaletteOnce`, `Loop`) takes its skin's palette
  colour's direction instead.
- **The brightness** is `LightBrightness` ÷ 255, shaped by the type in
  `GlobalLighting` (`0x10b05e90`) and kept to 0-1, then times the level's
  `Brightness` (a `LevelInfo` property, 1 on Liberty Island). Galaxy calls
  it too, for a light's ambient sound
  ([each frame](galaxy-dll.md#each-frame)).

| Type | Its shaping |
|---|---|
| pulse | `0.6 + 0.39 sin` |
| subtle pulse | `0.9 + 0.09 sin` |
| blink | out when its turn count, in 65536ths, is odd: by the frame, at any frame rate |
| flicker | a random number each frame: out below one half, else that fraction |
| strobe | out every other frame |
| palette | through its palette once over its life (`1 − LifeSpan ÷` the default's, times 255), or at 35 turns a second over the period; times `(2 red + 3 green + blue) ÷ 1536 × 2.8` of the entry |

Both pulses' sines run at 35 turns a second over `LightPeriod` (at
least 1), from `LightPhase`'s 256ths of a turn.

### Light maps

`SetupForSurf` (`0x10b06c90`) gives each surface drawn its light map.

- **Three kinds of light** (`AddLight`, `0x10b08b30`), from the surface's list
  of the level's lights, each with its shadow bits (a bit a texel, stored
  with the level), and the moving lights over it:

  | Kind | Lights |
  |---|---|
  | *static* | `bStatic`, `LT_Steady`, and an effect whose shape and brightness hold still |
  | *animated* | any other `bStatic` or `bNoDelete` light that is not `bDynamicLight` |
  | *moving* | `bDynamicLight`, or neither `bStatic` nor `bNoDelete`; it casts no shadow |

  With the client's `NoDynamicLights` on (an ini setting, off by default),
  animated lights count as static and moving ones are left out.
- **The static map:** the zone's ambient light, and each static light
  through its shadow bits (smoothed as they are unpacked, `0x10b02650`). It
  is kept in the global cache (`GCache`) under the model, the light map and
  the zone. It is built again only when it is not there, when one of its
  lights has `bLightChanged`, or, for a mover's surface, after the mover
  moves, turns or changes leaf.
- **The dynamic map**, only when an animated or moving light reaches the
  surface: the static map copied and those lights added, every frame. It is
  cached with the frame's time, so a surface drawn twice in a frame is lit
  once.
  - An animated light whose shape holds still is kept in the cache as its
    shadowed light on that surface, and only scaled by its current
    brightness.
  - One whose shape changes keeps its unpacked shadows there and has its
    shape run again.
  - A moving light is run without shadows.
  - As a light is added (`MergeLight`, `0x10b03040`), a waver dims each
    texel by a random amount of up to a: 5% for a torch waver, 20% for a
    fire waver, 40% for a watery shimmer. Its illumination i becomes
    `i × (1 − a + a × r) − 0.5`, cut down. The draws r are taken in turn
    from 0 over the texels of the light's rectangle on the map, row by row,
    round a table of 256.
- **The random tables** (`TickRandoms`, `0x10b13080`, each frame from the
  level's time):
  - 256 fresh draws: the torch's and fire's;
  - the watery shimmer's own, each entry easing toward a draw. At each of 35
    ticks a second, the 16 entries the tick moves past take the fresh
    table's draws as their targets, a sixteenth of the way a tick; the
    others move on that step for each tick passed. 16 ticks or more without
    a frame start it over with fresh draws. So an entry glides to a new
    value every 16 ticks (under half a second), each held to 0-1.
- **A texel's byte**, 0 to 127 a channel:
  - **The start:** the zone's ambient light, `FGetHSV`'s colour times 64,
    rounded down.
  - **Shadow bytes** (`ShadowFromBits`): each texel takes the bits around it
    through the kernel 24 40 24 / 40 64 40 / 24 40 24, a row at a time:
    255 × the row's weights ÷ 320, rounded down (254 where all are lit). A
    row takes its first bit again to the left of the map, and its last
    byte's last bit to the right; the first and last rows stand for the rows
    beyond them. A light without shadow bits (a moving one) is 127 all
    over.
  - **The plain shape** (`SpatialPlain`, `0x10b03360`): a table of
    `(2v³ − 3v² + 1) ÷ v` over `d² ÷ r²` in 4096ths, `v = d ÷ r`, times the
    light's height over the surface's plane ÷ r. So it is
    `(1 − 3v² + 2v³)` times the cosine of the light's angle to the surface.
    Times the shadow byte, rounded.
  - **The spotlight's** (`SpatialSpotlight`, `0x10b04f80`): the same times
    `((cos − c) ÷ (1 − c))²` inside its cone, `c = 1 − LightCone ÷ 256`,
    rounded down.
  - **The light's table** (`SetupLight`): the illumination i, 0 to 254,
    becomes i × its colour and brightness in 65536ths, rounded down, at
    most 127.
  - The lights add up, each channel held to 127.
- **To the device.** A map holds a byte a channel, up to 127. The render
  device gets the static map, which it holds already, or the dynamic map,
  marked changed (`bRealtimeChanged`) for it to upload whole. `D3DDrv` shows
  a byte as 1/128 of the texture's brightness in its one-pass path, the
  game's, and 1/64 in the two-pass one
  ([the light maps' brightness](d3ddrv-dll.md#the-light-maps-brightness)).

### Meshes

`SetupForActor` (`0x10b08c70`) picks an actor's lights once a draw, and
`Light` (`0x10b027f0`) lights each vertex with them.

- **The candidates:** the static lights that reach into the actor's leaf of
  the BSP, the moving lights in it, and the lights it had last frame (kept
  in the cache under the actor, up to 16). Each counts once a frame, and
  only if its `bSpecialLit` is the actor's. Its strength at the actor's
  centre is `(1 − distance / radius) × LightBrightness`, the byte. A
  cylinder light counts with three quarters of its brightness and radius.
- **The pick**, strongest first: static lights, up to 8; then the others
  while fewer than 8 lights in all are taken; none below an eighth of the
  strongest taken.
- **Shadowed or not:** a line from the light to the actor through the
  level's BSP, checked again for each light every 16 frames (by the frame
  count and the light's object index). A `bMovable` light that is not static
  is always taken. A light fades in when found, and out when shadowed or
  dropped, over about a third of a second; it lights as it fades.
- **Per vertex**, for each light:
  - a diffuse term, `(cos + 1)² − 1.5` of the angle to the light (nothing
    beyond about 77°, 2.5 facing it);
  - a highlight, `6 × cos²` of the angle between the eye and the light's
    reflection at the vertex, when the reflection heads toward the eye;
  - both times `(1 − distance / radius)` and the light's colour, the light
    maps' (colour and brightness above).

  The sum is scaled by `1.4 × ScaleGlow`. Added to it: the zone's ambient
  light in `FGetHSV`'s colour, and the actor's `AmbientGlow` ÷ 255 (255
  pulses, `0.25 + 0.2 sin(8 t)` of the viewport's time). Each channel is at
  most 1. An unlit draw (`PF_Unlit`, the actor's or a material's) is
  `AmbientGlow` / 256 + `ScaleGlow` / 2, held to 0-1: mid-grey for most
  (`0x10b0f6e0`).
- **Which faces are drawn.**
  - `DrawLodMesh` keeps a face whose corners are not all beyond one side of
    the view, and that faces the eye: `((A − B) × (C − A)) · A`, in view
    space, times the frame's `Mirror`, under 0. A face the actor's flags or
    its material's make two-sided (`PF_TwoSided`) need not face the eye
    (`0x10b0ff9e`, and `0x10b10320` in its second face loop).
  - `DrawMesh`, for a plain mesh, culls a face turned away only when its own
    flags are `PF_Flat` without `PF_TwoSided` or `PF_Invisible`
    (`0x10b0dc8a`).
  - The actor's flags are its style's (masked, translucent, modulated) and
    `bMeshEnviroMap`'s (`0x10b26230`): none makes a face two-sided.
  - `D3DDrv` draws with culling off, so only this keeps a translucent mesh's
    back faces unseen.
