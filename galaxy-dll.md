# Galaxy.dll

The native half of package Galaxy: the game's audio subsystem,
`UGalaxyAudioSubsystem` -- Epic's driver (`UnGalaxy.cpp`) with Ion Storm's
additions: a speech volume, volumes changed at once, lip sync, stopping a
sound by its ID -- over Carlo Vogelsang's Galaxy sound library (revision
5.00, compiled February 2000), linked in: its mixer, its player for tracker
music, its reverb, DirectSound or WinMM output, and A3D and EAX hardware. How
it was read:
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
`StopSound`, `SetVolumes`, `SoundPriority` and `IsObstructed` -- the last two
also written out inline where they are used.

- **Its fields:** the settings at 0x2c–0x6b ([below](#settings)); the ASTAT
  flags at 0x6c and 0x70; whether 3D hardware and A3D 2.0 are in use at 0x74
  and 0x78; the viewport at 0x7c; 32 channel records of 0x40 bytes from 0x80,
  of which `EffectsChannels` are used; the time of the last update at 0x880;
  the music at 0x888, its CD track at 0x88c and section at 0x88d; the reverb
  last set at 0x88e; the next free sound ID at 0x8fc; the music's fade at
  0x900.
- **A channel's record:** Galaxy's voice, the actor, the sound's ID, whether
  it plays in 3D, the sound, its place, volume, radius, pitch and priority,
  the time it has played, when its lip sync is next worked out, the
  sample's mean (worked out once, then unused), and its obstruction
  ([sounds behind walls](#sounds-behind-walls)).

## Settings

`[Galaxy.GalaxyAudioSubsystem]` in `DeusEx.ini`; the defaults are the game's.

| Setting | Default | What it does |
|---|---|---|
| `UseDirectSound` | True | DirectSound output, else WinMM (as `-nodsound` gives) |
| `UseFilter` | True | cosine interpolation when a sound is resampled, else the nearest sample |
| `UseStereo` | True | stereo output, else mono |
| `UseSurround` | False | a sound behind the listener gets Galaxy's surround pan |
| `ReverseStereo` | False | left and right swapped |
| `UseDigitalMusic`, `UseCDMusic` | True, False | the level's tracker music; CD audio |
| `UseReverb` | True | each zone's reverb ([reverb](#reverb)) |
| `Use3dHardware` | False | A3D or EAX hardware, when found and `-no3dsound` is not given |
| `LowSoundQuality` | False | read by the engine as it loads each sound: 16-bit ones become 8-bit, and ones at 22,050 Hz or more are halved in rate (`Engine.dll`, `0x1036f040`) |
| `Latency` | 40 | the output's mix-ahead in milliseconds |
| `OutputRate` | 44100Hz | the mixing rate, 8,000 to 48,000 Hz |
| `EffectsChannels` | 16 | the voices for sounds |
| `MusicVolume`, `SoundVolume`, `SpeechVolume` | 153, 204, 255 | the Sound options' sliders |
| `AmbientFactor` | 0.7 | the scale of ambient sounds' volume |
| `DopplerSpeed` | 6,500 | the speed of sound for Doppler, in units a second |

`UseSpatial`, also in `DeusEx.ini`, is no setting of this class: nothing
reads it.

## Playing a sound

- **`PlaySound(Actor, Id, Sound, Location, Volume, Radius, Pitch)`**
  (`0x10608100`) only queues the sound: the next update starts it. With no
  viewport or no sound it plays nothing; a radius of 0 fails an assertion. A
  sound with no slot gets an ID of its own, counting down in steps of 16
  from −16. The ID packs the slot ([`Engine.dll`](engine-dll.md#small)).
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
  (`Actor.StopSound`, [`Engine.dll`](engine-dll.md#small)).
- **`NoteDestroy(Actor)`** (`0x106083a0`), when an actor goes: its ambient
  sound stops, and its other sounds play on where they are, without it.
- **`SetViewport`** (`0x10605c40`) stops every sound; for a new viewport it
  restarts the output with the settings and registers every sound loaded.
  **`RegisterSound`** (`0x10606af0`) hands a sound's data to Galaxy and
  unloads it; data Galaxy cannot read is a fatal error.

## Each frame

`Update` (`0x10609510`) works on its own time step (0 to 1 s), in this order.

- **Ambient sounds start.** While the view is live and the game is not paused,
  every actor of the level is read, each frame: one with an `AmbientSound`,
  within its radius (25 × (`SoundRadius` + 1)) of the view target, and not
  already on a channel, is played in the ambient slot at `AmbientFactor` ×
  `SoundVolume` ÷ 255, with pitch `SoundPitch` ÷ 64. The fork does the same
  scan ([where a frame goes](../../ports/trimui-smartpro/README.md#where-a-frame-goes)).
- **Ambient sounds update.** One out of radius, whose actor's sound changed,
  or with the view not live, stops. The rest take their actor's radius and
  pitch again, and twice the starting volume. **An actor with a light** has
  its sound follow the light: the volume times `LightBrightness` ÷ 255, and
  times the light's pulse or flicker at the moment -- the renderer's
  `GlobalLighting`, which gives a steady light 1 -- then at most 1.
- **Every channel,** unless its voice has finished (then it is cleared):
  - its place becomes its actor's, and its priority is worked out again;
  - its **fall-off** is 1 − distance ÷ radius, from the listener: linear,
    silent at the radius;
  - its **pan** is the angle of the sound from straight ahead, left or right,
    front and back alike, turned into Galaxy's pan: at most seven-eighths of
    the way to one side, and nearer the middle for a sound within a tenth of
    its radius. `ReverseStereo` swaps it; with `UseSurround`, a sound behind
    gets the surround pan;
  - its [obstruction](#sounds-behind-walls), then its [volume](#volume);
  - **Doppler,** for an ambient sound only: the pitch times 1 − the actor's
    speed away from the view target ÷ `DopplerSpeed`, kept to 0.5–2;
  - a voice is started for a new sound, at the sample's rate × pitch ×
    Doppler: through 3D hardware if in use, else Galaxy's mixer. A playing
    one gets its rate, volume and pan again. [Lip sync](#lip-sync) is worked
    out here.
- **Then the music** ([music](#music)) and **the reverb** ([reverb](#reverb)).

### Sounds behind walls

Each channel keeps an obstruction time. When a line from the player's eyes
(the player's own place and `EyeHeight`, even when viewing through another
actor) to the sound's actor meets the level's BSP -- `UModel::FastLineCheck`,
which movers and other actors do not block -- it grows by the time step, up
to 0.5 s; when clear, it shrinks back to 0. The channel plays at 1 − 2 × that
time, at least 0.33: a sound behind a wall fades over half a second to a
third of its volume, and back as it clears. Speech is never muffled, nor a
sound whose actor has gone. `IsObstructed` (`0x10607fc0`) is the same test as
a function.

### Volume

A voice's volume is the sound's volume × its fall-off × its obstruction × the
balance of the sliders, at most full and at least 1/256 of it.

- **The sliders.** Galaxy's sample volume is the louder of `SoundVolume` and
  `SpeechVolume` (`SetVolumes`, `0x106061b0`). Speech -- a sound in the talk
  slot -- is scaled by the speech slider ÷ the sound slider when the sound
  slider is the louder, and the other sounds the other way round; so each
  plays at its own slider. When the two are equal, both are scaled by the
  slider a second time: at half each, everything plays at a quarter.
- **Instantly.** `SetInstantSoundVolume`, `SetInstantSpeechVolume` and
  `SetInstantMusicVolume` (`0x106063d0`, `0x106064f0`, `0x10606610`) set the
  slider and the volumes at once, for the menu's sliders as they move.

## Lip sync

The mouths in conversations: every 0.1 s of a channel's playing time, if it is
speech from a pawn whose script has set `bIsSpeaking`, Galaxy works out a
mouth shape and writes it to the pawn's `nextPhoneme`, which the script's
`LipSynch` animates.

- **What it hears:** 1,024 samples at the play position -- for a compressed
  sample (Deus Ex's speech is MP3), the voice's decoded buffer where it plays;
  for another, 0.1 s ahead of the time played -- through a triangle window
  and an FFT (`0x10609180`, `0x10609310`).
- **The shape** (`0x10608d70`), from the strongest frequency: `X` (mouth
  closed) when even that is weak; otherwise `T` above 2,000 Hz, `F` to
  2,000, `A` to 1,500, `O` to 600, `U` to 400, and `E` at 250 Hz or below.
  `M` never comes: its test (above 1,000 Hz) sits inside the branch for
  250 Hz or below. A second test, of the loudness below 300 Hz, always
  passes.

## Music

- **Changing the music.** When the player's `Transition` is set, the music
  playing fades out -- over 1 s for `MTRAN_Fade`, 5 s for `MTRAN_SlowFade`,
  1/3 s for `MTRAN_FastFade`, at once for the others -- plus twice `Latency`.
  Then the player's `Song` starts at full volume at the order `SongSection`
  (a different song is loaded first; the same one only jumps), with CD audio
  too if `UseCDMusic`. Section 255 is silence: the music stops.
- **Where it is.** While no transition is waiting, each frame writes the order
  playing back into the player's `SongSection`. Deus Ex's dynamic music keeps
  it to "save our place in the ambient track" (`DeusExPlayer.UpdateDynamicMusic`):
  combat and conversation music come in with `MTRAN_FastFade` and `MTRAN_Fade`,
  and the ambient music comes back where it was (after a fight, 5 s later and
  with `MTRAN_SlowFade`).
- **The sliders.** Music plays at `MusicVolume` × the fade (`SetVolumes`).

## Reverb

With `UseReverb`, when the zone of the player's view target has
`bReverbZone`, its settings become Galaxy's reverb for every sound:
`MasterGain` ÷ 255 the volume, `CutoffHz` (to 44,100) the damping of highs,
and six echoes, each `Delay` × 2 ms (1–340 ms) at `Gain` ÷ 255. Another zone
gives none. The reverb is set again only when it changes. 21 zones in 16
maps have it: Battery Park, the Mole People, Brooklyn Bridge Station, the
airfield, the NSF headquarters, the ship, parts of Hong Kong, the intro and
the endgame (the data).

## Hardware and the console

- **3D hardware** (Aureal's A3D, Creative's EAX), of its day: `Init`
  (`0x10605580`) detects it, and it plays positional voices when
  `Use3dHardware` is on. With A3D 2.0, `RenderAudioGeometry` (`0x106084d0`)
  hands the level's polygons to A3D for its wave tracing. `Init` also turns
  off Aureal's splash screen in the registry.
- **Console commands** (`Exec`, `0x10607070`): `CDTRACK`, `CDVOLUME`,
  `MUSICORDER` (a jump to an order, logged as "Galaxy order"), `ASTAT AUDIO`
  and `ASTAT DETAIL` (each channel's sound, and its volume, pitch, radius and
  priority, drawn by `PostRender`, `0x10608570`), `RECORDSOUND` and
  `ENDRECORDSOUND` (the microphone at 8 kHz, filtered, saved as `Test.wav`
  and played at the player), and A3D's `s_...` settings.

## The database

`gamefiles/System/Galaxy.dll.i64` has the class layouts, the UTF-16 strings
and the initializers' names ([working on the binaries](README.md#working-on-the-binaries)),
and by hand: `UGalaxyAudioSubsystem` and its channel record `FPlayingSound` as
read here, `UViewport`'s first members from the SDK's `UnCamera.h`, and
Galaxy's own structures and function prototypes from the SDK's `GALAXY.H`
(whose licence keeps them out of this repository). The library's functions
are named from their assertion texts, with the lip sync's helpers and the
music's globals. Each function above carries a one-line comment.
