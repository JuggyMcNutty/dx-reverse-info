# Galaxy.dll

The native half of package Galaxy: the game's audio subsystem,
`UGalaxyAudioSubsystem`. It is Epic's driver (`UnGalaxy.cpp`) with Ion
Storm's additions (a speech volume, volumes changed at once, lip sync,
stopping a sound by its ID), over Carlo Vogelsang's Galaxy sound library
(revision 5.00, compiled February 2000), linked in: its mixer, its player for
tracker music, its reverb, DirectSound or WinMM output, and A3D and EAX
hardware. The library's own structures and function prototypes are in the
SDK's `GALAXY.H` (whose licence keeps them out of this repository). Read with:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 360,448 bytes |
| Imagebase | `0x10600000` |
| SHA1 | `4d2599d1faa2d57742ee466d6694568d31950b40` |
| Exports | 43; no natives |
| Functions | 538 |

It registers one class, `GalaxyAudioSubsystem` (0x904 bytes, C++ only), the
`AudioDevice` of `DeusEx.ini`. Its exports are the engine's audio interface
(`Engine/Inc/UnAudio.h` in the SDK) and five helpers of its own: `GetSound`,
`StopSound`, `SetVolumes`, `SoundPriority` and `IsObstructed`. The last two
are also written out inline where they are used.

Its fields:

| Offset | Field |
|---|---|
| 0x2c–0x6b | the settings ([below](#settings)) |
| 0x6c, 0x70 | the ASTAT flags |
| 0x74, 0x78 | whether 3D hardware, and A3D 2.0, are in use |
| 0x7c | the viewport |
| 0x80 | 32 channel records of 0x40 bytes, of which `EffectsChannels` are used |
| 0x880 | the time of the last update |
| 0x888, 0x88c, 0x88d | the music, its CD track, its section |
| 0x88e | the reverb last set |
| 0x8fc | the next free sound ID |
| 0x900 | the music's fade |

A channel's record holds Galaxy's voice, the actor, the sound's ID, whether
it plays in 3D, the sound, its place, volume, radius, pitch and priority, the
time it has played, when its lip sync is next worked out, the sample's mean
(worked out once, then unused), and its obstruction
([sounds behind walls](#sounds-behind-walls)).

## Settings

`[Galaxy.GalaxyAudioSubsystem]` in `DeusEx.ini`; the defaults are the game's
`Default.ini`'s. The class sets none of its own (its `StaticConstructor`,
`0x10604bb0`, and constructor, `0x10604a20`), so a key the ini lacks is 0,
False or the first name: no voices, every volume 0, `OutputRate` 8000Hz.

| Setting | Default | What it does |
|---|---|---|
| `UseDirectSound` | True | DirectSound output, else WinMM (as `-nodsound` gives) |
| `UseFilter` | True | asks the mixer to interpolate a sound resampled up; its SSE routine interpolates linearly either way ([the mixer](#the-mixer)) |
| `UseStereo` | True | stereo output, else mono, mixed by the plain routine ([the mixer](#the-mixer)) |
| `UseSurround` | False | a sound behind the listener plays centred, its right side inverted |
| `ReverseStereo` | False | left and right swapped |
| `UseDigitalMusic`, `UseCDMusic` | True, False | the level's tracker music; CD audio |
| `UseReverb` | True | each zone's reverb ([reverb](#reverb)) |
| `Use3dHardware` | False | A3D or EAX hardware, when found and `-no3dsound` is not given |
| `LowSoundQuality` | False | read by the engine as each sound loads ([low sound quality](engine-dll.md#sounds)) |
| `Latency` | 40 | the output's mix-ahead in milliseconds, held to 5–495 by the output library at a load (`glxStartOutput`, `0x10613350`) |
| `OutputRate` | 44100Hz | the mixing rate, one of seven names, 8000Hz to 48000Hz, any other text keeping the rate it had (a byte enum, its `StaticConstructor` `0x10604be0`); `SetViewport` takes it from a table of seven unchecked (`0x10605e1e`-`0x10605e52`); the reverb's delays are whole samples of it |
| `EffectsChannels` | 16 | the voices for sounds, 0 to 32; a change applies at once (below) |
| `MusicVolume`, `SoundVolume`, `SpeechVolume` | 153, 204, 255 | the Sound options' sliders |
| `AmbientFactor` | 0.7 | the scale of ambient sounds' volume |
| `DopplerSpeed` | 6,500 | the speed of sound for Doppler, in units a second |

`UseSpatial`, also in `DeusEx.ini` (the original launcher writes it), is not
a setting of this class, and nothing in the game reads it.

A `SET` (the Sound menu's) ends in `PostEditChange` (`0x10605ad0`), which
holds the subsystem's own copy, not the class default that `GET` reads:
`OutputRate` to 48,000 Hz at most, `Latency` to 10–250, `EffectsChannels` to
0–32, `DopplerSpeed` to 1–100,000 and `AmbientFactor` to 0–10; then the
volumes are set again.

`EffectsChannels` is handed to Galaxy once, by `Init`: that many voices for
sounds, the music's voices after them. Every loop over the channels (a new
sound's choice of one, `Update`, `SetViewport`, `StopSoundId`, `NoteDestroy`,
the `ASTAT` display) reads the setting as it stands, so a change applies at
once. Lowered, a sound on a channel past it plays on, out of the driver's
reach. Raised, the channels past the start's count play on the voices after
it, the music's: channel n starts its sound on voice n + 1.

## Playing a sound

- **`PlaySound(Actor, Id, Sound, Location, Volume, Radius, Pitch)`**
  (`0x10608100`) only queues the sound; the next update starts it. With no
  viewport or no sound it plays nothing; a radius of 0 fails an assertion. A
  sound with no slot gets an ID of its own, counting down in steps of 16 from
  −16. The ID packs the slot ([`Engine.dll`](engine-dll.md#sounds)).
- **Its priority** (`SoundPriority`, `0x10604460`) is (1 − distance ÷
  radius) × volume, the distance from the player's view target (or the
  player). It is worked out as the sound starts and again each frame.
- **Which sound wins.** The new sound takes the channel that plays the same
  actor's same slot, unless it has `bNoOverride`: then it is dropped.
  Otherwise it takes the channel of the lowest priority, if that is no higher
  than its own (on a tie, the last such channel). What played there stops at
  once. So a sound beyond its radius, whose priority is below 0, is dropped
  even when a channel is free.
- **An MP3 plays 8 KB of silence first**, 4,096 frames of its 16-bit
  samples (92.9 ms at 44,100 Hz): a compressed sample's voice plays a ring of
  64 KB, 32,768 frames, zeroed as it starts (`0x10612310`), that its decoder
  fills as it plays (`0x1060e340`), the first fill from 8 KB past the voice's
  place (`0x1060e4c9`). Measured: a mission 1 line starts 4,083 to 4,096
  frames after a beep (a WAV) started on the same tick, 4,607 once as a run's
  first: the voice's place at the decoder's first call, 0 or a mixer call's
  512 frames ([the mixer](#the-mixer)).
- **The ring's fill.** The mixer hands the decoder thread each compressed
  voice's place at each tick of its music (`PostThreadMessageA` 0x400,
  `0x106151f5`), before it mixes the frames up to the tick. The decoder fills
  the ring on from where it filled it to as far as the voice's place, at most
  32 KB a call, so the ring is held full.
- **The ring's end.** Once the sample's data has run out, the rest of a
  call's fill is zeros, and the voice's end is set at the fill's place before
  them only while the voice's place lies before it in the ring. When the
  fill has wrapped past the ring's end and the voice has not, a later call
  sets it, past the zeros, at the fill's place then: a whole ring ahead of the
  voice's place at the call before it. So a voice whose data, the 4,096
  frames of silence counted, ends within the first fill, 20,480 frames, plays
  to that fill's end, its end set again at the next call; one whose data ends
  within the ring's first turn, 32,768 frames, ends with its data; and a
  longer one plays on, silent, with its lip sync, to within a tick of the
  ring's turn after its data's end, unless its place turned the ring in the
  tick whose call ran out of data.
- **A stereo sample** plays as two voices, its channel's and the next
  channel's (`0x10612310`, which `Update` calls with the channel + 1), the
  first its left side and the second its right, linked: a stop of the first
  stops the second (`0x10618410`), whatever the game has since started on
  that channel. A stereo sample plays from rings, as a compressed one does,
  a WAV's two rings filled from its data by the same call that would decode
  (`0x10619800`); an 8-bit one's ring holds 65,536 frames, but the voice's
  loop turns at 32,767 as a 16-bit one's. Measured, with the stock stereo line
  `ConAudioMission01_450`: the voice starts 4,107 and 4,608 frames after a
  beep, as a mono MP3's, and a stereo WAV of 16-bit samples at 22,050 Hz
  8,192 output frames after, its 4,096; each then plays its ring's first
  32,768 frames over and over, the ring never filled again, with its lip
  sync, until a sound on its slot stops it; a beep the speaker played with
  each later line went unheard, and at its exit the game crashed unloading a
  sound (`glxUnloadSample`), every run that played a stereo one.
- **`StopSoundId(Id)`** (`0x10607ef0`) stops the channel with that ID
  (`Actor.StopSound`, [`Engine.dll`](engine-dll.md#sounds)).
- **`NoteDestroy(Actor)`** (`0x106083a0`), when an actor goes: its ambient
  sound stops, and its other sounds play on where they are, without it.
- **`SetViewport`** (`0x10605c40`) stops every channel's sound. Given the
  viewport it already has, it does nothing more: the music plays on, mixed by
  the output's timer ([the mixer](#the-mixer)), so it plays through a map's
  load, which calls it so before and after
  ([the loading screen](engine-dll.md#the-loading-screen)). For a new viewport
  it restarts the output with the settings and registers every sound loaded.
- **`RegisterSound`** (`0x10606af0`) hands a sound's data to Galaxy and
  unloads it; data Galaxy cannot read is a fatal error.

## Each frame

`Update` (`0x10609510`) works on its own time step (0 to 1 s), in this order.

- **Ambient sounds start.** While the view is live and the game is not
  paused, every actor of the level is read, each frame. One with an
  `AmbientSound`, within its radius (25 × (`SoundRadius` + 1)) of the view
  target, and not already on a channel, is played in the ambient slot at
  `AmbientFactor` × `SoundVolume` ÷ 255, with pitch `SoundPitch` ÷ 64.
- **Ambient sounds update.** One out of radius, whose actor's sound changed,
  or with the view not live, stops. The rest take their actor's radius and
  pitch again, and twice the starting volume. **An actor with a light** has
  its sound follow the light: the volume × `LightBrightness` ÷ 255 × the
  light's pulse or flicker at the moment (the renderer's `GlobalLighting`,
  1 for a steady light), then at most 1. This comes before the frame's
  `PreRender`: a flicker takes the frame before's draws, and a strobe's
  switch, turned over here first, holds for the frame's picture. The x87
  is then at the precision the frame before's `PostRender` left it, 64 bits
  (read, not measured), so a blink's count here keeps its last bit past
  2^24, where the picture's is even.
- **Every channel,** unless its voice has finished (then it is cleared):
  - its place becomes its actor's, and its priority is worked out again;
  - its **fall-off** is 1 − distance ÷ radius from the listener (the view's
    own place, the coordinates `Update` is handed): linear, 0 at the radius,
    where the voice plays at its [floor](#volume);
  - its **pan** is the sound's angle from straight ahead, left or right,
    front and back alike, as Galaxy's pan of 0 (left) to 32,767 (right):
    - angle = atan2(distance to the right, |distance ahead|), in the view's
      axes;
    - for a sound within a tenth of the radius, the angle × distance ÷
      (radius ÷ 10);
    - pan = 16,383 + angle × 28,671.125 ÷ π, at most seven-eighths of the way
      to one side;
    - `ReverseStereo` swaps it. With `UseSurround`, a sound behind gets
      49,152, the surround pan. The mixer makes it the sides' gains
      ([the mixer](#the-mixer)).
    - Measured: a beep 234 units off, its radius 4,000, 90° to the right
      (its angle scaled to 0.585 of 90°) plays the left channel 5.1 dB under
      the right. Straight ahead, each channel is 1.8 dB under the right one's
      at the side: the two channels' power together is the same both ways,
      as the gains give.
  - its [obstruction](#sounds-behind-walls), then its [volume](#volume);
  - **Doppler,** for an ambient sound only: a factor on the pitch of 1 − the
    actor's speed away from the view target ÷ `DopplerSpeed`, kept to 0.5–2;
  - a voice is started for a new sound, at the sample's rate × pitch ×
    Doppler: through 3D hardware if in use, else Galaxy's mixer. A playing
    one gets its rate, volume and pan again. [Lip sync](#lip-sync) is worked
    out here.
- **Then the music** ([music](#music)) and **the reverb** ([reverb](#reverb)).

### Sounds behind walls

Each channel keeps an obstruction time:

- A line runs from the sound's actor to the player's eyes (the player's own
  place and `EyeHeight`, even when viewing through another actor): the
  check's start the actor's place, its end the eyes
  (`0x10609cb9`-`0x10609da3`), however short, so a sound at the eyes of a
  player inside solid is muffled ([traces](engine-dll.md#traces): a line of
  no length in solid is blocked). Run (DXEngine's `SolidSoundConsole`): a
  fan at the eyes 10 dB down in the solid under Liberty Island's pier.
- When it meets the level's BSP (`UModel::FastLineCheck`, `Engine.dll`
  `0x103f3280`, `FastTrace`'s test), the time grows by the time step, up to
  0.5 s. When clear, it shrinks back to 0. The BSP holds the movers' polygons
  ([traces](engine-dll.md#traces)), so a closed door muffles; no other actor
  does.
- The channel plays at 1 − 2 × that time, at least 0.33: a sound behind a
  wall falls to a third of its volume over a third of a second, the time
  running on to 0.5 s, and rises again once it clears and the time is back
  under a third of a second.
- Speech and a sound whose actor has gone run no line: their time only
  shrinks. So speech is never muffled.

`IsObstructed` (`0x10607fc0`) is the same test as a function.

### Volume

A voice's volume is the sound's volume × its fall-off × its obstruction × the
balance of the sliders, at most full (32,767) and at least 1/256 of it: 128,
put on after the cap (`0x10609ee3`), whatever the factors, on every voice
`Update` starts or updates, the 3D hardware's too. So a sound that leaves its
radius as it plays (an ambient sound stops there instead), one played at a
volume of 0 -- a window's at its unset volume among them
([window sounds](extension-dll.md#window-sounds)) -- and one whose own slider
is at 0 while the other is not play on at 1/256, never silent. Only both
sliders at 0 silence a voice, through the mixer's sample volume (below). The
music has no floor.

- **The sliders.** Galaxy's sample volume is 127 × the louder of
  `SoundVolume` and `SpeechVolume`, each over 255 (`SetVolumes`,
  `0x106061b0`), which the mixer squares ([the mixer](#the-mixer)).
  - Speech (a sound in the talk slot) is scaled by speech slider ÷ sound
    slider when the sound slider is the louder; the other sounds the other
    way round.
  - So each plays at its own slider × the louder one. At the game's 204 and
    255: the other sounds at 0.8 and speech at 1, times the mixer's 0.97.
  - When the two are equal, both are scaled by the slider a second time: at
    half each, everything plays at about an eighth.
- **Instantly.** `SetInstantSoundVolume`, `SetInstantSpeechVolume` and
  `SetInstantMusicVolume` (`0x106063d0`, `0x106064f0`, `0x10606610`) set the
  slider and the volumes at once, for the menu's sliders as they move.

### The mixer

The library's own (`0x10614920`), run every `Latency` ÷ 2 by the output's
timer:

1. The voices are mixed at `OutputRate` into a dry and a reverb buffer, at
   most 512 frames a call, in blocks that end at each tick. Their gains are
   worked out again every millisecond from what `Update` last set, or with a
   module playing at each of its ticks.
2. The reverb runs over its buffer into the dry one.
3. The result is saturated to 16 bits and added, saturating, to the music's
   (`0x106146a0`). The music's voices, summed apart, are written into the
   output's buffer, a second long (`0x10613943`), saturated to 16 bits where
   its play cursor has reached, and the sounds' mix is added at the write
   cursor plus `Latency` (DirectSound's, `0x106142a0`): the music is heard
   a turn of the buffer after the sounds mixed with it, less their lead,
   some 0.93 s.

- **A voice's gains:** the voice's volume × the sample volume squared × each
  side's share of the pan.
  - The sample volume squared: twice (127 × the louder slider)², over 32,768.
    With the voice's own full volume of 32,258, that is 0.969 with a slider
    full.
  - Each side's share: √(pan ÷ 32,767) for the right, √ of the rest for the
    left, from a table of 32,768 (`glxInit`, `0x1060df30`). Centred, each
    side is 0.707 of the voice; at the most, seven-eighths over, 0.968 and
    0.250.
  - The reverb gets each side at 127/128 of it. The surround pan plays
    centred with the right side's gains negated.
  - The pan moves to the one last set by at most 512 of 32,767 each time
    the gains are worked out (`0x10615329`). A song's pan commands and its
    order 0 set both at once (`0x106177aa`, `0x106159aa`), so its pans
    change at once; whether a sound's update sets only the pan it moves to
    is unread.
- **Mono output** (`UseStereo` off) mixes every voice, the music's too,
  with the plain routine (`0x10623210`, copied in by `0x1062414f`), the
  SSE, MMX and 3DNow! ones taken only for stereo output (`0x10614080`):
  - one gain, the mean of the two sides' (above), rounded down to one of 64
    levels, 16 × v² with v the whole square root of their sum over 16 (the
    table at `0x1064d338`): a voice whose sides sum to under 16 of 32,767
    is silent, and the rest lose up to 9.5 dB at the lowest levels, 0.3 dB
    near full;
  - a surround voice's right side added, not negated, the sounds' voices' too;
  - a 16-bit sample read at its whole frame, never interpolated, an 8-bit
    one through the cosine table when `UseFilter` asks and the voice steps
    under a frame;
  - nothing sent to the reverb, so the zone's reverb is silent;
  - the music's mix written out with its high byte saturated and its low
    byte as it falls, and the sounds' 32-bit mix added to it and saturated
    so, once (`0x10623eed`).
- **Resampling.** A voice steps through its sample at its rate × pitch in
  whole hertz, as a 16.16 fraction of `OutputRate`. The routine chosen for a
  CPU with SSE and stereo output, which is any modern one (`0x10622730`,
  copied in by `0x106231d1`), interpolates linearly between a sample and the
  next, with 15-bit weights, whatever `UseFilter` asks. The cosine table of
  16 steps at `0x1063da5c` is built for the other routines' 8-bit samples.
- **The tick** is the music's (`0x10615710`): with a module playing, every
  5/2 of `OutputRate` over its tempo, 50 a second at 125; with none, at 120
  beats of 48 ticks a minute (its reset, `0x1060e850`), 96 a second.
- **A WAV's data** is loaded as it is (`0x10619d20`; from a file,
  `0x10619940`), but 8-bit samples, each made signed (+0x80).
- **Loops** come from a WAV's `smpl` chunk: its first loop's start and end,
  and only from a chunk after the data chunk, where the loader sets the sample
  up afresh, an earlier loop lost. Measured: a sound so made plays once.
- **A voice's limit.** The mixer mixes a voice in blocks up to its limit --
  the loop's end, a stopping one its data's end --, a frame that falls on the
  limit too, then acts on the place past it (`0x10614920`): a loop goes back
  by its length, as often as a step longer than the loop needs, keeping the
  fraction; a voice past its data's end stops, the frame at the end reading
  the zeros the loader puts after the data. A compressed voice's ring loops
  from its first frame to its last, 32,767, so each turn after the first
  passes over the ring's first frame.
- **The ping-pong type** (the loop's type 1) turns the voice where it is at
  the loop's end, swapping the loop's ends and negating the step, and turns
  it again at the start, mirrored about it (`0x10614920`). Measured: the game
  crashes at the first turn, the sound played to its loop's end; its process
  is gone, with nothing logged.

## Lip sync

The mouths in conversations. `Update` (`0x1060a09a`) works out a channel's
mouth shape when it is speech (the talk slot) from a pawn whose script has
set `bIsSpeaking`, its voice playing, and its time played has reached the
next shape's time: the first at once, at the update after the voice starts,
the next a tenth of a second on each time one is worked out, so one held back
(`bIsSpeaking` set late) works one out an update until it catches up. It
writes it to the pawn's `nextPhoneme`, which the script's `LipSynch`
animates.

- **What it hears** (`0x10609180`): 1,024 frames, each sample over 32,768
  times its place over 1,024, the rising half of a triangle. For a
  compressed sample (Deus Ex's speech is MP3), the voice's ring
  ([playing a sound](#playing-a-sound)) from where the voice plays, cut at
  the ring's end; for another, the sample from 0.1 s past the time played,
  cut at its end. An 8-bit sample is read from its start, wherever it plays,
  its bytes two to a slot, the second kept: its first 1,024 bytes fill the
  input's first 512 slots, each 0 where the place read from and the byte
  pass the data's end, and the other 512 keep what the read before left, the
  input being one buffer for every voice (`0x1067588c`), which the FFT copies
  out and leaves.
- **The spectrum** (`0x10609310`): a 1,024-point FFT, of whose bins only the
  size of the real part is kept.
- **The shape** (`0x10608d70`), from the largest of the first 512 bins, DC's
  among them, the first of equals: `X` (mouth closed) at 5 or less;
  otherwise, at its frequency (the bin × the sample's rate ÷ 1,024), `T`
  above 2,000 Hz, `F` above 1,500, `A` above 600, `O` above 400, `U` above
  250, and `E` at 250 Hz or below.
- `M` never comes: its test (above 1,000 Hz) sits inside the branch for
  250 Hz or below. A second test, of the loudness below 300 Hz (the bins to
  300 Hz averaged, plus 1, above 0.2), always passes.
- Measured on three of mission 1's lines: the shapes the game wrote, worked
  out again from each line's samples with the window 4,096 frames behind
  the time played (the MP3's silence first), are 27 of 30, 5 of 6 and 24 of
  30 alike, one after another.

## Music

- **Changing the music.** When the player's `Transition` is set, the music
  playing fades out, the fade falling by the time step to 0 over 1 s for
  `MTRAN_Fade` (× 0.2: 5 s for `MTRAN_SlowFade`; × 3: 1/3 s for
  `MTRAN_FastFade`), at once for the others, then silent for twice `Latency`
  (`Update`, `0x10609510`): the change comes at the first update the fade
  has fallen past −2 × `Latency` ÷ 1,000 times its pace, so the hold is
  twice `Latency` whatever the fade, the transition read
  again at each, so one changed mid-way goes on from the fade as it stands.
  With nothing playing, or section 255, the change is at once. Then the
  player's `Song` starts at full volume at the order `SongSection` (a
  different song is loaded first; the same one only jumps, after the same
  fade, a section of its own too), with CD audio too if `UseCDMusic`.
  Section 255 is silence: the music stops.
- **The change is one step.** `Update` holds Galaxy's lock from its start to
  its end, and the output's timer takes it to mix (`0x106142a0`): the full
  volume is set and the song changed in it -- the old one unloaded, the new
  one loaded, the music stopped, its voices cleared, started again and set
  to the order before `SongSection` (`glxControlMusic`, `0x1060d0e0`), its
  next step `SongSection` -- so no mixed sound has the old song at the new
  volume.
- **A song's start.** Its load leaves every music voice centred and the
  sequencer's speed at its reset's 48 ticks a row (`0x1060e850`); the song's
  own speed and tempo and its channels' pans are set only as the
  sequencer's order count turns from 255 to order 0 (`0x10615710`), so a
  song loaded straight into another order plays centred, and slowly, until
  it reaches order 0 or a speed command (DXEngine's `MusicConsole`: its pair
  of a hard left and a hard right tone, so loaded, both centred, 0 dB apart
  in each channel; after order 0, the right tone 21 dB under in the left).
- **A song that will not load** is a line in the log, Galaxy's `%s failed:
  %i` with the call and its code, `glxLoadMusic(&Mem, GLX_LOADFROMMEMORY )
  failed: <code>` (`0x1060a77e`-`0x1060a7a2`, event `0x2ff`), and the change
  goes on, no song playing. Its loaders know their formats by the data's
  signature, the tracker formats and MIDI (`0x10618be0`); data none of them
  takes, an Ogg, MP3 or WAV song among it, falls to the MOD loader, the
  last, which fails with 15, finding no MOD signature at byte 1,080
  (`0x106252f0`).
- **Where it is.** While no transition is waiting, each frame writes the
  order playing back into the player's `SongSection`. Deus Ex's dynamic music
  keeps it to "save our place in the ambient track"
  (`DeusExPlayer.UpdateDynamicMusic`): combat and conversation music come in
  with `MTRAN_FastFade` and `MTRAN_Fade`, and the ambient music comes back
  where it was (after a fight, 5 s later and with `MTRAN_SlowFade`).
- **The sliders.** Music plays at 127 × the fade, never below 0, ×
  `MusicVolume` ÷ 255, cut to a whole number (`SetVolumes`, `0x106061b0`),
  which the mixer squares, 2v² ÷ 32,768 (`0x106152df`-`0x10615327`), times
  a music voice's own volume: twice its own byte squared (`0x10617f50`), the
  100 of 127 a song's load leaves it at (`0x1060e850`), 20,000 where a
  sound's is 32,258; with five more full-scale factors, 0.601 of full at
  255, 0.215 at the default 153 (8.9 dB under) and 0.036 at 64 (24.5 dB). The
  setting is read when `SetVolumes` runs: each update while a transition
  fades or holds, at its change, at a `SET` (`PostEditChange`) and a new
  viewport; the Sound menu's slider sets the music at once, without the fade
  (`SetInstantMusicVolume`). A song's own volumes play no part
  ([an IT song](#music), below). A channel's pan is twice the header's, at
  most 127 of 128, so a hard right one leaks 21 dB under into the left; the
  channels pan by a square-root table (`0x106153d4`). The zone reverb is the sounds' alone:
  the music's own send goes to a reverb that only a song file's reverb
  chunk sets (`0x1060f3c0`), which the game's IT songs have none of.
- **A song's voices.** A music voice's gain is the music volume's square,
  times its own 20,000 and five more factors of 32,767 at most (its note's
  volume, its volume envelope, its fade-out and two at full), each step over
  32,768, then each side's share of the pan from the square-root table
  (`0x10614920`): at a full slider and a full note 0.601 of full scale, a
  centred channel 0.425 a side; at the default 153, 0.215 and 0.152. The
  music's voices are summed apart from the sounds' and saturated to 16 bits
  before the sounds are added (`0x106146a0`).
- **An IT song** (`0x10628990`) is converted as it loads into the commands of
  Galaxy's own player (`0x10616eb0`), which plays only what the loader keeps:
  - **The header:** its global volume, which `Update`'s `SetVolumes` replaces
    with the slider's at once after the load (`0x1060a810`), its initial
    speed and tempo, its linear-slides flag and its channels' pans, a pan
    over 64 (IT's surround, or a muted channel) a surround a quarter to the
    left (`0x10628bcc`; left 0.866, right 0.5 inverted), the channel played;
    none of the game's songs plays a channel its header pans so. Never its
    mix volume, separation or channels' volumes. Only the first 32 channels
    play (`0x1062a26e`).
  - **A sample:** its volume, default pan, loop, ping-pong, 16-bit and signed
    flags, length and rate. Never its global volume, sustain loop, vibrato or
    stereo flag, nor whether its data is flagged present: a length is
    enough. **An instrument:** its keyboard's samples (not its notes), its
    fade-out and three envelopes of 10 nodes at most, a sustain loop a
    sustain point (the volume envelope's at the loop's start, the pan and
    pitch envelopes' at its end), the pitch envelope's sustain flag the pan
    envelope's; never its global volume, default pan, new note action,
    random variations, pitch-pan separation or filter, a filter envelope
    played as a pitch envelope.
  - **The orders** to the first end mark, at most 255, those after it out
    of reach of a section (`0x10628c04`-`0x10628c20`). An order whose pattern
    holds no data is passed over, the player going on to the next
    (`0x10615710`).
  - **The patterns,** each once, the first time the order list reaches it, the
    decoder's state of each channel carried on from the pattern converted
    before. A note cut is a volume of 0, the note playing on. The volume
    column's volumes alone are kept, doubled to 127 at most (`0x10629ca7`),
    none of its other commands.
  - **One effect memory** a channel for every command: each command stores its
    parameter there (`0x10629d63`) but A, D, E, F, K and L, which take a
    parameter of 0 from it and store theirs (`0x10629e36`-`0x1062a08c`). So a
    D00 slides by whatever any command on the channel gave last: after an
    S86, down by 6 a tick; after a GF0, up by 15.
  - **The commands** (`0x10629e0d`): A a speed of 32 at most; B; C, its row
    read as decimal digits; D, both digits set sliding down by the second, D0F
    and DF0 on every tick but the first; E and F, their extra-fine slides made
    fine, by (x + 2) / 4; G, H, J, K, L, O and R; Q, without its volume
    change, Q00 retriggering nothing; S3x, S4x, SBx, SDx and SEx; S8x a pan of
    (x × 2,048 + 1,024) ÷ 32,767; any S9x the 8xx's 0xA4, a surround; SCx a
    note's volume to 0 a tick later than IT's; T over 0x20 the tempo, T20 a
    speed of 32 (the player's speed command takes up to 0x20 for a speed),
    T0x and T1x kept as a command the player takes for a vibrato; X as the
    MOD's 8xx, its parameter as it is. S0x, S1x and SFx are kept and ignored
    by the player; I, M, N, P, U, V, W, Y, Z, S2x, S5x, S6x, S7x and SAx are
    dropped (`0x1062a180`). The player's 8xx (`0x10616eb0`, its command 8)
    sets a pan to 0x80, left to right, 0x80 at 127 of 128, and over it a
    surround, its right side inverted: 0x84 to 0xC4 at a pan of twice the
    step past 0x84 from the left, 0xA4 the middle and 0xC4 127 of 128, the
    others in the middle. The game's songs use XA4 and S91 alone.
  - **Its player** steps a voice's gains at each tick, unramped, and reads a
    sample between one frame and the next linearly ([the mixer](#the-mixer)).
    Entering the first order, the order count turning from 255 to 0 -- the
    song's start, a jump to order 0 by B00 or a section, a pattern loop back
    in it (SBx steps the count back, `0x10617a37`), the song's loop, an
    empty order 0 passed over too -- sets the speed, tempo and every
    channel's pan to the header's again (`0x10615710`); a song started at
    another section keeps the reset's speed, 48 ticks a row, and the tick
    the music last had, until its patterns set theirs. A section change
    silences the music's voices at once and flags a jump, which the player
    reads as the next row starts (`0x10616f29`), a pattern delay's rows
    played out first: the section starts as the row playing ends, the speed,
    tempo and pans playing on but for order 0 (`Update`,
    `0x1060a822`-`0x1060a863`), and until then the order written back into
    `SongSection` is the one before the section, 255 before order 0. The
    rest of the row's ticks run on the silenced voices, a note delay's note
    sounding and a retrigger moving its voice's place alone; a song just
    loaded, no row playing, starts its section at its first tick. A section
    past the last order is refused (`glxControlMusic`), logged as
    `glxControlMusic( GLX_SETPOSITION2, Viewport->Actor->SongSection )
    failed: 17` (`0x1060a86b`-`0x1060a888`), the order count as it was, but
    the voices are silenced and the jump flagged all the same: the song goes
    on at the order after the count as the row ends, a song just loaded at
    order 0.
  - **Its vibrato** (H, K's and a T under 0x20, the player's commands 4 and
    6) takes each nibble of its parameter that is not 0 as the channel's
    speed and depth on the row's first tick and plays none there, the row
    clearing it; on each tick after, the waveform's place steps on by the
    speed, 64 steps a cycle, and the voice's pitch (in 256ths of a semitone,
    larger lower) is raised by 32 times the depth times the step's value
    over 256, its rate taking 64ths (`0x10616eb0`, `0x10614920`,
    `0x10615660`). The waveform is ProTracker's sine table of 255
    (`0x1063daa0`; by E4x a ramp from 255 down to -255 or a square of 255,
    a waveform of 3 and up reading the table after them): the depth over 8
    of a semitone at the top, twice IT's with its old effects off, the pitch
    going down first. A struck note takes its instrument's waveform, the
    sine the IT loader leaves there, from its first step. The tremolo (R) is
    made alike, its depth twice IT's.
  - **E9y** (Q): on each tick of the row that is a multiple of y, the row's
    first among them, the voice's place goes back to its sample's start and
    nothing else changes; a voice that has ended stays silent, its playing
    flag cleared at its end. A note struck on the row plays from its start
    anyway, so a row with a note and a y dividing the speed sounds as IT's;
    a row with none retriggers on its first tick too, where IT's count,
    carried over the rows, does not: rows of Q04 with no note at speed 6
    retrigger 4 and 2 ticks apart in turn, IT's every 4.
  - **ECx** (SCx): on each tick past x the note's volume 0, the note playing
    on, so a later volume brings it back; ECF at a speed over 16 from tick
    16.

## Reverb

With `UseReverb`, when the zone of the player's view target has
`bReverbZone`, its settings become Galaxy's reverb for every sound:

- the volume: `MasterGain` ÷ 255;
- the damping of highs: `CutoffHz` (to 44,100);
- six echoes, each `Delay` × 2 ms (1–340 ms) at `Gain` ÷ 255, held to
  0.001–0.999, so an echo of `Gain` 0 is there too, at 0.001.

Another zone gives none. The reverb is set again only when it changes,
starting from silence. 21 zones in 16 maps have it: Battery Park, the Mole
People, Brooklyn Bridge Station, the airfield, the NSF headquarters, the
ship, parts of Hong Kong, the intro and the endgame.

How it sounds (`glxSetSampleReverb`, `0x106113d0`; with SSE the setup at
`0x106109f0` and the routine at `0x10622d33`; MMX and 3DNow! routines
besides; none at all without MMX): three stages of stereo allpass filters,
the left of each stage one echo and the right the next.

- **An echo** of delay d (whole samples of `OutputRate`) and gain g is a
  filter of coefficient c = 1 − g. Its line takes the input plus c × the
  delayed line through a one-pole lowpass. It passes on −c × the input plus
  (1 − c²) × the delayed line. So a strong echo is nearly a plain delay, and
  a weak one passes the sound on nearly as it came, ringing faintly.
- **The lowpass:** y += a(x − y), with a = √((v + 2)v) − v and
  v = 1 − cos(2π × cutoff ÷ rate).
- **The feedback:** the last stage's output feeds back into the first, left
  and right swapped, at half with the sound coming in, and is added to the
  dry sound at the volume.

Measured in Battery Park's `ZoneInfo5` (two echoes, at 40 and 68 ms and
`Gain` 150 and 70; cutoff 6,000 Hz): a gunshot rings about 2 s before falling
60 dB under its peak, and 0.5 to 1.5 s after the peak it is 32 dB under its
first 0.45 s. Outside the zone the shot ends with the sample. The structure
above, run over the original's own shot from outside the zone, gives 1.97 s
and 32.4 dB, and its peak 0.5 dB down, as the original's is.

## Hardware and the console

- **3D hardware** of its day (Aureal's A3D, Creative's EAX): `Init`
  (`0x10605580`) detects it, and it plays positional voices when
  `Use3dHardware` is on. With A3D 2.0, `RenderAudioGeometry` (`0x106084d0`)
  hands the level's polygons to A3D for its wave tracing. `Init` also turns
  off Aureal's splash screen in the registry.
- **CPU extensions:** `Init` turns off the mixer's MMX, KNI and 3DNow!
  routines where Core recorded none, as `-nommx`, `-nokni` and `-nok6` make
  it do ([Core](core-dll.md#the-platforms-start)): its own CPUID flags masked
  with Core's (`0x10605693`-`0x106056c1`). Without MMX the mix takes the plain
  routines, stereo too (`0x10623578`, chosen at `0x10614080`), with 64-level
  gains (`0x1062357c`-`0x106235a9`) and one interleaved buffer; without SSE the
  integer MMX routine, all but alike.
- **Console commands** (`Exec`, `0x10607070`), the engine's after the
  renderer's ([`Engine.dll`](engine-dll.md)), in this order:
  - `CDTRACK <n>`, with a viewport: "CD Track <n>" to the command's output,
    the player's `CdTrack` set to it and its `Transition` to `MTRAN_Instant`,
    so the next update changes the music as at any instant transition
    ([music](#music)), the same song going on from its own order;
  - `CDVOLUME <f>`: the CD audio's volume, 127 times it; nothing written;
  - `MUSICORDER <n>`, while a song is loaded: "Galaxy order <n>" to the
    command's output, and `glxControlMusic`'s position set (its case 1,
    `0x1060d0e0`): the order count made the order before it, the pattern's
    break flagged and the mixer's count to the next tick run out
    (`0x1060d15e`-`0x1060d193`), so the order starts at once, where a
    section's change (case 2 and the break, `0x1060a863`-`0x1060a88d`) waits
    for the playing row's end; a negative order counts from the order
    playing (-1 the next), and one past the song's last is refused, quietly;
  - `RECORDSOUND` (`0x106071c5`-`0x10607342`): the microphone opened
    (`waveInOpen`, the wave mapper) at 8 kHz, mono, 16 bits, one buffer of
    64 KB, 4.096 s, given it and started, "RecordSound begin" to the log;
    each call that fails is an assertion, a critical error;
  - `ENDRECORDSOUND`, while recording (else nothing,
    `0x1060735d`-`0x10607a95`): the recording reset and stopped, its
    samples, the bytes recorded over 2, "RecordSound end (%i samples)" to the
    log, the device closed. Then from the fourth sample on, in place, a
    slope coder: a step of 256 at first, grown by half (3/2, cut toward 0)
    when the three samples before it, as they now stand, rise or fall
    strictly one way, else cut by a third (2/3), held to 256-2048; a value
    from 0 moved up by the step if under the sample plus what was missed
    before, else down, held to -32,768-32,767 and written, what was missed
    the sample less it. Then from the fourth on, in place, a low pass: the
    sample 1 - 0.6 (the float) of itself and 0.6 of the one before, cut
    toward 0 (`_ftol`). Written as `Test.wav` in the current folder by
    `SaveRiffFile` (Core's `FRiffChunk.h`): a RIFF `WAVE` of a `fmt ` chunk
    of 16 bytes -- the format's tag, channels, rate, bytes a second, block
    and bits, each logged as it is written, "wFormatTag: 1" to
    "nBitsPerSample: 16" -- and a `data` chunk of the samples; nothing, its
    lines unlogged, when the file will not open. With a viewport and some
    samples, that file loaded into a new `USound` of the transient package
    and played at the player through the subsystem's `PlaySound`, Id 2, at
    the player's place, volume 1000 (full), radius 4,096 and pitch 1;
  - `ASTAT AUDIO` toggles the overlay, `ASTAT DETAIL` its detail, any other
    `ASTAT` taken too. `PostRender` (`0x10608570`), after the console's
    `PostRender` and before the renderer's statistics (Engine.dll
    `0x1038f775`-`0x1038f79b`), draws it white in the canvas's small font:
    `GalaxyAudioSubsystem Statistics` at the left 16 pixels down; then for
    each of `EffectsChannels` from 24 pixels down, 10 in, 8 pixels apart --
    16 with the detail -- `Channel %2i: %s`, the sound's full name, for a
    channel with a voice, `Channel %i: None` for another, `Channel %i:
    None` with a blank more from the tenth; with the detail 8 under each `
    Vol: %05.2f Pitch: %05.2f Radius: %07.2f Priority: %05.2f`, the
    record's, or `  ...`;
  - A3D's `s_...` settings, with A3D 2.0 in use.
