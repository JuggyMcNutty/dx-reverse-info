# Galaxy.dll

The native half of package Galaxy: the game's audio subsystem,
`UGalaxyAudioSubsystem`. It is Epic's driver (`UnGalaxy.cpp`) with Ion
Storm's additions (a speech volume, volumes changed at once, lip sync,
stopping a sound by its ID), over Carlo Vogelsang's Galaxy sound library
(revision 5.00, compiled February 2000), linked in: its mixer, its player for
tracker music, its reverb, DirectSound or WinMM output, and A3D and EAX
hardware. The library's own structures and function prototypes are in the
SDK's `GALAXY.H` (whose licence keeps them out of this repository). How it
was read: [working on the binaries](README.md#working-on-the-binaries).

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

`[Galaxy.GalaxyAudioSubsystem]` in `DeusEx.ini`; the defaults are the game's.

| Setting | Default | What it does |
|---|---|---|
| `UseDirectSound` | True | DirectSound output, else WinMM (as `-nodsound` gives) |
| `UseFilter` | True | asks the mixer to interpolate a sound resampled up; its SSE routine interpolates linearly either way ([the mixer](#the-mixer)) |
| `UseStereo` | True | stereo output, else mono |
| `UseSurround` | False | a sound behind the listener plays centred, its right side inverted |
| `ReverseStereo` | False | left and right swapped |
| `UseDigitalMusic`, `UseCDMusic` | True, False | the level's tracker music; CD audio |
| `UseReverb` | True | each zone's reverb ([reverb](#reverb)) |
| `Use3dHardware` | False | A3D or EAX hardware, when found and `-no3dsound` is not given |
| `LowSoundQuality` | False | read by the engine as it loads each sound: 16-bit ones become 8-bit, and ones at 22,050 Hz or more are halved in rate (`Engine.dll`, `0x1036f040`) |
| `Latency` | 40 | the output's mix-ahead in milliseconds |
| `OutputRate` | 44100Hz | the mixing rate, 8,000 to 48,000 Hz; the reverb's delays are whole samples of it |
| `EffectsChannels` | 16 | the voices for sounds |
| `MusicVolume`, `SoundVolume`, `SpeechVolume` | 153, 204, 255 | the Sound options' sliders |
| `AmbientFactor` | 0.7 | the scale of ambient sounds' volume |
| `DopplerSpeed` | 6,500 | the speed of sound for Doppler, in units a second |

`UseSpatial`, also in `DeusEx.ini` (the original launcher writes it), is not
a setting of this class, and nothing in the game reads it.

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
- **`StopSoundId(Id)`** (`0x10607ef0`) stops the channel with that ID
  (`Actor.StopSound`, [`Engine.dll`](engine-dll.md#sounds)).
- **`NoteDestroy(Actor)`** (`0x106083a0`), when an actor goes: its ambient
  sound stops, and its other sounds play on where they are, without it.
- **`SetViewport`** (`0x10605c40`) stops every sound. For a new viewport it
  restarts the output with the settings and registers every sound loaded.
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
  1 for a steady light), then at most 1.
- **Every channel,** unless its voice has finished (then it is cleared):
  - its place becomes its actor's, and its priority is worked out again;
  - its **fall-off** is 1 − distance ÷ radius from the listener (the view's
    own place, the coordinates `Update` is handed): linear, silent at the
    radius;
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

- A line runs from the player's eyes (the player's own place and
  `EyeHeight`, even when viewing through another actor) to the sound's actor.
- When it meets the level's BSP (`UModel::FastLineCheck`, which movers and
  other actors do not block), the time grows by the time step, up to 0.5 s.
  When clear, it shrinks back to 0.
- The channel plays at 1 − 2 × that time, at least 0.33: a sound behind a
  wall fades over half a second to a third of its volume, and back as it
  clears.
- Speech is never muffled, nor a sound whose actor has gone.

`IsObstructed` (`0x10607fc0`) is the same test as a function.

### Volume

A voice's volume is the sound's volume × its fall-off × its obstruction × the
balance of the sliders, at most full (32,767) and at least 1/256 of it.

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

1. The voices are mixed at `OutputRate` into a dry and a reverb buffer. Their
   gains are worked out again every millisecond or so from what `Update` last
   set.
2. The reverb runs over its buffer into the dry one.
3. The result is saturated to 16 bits and added, saturating, to the music's.

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
- **Resampling.** A voice steps through its sample at its rate × pitch in
  whole hertz, as a 16.16 fraction of `OutputRate`. The routine chosen for a
  CPU with SSE and stereo output, which is any modern one (`0x10622730`,
  copied in by `0x106231d1`), interpolates linearly between a sample and the
  next, with 15-bit weights, whatever `UseFilter` asks. The cosine table of
  16 steps at `0x1063da5c` is built for the other routines' 8-bit samples.
- **Loops** come from a WAV's `smpl` chunk (`0x10619940`): its first loop's
  start and end, the end being the first sample not played again. The
  ping-pong type plays back and forth. A sample ends when the voice passes
  its last frame, reading zeros beyond it.

## Lip sync

The mouths in conversations. Every 0.1 s of a channel's playing time, if it
is speech from a pawn whose script has set `bIsSpeaking`, Galaxy works out a
mouth shape and writes it to the pawn's `nextPhoneme`, which the script's
`LipSynch` animates.

- **What it hears:** 1,024 samples at the play position, through a triangle
  window and an FFT (`0x10609180`, `0x10609310`). For a compressed sample
  (Deus Ex's speech is MP3), the voice's decoded buffer where it plays; for
  another, 0.1 s ahead of the time played.
- **The shape** (`0x10608d70`), from the strongest frequency: `X` (mouth
  closed) when even that is weak; otherwise `T` above 2,000 Hz, `F` to 2,000,
  `A` to 1,500, `O` to 600, `U` to 400, and `E` at 250 Hz or below.
- `M` never comes: its test (above 1,000 Hz) sits inside the branch for
  250 Hz or below. A second test, of the loudness below 300 Hz, always
  passes.

## Music

- **Changing the music.** When the player's `Transition` is set, the music
  playing fades out: over 1 s for `MTRAN_Fade`, 5 s for `MTRAN_SlowFade`,
  1/3 s for `MTRAN_FastFade`, at once for the others, plus twice `Latency`.
  Then the player's `Song` starts at full volume at the order `SongSection`
  (a different song is loaded first; the same one only jumps), with CD audio
  too if `UseCDMusic`. Section 255 is silence: the music stops.
- **Where it is.** While no transition is waiting, each frame writes the
  order playing back into the player's `SongSection`. Deus Ex's dynamic music
  keeps it to "save our place in the ambient track"
  (`DeusExPlayer.UpdateDynamicMusic`): combat and conversation music come in
  with `MTRAN_FastFade` and `MTRAN_Fade`, and the ambient music comes back
  where it was (after a fight, 5 s later and with `MTRAN_SlowFade`).
- **The sliders.** Music plays at `MusicVolume` × the fade (`SetVolumes`).

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
  it do ([Core](core-dll.md#the-platforms-start)).
- **Console commands** (`Exec`, `0x10607070`):
  - `CDTRACK`, `CDVOLUME`;
  - `MUSICORDER`: a jump to an order, logged as "Galaxy order";
  - `ASTAT AUDIO` and `ASTAT DETAIL`: each channel's sound, volume, pitch,
    radius and priority, drawn by `PostRender` (`0x10608570`);
  - `RECORDSOUND` and `ENDRECORDSOUND`: the microphone at 8 kHz, filtered,
    saved as `Test.wav` and played at the player;
  - A3D's `s_...` settings.
