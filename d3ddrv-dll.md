# D3DDrv.dll

The original's display driver: `UD3DRenderDevice`, the Direct3D 7 render
device the game shipped with and the one its look was tuned on. Read for the
roadmap's on-screen milestone ([decided 4](../../agent.md#decided)): gamma,
the light maps' brightness on screen, fog, detail textures, and the blending
every pass uses -- the reference a reimplemented look is judged against.
How it was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Source | `D:\prj\Clean\D3DDrv\Src\Direct3D7.cpp` (March 2001, with the game's other DLLs) |
| API | DirectDraw 7 + Direct3D 7, one class: `UD3DRenderDevice` over `URenderDevice` |
| Image | base `0x10000000`, 337 functions, all exports C++-mangled methods |
| Options | `UseMultitexture`, `UseVertexFog`, `UseGammaCorrection`, `UsePalettes`, `UseMipmapping`, `UseTrilinear`, `Use32BitTextures`, `UseVSync`, `UseTripleBuffering`, `UsePrecache`, `UseAGPTextures`, `UseVideoMemoryVB`, `Use3dfx` |

The fixed state it draws with (`SetRes`): no culling, Z at less-equal,
dithering on, the masked alpha test at reference 127 with GREATER -- a masked
texel shows when its alpha is above half.

## Gamma

Brightness is a display gamma ramp, not arithmetic in the frame:

- `SetRes` asks DirectDraw for the primary surface's gamma control
  (`DDCAPS2_PRIMARYGAMMA`); without the capability it logs
  "Gamma control not available. Brightness adjustment won't work." and the
  slider does nothing.
- `Flush` computes and sets the ramp, so it takes effect on start and
  whenever the game flushes (a brightness change does):
  `ramp[i] = (i/255) ^ (1 / (2.5 x Brightness)) x 65535`, the same for R, G
  and B, from the client's `Brightness` (0 to 1, default 0.5 -- a 1.25
  gamma).
- `ReadPixels` (screenshots) applies the ramp to what it reads back, so a
  screenshot looks like the screen.

## The light maps' brightness

What decides how bright a lit wall is:

- A light map arrives as `TEXF_RGBA7` -- a byte a channel holding 0 to 127
  ([the maps](render-dll.md#light-maps)). On upload the driver scales the
  texels to saturation against the map's cached maximum colour
  (`FTextureInfo::CacheMaxColor`), and carries the inverse in the stage's
  modulation colour, whose base scale is **1/128** -- so the two together
  make a light map byte worth a 128th each of doubled light: **64 is unit
  brightness, 127 doubles the texture**.
- With `UseMultitexture` the base texture and its light map draw in one
  pass, the light map on stage 1 as a plain modulate; the per-stage scales
  collapse into one diffuse colour (`UpdateModulation`), where the doubling
  lives. Without, the base draws first and the light map is a second pass
  in the modulated blend below, which doubles on its own.
- One devices' path (`wMaxTextureBlendStages` reporting a single stage with
  a flag the driver keeps) selects the texture alone on stage 0 while
  light-mapping, so the diffuse is not applied twice.

## Blending

`SetBlending` maps a draw's polygon flags to the frame:

| Flags | Blend | Meaning |
|---|---|---|
| solid | none, Z written | opaque |
| `PF_Translucent` | `ONE` / `INVSRCCOLOR` | dest = src + dest x (1 - src): black adds nothing, white replaces; no Z write |
| `PF_Modulated` | `DESTCOLOR` / `SRCCOLOR` | dest = 2 x src x dest: mid-grey 0x80 is identity; no Z write |
| `PF_Highlighted` | `ONE` / `INVSRCALPHA` | premultiplied add: dest = src + dest x (1 - src alpha) |
| `PF_Masked` | alpha test | texel shows when alpha > 127/255; Z written |
| `PF_Invisible` | `ZERO` / `ONE` | draws nothing but still fills the Z buffer |
| `PF_NoSmooth` | point sampling | the filter drops to nearest for the draw |
| `PF_RenderFog` | specular on | vertex fog added per pixel (below) |

## Fog

Two kinds, as the engine hands them over:

- **Fog maps** (a zone's volumetric lighting): a surface with a `FogMap`
  draws it as an extra pass in the `PF_Highlighted` blend -- the fog's
  colour added over the scene, what lies behind dimmed by the fog's alpha.
  A fog map is `TEXF_RGBA7` like a light map, through the same 1/128
  modulation. **A surface with a fog map skips its detail texture**: the
  fog pass takes the detail pass's place.
- **Vertex fog** (`UseVertexFog`, for meshes and sprites): a draw flagged
  `PF_RenderFog` that is neither translucent nor modulated puts the
  vertex's fog colour in the D3D specular channel and turns specular on,
  so the hardware adds the fog after the texture is modulated. The fog
  values themselves come from the renderer's lighting
  ([meshes](render-dll.md#meshes)).

## Detail textures

The close-up grain on world surfaces, drawn only when `DetailTexture` is on
and the surface has one:

- Up to **three passes**, each a band by view depth: the first covers
  `Z < 380` units at the detail texture's own scale, and each further band
  divides the bound by ~4.22 (380, 90, 21.3) and multiplies the texture
  repeat by 4.223 -- finer and finer grain the closer the wall.
- Per vertex the detail fades by depth: `alpha = (bound/Z - 1) x 100`,
  clamped to 255, on a mid-grey vertex colour. The pass blends the detail
  texture toward mid-grey by that alpha (the driver requires
  `BLENDDIFFUSEALPHA`) and draws it modulated, so grey -- zero alpha, the
  band's far edge -- changes nothing and there is no seam. Polygons
  crossing a bound are clipped at it with zero alpha on the cut.
- The pass runs with a Z bias of 15 (reset to 0 after), so the detail
  never fights its own surface's depth.

## The rest of a frame

- **Screen flash** (`EndFlash`): with `FlashScale` at 0.5 and `FlashFog`
  black nothing is drawn; otherwise one full-screen translucent quad in the
  fog's colour, its alpha `min(2 x FlashScale, 1)` -- the pain and pickup
  flashes.
- **Meshes and sprites** (`DrawGouraudPolygon`): the vertex's light colour
  becomes the diffuse (times the modulation compensation); a modulated draw
  is untinted white. Tiles (`DrawTile`) carry one colour the same way.

## The database

`gamefiles/System/D3DDrv.dll.i64` has the types, the UTF-16 strings and the
names from the three scripts; backed up in `reference/idb-backup/`.
