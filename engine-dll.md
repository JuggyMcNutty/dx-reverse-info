# Engine.dll

The native half of package Engine: UE1's actors, pawns, levels, meshes,
networking and the interfaces to rendering and audio, with what Deus Ex added
to them -- AI senses (`AICanSee`, `AICanHear`, `AIVisibility`), the AI event
system that carries noises and alarms to NPCs, blend animations, instant
volume changes. How it is read: [working on the binaries](README.md#working-on-the-binaries).

Not yet read in IDA. Patch 0034's `AICanSee` and `AIVisibility` were read from
it with `objdump` ([its message](../../engine-patches/0034-deusex-ai-sight.patch)).

## The binary

| Property | Value |
|---|---|
| Size | 1,732,608 bytes |
| Imagebase | `0x10300000` |
| SHA1 | `9438119092df07046060f62b9d72914eba6a82cd` |
| Exports | 2,370: 88 classes, 168 `exec` natives (10 of them latent `Poll*` handlers) |

57 classes have a layout from their script; 31 are C++ only (`ULevel`,
`UModel`, `UMesh`, `UEventManager`, the network channels). The host check
reads 69 of the registrations, and the 51 of those with a script layout
match it.
