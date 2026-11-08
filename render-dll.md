# Render.dll

The native half of package Render: `URender`, UE1's scene renderer. It
occludes through the BSP, picks which actors are drawn and how, and draws
dynamic lighting, meshes, sprites, decals and coronas. Read with:
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
warp zones and the sky. [The overlays](#the-overlays) come last.

- **Its coordinates.** A surface's points are projected about the frame's
  `FX15` and `FY15`, `(FX + 1.0001) ÷ 2` (`FSceneNode::ComputeRenderSize`,
  `Engine.dll` `0x10372980`), as a mesh's are (`DrawMesh`, `0x10b0d1a0`;
  `DrawLodMesh`, `0x10b0ea80`) and a decal's (`ClipDecal`, `0x10b1bda0`); a
  child frame (`CreateChildFrame`, `0x10b15a40`) has its parent's size, and
  so its `FX15`. `Project` (`0x10b20750`), which places a sprite
  ([sprites](#sprites)), the coronas' places ([coronas](#coronas)) and
  `BoundVisible`'s box go about `FX2` and `FY2`, `FX ÷ 2`: half a pixel up
  and left of a polygon's.
- **`OccludeFrame`** calls `SetupDynamics` (`0x10b22d90`), then `OccludeBsp`
  (`0x10b173d0`).
  - `SetupDynamics` makes a sprite for each actor to draw, and a dynamic
    light for each light in view.
  - `OccludeBsp` walks the BSP front to back and keeps each sprite with some
    part left visible ([which actors are drawn](#which-actors-are-drawn)).
    It passes over a surface seen from more than a unit behind
    (`0x10b17fb9`) unless the surface's flags with the viewport's
    `ExtraPolyFlags` hold `PF_TwoSided` or `PF_Portal` (`0x10b17fc9`),
    before anything else; the texture's flags are ORed in only after
    (`0x10b181b2`), so a texture's `PF_TwoSided` shows no surface from
    behind. One within a unit behind is passed on, and no frame shows it
    (observed: a chain-link sheet and a door's face from 0.9 units behind).
    A portal passes what shows through it to the span buffer of the zone
    beyond.
  - **A node's box** (its `iRenderBound`) is tested only while the node is
    flagged hidden (`NF_BoxOccluded`, 0x10 of its flags at +55), and
    otherwise one frame in 16: when its index and a counter `DrawWorld`
    counts each frame agree in their low four bits. A node not tested is
    taken as showing. The test (`BoundVisible`, then the box against each
    zone's span buffer that the node's zone mask names) sets the flag when
    the box is off the frame or hidden, and clears it when some part shows;
    a flagged node's subtree is passed over.
  - **A surface** (`ClipBspSurf`, `0x10b14cb0`; with 3DNow!, `AMD3DClipBspSurf`,
    `0x10b1f7e0`) takes its points from a cache of the frame's transformed
    points (`URender::PointCache`, each stamped with the frame's
    `URender::Stamp`): each point is transformed and given its outcode against
    the view's four sides once a frame, however many surfaces share it, and
    projected when it lies within them, at any depth (`0x10b14eee`): the
    sides meet at the eye, and no plane before it cuts a surface. A
    surface whose points are all outside one side goes without a clip; one
    that crosses a side is clipped against that side only, and in a frame
    whose `NearClip` has a W, a mirror's, against that plane too
    (`0x10b1545e`; the master frame's is 0, `CreateMasterFrame`
    `0x10b15776`). Its edges are rasterized
    into a span a row (`0x10b19cc0`), which `FSpanBuffer::CopyFromRaster` (or
    `CopyFromRasterUpdate`, for a surface that also occludes) lays into the
    zone's span buffer; one with nothing left showing is flagged
    `NF_PolyOccluded` (0x08).
  - **The pixels.** A surface's rows run from the one its top falls in to
    the one before the one its bottom falls in; a row's span, from where its
    left edge crosses the row's lower boundary to where its right edge does,
    each floored (16.16 fixed point): a pixel is in when its lower right
    corner is, in coordinates about `FX15` -- so when its centre is, about
    the frame's middle. A span buffer's spans are half open,
    `[Start, End)`, and so is the box `BoxIsVisible` (`0x10b21a20`) tests.
    A sprite's rectangle and `BoundVisible`'s box take theirs by other
    corners ([which actors are drawn](#which-actors-are-drawn)).
  - **What occludes**: a surface neither masked, translucent, modulated nor
    invisible, and besides an invisible zone portal (`PF_Portal` and
    `PF_Invisible`) and a mirror (`PF_Mirrored`).
- **`DrawFrame`** draws the frame's three lists of surfaces, each surface
  with its decals, in turn, then the coronas. `OccludeBsp` puts each surface
  it keeps at the head of one: a mirror's or a portal's in the first; one
  that is none of invisible, masked, translucent or modulated in the second;
  the rest in the third. The first is drawn in reverse, the second sorted by
  its key, the third as it stands: back to front. The key (`0x10b1976b`) is
  an int: the zone actor's object index × 2^26, plus the surface's own
  texture's (not its animation's frame), plus that texture's palette's ×
  2^12. The sort (`0x10b1a45f`) is `Render.dll`'s own copy of the C library's
  quicksort (`0x10b20570`: the middle element the pivot, a run of 8 or fewer
  by selection), ascending, which keeps no order among equal keys. So which
  of two opaque surfaces that overlap at one depth shows, at the device's
  less-equal depth test ([`D3DDrv`](d3ddrv-dll.md#the-binary)), follows the
  indices the game's loads and frees gave its objects. `FDynamicSprite`'s
  leaf test puts each sprite at the head of the frame's list as its first
  part shows, so the sprites too go back to front. On a render device that is
  not span-based (`SpanBased` off, every hardware one) the sprites whose
  actor is not `STY_Translucent` follow the second list, and the translucent
  ones the third: glass blends over a mesh behind it. A span-based one (the
  software renderer) draws them all after the third. A surface's decals are
  drawn only while the client's `Decals` is on and the render device is not
  span-based. A surface goes to the device with a detail texture only when
  its texture's current frame (`AnimCurrent`) has one, it is no portal, and
  the client's `TextureDetail` is High, the client read through the static
  `UBitmap::__Client`, which a `UClient`'s constructor sets and its `Destroy`
  clears (`Engine.dll`). The texture goes with the surface's pan: `PanU` and
  `PanV`, the zone's auto-pan for `PF_AutoUPan` and `PF_AutoVPan` (its pan
  speed × the level's `TimeSeconds` × 35 texels, wrapping at 1,024: × 256
  made an int, truncated (`_ftol`, `0x10b278a4`), its low 18 bits, ÷ 256,
  `0x10b1a628`-`0x10b1a652`, V `0x10b1a6f6`; the level's time running on
  while paused, so a sky's auto-panned clouds drift then too), and for
  `PF_SmallWavy` a wave on the level's `TimeSeconds` t, 8 sin t + 4 cos 2.3t
  texels on U and 8 cos t + 4 sin 2.3t on V (`0x10b1a72a`-`0x10b1a82f`),
  each by the surface's own flags, not its texture's. The surface's texture
  is stepped (`Update`) and its current frame locked; the detail and macro
  textures are that frame's own, each locked as it is, not a frame of its
  own animation (`0x10b1a8df`-`0x10b1a965`), and the lock steps each texture
  it locks ([a texture's mips](engine-dll.md#a-textures-mips)). They go as
  the lock leaves them: not panned, at their own scale (`DrawScale`, times
  the mip's shrink).
- **The viewer's `Sprite`**, when a player views with one set (the Matrix
  cheat's), stands in for every surface's texture current frame, the
  Sprite's own current frame then giving the detail and macro textures; for
  every decal's; and for every corona drawn, which `DrawFrame` writes into
  the light's `Skin` before drawing it, so it stays there once the Sprite
  is gone. With [meshes](#mesh-textures) and
  [sprites](#sprites), every texture of the frame is the Sprite.
- **The depth buffer** is cleared (the render device's `ClearZ`) twice in
  `DrawFrame`: after the frame's children, when its first list holds a
  surface (a mirror or a portal), so what was drawn beyond hides none of
  the frame's own surfaces; and last, after the coronas, in the sky's frame
  (one whose zone, `ZoneNumber`, is a `SkyZoneInfo`'s), so the sky hides
  nothing in front of it.
- **The sky's frame** looks out from the zone's `SkyZone`, turned as the
  viewer is and by the inverse of the sky zone's rotation (observed, not
  read). Liberty Island's sky zone is turned 5,080 (28°).
- **A mirror's frame**: `OccludeBsp` opens one for a surface flagged
  `PF_Mirrored` (its own flags with the viewport's `ExtraPolyFlags`) while
  the frame's `Recursion` is under 3 and the viewer's `ShowFlags` has
  `SHOW_PlayerCtrl` (0x800). A one-sided surface more than a unit behind
  the eye is passed over first, a mirror among them. A translucent mirror is
  a shiny surface: with the render device's `ShinySurfaces` (+0x5C) off it
  opens none and goes into the second list solid, its `PF_Translucent`
  cleared and `PF_Occlude` set.
  - **The view** is the parent's reflected in the surface's plane, its axes
    and its eye (`FVector::MirrorByPlane`), and its `Mirror` the parent's
    negated, which turns each surface's points round. The frame's walk runs
    from its own eye (its `Coords.Origin`), the reflected one behind the
    mirror: front to back, and passing over faces seen from behind, as the
    reflection shows them.
  - **Where it starts**: the zone on the viewer's side of the mirror (the
    node's `iZone` on that side), whose span buffer is what of the mirror
    shows, and whose render time it stamps. Its `NearClip` is the mirror's
    plane in the parent's view space, turned round, and each surface and
    mesh face is clipped at it (`ClipBspSurf` `0x10b1545e`, the mesh's
    `0x10b0cb10`). What lies behind the mirror stays out through the zones'
    span buffers too, as in any frame.
  - **One frame a plane**: `CreateChildFrame` (`0x10b15a40`) returns the
    parent's child of the same level, surface number, `NearClip` and zone,
    the spans merged, when it has one. Every mirror's surface number is 0,
    so the mirrors of one plane seen from one zone share a frame.
  - **The mirror itself** goes into the first list with `PF_Occlude`: an
    opaque one `PF_Invisible`, its depth alone (on a span-based device not
    drawn), a translucent one with its own flags, over the reflection.
  - **Actors**: the viewer's pawn shows in it
    ([which actors are drawn](#which-actors-are-drawn)).
- **A warp zone's frame**: `OccludeBsp` opens one for a portal surface whose
  zone beyond is a `WarpZoneInfo`'s, while the frame's `Recursion` is under
  3, only with the zone's `OtherSideActor` set, calling the zone's
  `Generate` first when it is not (`FindFunctionChecked`); with none still,
  no frame.

## The overlays

What the view's `RenderOverlays` draws (the first-person weapon, or the item
in the player's hand) comes after the world, on a depth buffer cleared of
the world: no wall hides any part of it.

- **Sent** by `DrawWorld` (`0x10b1cb90`) after `DrawFrame`, outside the
  editor: to the viewport's player's `ViewTarget`, or to the player when it
  has none; to no one while it is `bBehindView`, or without `SHOW_Actors`
  (8) in its `ShowFlags`. A player logged in for play has it:
  `ULevel::SpawnPlayActor` (`Engine.dll` `0x10396bd0`) sets its `ShowFlags`
  to 0x480C (backdrop, actors, player controls, real time). The console's
  `HIDEACTORS` clears it and `SHOWACTORS` sets it (`UViewport::Exec`).
- **The order** (`0x10b1ce7f`): bit 0 of Core's `GUglyHackFlags` set; the
  render device's `ClearZ` on the frame; the event, with the viewport's
  canvas; the bit cleared (`0x10b1cec5`). Nothing else sets it: of the
  game's DLLs only `Render.dll` and `D3DDrv.dll` import it, and `Core.dll`,
  which exports it, never touches it.
- **The canvas's frame** is the one `DrawWorld` draws, given it before the
  player's `PreRender`
  ([the loading screen](engine-dll.md#the-loading-screen)).
  `Canvas.DrawActor` (`UCanvas::execDrawActor`, `Engine.dll` `0x10377ed0`)
  draws its actor through `DrawActor` on that frame: the world's view and
  field of view, no span buffer, no moving lights, and the polygon flags any
  mesh has ([meshes](#meshes)), none for depth. Its `ClearZ`, when true,
  clears the depth buffer first; its `WireFrame` draws with the player's
  `RendMap` at 1 (`REN_Wire`) for the call. The game sets neither:
  `Weapon`'s and `Inventory`'s `RenderOverlays` (`Engine.u`) call
  `Canvas.DrawActor(self, false)`.
  Both natives clear the actor's `bHidden` for the draw and set it
  afterwards, whatever it was. `Canvas.DrawClippedActor`
  (`execDrawClippedActor`, `0x103780d0`) does the same through the frame
  with its `X`, `Y`, `XB` and `YB` swapped for the call's
  (`ComputeRenderCoords`, `ComputeRenderSize`), put back after.
- **No depth of the world is left** after the clear, for the overlays or
  for the windows the player's `PostRenderFlash` draws after them: an actor
  that `GC.DrawActor` draws there without `bClearZ` shows through walls, as
  the vision augmentation's heat sources do
  ([actors in a window](extension-dll.md#actors-in-a-window)).
- **The drivers.** `D3DDrv`'s `ClearZ` (`0x10007550`) clears the depth
  buffer alone, to 1.0; `OpenGLDrv`'s (`0x1000bca0`) turns depth writes on
  and clears it (`glClear` of the depth bit). Only `D3DDrv` reads the flag
  (`DrawGouraudPolygon`, `0x100057ea`), and only in a 16-bit display mode:
  it quarters each vertex's 1/z, the overlays' depth taken as if four times
  as far. `OpenGLDrv`'s frustum runs from half a unit to 32,768.

## Which actors are drawn

`SetupDynamics` goes through every actor of the level, each frame. It passes
over one that is:

- hidden (`bHidden`; `bHiddenEd` in the editor);
- the actor the view is from, in first person in the main frame: the
  viewer's pawn, or its view target when it has one. `OccludeFrame`
  (`0x10b19fc0`) names it to `SetupDynamics` only for a frame with no
  parent, so a mirror's, a warp zone's and the sky's frames show it;
- `bOnlyOwnerSee`, unless it is the viewer's (anywhere up its `Owner` chain)
  in first person; or `bOwnerNoSee` and the viewer's, in first person: by
  the viewer's `bBehindView` alone, in every frame;
- `bHighDetail` while the render device's `HighDetailActors` is off. Of the
  game's classes only `Decal` sets it, and a decal is drawn with its
  surface, not here;
- a brush: a mover goes to the level's brush tracker, the rest is the world.
  The tracker files a mover's polygons into the level's BSP, where the walk
  takes each fragment's node as one of the level's own: of its surface it
  reads the flags (`0x10b17faa`) and the texture (`0x10b181a3`) alone, not
  the actor, and draws it in its node's zone ([light maps](#light-maps)). An
  opaque fragment fills its zone's span buffer as a wall does (`OccludeBsp`,
  `0x10b173d0`), so a sprite or a zone portal behind a closed door finds no
  span: DXEngine's harness's `DoorHideConsole`, a crate behind Liberty
  Island's `DeusExMover10`, not drawn for 13.5 s and on while the door is
  shut, drawn each frame once it is open. A
  one-sided one seen from behind is passed over, and a mirrored one opens a
  mirror's frame ([a frame](#a-frame)), 24 movers on 15 of the game's maps
  having one -- Hong Kong's club glass, the Smuggler's, the intro's and the
  endings' marble.

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
  the world at that depth, is its proxy (`0x10b233c0`), however near: a
  mesh's location within a unit of the eye puts it there, at the eye's own
  plane all its corners the eye's point, on the eye's side of every plane
  further off (DXEngine's `NearProxyConsole`).
- **The walk.** It starts at the BSP's root as a raster of the rectangle's
  rows. At each node it comes to (`0x10b23e30`), the part on each side of
  the node's plane goes on to that child, the raster cut along the line
  where the plane crosses the proxy. A corner counts on the plane's front
  more than 0.01 units before it, on its back more than 0.01 behind; a proxy
  with corners on one side alone goes whole to that side, and one with every
  corner within 0.01 of the plane to neither, so it is dropped
  (`0x10b23e88`-`0x10b23eb9`; the sides taken at `0x10b24303` and
  `0x10b244c7`).
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
  out: a pixel is in when its lower right corner is. A mesh whose location
  is behind the viewer gets no sprite at all.
- **A sprite's rectangle:** its texture's size times the draw scale, round
  where its location lands, rounded up: a pixel is in when its upper left
  corner is; none nearer than a unit, none whose right edge's pixel is the
  frame's first column or before it, and none whose left edge's is the
  frame's last column or past it (`0x10b23c85`-`0x10b23c9a`), so one at the
  right edge with a column showing is not drawn.

## Sprites

`DrawActorSprite` (`0x10b25080`) draws a kept sprite whose actor is
`DT_Sprite` or `DT_SpriteAnimOnce` with a texture as a tile: the canvas's
`DrawIcon` (`Engine.dll` `0x10376640`) hands `UCanvas::DrawTile`
(`0x10376160`) the whole texture at the sprite's place and depth, and the
render device draws it as a tile ([`D3DDrv`'s](d3ddrv-dll.md#tiles)).

- **The flags**: the actor's (below), its texture's own `PolyFlags`, and
  `PF_TwoSided`; `UCanvas::DrawTile` adds the masked bit of the frame it
  draws.
- **An actor's flags** (`0x10b26230`), its sprite's and its mesh's
  ([meshes](#meshes)): `PF_Masked` for `STY_Masked`, `PF_Translucent` for
  `STY_Translucent`, `PF_Modulated` for `STY_Modulated`; `PF_NoSmooth` for
  `bNoSmooth`; `PF_Selected` for `bSelected`; `PF_Environment` for
  `bMeshEnviroMap`; `PF_Flat` unless `bMeshCurvy`; `PF_Unlit` for `bUnlit`,
  an actor in zone 0, a viewer whose `RendMap` is not `REN_DynLight` (5), or
  the client's `NoLighting`.
- **The size**: the texture's `USize` and `VSize` times the draw scale, at
  the sprite's depth. The colour: white times `ScaleGlow`, each channel at
  most 1.
- **Upright**, as every tile: the texture's first row at the top of the
  screen.
- **The texture**: for `DT_SpriteAnimOnce`, the frame of its animation the
  actor's life has reached, `n × t − ½` rounded of its n frames, held to 0
  to n − 1, where t is 1 − `LifeSpan` ÷ the class's default `LifeSpan`, held
  to 0 to 1; otherwise the animation's current frame. A player viewer's
  `Sprite`, when set, is drawn in its place, at the size of the actor's
  texture ([mesh textures](#mesh-textures)).

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
    the first-person weapons) calls it too ([the overlays](#the-overlays)).
- **A zone's** (`Zones[i].LastRenderTime` in the level's model) is stamped by
  `OccludeBsp`: the frame's first zone, and each zone seen through a portal.
  `InStasis` reads it.
- **A decal's own `LastRenderedTime`** is stamped when `DrawFrame` draws it
  (its loop `0x10b1b0e6`-`0x10b1b2f0`): the decal is clipped to each of its
  surface's saved polygons, a node's polygon cut to the view's sides, which
  `OccludeBsp` saves for each node any span of which shows (`ClipDecal`,
  `0x10b1bda0`; a decal that lists its nodes, only to theirs). Its corners
  are lifted 0.75 units along the surface's normal (`0x10b2b304`) and cut by
  the planes through the eye and the polygon's edges, so on screen it fits
  the surface's drawn outline; no span buffer is asked. It is drawn and
  stamped where some of it is left: a decal behind nearer geometry, on a
  node that shows elsewhere, is stamped, the depth buffer hiding it
  (DXEngine's `DecalSeenConsole`: of 29 marks the eye's line to is blocked,
  15 stamped). `LastRendered()`
  does not read it: it reads `LastRenderTime`, which a decal never gets. So
  a decal, and Deus Ex's `Shadow`, never counts as drawn. When an NPC moves,
  its shadow is laid again only if the NPC was drawn in the last second,
  else taken off. The script always lays the player's.

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
  viewer's own pawn: two line checks. The first, of the level and the movers
  (`TRACE_Level | TRACE_Movers`), passes no node flags, so a surface that a
  sight test passes (`NF_NotVisBlocking`) stops it: an invisible one, such
  as the collision hull round a glass mover's pane. The second is of pawns
  and other actors (`TRACE_Pawns | TRACE_Others`), the viewer's own pawn
  allowed as the first one met.
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
- **Morphing.** With `LODMorph` above 0 and the mode's first bit set (below),
  on the budget before it is held to the mesh, B (at least `LODMinVerts`):
  past s, the whole number under (1 − `LODMorph`) × B, each vertex within the
  budget slides toward the vertex it collapses to by (its index − s) ÷
  (`LODMorph` × B), at most the whole way, toward that vertex's own place
  before it slides; one that collapses to the first vertex does not slide.
  A corner on a vertex that slides moves its texture coordinates as far
  toward those of the wedge it collapses to, as bytes, rounded down. Detail
  fades rather than pops, beginning before the first vertex goes.

**The settings** are `URender`'s. `Init` sets the shape LOD to 0.25, its
adjustment to 1 (nothing changes it), the mode to 1 and the fixed factor
to 1. Console commands set them (`URender::Exec`, `0x10b147b0`, which also
toggles a statistics panel a `STAT` word: Net, Fps, Global, Mesh, Actor,
Filter, Reject, Span, Zone, Light, Occlusion, Game, Soft, Cache, PolyV,
PolyC, Illum, Hardware, each drawn every frame by `DrawStats`, `0x10b13a50`;
`STAT FPS` the line "FPS=... Frame=... MSEC Render=... MSEC Nodes=...
Polys=... Tex=... TexMem=...K" 10 pixels above the view's bottom, and `STAT
RENDER` none):

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

## Wire meshes

With the viewer's `RendMap` at wire (1, as `Canvas.DrawActor`'s `WireFrame`
sets it), or an orthogonal view's (13 to 15), `DrawLodMesh` (`0x10b0ea80`)
asks `GetFrame` for the mesh's vertices in the world's axes, not the view's,
and after their outcodes and the weapon triangle draws lines in place of
faces, nothing culled or lit:

- each face within the detail budget, whatever its material, its corners
  down their collapse lists and slid as ever ([mesh detail](#mesh-detail)),
  as three lines: its last corner to its first, then each to the next;
- then each special face, the weapon triangle's, between its special
  vertices;
- through the render device's `Draw3DLine`, depth cued (2), in (0.6, 0.4,
  0.1), or (0.2, 0.8, 0.1) for a selected actor.

`DrawMesh` (`0x10b0d1a0`) draws a plain mesh's triangles the same, but a line
only from the corner of the greater X, so an edge two triangles share is
drawn once, and every line of a two-sided triangle. The outcodes are worked
out on those world-axis vertices against the view's sides, so a corner is
out by where it lies from the world's origin: the weapon triangle is nearly
always wholly out past one side, and what the pawn holds is not drawn
([a pawn's attachments](#a-pawns-attachments)). `URenderDevice::Draw3DLine`
(`Engine.dll` `0x10371c90`) takes a line into the view's axes, clips it to
the near plane and projects it, and `Draw2DClippedLine` (`0x10371700`) clips
it to the frame; `D3DDrv` draws it with its `Draw2DLine`
([the rest of a frame](d3ddrv-dll.md#the-rest-of-a-frame)).

## Mesh textures

Which texture each face of a mesh draws:

- **A slot's texture**, for each of the mesh's texture slots: the actor's
  `MultiSkins` entry; else the mesh's own texture; else the actor's `Skin`.
  Slot 0 takes the `Skin` before the mesh's texture. `UMesh::GetTexture`
  (`Engine.dll`) picks between the mesh's texture and the `Skin`.
- **Animated.** Each slot's texture is brought up to date and shown at its
  animation's current frame, so an animated texture plays (a fractal one
  steps as in [stepping](fire-dll.md#stepping)).
- **Where it lies**: a corner's coordinates are its wedge's U and V bytes
  times the texture's size (its `USize` and `VSize` times its scale) ÷ 256
  (`DrawLodMesh`, `0x10b10b4e`), so a byte of 255 falls a 256th short of the
  texture's far edge.
- **The environment map:** the actor's `Texture`; else its zone's
  `EnvironmentMap`; else the level's; else the texture of the last slot
  that has one. A face whose slot has no texture draws it, and so does an
  environment-mapped face (the actor's `bMeshEnviroMap`, or the face's own
  flags). Such a face's texture coordinates are a reflection (`0x10b0bab0`):
  at each corner, the line from the eye made a unit vector, mirrored by the
  corner's normal and turned into the world's axes (the frame's `Uncoords`);
  its X and Y + 1, × 128 × the texture's size ÷ 256, as a wedge's bytes are.
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
watery shimmer, warp and the unused slot; an `LE_OmniBumpMap` light lights no
surface ([light maps](#light-maps)). The cloud cast has it too: its function
(`0x10b04380`) only calls `SpatialPlain`, though the table counts its shape
as changing.

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
| blink | out when its turn count is odd: the level's time × 35 × 65536 ÷ (`LightPeriod` + 1), plus `LightPhase` × 256, truncated (`0x10b05a90`); in effect a fresh state each frame, at any frame rate, until the count reaches 2^24 (below) |
| flicker | the frame's random number at the low byte of the light's address, one of the 256 fresh draws of the [random tables](#light-maps) (`0x10b05af0`): out below one half, else that fraction; lights whose addresses end in the same byte flicker as one |
| strobe | out every other frame: one switch for every strobe, turned over whenever a strobe is lit at a level's time other than the last one seen (`0x10b05b30`; the time and the switch at `0x10b49ea4` and `0x10b49ea8`, 0 at the start); its period and phase play no part |
| palette | through its palette once over its life (`1 − LifeSpan ÷` the default's, times 255), or at 35 turns a second over the period; times `(2 red + 3 green + blue) ÷ 1536 × 2.8` of the entry |

Both pulses' sines run at 35 turns a second over `LightPeriod` (at
least 1), from `LightPhase`'s 256ths of a turn. The palette loop runs at
that rate too, but adds `LightPhase` in whole turns, which its entry, the
turn's 256ths modulo 255, drops: the phase changes nothing, and the
palette's last entry never shows (`0x10b05d40`).

- **By the frame.** The level's time goes on while the game is paused
  ([a level's tick](engine-dll.md#a-levels-tick)) and the random tables are
  drawn at every frame's `PreRender`: a blink, a strobe and a flicker change
  with each frame drawn, paused or not, faster at a higher frame rate.
  `GlobalLighting`'s first argument, bit 0x800 of the viewport's actor's
  `ShowFlags`, makes every light steady when it is off. A lamp of each made
  over Liberty Island's dock, held to 60 frames and sampled frame by frame
  (DXEngine's `LightConsole` with `Burst`): a strobe turned over at every
  frame; a flicker's state changed at half of them, its brightness at 0.72;
  a torch's and a fire's waver at 0.95 and 0.94.
- **In floats.** `URender::PreRender` (`0x10b14560`) holds the x87 to 24 bits
  for the frame (Core's `appEnableFastMath`, `0x1016e050`: `_controlfp`'s
  `_PC_24`; Core's start sets 64), and `PostRender` (`0x10b14700`) gives it
  its 64 back. So each step of a turn count drawn in the frame is rounded to
  a float: from 2^24 every float the count can be is even, and a blink stays
  lit from some 7.3 s × (`LightPeriod` + 1) of the level's time on (sooner by
  the phase, at most 0.4%). No stock map's light is a blink, as saved or by
  its class's default. Run the same way: a blink of period 32 in the state
  its count worked out in floats gives at 0.998 of 569 frames, in doubles at
  0.946; one of period 1 last out at 14.62 s of the level's time, and lit
  at every frame after, to 24 s.
  - **The console's tick inside it.** `UGameEngine::Draw` (Engine.dll
    `0x1038f110`) calls `PreRender` (`0x1038f66c`) before the console's own
    `PreRender` (`0x1038f685`), which sends the console's `Tick`
    (`UConsole::PreRender`, `0x10379d10`), and `PostRender` (`0x1038f79b`)
    after the console's `PostRender` (`0x1038f74b`). So the console's tick
    and every script event of the frame -- the player's and the console's
    `PreRender` and `PostRender` -- work at 24 bits, and so does every
    native they call: DXEngine's `OpsConsole`'s `7 *= 3e9` in its tick gives
    the 24-bit product, and a trace's sums there are the 24-bit ones
    ([traces](engine-dll.md#traces)). The level's tick runs outside it, at
    the 64 bits the frame before's `PostRender` left: an actor's own tick
    gives `7 *= 3e9` as -474,836,480, the whole product's, where the
    console's gives -474,836,992 (DXEngine's `PrecisionConsole`);
    DeusEx.dll's own CRT sets 53 as it loads (`0x1001c4d8`, called at
    `0x1001b1aa`), until the first frame's `PostRender`.

### Light maps

`SetupForSurf` (`0x10b06c90`) gives each surface drawn its light map.

- **Three kinds of light** (`AddLight`, `0x10b08b30`), from the surface's list
  of the level's lights, each with its shadow bits (a bit a texel, stored
  with the level), and the moving lights over it:

  | Kind | Lights |
  |---|---|
  | *moving* | `bDynamicLight`, whatever else it is, or neither `bStatic` nor `bNoDelete`; it casts no shadow |
  | *static* | `bStatic`, `LT_Steady`, and an effect whose shape and brightness hold still |
  | *animated* | any other `bStatic` or `bNoDelete` light |

  In that order: `bDynamicLight` (bit 0x800 of the actor's first flags) is
  tested first, so a static light that has it is a moving one, but for an
  `LE_OmniBumpMap` light with no owner, tested before it, kind 3, which
  `SetupForSurf` merges into no map (`0x10b08b7a`-`0x10b08b85`): it lights no
  surface. A light with no type or no brightness is none; lighting an actor
  (its owner given), every light is a moving one, but the actor itself. With
  the client's `NoDynamicLights` on (an ini setting, off by default),
  animated lights count as static and moving ones are left out.
- **A mover with `bDynamicLightMover`** (`0x10b06efe`): its surface takes the
  lights of the mover's leaf in front of the surface's plane, with no owner
  and no shadow bits (`0x10b06f63`-`0x10b06fca`), and the moving lights over
  it with the mover for their owner (`0x10b06ffc`): so those are moving
  lights, an `LE_OmniBumpMap` one too, which lights the mover's surface.
- **No light map at all** when the viewer's `RendMap` is not `REN_DynLight`
  (5) or the client's `NoLighting` is on: `DrawFrame` asks for a surface's
  maps only when it has a light map, the level has light maps, and neither
  (`0x10b1aa3a`-`0x10b1aa99`), so it goes with no light map and no fog map.
  `SetupForActor` takes no light then, nor for a `bUnlit` actor or one in no
  leaf, the lights kept under the actor left as they were
  (`0x10b08e40`-`0x10b08e98`), and the actor's flags make it unlit
  ([sprites](#sprites)). `DrawWorld` (`0x10b1cc20`-`0x10b1cc62`), before
  each frame, puts a viewer's `RendMap` back at 5 and the client's
  `NoLighting` off, when the viewer is no admin (`bAdmin`), its level has
  `bNoCheating` and the game is not the editor.
- **The static map:** the zone's ambient light, and each static light through
  its shadow bits (smoothed as they are unpacked, `0x10b02650`). The zone is the
  one the surface is seen from: `OccludeBsp` (`0x10b173d0`) gives each draw its
  node's zone on the side of the plane the view's origin lies, the front only
  when the origin is over 0 from it (`0x10b17d9f`), `iZone[1]` in front and
  `iZone[0]` behind (`0x10b19561`), the `LevelInfo` for a zone with no zone
  actor, zone 0 among them (`0x10b19577`), and a portal the other side's.
  Each of a plane's coplanar nodes (its `iPlane` list) is judged by its own
  plane, which may face the other way (`0x10b19b8c`). `SetupForSurf` starts
  the map from that zone's ambient light (`0x10b06e83`, `0x10b07fa8`). The
  map is kept in the global cache (`GCache`) under the model, the light map
  and the zone. It is built again only when it is not there, when one of
  its lights has `bLightChanged`, or, for a mover's surface, after the mover
  moves, turns or changes leaf. A mover's surface is lit where the brush
  tracker filed it ([`Engine.dll`](engine-dll.md#traces)), from its brush's
  light map (`0x10b06e29`: for a surface the tracker owns, its actor's
  `Brush` is the model), its static lights through the shadow bits
  raytraced at its `BrushRaytraceKey`, and each fragment by its own node's
  zone, not the mover's: a polygon the tracker split across two zones takes
  each one's ambient light, pan speeds and fog on its own side of the split,
  and a mover whose place lies in another zone than its faces takes their
  zones'. Measured: a door moved 100 units off its place is lit there, by
  its own lights' fall-off and by a moving light 48 units before it that
  reaches no further.
- **The fog map** ([`D3DDrv`'s fog](d3ddrv-dll.md#fog)), only when the render
  device takes fog maps and does volumetric lighting (`SupportsFogMaps`,
  `VolumetricLighting`) and the viewport's actor is in a fog zone
  (`bFogZone`): then `OccludeBsp` gathers the volumetric lights listed for
  each leaf it walks (`LeafVolumetricLighting`, `0x10b170e0`), and each draw
  keeps those whose sphere, (`VolumeRadius` + 1) × 25 units, reaches the view
  through its polygon, each lit as it is that frame, a moving one where it is:
  DXEngine's harness's `FogTintConsole`, 02_NYC_Bar's `Light90` turned to full
  brightness and red, the fog bright red at once. Its colour is the light
  map's record of the light (`FGetHSV` of its hue and saturation at full
  value, times its brightness shaped by its type, `GlobalLighting`
  `0x10b05e90`, and the level's), its density K = `VolumeBrightness` ×
  brightness / 64 (`0x10b06bf7`-`0x10b06c03`): a table of 256 entries, d ×
  the colour and d × `VolumeFog`/255, each held to 127 (`0x10b06a35`-
  `0x10b06b60`), each texel the entry of 255 × min(3K ∫(1 - r²/R²) ds / R, 1)
  for the first light (`0x10b07830`), and each later one, farthest first by
  depth (`0x10b06c60`), dimming the map by its own and adding its colour
  (`0x10b020e3`-`0x10b02105`). `SetupForSurf` (`0x10b06c90`) then makes a fog map for
  a draw with any, not translucent, whose zone (the one the surface is seen
  from, above) is a fog zone too.
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
  - As a light is added (`MergeLight`, `0x10b03040`), a waver dims each texel
    by a random amount of up to a: 5% for a torch waver, 20% for a fire
    waver, 40% for a watery shimmer. Its illumination i becomes `i × (1 − a +
    a × r) − 0.5`, cut down. The draws r are taken in turn from 0 over the
    texels of the light's rectangle on the map, row by row, round a table of
    256.
- **The light's rectangle** (`SetupLight`, `0x10b0660e`-`0x10b06865`): the
  texels within |axis| × √(max(0, 1.05 r² − h²)) of the light's foot on the
  surface's plane, h its height over it, along each of the map's axes: each
  edge, the foot's U less or plus that, over the map's `UScale` (V by
  `VScale`), rounded to the nearest texel (`fistp`), the first edge held at
  0 and the last, which is left out, at the map's size. Every light's shape
  runs over those texels alone and is merged over them alone, a static
  light's into the static map too: so a light 1.025 r or more off the plane
  lights none of the map, a cylinder light high over a surface lights a
  square, and a texel on or past the last edge none, within the light's
  radius or not. The two roots are the light manager's
  (`FLightManager::Init`'s table, `0x10b0225d`-`0x10b022ce`, read at
  `0x10b06681`): of the value with its significand cut to its top 10 bits.
- **The random tables** (`TickRandoms`, `0x10b13080`, each frame from the
  level's time, at the end of `PreRender`):
  - 256 fresh draws: the flicker's, the torch's and fire's;
  - the watery shimmer's own, each entry easing toward a draw. At each of 35
    ticks a second, the 16 entries the tick moves past take the fresh
    table's draws as their targets, a sixteenth of the way a tick; the
    others move on that step for each tick passed. 16 ticks or more without
    a frame start it over with fresh draws. So an entry glides to a new
    value every 16 ticks (under half a second), each held to 0-1.
- **A texel's place** (`SetupLight`, from `0x10b0615e`): texel (i, j) is lit
  at the point of the surface whose texture coordinates are
  `(Pan.X + i × UScale, Pan.Y + j × VScale)`, by the light map's own pan and
  scales: where a render device draws the texel's centre
  ([where a light map lies](d3ddrv-dll.md#where-a-light-map-lies)).
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
    The height is its size: a moving light behind a surface lights it as
    from in front (a light 24 units under Liberty Island's pier lights its
    deck).
    Times the shadow byte, rounded.
  - **The spotlight's** (`SpatialSpotlight`, `0x10b04f80`): the same times
    `((cos − c) ÷ (1 − c))²` inside its cone, `c = 1 − LightCone ÷ 256`,
    rounded down; the cone about the light's rotation, a pawn's view
    rotation (`0x10b04f89`-`0x10b04fa9`).
  - **Each effect's** (a table of a function, whether the shape changes each
    frame, and whether it wavers, at `0x10b2a0f0`): the plain shape for
    `LE_None`, the wavers, `LE_Warp` and `LE_Unused` (`LE_OmniBumpMap`'s,
    which no light map takes); the spotlight's for `LE_StaticSpot` too;
    `LE_CloudCast` the plain shape again (`0x10b04380`), but counted as
    changing. The others, each within the light's radius (`d < r`) but the
    cylinder, rounded down (half a unit taken off, then rounded) and the
    waves', shock's, searchlight's, rotor's, disco's and interference's on
    the plain shape; (dx, dy, dz) the texel less the light, `t` the level's
    `TimeSeconds`, the angles from the sine table:
    - **Cylinder** (`0x10b04a80`): the shadow byte ×
      `(1 − (dx² + dy²) ÷ r²)`, held at 0: a fall-off round the light's
      vertical axis, with no angle and no height.
    - **Non-incidence** (`0x10b054e0`): the shadow byte × `(1.02 − d ÷ r)`,
      with no angle. Its byte is not held: a lit texel within 1.4% of the
      radius from the light makes over 255 and wraps to a few.
    - **Slow wave** (`0x10b03de0`): × `0.7 + 0.3 sin(2π (n − 35t) ÷ 64)`, `n`
      the distance in whole units: a wave 64 units long going out at 35
      units a second.
    - **Fast wave** (`0x10b040b0`): the same with `n` a quarter of that,
      rounded down, over 32: 128 units long, going out at 140 a second.
    - **Shock** (`0x10b043a0`): × `(0.9 + 0.1 cos(2π (n + 4000t) ÷ 4096))`
      × `(0.9 + 0.1 sin(2π (2n − 4000t) ÷ 4096))` ×
      `(0.9 + 0.1 sin(2π (n ÷ 2 − 4000t) ÷ 4096))`, `n` the distance in
      eighths of a unit and `n ÷ 2` rounded down: three ripples of a tenth,
      512, 256 and 1024 units long, the first coming in at 500 units a
      second, the others going out at 250 and 1000.
    - **Shell** (`0x10b05740`): the shadow byte × `(1 − 10 |d ÷ r − 0.9|)`
      from 0.8 to 1 of the radius, dark elsewhere: a thin shell, brightest
      at 0.9 of the radius, with no fall-off and no angle.
    - **Interference** (`0x10b04c80`): × `(1 + cos(11x + 5t)) ÷ 2`, `x` the
      angle from the vertical `atan2(√(dx² + dy²), dz)`: rings round the
      axis by that angle, disco's second term alone.
    - **Searchlight** (`0x10b03770`): × `(1 + cos a) ÷ 2` for
      `a = 4 atan2(dx, dy) + LightPhase × π/32 + 35t ÷ LightPeriod + 2π`
      (no time term with no period) taken mod 8π, between π and 3π, and
      dark elsewhere; times `(dx² + dy²) × 0.00006` within some 129 units of
      the light's vertical axis. One beam a quarter turn wide round that
      axis, fading to nothing near it, turning once in
      `8π × LightPeriod ÷ 35` s.
    - **Rotor** (`0x10b03ae0`): × `(1 + cos(3.5t + 6 atan2(dx, dy))) ÷ 2`,
      blended toward 1 within 100 units of the axis by
      `(dx² + dy²) × 0.0001`: six blades turning at 3.5/6 radians a second,
      lit full at the axis. The light's period and phase play no part.
    - **Disco** (`0x10b046f0`): × `(1 − u)`, `u = A + B − AB` for `A` and
      `B` each `(1 + cos(11x + 5t)) ÷ 2`, `x` the azimuth `atan2(dx, dy)` and
      the angle from the vertical `atan2(√(dx² + dy²), dz)`, and `u` faded to
      nothing within some 141 units of the axis by `(dx² + dy²) × 0.00005`.
      Away from the axis it is `(1 − A)(1 − B)`: a grid of spots, 11 round by
      11 down, turning at 5/11 radians a second; lit full at the axis.
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

- **The candidates:** the lights it had last frame (kept in the cache under
  the actor, up to 16, each with its fade, below), the static lights that
  reach into the actor's leaf of the BSP, and the moving lights in it (its
  sprite's leaf lights, [which actors are drawn](#which-actors-are-drawn)).
  An actor drawn on its own has no moving lights there: `URender::DrawActor`
  (`0x10b262c0`), which `Canvas.DrawActor`, `Canvas.DrawClippedActor` and
  `GC.DrawActor` draw through, makes it a sprite with no leaf lights, so a
  first-person weapon is lit by the static lights and those it kept. Each
  counts once, and only if it reaches the actor and its `bSpecialLit` is
  the actor's: a kept light that no longer reaches it is dropped at once.
  Its strength at the actor's centre is `(1 − distance / radius) ×
  LightBrightness`, the byte, in 1024ths. A cylinder light counts with
  three quarters of its brightness and radius, its reach tested at the
  whole radius: one between the two stays, its strength below 0, and fades
  out. A light that is off, or of no brightness, stays a candidate too.
  The leaf's volumetric lights (`LeafVolumetricLighting`, the fog map's
  list) are the actor's fog, every one listed while the light infos have
  room (256 in all).
- **The pick**, one pass over them, strongest first: a static light is lit
  while fewer than 8 static ones are, any other while fewer than 8 in all
  are, none under an eighth of the first one lit. The actor's own light,
  among them, counts as any other, its place among the 8 and its eighth,
  but lights nothing of it: `AddLight` (`0x10b08b30`) takes no light that is
  the actor lit, nor one that is off. So a lamp or a sword that glows is lit
  only by lights an eighth as strong at its centre as its own, and a lamp
  switched off beside an actor still keeps a weaker light from it.
- **Shadowed or not:** a `bMovable` light that is not static is lit. Another
  is lit as a line from it to the actor through the level's BSP found it,
  the line run again every 16 frames, by the viewport's frame count and the
  light's object index; between, as it was. On the actor's first draw (no
  cache under it) every light's line is run, and one found open is lit full
  at once.
- **The fade**, a byte each light keeps under the actor: a light new to the
  actor starts by the list it is first found in -- the kept ones come first,
  then the leaf's static lights, then its moving ones (`0x10b091a8`,
  `0x10b09366`, `0x10b094c9`): one of the static lights at 0 and unlit until
  its line is next run, one of the moving lights at 255 and so lit until its
  line is run, whatever its own flags: a `bDynamicLight` light that is static and
  in no light list of the model (15_Area51_Final's `Light809`, `Light221`,
  `Light810`) lights an actor full from the first frame it reaches it
  (DXEngine's `LightPickConsole`, `Scene=Late`). Each draw it steps by the
  viewport's time since its last frame
  × 768, at most 255 (a third of a second): lit, up and odd, at most 255;
  else down and even, at least 0. A light lights as it fades, its colour ×
  the byte ÷ 255; up to 16 whose byte is over 1 are kept, strongest
  first.
- **Per vertex** (`Light`, `0x10b027f0`), each vertex of a face kept lit
  once, by its normal alone, whatever its faces' flags: so a two-sided
  face shows on both sides the light its normal gets. Its normal is
  the sum of its faces' unit normals in the frame's pose, from every face
  within the detail budget, made a unit (a table's 1/√ of its square plus
  0.001) just before; the vertex then moved out along it by the fatness
  (`Fatness` ÷ 16 − 8). Its distance to a light is a table's √. For each
  light:
  - a diffuse term, `(cos + 1)² − 1.5` of the angle to the light (nothing
    beyond about 77°, 2.5 facing it);
  - a highlight, `6 × cos²` of the angle between the eye and the light's
    reflection at the vertex, when the reflection heads toward the eye;
  - both times `(1 − distance / radius)` and the light's colour, the light
    maps' (colour and brightness above).

  The sum is scaled by `1.4 × ScaleGlow`. Added to it: the zone's ambient
  light in `FGetHSV`'s colour, and the actor's `AmbientGlow` ÷ 255 (255
  pulses, `0.25 + 0.2 sin(8 t)`, t the viewport's clock, `CurrentTime`, the
  real time at each lock, whatever the level's `TimeDilation`: at 0.01 a
  glowing crate's twelve shots 1.5 s apart run through the pulse's range --
  DXEngine's `GlowConsole`, run on the original). Each channel is at most
  1. An unlit draw (`PF_Unlit`, the actor's or a material's) is
  `AmbientGlow` / 256 + `ScaleGlow` / 2, held to 0-1: mid-grey for most
  (`0x10b0f6e0`), the mesh drawn's own, a held weapon's its own though the
  holder is its light sink (`DrawActorSprite`, `0x10b25080`;
  `HeldGlowConsole`). An unlit face writes it into each of its corners'
  light as the faces are drawn (`0x10b0bab0`), so a lit face drawn after it
  takes it at the corners they share: the LAM's, the NanoKey's, the security
  camera's.
- **Fog** (`Fog`, `0x10b02c00`), for a draw that `SetupForActor` flags
  `PF_RenderFog`, the actor's leaf having volumetric lights. One of them
  that also lights the actor stays a light; the rest are the fog's alone.
  Per vertex, each in turn:
  - its sphere, radius R = (`VolumeRadius` + 1) × 25 units about the light,
    is dense 1 − r²/R² at r from its middle; that density's integral along
    the line from the eye to the vertex, × 3/R, × `VolumeBrightness` × the
    light's brightness (its `LightBrightness` ÷ 255, pulsed as its light
    maps' is) ÷ 64, held to 0-1, then doubled, is the light's fog f. A
    sphere behind the eye, the eye outside it, gives none.
  - The fog's alpha gains f × `VolumeFog` ÷ 255, at most 1, and its colour
    is f × the light's colour plus the colour so far × 1 − that gain, each
    channel at most 1.

  The vertex goes to the render device with its fog beside its light;
  `D3DDrv` draws it only with `UseVertexFog`, which the game's ini has off
  ([`D3DDrv`'s fog](d3ddrv-dll.md#fog)), so the game's meshes are drawn
  unfogged.
- **Which faces are drawn.**
  - `DrawLodMesh` keeps a face whose corners are not all beyond one side of
    the view, and that faces the eye: `((A − B) × (C − A)) · A`, in view
    space, times the frame's `Mirror`, under 0. A face the actor's flags or
    its material's make two-sided (`PF_TwoSided`) need not face the eye
    (`0x10b0ff9e`, and `0x10b10320` in its second face loop).
  - `DrawMesh`, for a plain mesh, culls a face turned away only when its
    flags with the actor's (`0x10b0dbac`) are `PF_Flat` without
    `PF_TwoSided` or `PF_Invisible` (`0x10b0dc8a`). The actor's flags give
    `PF_Flat` unless `bMeshCurvy` (`0x10b26284`), but `DrawMesh` first ORs
    it into the flags it is given (`0x10b0d1c9`), a LOD mesh's too, before
    it hands one on to `DrawLodMesh`, the one way in to either: a face
    turned away is culled unless it is two-sided or invisible, whatever
    `bMeshCurvy`, and the face's draw never takes the path it keeps for a
    face without `PF_Flat`, a curved mesh's, cut into four up to three
    times (`0x10b0bc13`). `D3DDrv` tests no such bit.
  - A plain mesh's face whose own flags hold `PF_Invisible` is its weapon
    triangle ([a pawn's attachments](#a-pawns-attachments)): kept whichever
    way it faces, its place noted, never drawn (`0x10b0e329`).
  - The actor's flags (`0x10b26230`, [sprites](#sprites)) make no face
    two-sided.
  - `D3DDrv` draws with culling off, so only this keeps a translucent mesh's
    back faces unseen.
  - **At the eye.** A corner is projected only when it lies within the
    view's four sides and deeper than a unit (`DrawLodMesh` `0x10b0f8d1`-
    `0x10b0f8e6`, `DrawMesh` `0x10b0d7da`-`0x10b0d7ef`). A face is clipped
    at the sides it crosses alone (`0x10b0c598`, in the face's draw
    `0x10b0bab0`), each corner the clip makes projected whatever its depth
    (`FTransform::Project`, `0x10b12400`), so a face crossing before the eye
    goes to the render device down to the eye, its corners' depths under a
    unit among them; in a frame whose `NearClip` has a W, a mirror's, it is
    clipped at that plane too (`0x10b0cb10`-`0x10b0cb93`). A corner within
    the sides a unit or less before the eye is never projected: the face
    takes the screen place and depth its memory last held, its place held
    to the frame like every corner's (`0x10b0cb96`-`0x10b0cbeb`), a mesh
    within a unit of the eye drawn wrong.
  - **In face order** on a render device that is not span-based: opaque,
    masked and translucent faces as they come, each with its own flags. A
    span-based one (the software renderer) first sorts the faces kept by
    their depth key, the largest first (`appQsort`, comparator
    `0x10b0ea60`). So on `D3DDrv` a translucent face drawn before an opaque
    face behind it is covered where that face is drawn.
