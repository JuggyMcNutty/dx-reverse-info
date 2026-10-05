# D3DDrv.dll

The game's display driver: `UD3DRenderDevice`, the Direct3D 7 render device
it shipped with and its look was tuned on. Here: gamma, the light maps'
brightness on screen, fog, detail textures, and the blending every pass
uses, the reference a reimplemented look is judged against. How it was read:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 212,992 bytes |
| SHA1 | `d277f7467b1612282b123ed039cfac92937979c0` |
| Source | `D:\prj\Clean\D3DDrv\Src\Direct3D7.cpp` (March 2001, with the game's other DLLs) |
| API | DirectDraw 7 + Direct3D 7, one class: `UD3DRenderDevice` over `URenderDevice` |
| Image | base `0x10000000`, 337 functions, all exports C++-mangled methods |
| Options | `UseMipmapping`, `UseTrilinear`, `UseMultitexture`, `UsePalettes`, `UseGammaCorrection`, `Use3dfx`, `UseTripleBuffering`, `UseVSync`, `UsePrecache`, `UseVideoMemoryVB`, `UseAGPTextures`, `UseVertexFog` (`StaticConstructor`, `0x10001880`); the game's ini also has `Use32BitTextures`, which nothing reads |

The fixed state it draws with (`SetRes`): no culling, Z at less-equal,
dithering on, and the masked alpha test at reference 127 with GREATER, so a
masked texel shows when its alpha is above half.

## Gamma

Brightness is a display gamma ramp, not arithmetic in the frame.

- `SetRes` asks DirectDraw for the primary surface's gamma control
  (`DDCAPS2_PRIMARYGAMMA`). Without the capability it logs
  "Gamma control not available. Brightness adjustment won't work." and the
  slider does nothing.
- `Flush` computes and sets the ramp, so it takes effect at start and
  whenever the game flushes (a brightness change does). The same for R, G
  and B:

  `ramp[i] = (i/255) ^ (1 / (2.5 x Brightness)) x 65535`

  `Brightness` is the client's, 0 to 1. The game's ini ships 0.6, a gamma of
  1.5; 0.5 would be 1.25.
- `ReadPixels` (screenshots) applies the ramp to what it reads back, so a
  screenshot looks like the screen.

## The light maps' brightness

What decides how bright a lit wall is:

- **The upload.** A light map arrives as `TEXF_RGBA7`, a byte a channel
  holding 0 to 127 ([the maps](render-dll.md#light-maps)). It is uploaded as
  2c/255 of full brightness for a byte c ([textures](#textures)):
  - in 32-bit textures (any display of 24 bits or more: every current one),
    each byte doubled;
  - in 16-bit ones, only on a display under 24 bits, taken to 5 bits against
    its largest byte and drawn times twice that byte.
- **The passes:**

  | Path | When | The light map | Unit brightness |
  |---|---|---|---|
  | one pass | `UseMultitexture` (on in the game's ini), a surface without a macro texture | on stage 1 as a plain modulate (`D3DTOP_MODULATE`); the stages' modulation colours multiplied into the vertices' diffuse | **128 is unit brightness**: a light map dims a texture or leaves it, never brightens it |
  | two passes | the option off, or a surface with a macro texture | a second pass after the base, in the modulated blend ([blending](#blending)), which doubles | **64 is unit, 127 doubles the texture** |

  Observed: two passes draw lit surfaces twice as bright as one (1.6 times
  through the frames' gamma of 1.5) and unlit ones alike; `OpenGLDrv` draws
  as one pass.
- **A 3dfx Voodoo3** (known by its device ID in `SetRes`): stage 0 takes the
  texture alone while light-mapping, so the diffuse is not applied twice.

## Textures

How a texture's texels reach the card (`SetTexture`, `0x10008a60`):

- **The format.** `SetRes` looks for A8R8G8B8 when the display is 24 bits or
  more (`0x1000cff4`), and for A1R5G5B5 only when it finds none
  (`RecognizePixelFormat`, `0x10009d60`, keeps a list). So 32-bit textures on
  any display of 24 bits or more, 16-bit ones under that.
  `Use32BitTextures` plays no part.
- **The handlers.** Each texture format has a handler, a setup and a per-mip
  conversion (constructor, `0x10001ee0`): palettized (`TEXF_P8`),
  `TEXF_RGBA7` (light and fog maps), and DXT1 as it is.
- **32-bit.** A palette's colours as they are, alpha whole (`0x10002320`); a
  light map's bytes doubled (`0x10002120`); the stage's modulation colour 1.
  So the colours drawn are the texture's own.
- **16-bit, a palette** (`0x100026b0`):
  - each channel against the texture's `MaxColor` M (at least 1):
    (2^n − 1) / M in fixed point (2^31 for red, 2^26 green, 2^21 blue, the
    quotient made a float and back), times the colour, the top 5 bits, at
    most 31. So the largest colour is 31, and one under 1/32 of M is 0;
  - alpha one bit, set at 128; a masked texture's entry 0 cleared.

  A texture first drawn modulated takes its colours to 5 bits unscaled
  ((c − 1) / 8 for c over 0, alpha set) and is drawn untinted. `MaxColor` is
  the texture's own, saved with it: the editor's
  `UTexture::CreateColorRange` (Engine.dll `0x103ef1c0`) takes each
  channel's largest over the palette entries its mips use, and
  `UTexture::Lock` passes it on.
- **16-bit, a light map** (`0x10002390`): triangular tables that `Init`
  (`0x100029b0`) makes, by a maximum m up to 127 and a value up to it:
  min(31, ⌊32 × value / m⌋). m is half the map's `MaxColor`
  (`FTextureInfo::CacheMaxColor`, Engine.dll `0x103f08f0`: twice each
  channel's largest byte, at least 1). Red's entry is capped for A1R5G5B5
  but masked with R5G6B5's `0xF800`, so red loses its lowest bit.
- **The modulation.** In 16 bits the stage's colour is `MaxColor` over 255,
  multiplied into the vertex colour of every draw that is not modulated. A
  one-pass surface's diffuse is trunc(256 × both stages' colours − 0.5). So
  a texel comes out (q / 31) × M / 255.

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
  draws it as an extra pass in the `PF_Highlighted` blend. The fog's colour
  is added over the scene; what lies behind is dimmed by the fog's alpha. A
  fog map is `TEXF_RGBA7` like a light map, uploaded the same way, a byte c
  worth 2c/255. **A surface with a fog map skips its detail texture**: the
  fog pass takes the detail pass's place.
- **Vertex fog** (`UseVertexFog`, for meshes and sprites): a draw flagged
  `PF_RenderFog` that is neither translucent nor modulated puts the vertex's
  fog colour in the D3D specular channel and turns specular on. So the
  hardware adds the fog after the texture is modulated. The fog values come
  from the renderer's lighting ([meshes](render-dll.md#meshes)).

## Detail textures

The close-up grain on world surfaces, drawn only when `DetailTexture` is on
and the surface has one:

- **Up to three passes**, each a band by view depth. The first covers
  `Z < 380` units at the detail texture's own scale. Each further band
  divides the bound by ~4.22 (380, 90, 21.3) and multiplies the texture
  repeat by 4.223: finer grain the closer the wall.
- **The fade.** Per vertex the detail fades by depth:
  `alpha = (bound/Z - 1) x 100`, clamped to 255, on a mid-grey vertex
  colour. The pass blends the detail texture toward mid-grey by that alpha
  (the driver requires `BLENDDIFFUSEALPHA`) and draws it modulated. So grey
  (zero alpha, the band's far edge) changes nothing, and there is no seam.
  Polygons crossing a bound are clipped at it, with zero alpha on the cut.
- **Z bias.** The pass runs with a Z bias of 15 (reset to 0 after), so the
  detail never fights its own surface's depth.

## The rest of a frame

- **Screen flash** (`EndFlash`), the pain and pickup flashes:
  - with `FlashScale` at 0.5 and `FlashFog` black, nothing is drawn;
  - otherwise one full-screen translucent quad in the fog's colour, its
    alpha `min(2 x FlashScale, 1)`.

  The two values are the game engine's (`Engine.dll`'s `UGameEngine::Draw`,
  `0x1038f110`): the viewport's player's `FlashScale` halved and its
  `FlashFog`, each clamped to 0-1 with a fourth component of 0. They are 0.5
  and black when the client's `ScreenFlashes` is off, unless the level is a
  net game (`NetMode` not standalone). A player's `FlashScale` of 1, its
  resting value, draws nothing.
- **Meshes and sprites** (`DrawGouraudPolygon`): the vertex's light colour
  becomes the diffuse (times the modulation compensation); a modulated draw
  is untinted white. Tiles (`DrawTile`) carry one colour the same way.
