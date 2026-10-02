# D3DDrv.dll

The original's display driver: `UD3DRenderDevice`, the Direct3D 7 render
device the game shipped with and the one its look was tuned on. Read for the
roadmap's on-screen milestone ([decided 4](https://github.com/JuggyMcNutty/port-ex-machina/blob/main/agent.md#decided)): gamma,
the light maps' brightness on screen, fog, detail textures, and the blending
every pass uses -- the reference a reimplemented look is judged against.
How it was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Source | `D:\prj\Clean\D3DDrv\Src\Direct3D7.cpp` (March 2001, with the game's other DLLs) |
| API | DirectDraw 7 + Direct3D 7, one class: `UD3DRenderDevice` over `URenderDevice` |
| Image | base `0x10000000`, 337 functions, all exports C++-mangled methods |
| Options | `UseMipmapping`, `UseTrilinear`, `UseMultitexture`, `UsePalettes`, `UseGammaCorrection`, `Use3dfx`, `UseTripleBuffering`, `UseVSync`, `UsePrecache`, `UseVideoMemoryVB`, `UseAGPTextures`, `UseVertexFog` (`StaticConstructor`, `0x10001880`); the game's ini also has `Use32BitTextures`, which nothing reads |

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
  ([the maps](render-dll.md#light-maps)) -- and is uploaded as 2c/255 of
  full brightness for a byte c: in 32-bit textures, every display's today,
  each byte doubled; in 16-bit ones, only on a display under 24 bits, taken
  to 5 bits against its largest byte and drawn times twice that byte
  ([textures](#textures)).
- With `UseMultitexture` (on in the game's ini) a surface without a macro
  texture draws in one pass: the light map on stage 1 as a plain modulate
  (`D3DTOP_MODULATE`), the stages' modulation colours multiplied into the
  vertices' diffuse. So **128 is unit brightness**: a light map dims a
  texture or leaves it, never brightens it. Without -- the option off, or
  a surface with a macro texture --, the base draws first and the light
  map is a second pass in the modulated blend below, which doubles: **64
  is unit, 127 doubles the texture**. Measured under the harness
  (2026-09-28, Liberty Island's start): a two-pass frame 1.6 times as
  bright as a one-pass one on every lit surface -- twice, the frames' gamma
  of 1.5 taken out --, the unlit ones alike; `OpenGLDrv`'s frames are the
  one-pass ones'.
- On a 3dfx Voodoo3 (found by its device ID in `SetRes`) stage 0 takes the
  texture alone while light-mapping, so the diffuse is not applied twice.

## Textures

How a texture's texels reach the card (`SetTexture`, `0x10008a60`):

- **The format.** `SetRes` looks for A8R8G8B8 when the display is 24 bits
  or more (`0x1000cff4`), and for A1R5G5B5 only when no format was found
  (`RecognizePixelFormat`, `0x10009d60`, keeps a list): so 32-bit textures
  on any display of 24 bits or more, 16-bit ones under that.
  `Use32BitTextures` plays no part. Each texture format has a handler, a
  setup and a per-mip conversion (constructor, `0x10001ee0`): palettized
  (`TEXF_P8`), `TEXF_RGBA7` (light and fog maps), and DXT1 as it is.
- **32-bit.** A palette's colours as they are, alpha whole (`0x10002320`);
  a light map's bytes doubled (`0x10002120`); the stage's modulation
  colour 1. So the colours drawn are the texture's own.
- **16-bit, a palette** (`0x100026b0`): each channel against the texture's
  `MaxColor` M (at least 1) -- (2^n − 1) / M in fixed point (2^31 for red,
  2^26 green, 2^21 blue, the quotient made a float and back), times the
  colour, the top 5 bits, at most 31 -- so the largest colour is 31 and one
  under 1/32 of M is 0; alpha one bit, set at 128; a masked texture's
  entry 0 cleared. A texture first drawn modulated takes its colours to 5
  bits unscaled ((c − 1) / 8 for c over 0, alpha set) and is drawn
  untinted. `MaxColor` is the texture's own, saved with it: the editor's
  `UTexture::CreateColorRange` (Engine.dll `0x103ef1c0`), each channel's
  largest over the palette entries its mips use, which `UTexture::Lock`
  passes on.
- **16-bit, a light map** (`0x10002390`): triangular tables `Init`
  (`0x100029b0`) makes, by a maximum m up to 127 and a value up to it:
  min(31, ⌊32 × value / m⌋), m half the map's `MaxColor`
  (`FTextureInfo::CacheMaxColor`, Engine.dll `0x103f08f0`: twice each
  channel's largest byte, at least 1). Red's entry is capped for A1R5G5B5
  but masked with R5G6B5's `0xF800`, so red loses its lowest bit.
- **The modulation.** In 16 bits the stage's colour is `MaxColor` over
  255, multiplied into the vertex colour of every draw that is not
  modulated -- a one-pass surface's diffuse is trunc(256 × both stages'
  colours − 0.5) --, so a texel comes out (q / 31) × M / 255.

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
  A fog map is `TEXF_RGBA7` like a light map, uploaded the same way, a
  byte c worth 2c/255. **A surface with a fog map skips its detail texture**: the
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
  flashes. The two values are the game engine's (`Engine.dll`'s
  `UGameEngine::Draw`, `0x1038f110`): the viewport's player's `FlashScale`
  halved and its `FlashFog`, each clamped to 0-1 with a fourth component
  of 0 -- 0.5 and black when the client's `ScreenFlashes` is off, unless
  the level is a net game (`NetMode` not standalone). A player's
  `FlashScale` of 1, its resting value, draws nothing.
- **Meshes and sprites** (`DrawGouraudPolygon`): the vertex's light colour
  becomes the diffuse (times the modulation compensation); a modulated draw
  is untinted white. Tiles (`DrawTile`) carry one colour the same way.

## The database

`gamefiles/System/D3DDrv.dll.i64` has the types, the UTF-16 strings and the
names from the three scripts; backed up in `reference/idb-backup/`.
