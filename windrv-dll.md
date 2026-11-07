# WinDrv.dll

The Windows client and viewport: the window the game draws into, DirectDraw for the
software renderer's fullscreen modes, DirectInput for the mouse, the joystick, and which
render device a viewport opens with. Read for the command-line flags it honours -- four of
the nine the launcher's safe mode emits
([`cli-flags.md`](cli-flags.md#flags-the-launcher-emits-safe-mode)), and `-safe` -- for
how a key and a typed character reach the game and what losing the focus does, and for
where the game's window opens, how it goes full screen and back, its window's commands, which
viewport a frame draws and which render device a viewport opens with; not in full. Method:
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
  (`0x1110a28e`). The window returns on each, `DefWindowProc` never seeing them: Alt's
  release enters no menu mode, Alt+F4 closes nothing. A held key's repeats press it again. A
  shift, control or alt comes as the code of both sides: `VK_SHIFT`, `VK_CONTROL`, `VK_MENU`
  (`IK_Alt`).
- **A poll of every code** at the end of `UWindowsViewport::UpdateInput` (`0x11109280`, its
  loop at `0x11109880`): each code from 0 to 255 that is not a joystick's or the mouse's this
  poll is released when the game has it down and `GetKeyState` says it is up, and, while the
  window has the focus, pressed when the game has it up and `GetKeyState` says it is down. So
  a side's own code is pressed too, once, after the code of both: `VK_LSHIFT` (`IK_LShift`),
  `VK_RSHIFT`, `VK_LCONTROL`, `VK_RCONTROL`, and `VK_LMENU` and `VK_RMENU`, which `EInputKey`
  names `UnknownA4` and `UnknownA5`.

The keypad's digits and point are `VK_NUMPAD0` to `VK_NUMPAD9` and `VK_DECIMAL` (`NumPad0` to
`NumPadPeriod`) while Num Lock is on and, with it off, the keys they move by, as Windows' layouts
code them: `VK_INSERT`, `VK_END`, `VK_DOWN` and the rest, `VK_CLEAR` for 5 (`Unknown0C`),
`VK_DELETE`. The ISO key beside the left Shift is `VK_OEM_102`, `EInputKey`'s `JoyZ`. Under Wine
a key's code is the one Wine's X11 keyboard driver gives it: from what the keys type it finds the
layout's family and takes the typing keys' codes from that family's table
(Wine's `keyboard.c` in `winex11.drv`, `main_key_vkey_*`) -- a QWERTY's by their places, as most
layouts', a QWERTZ's with Y and Z swapped, an AZERTY's, a Dvorak's and a Swedish's as Windows'
French, Dvorak and Swedish layouts code them, a Brazilian ABNT's and a Japanese 106's by tables of
their own.

The Windows keys and the menu key are `Unknown5B`, `Unknown5C` and `Unknown5D`, Print Screen
`IK_PrintScrn` (`VK_SNAPSHOT`), the keypad's operators `GreyStar`, `GreyPlus`, `GreyMinus`
and `GreySlash`, its Enter `IK_Enter`. DirectInput is the mouse's alone
(`UWindowsViewport::diSetupKeyboardMouse`, `0x1110c700`: `GUID_SysMouse`, the mouse's data
format, exclusive in the foreground): its buttons `LeftMouse`, `RightMouse` and
`MiddleMouse`, its moves `MouseX` and `MouseY`, and its wheel's movement since the last
poll, whatever its size, one press and release of `MouseWheelUp` or `MouseWheelDown` by its
sign (`UpdateInput` reads the device's state once a poll, `GetDeviceState`; its buffered
data serves the buttons alone). A `WM_MOUSEWHEEL` the window gets likewise presses and
releases once by the delta's sign, whatever the delta, after handing the delta to the
`MouseW` axis (`0x1110b2bd`). The joystick (`joyGetPosEx`) gives `Joy1` up, its axes and its
hat.

**Typed characters** come apart from the keys: `WM_CHAR` and `WM_SYSCHAR` (`0x11109b30`) hand
the engine's `Key` the character's code, one a message, as Windows sends it to the window --
on a Unicode system its UTF-16, so an e acute is 0xE9 -- all but a carriage return, which
Enter's own key carries. The console takes it first; in Deus Ex, the root window then
([the engine and the input](extension-dll.md#the-engine-and-the-input)).
A `WM_SYSCHAR`, a character typed with Alt held, that neither of them takes (the root window
takes every one while a modal window holds the keyboard:
[what it takes](extension-dll.md#the-root-window)) goes on to `DefWindowProc`
(`0x1110a4e1`-`0x1110a50d`), and Alt+Enter's carriage return always does. Windows makes it a
command for the window's menu (`SC_KEYMENU`, [the window's commands](#the-windows-commands)):
Alt+Space opens the menu, in a window or full screen, the window keeping its menu there
([the window](#the-window)); any other character Windows takes for a menu's underlined
letter, and with no menu bar to find it in, beeps. A `WM_CHAR` the engine leaves goes no
further.

**The focus** (`ViewportWndProc`): losing it (`WM_KILLFOCUS`, `0x1110a0a3`) lets the mouse's
capture go (`SetMouseCapture`), runs `SETPAUSE 1` -- a command nothing in the game takes, so the
game goes on -- ends a drag and resets the engine's input (`UInput::ResetInput`, `Engine.dll`
`0x10394910`): its table of the keys held cleared and every `input` property of the player's
zeroed, with no release sent, so the root window keeps its marks of the keys held and an Alt held
into Alt+Tab stays down to its windows until Alt is pressed again
([the root window](extension-dll.md#the-root-window)); full screen, the window leaves full screen
and is minimised (`0x1110a12f`-`0x1110a159`), and its restore, `WM_SIZE`'s `SIZE_RESTORED`,
toggles it full screen again (`0x1110a003`-`0x1110a019`); the mouse's DirectInput device is let
go. Gaining it (`WM_SETFOCUS`, `0x1110a1ab`) runs `SETPAUSE 0`, resets the input again and takes
the mouse's device back.

## The window

`UWindowsViewport::OpenWindow` (`0x11107590`) takes the window's place and its
client area's size; a place of `INDEX_NONE` (-1) is Windows' default,
`CW_USEDEFAULT`, and a size of -1 the client's `WindowedViewportX` and `Y`.
The game's viewport is opened so, with neither given: `UGameEngine::Init`'s
call (`Engine.dll` `0x10389776`) passes no parent, not temporary, and -1 for
all four. So Windows puts the game's window where it puts any new one, and
sizes it about a client area of `WindowedViewportX` by `WindowedViewportY`
(`AdjustWindowRect` on the window's style, `WS_OVERLAPPEDWINDOW`, its caption
and frame round the client area), the menu bar the editor's alone. A viewport
already open is moved and sized with `SetWindowPos` instead.

Going full screen (`UWindowsViewport::ResizeViewport`, `0x1110d640`) the window keeps its
rectangle in a window (`GetWindowRect`, `0x1110d89c`; kept at `0x1110da99`-`0x1110dab9`), drops
its menu bar and takes off its caption and sizing frame but keeps its window menu
(`WS_SYSMENU`; `0x1110db71`), and asks Windows for Alt+Esc, Alt+Tab, Ctrl+Esc and Ctrl+Tab as
its hot keys (`RegisterHotKey`, `0x1110e11a`-`0x1110e168`), whose messages it takes and drops.
Back in a window it gives the hot keys back (`0x1110da29`-`0x1110da77`), puts its caption and
frame back (`0x1110e1ac`) and moves to the rectangle's corner it kept, at its new size
(`MoveWindow`, `0x1110e29f`).

The toggle (`UWindowsViewport::ToggleFullscreen`, `0x1110d500`) is Alt+Enter's
([the keys](#the-keys)), Maximize's ([the window's commands](#the-windows-commands)), the
console's `TOGGLEFULLSCREEN` (`0x11106e1c`) and the restore's after the focus is lost
([the focus](#the-keys)). Full screen, it ends full screen (`EndFullscreen`, `0x1110d380`,
logged `EndFullscreen`), back in a window at its windowed size. In a window, unless its viewport
is a child window's (the editor's), it logs `AttemptFullscreen` and opens the first that opens
of `GameRenderDevice` full screen, `WindowedRenderDevice` full screen and `WindowedRenderDevice`
in a window (`TryRenderDevice`, `0x1110d150`), full screen at `FullscreenViewportX` by `Y`.
`EndFullscreen` is the console's `ENDFULLSCREEN` too, in any state, in a window logged and its
window put back at its windowed size (`0x11106dcf`-`0x11106dea`); `PREFERENCES` and the window's
`WM_DESTROY` end full screen first (`0x111072bb`, `0x11109c3e`).

In a window, `WM_SIZE` (`0x11109f82`) gives the viewport or its render device the client area's
new size, so a maximize that no command carries leaves the window maximized and the game drawn
at its size. As it is dragged the window is held to 640 by 480 at least, the whole window, its
frame and caption too: `WM_GETMINMAXINFO`'s least tracking size (`0x1110a812`), whatever the
window's state.

## The window's commands

The window's commands (`WM_SYSCOMMAND`, `0x1110b149`), from its caption, its window menu or
Windows, each read without the four low bits Windows keeps for itself (`0x1110b152`), so that a
double click on the caption, whose Maximize has them set, is Maximize too:

- the screen saver and the monitor's power saving are refused, each logged (`SC_SCREENSAVE`,
  `SC_MONITORPOWER`), in a window or full screen;
- Maximize -- the caption's box, a double click on the caption, the window menu's -- toggles
  full screen, as Alt+Enter does (`SC_MAXIMIZE`, `0x1110b172`), and goes no further, so the
  window is never maximized (`0x1110b177`). Full screen the window keeps its maximize box with
  its menu, its style losing `WS_CAPTION` and `WS_THICKFRAME` alone (`0x1110db65`), so the
  menu's Maximize goes back to a window;
- full screen, the switches to another window and the task list are refused (`SC_NEXTWINDOW`,
  `SC_PREVWINDOW`, `SC_TASKLIST`, `SC_HOTKEY`; `0x1110b18c`-`0x1110b1af`);
- every other goes to `DefWindowProc`: the window's menu (`SC_KEYMENU`, from Alt+Space and the
  other characters [the keys](#the-keys) leave), Move, Size, Minimize and Close.

While the window's menu is open (`WM_ENTERMENULOOP` to `WM_EXITMENULOOP`, `0x1110b626`,
`0x1110b70c`) the viewport takes no mouse move, its opening ending a drag. Windows runs the
menu inside the message, so the game's loop waits until the menu closes.

## Drawing a frame

The game engine's tick ends with the client's (`UWindowsClient::Tick`,
`0x11102c60`), unless it took a travel
([the game engine's frame](engine-dll.md#a-levels-tick)). It draws one
viewport: of those whose player shows real time (its `ShowFlags` with 0x800
or 0x4000 set) and whose window has a width and a height, the one drawn
longest ago (its `LastUpdateTime`). A viewport whose window is gone is
destroyed instead, and the tick ends there. The viewport's `Repaint`
(`0x111082e0`) is the engine's `Draw` of it
([`Engine.dll`](engine-dll.md#the-loading-screen)).

## Choosing the render device

`OpenWindow` gives a viewport with no device the first of these that opens:

1. the software renderer, if the viewport asks for it;
2. `GameRenderDevice`, fullscreen if `StartupFullscreen` (not with `-nohard`, never in the
   editor);
3. `WindowedRenderDevice` fullscreen, if `StartupFullscreen`;
4. `WindowedRenderDevice` in a window.

With none, it asserts. The device opens (`TryRenderDevice`, `0x1110d150`) in full screen at the
client's `FullscreenViewportX` and `Y` and `FullscreenColorBits` ÷ 8 bytes a pixel; in a window
at `WindowedViewportX` and `Y` and the desktop's depth, as the viewport's constructor reads it
(`GetDeviceCaps`' `BITSPIXEL`, `0x111069b7`): 4 bytes on a desktop of 24 or 32 bits, 2 on any
other. The game's ini has `FullscreenColorBits` 16; the Display menu's Texture Color Depth
(`MenuChoice_TextureColorBits`, 16-bit or 32-bit, from the next start) sets it and
`WindowedColorBits`.
