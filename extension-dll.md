# Extension.dll

The native half of package Extension, Ion Storm's own: the UI's window system
(`Window` and its subclasses: text, lists, edit fields, scrolling, tab groups,
the computer terminal's window), the graphics context `GC` that draws them,
and the flag base behind every mission flag. How it is read:
[working on the binaries](README.md#working-on-the-binaries).

Not yet read.

## The binary

| Property | Value |
|---|---|
| Size | 675,840 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `5f03bd11022e45a44ed8de95e385009cacd0c41c` |
| Exports | 2,395: 36 classes, 453 `exec` natives |

34 classes have a layout from their script; `XGameEngineExt` and `XInputExt`
are C++ only. The host check reads 26 of the registrations, and the 24 of
those with a script layout match it.
