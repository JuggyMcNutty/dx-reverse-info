# Extension.dll

The native half of package Extension, Ion Storm's own: the UI's window system
(`Window` and its subclasses: text, lists, edit fields, scrolling, tab groups,
the computer terminal's window), the graphics context `GC` that draws them,
the flag base behind every mission and conversation flag, and the game engine
and input classes that put the UI in front of the game. How it was read:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 675,840 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `5f03bd11022e45a44ed8de95e385009cacd0c41c` |
| Exports | 2,395: 36 classes, 453 `exec` natives |
| Functions | 2,551 |

As in `DeusEx.dll`, an export is its code, not a jump to it.

It registers the 36 classes it exports. 34 match the layout of their script;
`XGameEngineExt` and `XInputExt` are C++ only (the SDK's
`Extension/Inc/ExtGameEngine.h` and `Extension/Inc/ExtInput.h`). The script
declares the classes' native arrays, and ConSys's, as `DynamicArray`: three
ints named `Num`, `Max` and `Ptr` that are a `TArray`'s data, count and
capacity, whatever the names say.
[`tools/ida/ue1_types.py`](../../tools/ida/ue1_types.py) types them as
`TArray`s.

## Classes

Every size is the one the class's registration passes to `UClass`. Natives
are `exec` exports.

| Class | Base | Size | Natives |
|---|---|---|---|
| `XWindow` | `XExtensionObject` | 0x14c | 90 |
| `XTabGroupWindow` | `XWindow` | 0x174 | -- |
| `XModalWindow`, `XClipWindow`, `XRadioBoxWindow` | `XTabGroupWindow` | 0x588, 0x1a0, 0x188 | 2, 12, 1 |
| `XRootWindow` | `XModalWindow` | 0x744 | 15 |
| `XTextWindow` | `XWindow` | 0x174 | 15 |
| `XLargeTextWindow`, `XTextLogWindow`, `XButtonWindow` | `XTextWindow` | 0x1d0, 0x188, 0x1ec | 1, 4, 9 |
| `XEditWindow` | `XLargeTextWindow` | 0x28c | 31 |
| `XToggleWindow` | `XButtonWindow` | 0x1f4 | 4 |
| `XCheckboxWindow` | `XToggleWindow` | 0x214 | 5 |
| `XListWindow` | `XWindow` | 0x1d0 | 69 |
| `XScaleWindow`, `XScaleManagerWindow` | `XWindow` | 0x274, 0x174 | 34, 9 |
| `XScrollAreaWindow`, `XTileWindow`, `XBorderWindow` | `XWindow` | 0x180, 0x174, 0x1c8 | 4, 11, 5 |
| `XViewportWindow`, `XComputerWindow` | `XWindow` | 0x1b4, 0x218 | 12, 33 |
| `XGC` | `XExtensionObject` | 0xb8 | 51 |
| `XFlagBase` | `XExtensionObject` | 0x12c | 25 |
| `XFlag` | `XExtensionObject` | 0x40 | -- |
| `XFlagBool`, `XFlagByte`, `XFlagInt`, `XFlagFloat`, `XFlagName`; `XFlagVector`, `XFlagRotator` | `XFlag` | 0x44; 0x4c | -- |
| `XExtString` | `UObject` | 0x38 | 7 |
| `XExtensionObject` | `UObject` | 0x28 | 1: `StringToName` |
| `APlayerPawnExt` | `APlayerPawn` | 0x99c | 3: `PreRenderWindows`, `PostRenderWindows`, `InitRootWindow` |
| `XGameEngineExt` | `UGameEngine` | 0xd0 | -- (C++ only: the base of `DeusEx.DeusExGameEngine`) |
| `XInputExt` | `UInput` | 0xfb0 | -- (C++ only: the ini's `Input=Extension.InputExt`) |

## The UI in front of the game

### The engine and the input

- **`XGameEngineExt`**, the game engine's base:
  - `Init` (`0x100261b0`) registers the window events' names (`InitWindow`,
    `DrawWindow` and the rest).
  - `Browse` (`0x10026330`), after a level loads, makes the player's root
    window.
  - `Tick` (`0x100266a0`) ticks the windows, then the engine.
  - The mouse's position and movement go to the player's root window first
    (`0x100264b0`, `0x10026580`); typed characters go to it after the console
    (`0x10026650`).
  - `Destroy` destroys every window first.
- **`XInputExt`**, the input: `Process` (`0x1002d0b0`) gives each key to the
  root window first.
  - When the root window takes one, the input runs the release binding of
    every key it holds down. Nothing stays held under a menu: a movement key
    held when the menu opened is released then.
  - Otherwise it runs the key's binding itself: a press only once until the
    key is released, and a release only after a press.

### The root window

- **What it takes** (`Process`, `0x1003b3e0`): every key while any window has
  grabbed the keyboard, and every mouse button while any window has grabbed
  the mouse. Taking a button clears the player's `bFire` and `bAltFire`.
  Every modal window grabs both while it is shown: the menus and the game's
  screens.
- **Keys** go to the focus window, else the topmost modal window, then up its
  parents until one handles them: `RawKeyPressed`, then, for a press,
  `VirtualKeyPressed`. Typed characters go the same way as `KeyPressed`,
  passed over by windows that are not modal while Alt is down (accelerators).
- **Mouse buttons** (`HandleButtons`, `0x1003b960`) go to the window under
  the pointer, then up its parents. A press grabs the mouse for that window,
  and may give it focus. Presses of one button on one window within a short
  time and distance count up, wrapped at the window's `maxClicks`, so a list
  sees a double click as 2.
- **`LockMouse(bLockMove, bLockButton)`** (`0x1003a290`): with movement
  locked the pointer stays where it is; with buttons locked the UI takes and
  ignores them. The Customize Keys screen locks movement while it waits for a
  key.

### Showing and hiding

- **`Show` and `Hide`** (`SetVisibility`, `0x1004c7d0`) ask the window's
  parent. Its `ChildRequestedVisibilityChange` event decides, and the
  script's default calls `SetChildVisibility`. The root window, having no
  parent, sets its own.
- **`SetChildVisibility(bNewVisibility)`** (`0x1004ee20`) sets the window's
  flag. When that changes whether it can be seen, it:
  - moves focus and grabs away from what is hidden;
  - sends `VisibilityChanged` to the window and to its descendants;
  - lays the tree out again.
- **`DeusExHUD`** overrides the event to lay the HUD out again as its parts
  come and go, the InfoLink and the log among them.

### Window sounds

`PlaySound(sound, volume, pitch, posX, posY)` (`0x10050050`) plays one unit
from the player. When the root window has positional sound on, the sound is
turned left or right by the point's place across the screen, a quarter turn
at either edge; otherwise it is straight ahead. The point defaults to the
window's centre, and the volume to the window's own.

## Lists

`XListWindow`: the load and save screens, emails, the logs, images, the
conversation history, the key bindings, the colour themes, the skills of a
new game.

### Rows and fields

- **Rows.** A row's text is split at the delimiter into its columns' fields.
  A row ID is the row itself; 0 is none.
- **Column types:** string, float and time.
  - A float or time field keeps the number read from the text
    (`StringToFloat`, `0x100317c0`: a sign; octal after a leading `0` and
    hex after `0x`; a decimal point or comma; `'` adds the number so far as
    hours, `:` or `"` as minutes; anything else ends it).
  - A float field shows its number through the column's format, `%f` by
    default. A time field shows it as `%f` too: its own format
    (`%02h:%02m` by default) is not used.
  - A string field's number is 0.
- **Defaults** (`Init`, `0x1002e900`):
  - the delimiter is `;`;
  - auto sort is off, and auto-expanding columns, multiple selection and hot
    keys (column 0) are on;
  - the column margin is 3 and the row margin 1, and a double click counts;
  - there is one column.
- **A new column** (`0x100314f0`): 20 wide plus both margins, left-aligned,
  the window's text colour and font, string, and a sort key.
- **`GetField`** (`0x1002f250`) of a column that is not there is empty.
  **`GetSelectedRow`** (`0x1002f740`) is the focus row if it is selected, else
  the first selected row.

### Sorting

- **Keys.** Each column has a sort index: -1 is not a key, and the keys sort
  highest first. Up to 256 are used.
  - `SetSortColumn(col, bReverse, bCaseSensitive)` (`0x10030860`): that
    column first, then every other column in column order, their reverse and
    case flags cleared.
  - `AddSortColumn` (`0x10030980`) adds a column as the last key, and
    `RemoveSortColumn` (`0x10030a90`) drops one.
  - `ResetSortColumns(bSort)` (`0x10030b40`), true by default: every column
    a key, in column order, or with false none. Reverse and case are cleared.
- **The order** (`0x100326d0`): each key in turn. A float or time column
  compares numbers, a string column text with or without case, either
  reversed on request. Rows equal in every key keep their order.
- **When.** `Sort()` sorts at once (`appQsort`). `EnableAutoSort(true)`
  sorts, and while it is on a new row goes in at its place and a changed row
  is moved to its place (`0x10032b50`, `0x10032a70`). Changing the keys
  with auto sort on sorts again.
- **The game's lists.** The load game list sorts by a hidden column, the
  save's date as a number, with auto sort, and by name or date when the
  player clicks a header, reversing on a second click. The emails sort by
  sender or subject the same way. The conversation history, the images, the
  logs and a new game's skills are sorted too.

### Column widths

With auto-expanding columns, each field set widens its column to the field's
text plus both margins. Turning it on widens every column
(`ResizeColumns(true)`, `0x1002fc40`); `ResizeColumns(false)` first shrinks
every column to its margins.

### Moving, selecting, activating

- **`MoveRow(move, bSelect, bClearRows, bDrag)`** (`0x1002f790`) moves the
  focus row: up, down, a page up or down, first, last. It is clamped to the
  rows, and starts from the first row when there is no focus. A page is the
  rows that fit the list's clipped height (`GetPageSize`, at least 1). The
  list's script calls it for the arrow keys, Page Up and Down, Home and End.
- **A click** (`0x10033750`) selects the row under the pointer, the last row
  when below them all. Shift extends from the anchor; Ctrl toggles. Dragging
  moves the selection, scrolling every 0.1 s.
- **Activating.** A double click (`0x100339c0`) or Enter (`0x10033ca0`)
  activates the focus row: `ListRowActivated` to the list's parents, with
  the activate sound.
- **Notices.** Every change of selection calls `ListSelectionChanged` up the
  parents, and a new focus row plays the move sound (`MoveToRow`,
  `0x10032e30`).
- **Hot keys** (`0x10033ae0`): letters, digits and `_` typed within a second
  of each other search the hot key column for a row starting with them,
  case-blind.
- **`ShowFocusRow`** (`0x10033040`) asks the parent to scroll the focus row
  into view.

## Flags

`XFlagBase`: the player's flags, what missions and conversations set and
test.

- **Storage** (`FindName`, `0x10024e60`): 64 buckets, by a CRC of the flag's
  name in upper case. Each is a chain kept in order of hash, then type, so
  there is no limit to the flags. A flag is an object inside the flag base.
- **Setting** (`SetBool`, `0x10023c60`, and the other types alike):
  `Set*(name, value, bAdd, expiration)`, bAdd true and expiration -1 by
  default. It sets the flag, adding it with bAdd, and stamps its expiration
  each time: the one given, or the flag base's default for -1.
- **`GetExpiration`** (`0x10024a20`) is -1 for a flag that is not there.
- **Expiring.** An expiration of 0 never expires.
  `DeleteExpiredFlags(criteria)` (`0x10024ac0`) deletes every flag whose
  expiration is not 0 and at most the criteria.
- **The game's use.** `MissionScript.InitStateMachine` runs at every level:
  - on a level reached by travel (`PlayerTraveling`), it deletes the flags
    expired at the level's mission number;
  - then it sets the default expiration to that number plus 1.

  So a flag set without an expiration of its own lasts to the end of its
  mission. The conversations' `<name>_Played` flags are set so; barks set
  none. Most of the scripts' own flags carry one: the number of a later
  mission, or 0 for a few that never expire.

## Drawing

### Borders

`GC.DrawBorders` (`0x10028df0`) draws a box from nine textures: four
corners, four edges and a centre.

- **Margins.** Each side's margin is the largest of its textures: left from
  the two left corners and the left edge, and so on. A margin given above 0
  replaces it. When the box is narrower or shorter than two margins, both
  shrink in proportion.
- **The pieces.** The corners are drawn at one texel a pixel, from their
  inner corner. The edges and the centre are tiled at one texel a pixel
  (`DrawIconPattern`, `0x10028770`: a source size of 0 tiles), unless
  stretching is asked for across or down.
- **The game** passes no margins and no stretching in all 13 of its calls:
  the HUD's and the menus' frames are tiled.

### Actors in a window

`GC.DrawActor(actor, bClearZ, bConstrain, bUnlit, drawScale, scaleGlow, skin)`
(`0x1002aa60`) draws an actor through the renderer, into the scene being
drawn:

- with the GC's style, the glow and unlit given, its draw scale multiplied,
  and with a skin every skin replaced, as if not hidden;
- with `bConstrain` clipped to the window, with `bClearZ` over whatever the
  depth buffer holds;
- all of it put back afterwards.

`AugmentationDisplayWindow` uses it for the vision augmentation. From level
1, each heat source within range is drawn in a grid skin at twice its glow,
unlit, with or without a line of sight; it does not clear the depth buffer,
and what a wall in front does to it is the renderer's. The augmentation's
description promises sight through walls from its third level. A debug
window shows an actor with it too.

### Save pictures

`RootWindow.GenerateSnapshot(bFilter)` (`0x10039410`), after
`SetSnapshotSize(w, h)`:

- reads the rendered frame from the render device;
- averages it down to w × h, each pixel the mean of the pixels it covers;
- stores it in a new 8-bit texture, its sizes rounded up to powers of two
  (160 × 120 in a 256 × 128), in grey. The C++ can quantize to a palette of
  256 colours instead, and nothing asks it to.

`bFilter` is not used. The save's picture is the grey snapshot `SaveGame`
takes ([the game engine](deusex-dll.md#the-game-engine-travel-and-saving)).

## Small

- **Edit fields.** `Undo` (`0x1001e0a0`) and `Redo` (`0x1001e170`) walk a
  list of changes: each a position, the text removed and the text put in.
  Typing straight after the last change joins it (`AddUndo`, `0x10020450`),
  and the list keeps at most `maxUndos`. `ClearUndo` empties it. The script's
  Ctrl+Z and Ctrl+Y call them.
- **Tab groups.** `MoveTabGroupNext` and `MoveTabGroupPrev` (`0x100033f0`,
  `0x10003400`) move the focus to the next or previous tab group; the root
  window's script calls them for Tab and Shift+Tab. `GetTabGroupWindow`
  (`0x1004c560`) is the nearest tab group at or above a window.
- **`GetTickOffset`** (`0x1004fda0`): the real time since the windows were
  last ticked.
- **Text windows.** `ResetLines` (`0x10046310`) and `ResetMinWidth`
  (`0x10046450`) lift a text window's line limits and minimum width,
  `LargeTextWindow.SetVerticalSpacing` (`0x1002d7e0`) sets the space between
  lines (not below 0), and `RadioBoxWindow.GetEnabledToggle` (`0x10015970`)
  is the box's selected toggle. No script calls them.
- **`ExtString.GetNextTextPart`** (`0x10044ad0`): the text in parts of 239
  characters, a part a call. No script calls it.
- **No script calls** `GC`'s `PushGC`, `PopGC`, `CopyGC` and `Intersect`,
  `ClipWindow`'s unit sizes, or the 22 `ComputerWindow` natives the fork
  stubs ([not needed](natives.md#not-needed-for-single-player)).

## The database

`gamefiles/System/Extension.dll.i64` has the class layouts, the UTF-16
strings and the initializers' names ([working on the binaries](README.md#working-on-the-binaries)).
By hand it has the list's row comparison (`XListWindow_CompareRows`) and its
sort keys (`GListSortCols`, `GListNumSortCols`), and
`Extension_RegisterNames`. Each function above carries a one-line comment.
