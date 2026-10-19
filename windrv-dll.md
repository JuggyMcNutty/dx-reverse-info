# WinDrv.dll

The Windows client and viewport: the window the game draws into, DirectDraw for the
software renderer's fullscreen modes, DirectInput for the mouse, the joystick, and which
render device a viewport opens with. Read for the command-line flags it honours -- four of
the nine the launcher's safe mode emits
([`cli-flags.md`](cli-flags.md#flags-the-launcher-emits-safe-mode)), and `-safe` -- and for
how a key reaches the game, not in full. Method:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 159,744 bytes |
| Imagebase | `0x11100000` |
| SHA1 | `18396b8ca4c50a32915c75de1ebb7f94c3bc33b0` |
| Exports | 83; no natives |
| Functions | 502, 93 of them five-byte jumps (incremental linking) |

It registers two classes, `UWindowsClient` (the `ViewportManager` of `DeusEx.ini`, section
`[WinDrv.WindowsClient]`) and `UWindowsViewport`, both C++ only; the SDK's
`WinDrv/Inc/WinDrv.h` has them. That header declares each `BITFIELD` as a whole dword, and
the code agrees:

| Fields | Offsets |
|---|---|
| `UClient`'s six options, `CaptureMouse` to `NoDynamicLights` | 0x3c–0x50 |
| `WindowedViewportX`, `Y` | 0x54, 0x58 |
| `FullscreenViewportX`, `Y` | 0x60, 0x64 |
| `UWindowsClient`'s `UseDirectDraw`, `UseDirectInput`, `UseJoystick`, `StartupFullscreen` | 0x9c, 0xa0, 0xa4, 0xa8 |

## The flags

| Flag | Read in | What it does |
|---|---|---|
| `-nohard` | `UWindowsViewport::OpenWindow` (`0x11107590`) | the viewport skips `GameRenderDevice` and opens with `WindowedRenderDevice` (`SoftDrv.SoftwareRenderDevice` in the game's `DeusEx.ini`), fullscreen first if `StartupFullscreen`, then windowed |
| `-noddraw` | `UWindowsClient::Init` (`0x11101d20`) | no DirectDraw, so no fullscreen modes for a renderer that goes through the client's DirectDraw: the software renderer. With Glide or Direct3D as `GameRenderDevice` the client never starts DirectDraw anyway |
| `-defaultres` | `UWindowsClient::Init` | the windowed and fullscreen viewport sizes become 640×480 for the run; the colour depths are left alone |
| `-nojoy` | `UWindowsClient::PostEditChange` (`0x111030f0`) | joystick 0 is not opened, so a pad gives no input even with `UseJoystick` |
| `-safe` | `UWindowsClient::Init` | no DirectInput even with `UseDirectInput`: the mouse comes through window messages, as the keyboard always does ([the keys](#the-keys)) |
| `HWND=` | `UWindowsViewport::OpenWindow` | the window to open the viewport inside, when the caller gives none |

So the flags the safe mode's "Run the game in a window" stands for, `-nohard -noddraw`, give
a window through the software renderer: without DirectDraw it has no fullscreen mode to take,
and the viewport falls back to a window. The box itself is never read: those flags follow
"Disable 3D sound hardware"
([the dead checkboxes](wizard.md#-shipped-bug-three-safe-mode-checkboxes-are-dead)). A run
with `-safe` on its command line (the SafeMode page's Run, when `-safe` opened the page) has
no DirectInput either.

## The keys

A key reaches the game as the Windows virtual-key code that names it, which is its
`EInputKey` (`VK_SHIFT`, 0x10, `IK_Shift`; `VK_OEM_1`, 0xBA, `IK_Semicolon`), so a key's name
follows the keyboard's layout. It comes two ways, each into
`UWindowsViewport::CauseInputEvent` (`0x11108d60`), which drops a code above 0xFE and hands
the rest to the engine's input:

- **The window's key messages** (`UWindowsViewport::ViewportWndProc`, `0x11109b30`):
  `WM_KEYDOWN` and `WM_SYSKEYDOWN` press their code (`0x1110a2a9`), `WM_KEYUP` and
  `WM_SYSKEYUP` release it (`0x1110a356`); Enter with Alt held toggles fullscreen instead
  (`0x1110a28e`). A held key's repeats press it again. A shift, control or alt comes as the
  code of both sides: `VK_SHIFT`, `VK_CONTROL`, `VK_MENU` (`IK_Alt`).
- **A poll of every code** at the end of `UWindowsViewport::UpdateInput` (`0x11109280`, its
  loop at `0x11109880`): each code from 0 to 255 that is not a joystick's or the mouse's this
  poll is released when the game has it down and `GetKeyState` says it is up, and, while the
  window has the focus, pressed when the game has it up and `GetKeyState` says it is down. So
  a side's own code is pressed too, once, after the code of both: `VK_LSHIFT` (`IK_LShift`),
  `VK_RSHIFT`, `VK_LCONTROL`, `VK_RCONTROL`, and `VK_LMENU` and `VK_RMENU`, which `EInputKey`
  names `UnknownA4` and `UnknownA5`.

The Windows keys and the menu key are `Unknown5B`, `Unknown5C` and `Unknown5D`, Print Screen
`IK_PrintScrn` (`VK_SNAPSHOT`), the keypad's operators `GreyStar`, `GreyPlus`, `GreyMinus`
and `GreySlash`, its Enter `IK_Enter`. DirectInput is the mouse's alone
(`UWindowsViewport::diSetupKeyboardMouse`, `0x1110c700`: `GUID_SysMouse`, the mouse's data
format, exclusive in the foreground): its buttons `LeftMouse`, `RightMouse` and
`MiddleMouse`, its moves `MouseX` and `MouseY`, a notch of its wheel a press and release of
`MouseWheelUp` or `MouseWheelDown`. The joystick (`joyGetPosEx`) gives `Joy1` up, its axes
and its hat.

## Choosing the render device

`OpenWindow` gives a viewport with no device the first of these that opens:

1. the software renderer, if the viewport asks for it;
2. `GameRenderDevice`, fullscreen if `StartupFullscreen` (not with `-nohard`, never in the
   editor);
3. `WindowedRenderDevice` fullscreen, if `StartupFullscreen`;
4. `WindowedRenderDevice` in a window.

With none, it asserts.
