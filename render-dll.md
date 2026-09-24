# Render.dll

The native half of package Render: `URender`, UE1's scene renderer --
occlusion through the BSP, which actors are drawn and how, dynamic lighting,
meshes, sprites, decals and coronas. Read where a feature's drawing lives
there: render iterators, the render time the engine and the scripts read, and
coronas. How it was read: [working on the binaries](README.md#working-on-the-binaries).

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

## The database

`gamefiles/System/Render.dll.i64` has the script types, the UTF-16 strings,
the initializers' names and the renderer's C++ types from
[`tools/ida/render_types.py`](../../tools/ida/render_types.py), which also
types `URender`'s methods and names the sprite's constructor and `Setup` and
the weapon triangle's globals. By hand it has `CoronaTest`. Each function
above carries a one-line comment.
