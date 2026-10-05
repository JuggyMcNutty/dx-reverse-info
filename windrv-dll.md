# WinDrv.dll

The Windows client and viewport: the window the game draws into, DirectDraw
for the software renderer's fullscreen modes, DirectInput for the keyboard
and mouse, the joystick, and which render device a viewport opens with. It
was read for the command-line flags it honours -- four of the nine that the
launcher's safe mode emits ([`cli-flags.md`](cli-flags.md#flags-the-launcher-emits-safe-mode)),
and `-safe`
-- not in full. How it was read:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 159,744 bytes |
| Imagebase | `0x11100000` |
| SHA1 | `18396b8ca4c50a32915c75de1ebb7f94c3bc33b0` |
| Exports | 83; no natives |
| Functions | 502, 93 of them five-byte jumps (incremental linking) |

It registers two classes, `UWindowsClient` (the `ViewportManager` of
`DeusEx.ini`, section `[WinDrv.WindowsClient]`) and `UWindowsViewport`, both
C++ only; the SDK's `WinDrv/Inc/WinDrv.h` has them. That header declares each
`BITFIELD` as a whole dword, and the code agrees: `UClient`'s six options
(`CaptureMouse` to `NoDynamicLights`) take 0x3c–0x50, so `WindowedViewportX`
and `Y` are at 0x54 and 0x58 and `FullscreenViewportX` and `Y` at 0x60 and
0x64; `UWindowsClient`'s `UseDirectDraw`, `UseDirectInput`, `UseJoystick` and
`StartupFullscreen` are at 0x9c, 0xa0, 0xa4 and 0xa8.

## The flags

| Flag | Read in | What it does |
|---|---|---|
| `-nohard` | `UWindowsViewport::OpenWindow` (`0x11107590`) | the viewport skips `GameRenderDevice` and opens with `WindowedRenderDevice` -- `SoftDrv.SoftwareRenderDevice` in the game's `DeusEx.ini` -- fullscreen first if `StartupFullscreen`, then windowed |
| `-noddraw` | `UWindowsClient::Init` (`0x11101d20`) | no DirectDraw, so no fullscreen modes for a renderer that goes through the client's DirectDraw -- the software renderer; with Glide or Direct3D as `GameRenderDevice` the client never starts DirectDraw anyway |
| `-defaultres` | `UWindowsClient::Init` | the windowed and fullscreen viewport sizes become 640×480 for the run; the colour depths are left alone |
| `-nojoy` | `UWindowsClient::PostEditChange` (`0x111030f0`) | joystick 0 is not opened, so a pad gives no input even with `UseJoystick` |
| `-safe` | `UWindowsClient::Init` | no DirectInput even with `UseDirectInput`: the keyboard and mouse come through window messages |
| `HWND=` | `UWindowsViewport::OpenWindow` | the window to open the viewport inside, when the caller gives none |

So the safe mode's "Run the game in a window" (`-nohard -noddraw`) gets there
by way of the software renderer: without DirectDraw it has no fullscreen mode
to take, and the viewport falls back to a window. A run with `-safe` on its
command line -- the SafeMode page's Run, when `-safe` opened the page -- has no
DirectInput either.

## Choosing the render device

`OpenWindow` gives a viewport with no device the first of these that opens:
the software renderer, if the viewport asks for it; `GameRenderDevice`,
fullscreen if `StartupFullscreen` (not with `-nohard`, never in the editor);
`WindowedRenderDevice` fullscreen, if `StartupFullscreen`; then
`WindowedRenderDevice` in a window. With none, it asserts.

## The database

`gamefiles/System/WinDrv.dll.i64` (new, 2026-09-27) has the three scripts'
work ([working on the binaries](README.md#working-on-the-binaries)) -- the
two classes have no script, so their layouts are only the header's -- and a
one-line comment on each function above.
