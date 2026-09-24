# ConSys.dll

The native half of package ConSys: conversations -- their events (speech,
choices, flags, animations, trades, camera moves), the camera, the history
the player's log keeps, and the lists that bind them to actors. How it is
read: [working on the binaries](README.md#working-on-the-binaries).

Not yet read.

## The binary

| Property | Value |
|---|---|
| Size | 135,168 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `18c6b7ff257561d8f3d755503b2f9d9b00434790` |
| Exports | 495: 34 classes, 10 `exec` natives |

33 classes have a layout from their script, and `DConImport` is C++ only.
The host check reads all 34 registrations. Unlike the other DLLs, a script
layout is not always the code's; two classes are as their SDK headers
declare them:

- `DConCamera` registers 0x84 bytes (`ConSys/Inc/ConCamera.h`), where its
  script declares 0xbc;
- `DConEventAnimation` registers 0x60 (`ConSys/Inc/ConEventAnimation.h`: a
  play mode and a play length where the script has `bLoopAnim`), where its
  script declares 0x58.
