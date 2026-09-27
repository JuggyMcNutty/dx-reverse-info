# Fire.dll

The native half of package Fire: the fractal textures, drawn by the CPU a
step at a time -- fire (`FireTexture`), water lit as a surface
(`WaveTexture`) or bending another texture (`WetTexture`), and ice
(`IceTexture`). Deus Ex's energy weapons, lasers, fires, smoke, gas, water and
screen effects are made of them ([what uses them](#what-deus-ex-uses)). How it
was read: [working on the binaries](README.md#working-on-the-binaries); every
part below was also checked by running the DLL's own routines on test inputs
([checked](#how-it-was-checked)).

## The binary

| Property | Value |
|---|---|
| Size | 106,496 bytes |
| Imagebase | `0x10500000` |
| SHA1 | `97b6180345476d47a4b17768003f18d0ceeb3f53` |
| Source | `D:\prj\Clean\Fire\Src\UnFractal.cpp` |
| Classes | six: `FractalTexture` (216 bytes), `FireTexture` (1,292), `WaterTexture`, `WaveTexture` (4,860), `WetTexture` (4,868), `IceTexture` |

The per-pixel passes are hand-written assembly kept in `.data`, because they
patch their own instructions -- each address and offset a pass needs is
written into it before it runs. There are two copies of each, for the Pentium
Pro and for older CPUs (`GIsPentiumPro`), which compute the same.

## Stepping

A fractal texture moves on only when it is drawn (`Engine.dll`):

- **`UTexture::Update`** (`0x103ecb70`), from whatever locks the texture to
  draw it, calls `Tick` with the time since the texture's own last update
  (`InternalTime`) -- once for each new time, however often it is drawn.
- **`UTexture::Tick`** (`0x103ed0d0`) first runs `PrimeCount` steps, once (it
  counts them in `PrimeCurrent`), so a fire is already burning when first
  seen. Then, with no `MaxFrameRate`, one step each call -- a step a drawn
  frame. With one: the time builds up in `Accumulator`, and once it reaches
  1/`MaxFrameRate` one step goes; the rest is kept, up to 1/`MinFrameRate`
  (the rates held to 0.01 to 100). Never more than one step a call.
- **A step** is the texture's `ConstantTimeTick`. A plain texture's steps an
  animation to its next frame (`AnimCurrent` along the `AnimNext` chain);
  a fractal texture's draws its next image.
- **The pixels** of a fractal texture are not in its package: only its size
  is. On load each mip gets its size's bytes, zeroed (`UTexture::Serialize`,
  `0x103ed470`, for a texture with `bParametric`).

Most of Deus Ex's fractal textures have no `MaxFrameRate`, so the original
steps them once a frame: they run faster at a higher frame rate.

## The shared tables

Built once, by the first fractal texture's constructor (`0x10501020`):

- **A sine** of 256 steps as bytes: 127.5 + 127.5 x sin(i/256 x 2 pi),
  through a float, truncated -- 0 to 255 about the middle. Beside it the same
  raised by 32 (capped at 255) and by 128 (wrapped).
- **The random bytes** every fractal texture draws from in turn: a table of
  64 words from the C runtime's `rand`, and a draw takes the word 32 places
  on from the current one, steps to the next and XORs the taken word into
  it. Every kind below that is random draws its bytes from this, in a fixed
  order.

## Fire

A fire texture is a heat map in palette indices: sparks put heat into it,
then a pass blurs it and cools it, and the palette colours it.

**Loading** (`UFireTexture::PostLoad`, `0x10507b70`): its masks from its
size; its `bMasked` cleared -- a fire is never masked; the colour table
(`RenderTable`, from `RenderHeat` whenever that changed), which turns the sum
of four heats (0 to 1,020) into an index: a quarter of the sum, plus one,
less (255 - `RenderHeat`)/16, held to 0..255 -- so `RenderHeat` is how slowly
the fire cools; and room for `SparksLimit` sparks (held to 4..8,192). The
package holds the sparks placed in the editor, after the empty mips
(`Serialize`, `0x10508300`).

**A step** (`ConstantTimeTick`, `0x10507ff0`), for a texture of 8 by 8 or
more:

1. **The sparks** (`RedrawSparks`, `0x105025b0`) draw, move and spawn, in
   order ([below](#the-sparks)). A spark spawned in the step is drawn in the
   same step; one that ends is replaced by the last one, which then waits
   for the next step.
2. **The pass**: each pixel becomes the colour table's entry for the sum of
   four heats, all read from the image as it was before the pass, wrapping
   at every edge. With `bRising` they are the three pixels below it and the
   one below those -- the fire climbs a row a step; without, the pixel, its
   two neighbours and the one below -- it glows in place.
3. **The stars** (`PostDrawSparks`, `0x10505930`), while there are any: each
   star notes the heat the pass left under it, and relights its spot where
   that is below 38.

### The sparks

Each spark is eight bytes: its kind, a heat, a place (X, Y), and four
parameters (A, B, C, D) whose meaning is the kind's. The editor sets them
from the texture's `FX_` properties as each is placed (`AddSpark`,
`0x10501100`). A "chance" below is a random byte under the given value, of
256.

| Kind | What it does |
|---|---|
| Burn | a random heat at its place |
| Sparkle | its heat at a random spot within A by B of its place |
| Pulse | its heat, which rises by D a step, wrapping |
| Signal | its heat when above C; the heat rises by D, and starts again at random when it passes 255 |
| Blaze | half the time, a spark with a random direction |
| OzHasSpoken | half the time, a rising spark drifting sideways at random |
| Cone | a quarter of the time, a spark thrown sideways that falls ever faster, for C steps |
| BlazeRight, BlazeLeft | a quarter of the time, a spark thrown up to the right, or the left, falling back |
| Cylinder | a point swinging across by B about its place as A turns by D, brighter in front |
| Cylinder3D | the same, only while in front |
| Lissajous | a point on a Lissajous curve of size Heat, A and B turning by C and D |
| Jugglers | a point swinging up and down by B as A turns by D, brighter in front |
| Emit | a quarter of the time, a spark with its own speed (A, B), cooling by D |
| Fountain | a quarter of the time, a spark thrown up that falls back |
| Flocks | a bird circling as it goes, near its place, which wanders |
| Eels | now and then (a chance of 20), a spark with a random direction nearby; its place wanders |
| Organic | half the time, a wisp within C of it that rises 2 rows a step, fading |
| WanderOrganic | the same each step, near its wandering place |
| RandomCloud | a puff rising 2 rows a step, brightening; its place wanders |
| CustomCloud | a puff with its own drift (A, B), brightening; its place wanders |
| LocalCloud | the same within C of it, its place still |
| Stars | a star at its place, which relights dark spots (above) |
| LineLightning | a bolt along its line (A, B) for C steps, then off until a chance over D restarts it |
| RampLightning | the same, fading along its length |
| SphereLightning | now and then (a chance over D), a bolt to a random point within C, fading |
| Wheel | a spark circling as it goes, let go as its angle turns |
| Gametes | now and then, a swimmer that sways about a heading; its place wanders |
| Sprinkler | a spark thrown out as its angle turns by D |

What the kinds let go are sparks of their own kinds, 32 to 43, which draw
their heat where they are and move a pixel at a time -- a pixel sideways
with a chance of its speed over 128, and likewise up or down --, cooling,
fading or counting down until they end. The runtime kinds are dropped when a
texture is saved.

**Lightning** (`DrawFlashRamp`, `0x105022f0`) draws a line given as its start
and its lengths along X and Y, each length's lowest bit its sign. It goes a
pixel at a time along the longer axis; across, it moves by the straight
line's step plus a random byte less their mean, in 64ths of a pixel -- so it
jags but ends where it should. The heat runs evenly from one end's to the
other's.

## Water

A water texture keeps its water at half its size each way, as two height
fields side by side in each row (`SourceFields`, allocated at load, all 128:
flat), the second field's cells sitting diagonally between the first's.

**A step** (`WaterRedrawDrops`, `0x10506410`, then `CalculateWater`,
`0x105059c0`):

1. **The drops** set heights in both fields, so the water moves from there.
2. **The water**: every other step the first field moves, else the second
   (`WaterParity`). A moving cell becomes the water table's entry for the sum
   of its four neighbours in the other field less twice its own height: half
   that, floored, held to 0..255 (`WaterTable`, built by the constructor) --
   the wave equation, 128 at rest.
3. **The pixels**: each cell's four pixels (half a cell over, on the steps
   of the second field) get the render table's entry, 512 on, for the other
   field's slope across there: its height two cells on less its own, summed
   over the pixels' neighbours and, for the row between, averaged with the
   row beyond. Only the slope along X is used.

**The drops** (eight bytes each, like sparks):

| Kind | What it does |
|---|---|
| FixedDepth | a height held at D |
| PhaseSpot, ShallowSpot | a height rising and falling with the sine (the shallow one half as far), its phase stepping by D |
| HalfAmpl | the same, its lower half cut off |
| RandomMover | a push where it is, then a step of up to 3 cells at random |
| FixedRandomSpot | random heights |
| WhirlyThing, BigWhirly | a spot circling, 16 or 32 cells across, its 16-bit angle turning by C and D (either way) |
| HorizontalLine, VerticalLine, DiagonalLine1, DiagonalLine2 | a line of D/2+1 cells held at its depth |
| HorizontalOsc and the other three | the same line, rising and falling with the sine |
| RainDrops | in one step of 16, a drop at random within D of it |
| AreaClamp | a square of D/2 cells held at its depth: a dry or shallow patch |
| LeakyTap | a drop each time A, rising by D, passes 255 |
| DrippyTap | the same, A starting again at random |

**`WaveTexture`**: the render table lights the slope (`SetWaveLight`,
`0x105091a0`): the slope becomes a tilt short of a right angle, lit by
`BumpMapLight` as a cosine, with a highlight of size `PhongSize` and
strength `PhongRange` where it faces `BumpMapAngle`. Its palette is its own.

**`WetTexture`**: the water bends `SourceTexture`. The render table turns a
slope into a sideways shift of up to 127 pixels either way, scaled by
`WaveAmp` (`SetRefractionTable`, `0x10509910`), and after the water each
pixel takes the source's pixel along its row by the shift found there
(`ApplyWetTexture`, `0x10505a10`). On load (`PostLoad`, `0x10509590`) the
source is used as it is when it is the same size, scaled up into a copy when
smaller, and dropped when larger; and the wet texture takes the source's
palette. A source that is itself animated is stepped with it.

## Ice

An ice texture shows `SourceTexture` through `GlassTexture`: each pixel takes
a pixel along the row of one by the other's value there. With `MoveIce` the
glass moves over a still source; without, the source moves under a still
glass (`BlitTexIce`, `0x10505e60`; `BlitIceTex`, `0x105061e0`). The panning
(`MoveIcePosition`, `0x10505b10`) goes by `HorizPanSpeed` and `VertPanSpeed`
(offset by 128), along a line, a circle, a wobbling circle, or waving along
X or Y by `Amplitude` and `Frequency`; it is redrawn only when the position
moves a whole pixel. `TIME_RealTimeScroll` pans by the time between the
frames that draw it; `TIME_FrameRateSync` by 1/120 s a step, stepped as any
texture. A source or glass not of the texture's size leaves a scaled-up copy
of the source, still. No Deus Ex texture is ice.

## What Deus Ex uses

49 fractal textures -- 45 in `Effects.utx`, 3 in `BobPage.utx`, 1 in
`OceanLab.utx`: 40 fires, 8 wet and 1 wave texture (`water.waterfntn_a`). The wet ones are the Dragon's Tooth
blade (`Electricity.WavyBlade`, over `Electricity.Blade`), tear and poison gas,
the drunk effect (`UserInterface.DrunkFX`, `DrunkBoy`), the EMP grenade's
blast, and two waters. The fires use every spark kind but Pulse, Cylinder3D,
Lissajous, Eels, Stars and Sprinkler; the Dragon's Tooth, for one, carries a
Gametes fire and a Cone fire with SphereLightning bolts on its blade, beside
the wet texture.

## How it was checked

The DLL's own routines were run in a CPU emulator (Unicorn, from a Python
script in the session's scratch space, never committed), on objects laid
out as the class layouts give, against the reimplementation in
[VibeEngine](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/NATIVES.md#fire-water-and-ice-textures)
with the same random table: every spark kind and runtime kind over up to 60
steps, and every drop kind over up to 30, in several sizes, ended with the
same pixels, sparks or fields and random table, byte for byte. The wet
shift and refraction table matched exactly; the wave lighting table matched
but for a step of one at a single entry in 3 of 200 settings, where the
x87's cosine and the C library's differ in the last bit.

## The database

`gamefiles/System/Fire.dll.i64` has the class layouts, the UTF-16 strings and
the initializers' names ([working on the binaries](README.md#working-on-the-binaries)),
and by hand the shared tables' names (`GFireSinTable`, `GFireSinTablePlus32`,
`GFireSinTablePlus128`, `GFireRandTable`, `GFireRandIndex`) and
`FireInitTables`.
