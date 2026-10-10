# Extension.dll

The native half of package Extension, Ion Storm's own:

- the UI's window system: `Window` and its subclasses (text, lists, edit
  fields, scrolling, tab groups, the computer terminal's window);
- the graphics context `GC` that draws them;
- the flag base behind every mission and conversation flag;
- the game engine and input classes that put the UI in front of the game.

How it was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 675,840 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `5f03bd11022e45a44ed8de95e385009cacd0c41c` |
| Exports | 2,395: 36 classes, 453 `exec` natives |
| Functions | 2,551 |

- An export is its code, not a jump to it, as in `DeusEx.dll`.
- It registers the 36 classes it exports. 34 match the layout of their
  script. `XGameEngineExt` and `XInputExt` are C++ only (the SDK's
  `Extension/Inc/ExtGameEngine.h` and `Extension/Inc/ExtInput.h`).
- **Native arrays.** The script declares the classes' native arrays, and
  ConSys's, as `DynamicArray`: three ints named `Num`, `Max` and `Ptr`. They
  are a `TArray`'s data, count and capacity, whatever the names say.
  [`tools/ida/ue1_types.py`](tools/ida/ue1_types.py) types them as
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
    `DrawWindow` and the rest; `Extension_RegisterNames`).
  - `Browse` (`0x10026330`), after a level loads, makes the player's root
    window.
  - `Tick` (`0x100266a0`) ticks the windows, then the engine. The windows
    tick by the real time since they last ticked (`TickWindows`,
    `0x1003a4a0`, by `GetWindowsTickOffset`, `0x1003a3b0`), not the level's.
    `GetTickOffset` (`0x1004fda0`) is that time at any moment: a timer
    added, and a held button's or scale's first repeat, count what of the
    frame has gone.
  - The mouse's position and movement go to the player's root window first
    (`0x100264b0`, `0x10026580`). Typed characters go to it after the
    console (`0x10026650`).
  - `Destroy` destroys every window first.
- **`XInputExt`**, the input: `Process` (`0x1002d0b0`) gives each key to the
  root window first.
  - When the root window takes one, the input runs the release binding of
    every key it holds down. Nothing stays held under a menu: a movement key
    held when the menu opens is released then.
  - Otherwise it runs the key's binding itself: a press once per hold, and a
    release only after a press.

### The root window

- **What it takes** (`Process`, `0x1003b3e0`): every key while any window has
  grabbed the keyboard, and every mouse button while any window has grabbed
  the mouse. Taking a button clears the player's `bFire` and `bAltFire`.
  Every modal window grabs both while it is shown: the menus and the game's
  screens. The root marks every press and release of a key or button, taken
  or not; a release of one not down is taken, while the grab holds, and goes
  to no window. With no grab it goes to the game as any other. `IsKeyDown`
  (`0x1004c980`) reads those marks.
- **Keys** go to the focus window, else the topmost modal window, then up its
  parents until one handles them: `RawKeyPressed`, then, for a press,
  `VirtualKeyPressed`. Typed characters go the same way as `KeyPressed`.
  Windows that are not modal pass them over while Alt is down.
- **Accelerators**: a character the modal's script leaves, with Alt down
  and the modal on top, goes to the window whose accelerator it is
  (`XModalWindow::KeyPressed`, `0x10037510`; `GetAcceleratorWindow`,
  `0x100372a0`) as `AcceleratorKeyPressed`, by which the base button script
  presses the button. The modal's table (`SetAcceleratorWindows`,
  `0x10036a50`, built again once marked dirty) holds for each key the first
  window -- the modal, then its shown children bottom to top, each in
  turn, passing over a modal inside and an insensitive window's children --
  that shows, is sensitive with every parent and is selectable; a letter
  under both its cases.
- **Mouse buttons** (`HandleButtons`, `0x1003b960`) go to the window the
  mouse acts on (`GetMouseWindow`, `0x1003b0d0`): the one that grabbed it,
  else the one under the pointer in the topmost modal, else that modal.
  Under the pointer (`FindWindowByPoint`, `0x1004f740`) is the deepest
  window that shows, is sensitive and holds the point, passing over other
  modals. From there the button goes up the parents, each asked
  `RawMouseButtonPressed`, then `MouseButtonPressed` or
  `MouseButtonReleased`, until one handles it.
  - A press grabs the mouse for that window and, when the modal's
    `focusMode` is set, gives focus to it or its nearest selectable parent.
    A release of any button lets that window's grab go before it is passed
    on.
  - Presses of one button on one window, each within `multiClickTimeout`
    (0.5 s, set by `Init`) of the last and `maxMouseDist` (10 units) of the
    first, count up, wrapped at the window's `maxClicks`, so a list sees a
    double click as 2. The clock is real time
    (`GetWindowsTickOffset`, `0x1003a3b0`).
- **`LockMouse(bLockMove, bLockButton)`** (`0x1003a290`): with movement
  locked the pointer stays where it is; with buttons locked the UI takes and
  ignores them. The Customize Keys screen locks movement while it waits for
  a key.

### Showing and hiding

- **`Show` and `Hide`** (`SetVisibility`, `0x1004c7d0`) ask the window's
  parent. Its `ChildRequestedVisibilityChange` event decides; the script's
  default calls `SetChildVisibility`. The root window, having no parent,
  sets its own.
- **`SetChildVisibility(bNewVisibility)`** (`0x1004ee20`) sets the window's
  flag. When that changes whether it can be seen, it:
  - moves focus and grabs away from what is hidden;
  - sends `VisibilityChanged` to the window and to its descendants, each
    then playing its `visibleSound` or `invisibleSound`;
  - lays the tree out again.
- **A new window** (`NewChild`, `CreateNewWindow`, `0x1004df70`) starts
  hidden. Its parent gets `ChildAdded`, then the parent and each ancestor
  `DescendantAdded`, all before the window's `InitWindow`. Then, unless
  `NewChild` was asked not to, it is shown as `Show` shows it, so
  `VisibilityChanged` reaches it and every window its `InitWindow` made.
- **`DeusExHUD`** overrides the event to lay the HUD out again as its parts
  come and go, the InfoLink and the log among them.
- **`Destroy`** (`SafeDestroy`, `0x1004c0b0`, through `PreDestroy`,
  `0x10050500`, and `CleanUp`, `0x1004bec0`), once per window:
  1. a window that shows is hidden, as by `Hide`, and the window is made
     unselectable, so the focus and grabs move away from it;
  2. its children are destroyed, first to last;
  3. it gets `DestroyWindow`;
  4. its parent gets `ChildRemoved` and every ancestor `DescendantRemoved`
     (a modal's lets go of its `preferredFocus` when that is the window,
     `0x10037400`);
  5. the root lets go of it as the window under the mouse and as the grab;
     its timers go, and it leaves its parent.

  The object is deleted unless its `lockCount` holds it.
- **The pointer** (`XRootWindow::PaintWindows`, `0x1003ac18`) is drawn last,
  while a window takes the mouse (every modal one does) and the root's
  `bCursorVisible` holds. `Init` sets that as the root starts; `ShowCursor`
  clears and sets it. The game hides the pointer while a conversation plays
  (but for its choices), while a key waits to be bound, while the credits
  roll, and while its multiplayer HUD and message window are up.

### Keyboard focus

- **Window types** (`windowType`):

  | Value | Window |
  |---|---|
  | 0 | any other window |
  | 1 | a tab group (`XTabGroupWindow::Init`, `0x10044d90`) |
  | 2 | a modal (`XModalWindow::Init`, `0x10036c00`) |
  | 3 | the root |

  A modal that is not the root's child logs "Modal window must be a child
  of Root!" and stays 1. A modal and the root are tab groups too, so a
  conversation window is its choices' group.
- **The tables.** A tab group lists its selectable windows twice
  (`ResortWindowTables`, `0x10045140`) by where each lies on the screen (its
  clip rectangle's corner): by row (top to bottom, then left to right) and
  by column (left to right, then top to bottom), ties broken by address. It
  keeps each window's index in both. `SetSelectability` (`0x1004c390`) puts
  a window in its group's lists or takes it out (`AddWindowToTables`,
  `0x10045350`).
- **A modal's tab groups.** A modal keeps a table of its tab groups: itself
  (`XModalWindow::Init`) and each tab group made under it. It is sorted top
  to bottom, then left to right, by each group's place: that of its first
  traversable window (`ComputeTabGroupLocation`, `0x10045000`).
- **The focus moving off** (`CheckFocusWindow`, `0x10050b80`), which
  `SetChildVisibility` and `SetSelectability` call: a focus window that is no
  longer traversable with the modal check goes to the topmost modal's (or
  the root's) `preferredFocus` when that is traversable, else on as
  `MoveFocus` right moves it, and to none when that leaves it where it was.
  A grab (`CheckGrabbedWindow`, `0x10050c90`) is let go when the window or a
  parent is hidden or insensitive.
- **`XWindow::IsTraversable`** (`0x1004c460`): a window can take the focus
  when it is selectable, and it and every parent are visible and sensitive.
  With the modal check, its nearest modal (or the root) must also be the
  topmost modal: the root's topmost child that shows and is a modal, or the
  root when none is. Nothing under a buried modal takes it.
- **`XWindow::MoveFocus`** (`0x1004ef30`), behind `MoveFocusLeft`,
  `MoveFocusRight`, `MoveFocusUp` and `MoveFocusDown`, steps from the focus
  window to the first window traversable with the modal check:
  - along its group's row list for left and right, its column list for up
    and down;
  - backward for left and up;
  - round the ends (a tab group's default).

  With none in the list, or no focus at all, it hands the move to
  `MoveTabGroup`. Both return the focus window, moved or not.
- **`XWindow::MoveTabGroup`** (`0x1004f440`) works in the topmost modal (or
  the root). `MoveTabGroupNext` and `MoveTabGroupPrev` call it forward and
  back ([small](#small)). It starts at the tab group after or before the
  focus's, or at the table's first when the focus is not in that modal. The
  first window of a group's row list traversable without the modal check
  takes the focus. A group with none is passed over the same way, round the
  ends.
- **`SetFocusWindow`** (`0x1004f0e0`) gives the focus to the nearest
  selectable window at or above the one asked for, only when that is
  traversable with the modal check, and its modal keeps it as its
  `preferredFocus`. The window that had the focus gets `FocusLeftWindow`
  and its unfocus sound, and it and each ancestor `FocusLeftDescendant`; the
  new one is shown (`AskParentToShowArea` of all of it, so a clip window
  scrolls to it), plays its focus sound and gets `FocusEnteredWindow`, and
  it and each ancestor `FocusEnteredDescendant`. None asked for clears the
  focus. A window not yet shown -- one a screen's `InitWindow` makes before
  it shows itself -- does not take it.
- **The root's tick** (`XRootWindow::Tick`, `0x1003a540`), while nothing has
  the focus: the topmost modal (or the root, with none up) gives the focus to
  its `preferredFocus` when that is traversable with the modal check, else as
  `MoveTabGroup` forward does from the table's first group. It does not when
  its `focusMode` is `MFOCUS_EnterLeave` (3). So a conversation's first
  choice takes the focus as the choices appear. The keypad
  (`HUDKeypadWindow`) sets `MFOCUS_EnterLeave`.
- **What takes no focus.** A scroll area makes its scales, its four buttons
  and itself unselectable (`XScrollAreaWindow::Init`, `0x10042d80`): the
  focus goes to what it holds, a list or a text. A list, an edit field, a
  computer window and a button make themselves selectable (their `Init`).

### Window sounds

`PlaySound(sound, volume, pitch, posX, posY)` (`0x10050050`) plays one unit
from the player.

- With the root window's positional sound on, the sound is turned left or
  right by the point's place across the screen, a quarter turn at either
  edge. Otherwise it is straight ahead.
- The point defaults to the window's centre, and the volume to the window's
  own.

## Layout

- **A new window** (`XWindow::Init`, `0x1004bb30`) is 10 by 10 at its
  parent's corner, left- and top-aligned with no margins and no size set.
- **`SetPos(x, y)`** (`Move`, `0x1004ce80`) makes the window left- and
  top-aligned with x and y its margins. **`SetSize`**, `SetWidth` and
  `SetHeight` (`Resize`, `0x1004cf70`) set its size, none below 0;
  `ResetSize` takes it away; `SetConfiguration` (`Configure`, `0x1004cd40`)
  does both. **`SetWindowAlignments`** (`0x1004d300`) sets the alignments
  and all four margins -- from a script (`0x10052360`) a first margin not
  given is 0, a second the first. Each lays the window out again when it
  changes anything.
- **Its preferred size** (`QueryPreferredSize`, `0x1004e790`): a side the
  window has a size for counts as asked for. With a side not asked for, the
  window says (`ParentRequestedPreferredSize`), -1 standing for that side;
  a side it leaves below 0 is its background's size, else its own size now.
  The answer is kept while it is asked the same, until the window next asks
  to be laid out. `QueryPreferredWidth` and `QueryPreferredHeight`
  (`0x1004e5f0`, `0x1004e680`) ask it with the other side given.
  - So a plain window stays 10 by 10, and an empty text window is 0 wide --
    its minimum width takes the -1 ([text](#text)) -- and keeps its height.
- **Laying out again** (`AskParentForReconfigure`, `0x1004e060`) marks the
  window and, if it and every parent show, asks its parent
  (`ChildRequestedReconfiguration`); a parent that does not take it asks its
  own, up to the root, which lays itself out. A window still marked then,
  which no parent placed, places itself by its alignment at its preferred
  size (`ResizeChild`, `0x1004eab0`): centred (the half truncated) plus its
  first margin, right less it, else at it; full, the parent's size less
  both margins. The base `Window` script takes every child's request by
  placing the child so.
- **A parent laid out** (`ChangeConfiguration`, `0x10050f90`) counts its
  left- and top-aligned children as placed; after its
  `ConfigurationChanged`, each other child that shows and that it did not
  place places itself by its alignment.
- **`ConfigureChild(x, y, w, h)`** (`0x1004ec50`) sets just what it is given
  -- a size set on the window is only what it asks for -- and the window
  gets `ConfigurationChanged` when its size changed or it was marked. A
  window that does not show is only counted as placed.
- **Showing an area** (`AskParentToShowArea(x, y, w, h)`, `0x1004e230`;
  from a script, 0, 0 and the window's own size for a size of 0): of the
  area, the part inside the window; when the window's parents clip any of
  that, its parent is asked to show it (`ChildRequestedShowArea`) -- a clip
  window scrolls to it -- and then asks its own parent, the area in its
  coordinates. Only a window that shows asks.
- **Granularity** (`QueryGranularity`, `0x1004e9e0`), the steps a window
  scrolls by, at least 1 each way: a text window's line (its font's height
  with the line spacing, `0x10046880`), a large text window's (its font's
  height, at least 1, plus its vertical spacing, `0x1002e380`), a list's
  row, and with equal widths or heights a tile's child and its spacing
  (`0x10048860`). The script's event has the last say, but for a tile's.

## Text

- **The GC** (`XGC`) draws with word wrap and special text on, a line
  spacing of 1, and an underline 1 high, 2 up from a character's foot, in
  its class's underline texture (`Solid`).
- **Codes** (`GetNextChar`, `0x100294d0`), with special text on: `|b` bold;
  `|c` and up to three hex bytes a colour; `|p0` to `|p7` a palette colour
  (black, white, red, green, yellow, blue, magenta, cyan); `|&` the next
  character an accelerator, underlined; each undone by `|!` before it
  (`|!c` and `|!p` back to the GC's text colour). Any other `|x` is x.
- **Lines** (`ParseLine`, `0x10029ae0`) break at spaces; the first
  character always fits; trailing spaces count unless the line broke there;
  a final line break makes one more, empty line. A width of 0 or less is
  taken as 500,000: `GetTextExtent(0, ...)` measures each line whole. The
  multiplayer message window measures its progress lines so, before drawing
  them in a box of that width.
- **Measuring** (`GetTextExtent`, `0x10027bb0`): the widest line, and each
  line as tall as its tallest character (a space when it has none) plus the
  line spacing.
- **Drawing** (`DrawText`, `0x10028180`) clips to its box. It hands its wrap
  width (the width with word wrap on, 0 with it off) only to line breaking,
  and places the lines in the width and height it was given: centred by the
  whole half the room left, right-aligned, or (full) left. A character
  (`DrawChar`, `0x10029e40`) lands on whole pixels; a font's character is
  found on its page alone, none from another.
- **`|n`** becomes a line break as a script sets text (`ConvertScriptString`,
  `0x10050710`, by `SetText`, `AppendText` and `InsertText` alone), so
  `GetText` gives the break.
- **A text window** (`XTextWindow::Init`, `0x10045af0`): margins of 3,
  centred both ways, word wrap on, no line limits, no minimum width, its
  text its accelerator. `SetText` (`0x10045d50`) takes no text that differs
  only in case; it and `AppendText` (`0x10045e60`, laid out again even for
  nothing added) keep the accelerator with the text while the text is the
  accelerator (`EnableTextAsAccelerator`, `0x100464e0`, on when a script
  gives no value; `SetAcceleratorText`, `0x1004f310`: the character after
  the first `|&`, none past 254). It draws (`Draw`, `0x10046930`) its
  alignments and word wrap into the GC, the script's `DrawWindow`, then its
  text within the margins. Its size (`ParentRequestedPreferredSize`,
  `0x100465a0`), with its own fonts and text settings: the text's extent --
  wrapped at the width given less the margins with word wrap on -- held
  within the line limits when no height is given, plus the margins; with no
  text its background's size, else the script's say. A width not given is at
  least the minimum width: an empty text window is 0 wide.
- **A large text window** (`XLargeTextWindow`, `Init` `0x1002d480`) lays its
  text out in rows (`GenerateLines`, `0x1002da70`) spaced by its vertical
  spacing (1) and is not its accelerator. Its size (`0x1002e1d0`): rows of
  the font's height, at least 1 (`ComputeLineHeight`, `0x1002d9d0`), the
  spacing between rows alone -- an empty text one row high -- as wide as
  the widest, wrapped as a text window's; a line limit its own rows pass
  holds it to that many rows of the font's height and line spacing, its
  vertical spacing between. It draws (`Draw`, `0x1002e500`) only the rows
  its clip shows, the block of rows placed by its alignment -- centred by
  the whole half of the room, margins and all -- each row by its own.
- **An edit field** (`XEditWindow::Init`, `0x1001cea0`): from the top left,
  3 in from the sides; editable and on several lines -- no game script
  makes one single-line, so Enter is the script's line break in every one;
  a white insertion point and grey selection; up to 200,000 characters and
  64 undos; the cursor blinking each second after 0.75 s; no special text;
  selectable. Measured (`0x10020ac0`) as a large text window, a single line
  as one line high, a width not given a space wider.
  - A script's `SetText` (`0x1001e260`) selects the whole text and puts the
    new one in as typing does (`InsertText`, `0x1001e3c0`, without undo:
    the undo list cleared, the text marked changed), then sets the
    insertion point at the start; `AppendText` (`0x1001e310`) puts its text
    in at the end, the insertion point then at the start too.
  - A change of anything (`ReplaceText`, `0x1001fe20`) announces
    `TextChanged` to the field and up its parents until one takes it
    (`ChangeText`, `0x1001fab0`), lays the field out again and leaves the
    insertion point after what it put in.
  - With nothing selected the selection is -1, so `GetSelectedArea`
    (`0x1001d5c0`) gives 0 and 0.

## Buttons

- **Defaults** (`XButtonWindow::Init`, `0x10007640`): no repeat, a press
  from the keyboard shown 0.3 s, a held repeat after 0.5 s every 0.1 s, no
  sounds, white tiles and green text in every state, selectable.
- **The mouse**: the script first; then the left button, or the right
  where `EnableRightMouseClick` is on:
  - a press (`0x10007bd0`) shows the button pressed; one that repeats
    activates at once with its click sound, any other plays its press sound;
  - held (`Tick`, `0x10008190`), one that repeats activates again with its
    click sound every repeat rate while the pointer is over it, the first
    after its initial delay;
  - while held (`MouseMoved`, `0x10007e30`), it shows pressed only with the
    pointer over it;
  - the release (`0x10007d10`) lets it go; over it, one that does not repeat
    plays its click sound and activates.
- **Activating** (`ActivateButton`, `0x100077e0`) sends `ButtonActivated` up
  the parents until one takes it; a right click, `ButtonActivatedRight`, a
  script function `Window` declares no event for (the game's menu choices
  step back a value by it).
- **From the keyboard or a script** (`PressButton`, `0x10007b20`, Space by
  default), the button shows pressed for its activate delay, plays its
  click sound and activates. The script's Enter, Space and accelerator
  press it.
- **Made insensitive** while the mouse holds it, it lets go
  (`SensitivityChanged`, `0x10007f10`).
- **Its look** (`ChangeButtonAppearance`, `0x10008380`):
  - the insensitive pair of textures and colours when the button or a parent
    is insensitive;
  - else the focused pair while it has the focus;
  - else the normal pair.

  Of the pair, the pressed one while pressed. A state with no texture takes
  the pressed one while pressed, else the normal one.
- **The game's** menu buttons click `Menu_Press`; the scroll arrows repeat.
- **A toggle** (`XToggleWindow`) keeps its state in the pressed flag, so one
  on looks pressed. The left button released over it flips it
  (`0x10049b30`), after the sound of the state it leaves -- the enable
  sound as it turns off; the press is taken and shows nothing. From the
  keyboard (`PressButton`, `0x10049c30`) it flips, then plays the sound of
  its new state. `SetToggle` sends `ToggleChanged` up the parents when the
  state changes, and `ChangeToggle` sends it without changing it. A toggle
  never activates.
- **A checkbox** (`XCheckboxWindow`, `Init` `0x1000a710`): the box -- the
  on or off texture, at the size given or the larger texture's -- 3 from its
  text, on the left unless put on the right. It draws (`Draw`, `0x1000aad0`)
  the script's `DrawWindow`, its text in the button's text colour for its
  state, a line down from the top margin, beside the box, which is centred
  down the window; no button texture. Its size (`0x1000acb0`) is a text
  window's plus the box and its spacing beside the text, never smaller than
  the box within the margins.
- **A radio box** (`XRadioBoxWindow`) holds the toggles under it with no
  nearer radio box (`DescendantAdded`, `0x10038b90`), one of them on at a
  time (`ToggleChanged`, `0x10038a60`): a toggle turned on becomes the one,
  the last one turned off; while one must be on (`bOneCheck`, set by `Init`)
  the one on cannot be turned off, and another's turning off is taken
  without a word; the rest goes to the script. It sizes its shown children
  to itself (`0x10038840`) and asks for the largest of their sizes.

## Scales and scrolling

- **A scale** (`XScaleWindow`, `Init` `0x1003d200`) keeps a tick position
  among its ticks, 10 by default. A slider's thumb sits on a tick; a
  scrollbar's (`SetThumbSpan` of 1 or more, `0x1003de40`) spans that many,
  stopping that many short of the end.
  - **Values** (`TickToValue`, `0x1003ebb0`): the ticks share the value
    range, 0 to 1 by default, evenly (a scrollbar's one more than it has).
    `SetValue` goes to the nearest tick, halves away from 0, and `GetValue`
    reads the tick's value.
  - **The value text** (`GetValueString`, `0x1003e460`): the tick's own text
    (`SetEnumeration`, ticks 0 to 511) when it has one, else the value
    through the value format, `%1.2f` by default.
  - **A move** (`ChangeThumbPosition`, `0x1003f170`) is held to the ticks. A
    new position goes up the parents until one takes it, as
    `ScaleRangeChanged` from a scrollbar or `ScalePositionChanged` from a
    slider; a new position, count or span sends `ScaleAttributesChanged`,
    from a scale that shows. A new range, format, or text for the position
    sends the move again.
  - **Steps** (`MoveThumb`, `0x1003e860`): a step is the thumb step (1 by
    default, at least 1), a page a scrollbar's span or a slider's 4 ticks.
    The script's arrows step it, and Home, End, Page Up and Page Down move
    it.
  - **The mouse** (`0x1003fdc0`, `0x10040030`, `0x10040150`): on the thumb
    the left button drags it, the move sent as not final until the release;
    on a slider's scale it drags from there, the thumb jumping to the tick;
    beside a scrollbar's thumb it pages toward the click, and while held and
    still beside it again every 0.1 s after 0.5 s (`Tick`, `0x10040250`;
    across, the far side is measured by the thumb's height). Each with the
    scale's click, drag and set sounds.
  - **The geometry** (`ConfigurationChanged`, `0x1003f8f0`;
    `ComputeThumbConfig`, `0x1003ed60`): the scale centred in the window, a
    stretched one (`EnableStretchedScale`, its texture then repeated) filling
    its length within the margins; the ticks run from its start offset to
    its end offset, inside its border. The thumb is its texture with its
    caps added along the scale, centred across; a scrollbar's is as long as
    its span's share of the scale, 6 at least, its caps cut to fit.
  - **Drawing** (`Draw`, `0x1003fb10`), with no script `DrawWindow`: the
    scale, the ticks (the end ones unless left out), then the thumb with its
    caps, each within its border, tiled across it, and along it when
    repeated.
- **A scale manager** (`XScaleManagerWindow`) lines its shown children up
  along its orientation, each at its preferred size and placed across by
  the child alignment; the room left goes to the scale and the value field
  that stretch, shared evenly if both do (`ConfigurationChanged`,
  `0x10042260`). Its arrows step its scale (`ButtonActivated`,
  `0x10042720`). The decrement arrow is sensitive unless the scale is at its
  start, the increment arrow unless its span reaches the end
  (`ScaleAttributesChanged`, `0x10042640`); the value field shows the value
  text.
- **A scroll area** (`XScrollAreaWindow`, `Init` `0x10042d80`): for each
  axis a scale manager, made hidden, with an arrow, a scrollbar of one tick
  spanning one, and an arrow, then a clip window; the arrows repeat; only
  vertical scrolling is on; margins and the scrollbar distance are 3, and a
  bar hides while not needed.
  - **Sizes** (`ComputeChildSizes`, `0x100432d0`): the clip window within
    the margins, each shown bar beside it at the distance. A bar that hides
    shows only while the clip's child does not fit: the sizes are tried with
    the bars as last shown, then a bar put in or taken out as the fit asks,
    a try for each, all shown if that does not settle it; a hidden bar keeps
    its place at no width. Down, the size asked for adds the margin width
    twice, not the height.
  - **Events**: the clip window's size and its child's in units become the
    scales' spans and tick counts (`ClipAttributesChanged`, `0x10043b50`),
    its position their ticks (`ClipPositionChanged`, `0x10043c40`), and a
    scale's first tick the child's position (`ScaleRangeChanged`,
    `0x10043a50`). The wheel steps the vertical scale while it shows
    (`MouseButtonPressed`, `0x10043d10`).
- **A clip window** (`XClipWindow`, `Init` `0x1000b320`) shows a larger
  child -- its topmost shown one -- moved by whole units: the child's
  granularity while it snaps to units (on by default), else pixels.
  - **Laying out** (`ConfigurationChanged`, `0x1000c560`; `ReconfigureChild`,
    `0x1000c0e0`): the child as wide or high as the clip on an axis whose
    size is forced, at its preferred size on another; filling the clip when
    smaller (on by default); placed at its position in units and kept over
    the clip. Its size and the clip's in units go up as
    `ClipAttributesChanged` when they change.
  - **`SetChildPosition`** (`0x1000b470`) moves the child, but along a forced
    axis, keeps it over the clip and sends `ClipPositionChanged`.
  - **Showing an area** (`ChildRequestedShowArea`, `0x1000c360`): the child
    moved by the least whole units that bring the area in, its start when it
    does not fit.
  - Its preferred size is its child's, or a preferred size in units
    (`SetUnitSize`). `ResetUnitHeight` resets the width in units, not the
    height; no script calls it.

## Tiles and tab groups

- **A tile** (`XTileWindow`, `Init` `0x10048360`): left to right, wrapping,
  filling its parent, equal heights, margins of 3, 1 between children and
  between rows, each child as thick as its row.
  - **Layout** (`ComputeChildSizes`, `0x10048a90`): each shown child at its
    preferred size -- a tile that fills its parent and does not wrap gives
    each its space across less the margins -- made as wide and high as the
    widest and highest where those are equal. The children go into rows
    along the orientation, from the side its directions say, a new row where
    the next would pass the space less the margins; each row as thick as its
    thickest child, each child placed across it by the child alignment
    (centred by a whole half; full, made as thick as the row). Its preferred
    size is the rows' plus the margins.
  - `SetOrder` (`0x10048560`) sets the orientation, both directions and
    whether it wraps. Each setter lays the tile out again. A child's request
    goes on up (`ChildRequestedReconfiguration`, `0x100421d0`, takes none).
- **A tab group** (`XTabGroupWindow`) -- every modal, the root and a clip
  window are ones -- sizes itself to its children unless told not to
  (`bSizeParentToChildren`, on by `Init`, `0x10044d90`): the largest of its
  shown children's sizes, each with its margins unless they are sized to it
  (`0x10045700`); with neither, the script's say. With
  `bSizeChildrenToParent` it sizes its shown children to itself
  (`ConfigurationChanged`, `0x10045640`), else its layout is the script's.
  `MenuUIWindow` turns the first off, for its script's.

## Lists

`XListWindow`: the load and save screens, emails, the logs, images, the
conversation history, the key bindings, the colour themes, the skills of a
new game.

### Rows and fields

- **Rows.** A row's text is split at the delimiter's first character into a
  field for each column (`FillRow`, `0x100322a0`): a field past the last
  column is dropped, a column past the last field gets an empty one, and a
  field keeps at most 2,047 characters. A row ID is the row itself; 0 is
  none.
- **Column types:** string, float and time.
  - A float or time field keeps the number read from the text
    (`StringToFloat`, `0x100317c0`): a sign; octal after a leading `0` and
    hex after `0x`; a decimal point or comma; `'` adds the number so far as
    hours, `:` or `"` as minutes; anything else ends it.
  - A float field shows its number through the column's format, `%f` by
    default. A time field shows it as `%f` too: its own format (`%02h:%02m`
    by default) is not used. The field's text is that shown text:
    `GetField` gives `1.000000` for a float field set to `1`.
  - A string field's number is 0. `SetFieldValue` on one sets its text to
    the number as `%f`.
  - `SetColumnType` (`0x10030480`) sets every row's field again from its
    text as the new type reads it.
- **Defaults** (`Init`, `0x1002e900`):
  - the delimiter is `;`;
  - auto sort is off; auto-expanding columns, multiple selection and hot
    keys (column 0) are on;
  - the column margin is 3 and the row margin 1, and a double click counts;
  - there is one column.
- **A new column** (`0x100314f0`): 20 wide plus both margins, left-aligned,
  the window's text colour and font, string, and a sort key.
- **`GetField`** (`0x1002f250`) of a column that is not there is empty.
- **`GetSelectedRow`** (`0x1002f740`) is the focus row if it is selected,
  else the first selected row.

### Sorting

- **Keys.** Each column has a sort index: -1 is not a key, and the keys sort
  highest first. Up to 256 are used.
  - `SetSortColumn(col, bReverse, bCaseSensitive)` (`0x10030860`): that
    column first, then every other column in column order, their reverse and
    case flags cleared.
  - `AddSortColumn` (`0x10030980`) adds a column as the last key;
    `RemoveSortColumn` (`0x10030a90`) drops one.
  - `ResetSortColumns(bSort)` (`0x10030b40`), true by default: every column a
    key, in column order; with false, none. Reverse and case are cleared.
- **The order** (`XListWindow_CompareRows`, `0x100326d0`, over the keys in
  `GListSortCols` and `GListNumSortCols`): each key in turn. A float or time
  column compares numbers, a string column text with or without case, either
  reversed on request. Rows equal in every key keep their order.
- **When.** `Sort()` sorts at once (`appQsort`). `EnableAutoSort(true)`
  sorts; while it is on, a new row goes in at its place and a changed row is
  moved to its place (`0x10032b50`, `0x10032a70`). Changing the keys with
  auto sort on sorts again.
- **The game's lists.** The load game list sorts by a hidden column, the
  save's date as a number, with auto sort, and by name or date when the
  player clicks a header, reversing on a second click. The emails sort by
  sender or subject the same way. The conversation history, the images, the
  logs and a new game's skills are sorted too.

### Column widths

With auto-expanding columns, each field set widens its column to the field's
text plus both margins. Turning it on widens every column
(`ResizeColumns(true)`, `0x1002fc40`). `ResizeColumns(false)` first shrinks
every column to its margins.

### The list's size

- **What it asks for** (`ParentRequestedPreferredSize`, `0x10033260`): the
  visible columns' widths side by side, and a row size for each row. The
  clip window a list sits in sizes it so. The scroll area around it scrolls
  a row at a time (`ParentRequestedGranularity`: 1 across, a row size down).
- **The row size** (`ComputeRowSize`, `0x10031fd0`): the tallest of the
  columns' fonts, by the height of a space, plus the row margin above and
  below.
- **When it changes.** Each of these asks the parent to lay the list out
  again (`AskParentForReconfigure`): adding, changing or deleting rows;
  setting a field's text or number when that widens its column
  (`0x1002f170`, `0x1002f2f0`); a column's number, width, font, title or
  hiding; the margins.

### Moving, selecting, activating

- **The selection and the focus row** move together (`MoveToRow`,
  `0x10032e30`). `SetRow(row, bSelect, bClearRows, bDrag)` (`0x1002f8c0`;
  the script's defaults true, true, false) clears the selection, selects
  the row and gives it the focus and the anchor; with `bDrag` it selects the
  span from the anchor instead, the old span let go. A single selection list
  always clears and never spans. `ListSelectionChanged` goes up the parents
  only when the selection changed; a new focus row plays the move sound.
  `SetFocusRow(row, bMoveTo, bAnchor)` (`0x1002f970`, defaults true, true)
  moves the focus alone; `SelectRow` (`0x1002f480`) selects alone, a single
  selection list letting go of the others first; `SelectToRow`
  (`0x1002f600`) moves the selection, not the focus.
- **Shown** (`VisibilityChanged`, `0x10033d90`), a list with rows and no
  focus row selects and focuses its first. A screen that fills a list in its
  `InitWindow` so selects the first entry as it opens: the images, the logs,
  the load game list.
- **`MoveRow(move, bSelect, bClearRows, bDrag)`** (`0x1002f790`) moves the
  focus row: up, down, a page up or down, first, last, then as `SetRow`. It
  is clamped to the rows; with no focus every move but to the last lands on
  the first row. A page is the rows that fit the list's clipped height
  (`GetPageSize`, at least 1). The list's script calls it for the arrow
  keys, Page Up and Down, Home and End.
- **A click** (`0x10033750`) selects the row under the pointer, the last row
  when below them all. Shift extends from the anchor; Ctrl toggles. Dragging
  moves the selection, scrolling every 0.1 s.
- **Activating.** A double click (`0x100339c0`) or Enter (`0x10033ca0`)
  activates the focus row: `ListRowActivated` to the list's parents, with
  the activate sound.
- **Notices.** Every change of selection calls `ListSelectionChanged` up the
  parents. A new focus row plays the move sound (`MoveToRow`,
  `0x10032e30`).
- **Hot keys** (`0x10033ae0`): letters, digits and `_` typed within a second
  of each other search the hot key column for a row starting with them,
  case-blind.
- **`ShowFocusRow`** (`0x10033040`) asks the parent to scroll the focus row
  into view.

## Flags

`XFlagBase`: the player's flags, what missions and conversations set and
test.

- **Storage** (`FindName`, `0x10024e60`): 64 buckets, by the low six bits of
  the flag's name hashed with UE1's `appStrihash`
  ([names](core-dll.md#names-hashed-and-compared)). Each bucket is a chain
  kept in order of the hash, compared as a signed number, then of type, so
  the flags have no limit. A flag is an object inside the flag base.
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

### Styles

- **`GC.SetStyle`** (`0x10027170`) sets only how tiles draw. `DSTY_None`
  stops drawing and leaves the rest. Any other style draws: `DSTY_Masked`,
  `DSTY_Translucent` or `DSTY_Modulated` with that one of the three, and
  `DSTY_Normal` with none.
- **A tile's flags** (`GeneratePolyFlags`, `0x1002af00`): two-sided, then
  masked, translucent and modulated as set, and no smoothing unless
  smoothing is on.
- **Text** keeps its own flags, which only `EnableTranslucentText`
  (`0x10027610`) sets: masked, or translucent when it is on, never
  modulated, whatever the style.

### Borders

`GC.DrawBorders` (`0x10028df0`) draws a box from nine textures: four
corners, four edges and a centre.

- **Margins.** Each side's margin is the largest of its textures: left from
  the two left corners and the left edge, and so on. A margin given above 0
  replaces it. When the box is narrower or shorter than two margins, both
  shrink in proportion.
- **The pieces**, in this order, each filling its band of the box:
  - the four corners, each in its two margins (the top-left from the box's
    corner to the left and top margin lines, and so on);
  - the left and right edges, in their margins' width, from the top margin
    line to the bottom one;
  - the top and bottom edges, in their margins' height, from the left margin
    line to the right one;
  - the centre, between all four.
- **The source.** Each piece is read from its texture so that its **inner**
  side lies on the margin line: a corner's inner corner, an edge's inner
  side. The source is offset by the texture's size less the margin on a left
  or top piece, 0 on a right or bottom one.
- **The scale.** The corners are drawn at one texel a pixel. The edges and
  the centre are tiled at one texel a pixel along their length
  (`DrawIconPattern`, `0x10028770`: `DrawTile` with a source size of 0 tiles
  that axis, any other stretches), unless stretching is asked for across or
  down. A box with no width or height draws nothing.
- **The game** passes no margins and no stretching in all 13 of its calls:
  the HUD's and the menus' frames are tiled.

### Actors in a window

`GC.DrawActor(actor, bClearZ, bConstrain, bUnlit, drawScale, scaleGlow, skin)`
(`0x1002aa60`) draws an actor through the renderer, into the scene being
drawn:

- with the GC's style, the glow and unlit given, its draw scale multiplied,
  and with a skin every skin replaced, as if not hidden;
- with `bConstrain`, clipped to the window; with `bClearZ`, over whatever
  the depth buffer holds;
- all of it put back afterwards.

`AugmentationDisplayWindow` uses it for the vision augmentation:

- From level 1, each heat source within range is drawn in a grid skin at
  twice its glow, unlit, with or without a line of sight.
- It does not clear the depth buffer; what a wall in front does to it is the
  renderer's.
- The augmentation's description promises sight through walls from its third
  level.

A debug window shows an actor with it too.

### Save pictures

`RootWindow.GenerateSnapshot(bFilter)` (`0x10039410`), after
`SetSnapshotSize(w, h)`:

- reads the frame the render device last drew, at the viewport's size;
- averages it down to w × h: each pixel the mean of the box of pixels it
  covers (steps of the frame's size over w and h, each box starting where
  its step truncates to), each channel scaled by 256/255 and clamped;
- keeps the mean of the three channels in an 8-bit texture with a grey
  palette, its sizes rounded up to powers of two (160 × 120 in a
  256 × 128, the rest black). The C++ can quantize to a palette of 256
  colours instead; nothing asks it to.

The C++ fills a texture it is given, or makes one beside the root window.
The script's call always makes one. `bFilter` is not used. Three callers:

- **The Save Game screen**, for the new save's row: it hides the UI, and two
  ticks later takes one, but not under the OpenGL driver
  (`MenuScreenSaveGame.GenerateNewSnapShot`).
- **The save itself:** `SaveGame` takes a 160 × 120 one into a texture made
  beside the save info, so the save's `SaveInfo` file carries it
  ([the game engine](deusex-dll.md#the-game-engine-travel-and-saving)). The
  screens show it for the selected save.
- **The menus' background:** [the raw background](#the-raw-background).

### The raw background

What the game shows under a menu, by the player's UI background option
(`UIBackground`: Render 3D, Snapshot, Black):

- **`EnableRendering(false)`** (`0x10039e20`) stops the world: the root's
  `PreRender` (`0x1003a760`) gives the scene a frame of no size, so neither
  the level nor the player's overlays are drawn; the windows still are.
  `SetRenderViewport` gives the scene a rectangle of the root instead (the
  conversations' letterbox).
- **The raw background** (`SetRawBackground(texture, colour)`,
  `SetRawBackgroundSize`, `StretchRawBackground`) is drawn before any window
  (`DrawRawBackground`, `0x1003c720`), wherever the scene is not: over the
  whole root with rendering off, around the render viewport with one set,
  nowhere otherwise.
  - Every window is made with `bDrawRawBackground` on (`XWindow::Init`) and
    nothing clears it, so no window keeps it out.
  - Each piece left (above the viewport, below it, then left and right of
    it) is drawn in the colour, unsmoothed: stretched from the background's
    own size, or tiled from the piece's corner.
- **The game's use** (`DeusExRootWindow.ShowSnapshot`):
  - opening a menu with Snapshot takes a snapshot of the frame under it at
    the root's snapshot size (256 × 192), draws it stretched at half
    brightness and turns rendering off;
  - Black has no background and turns rendering off;
  - closing the menus turns rendering on and leaves the background set;
  - the credits turn rendering off for their own screen.

## Small

- **Edit fields.** `Undo` (`0x1001e0a0`) and `Redo` (`0x1001e170`) walk a
  list of changes, each a position, the text removed and the text put in.
  Typing straight after the last change joins it (`AddUndo`, `0x10020450`).
  The list keeps at most `maxUndos`; `ClearUndo` empties it. The script's
  Ctrl+Z and Ctrl+Y call them.
- **Tab groups.** `MoveTabGroupNext` and `MoveTabGroupPrev` (`0x100033f0`,
  `0x10003400`) move the focus to the next or previous tab group
  ([keyboard focus](#keyboard-focus)). The root window's script calls them
  for Tab and Shift+Tab. `GetTabGroupWindow` (`0x1004c560`) is the nearest
  tab group at or above a window.
- **Text windows.** No script calls these: `ResetLines` (`0x10046310`) and
  `ResetMinWidth` (`0x10046450`) lift a text window's line limits and
  minimum width; `LargeTextWindow.SetVerticalSpacing` (`0x1002d7e0`) sets the
  space between lines (not below 0); `RadioBoxWindow.GetEnabledToggle`
  (`0x10015970`) is the box's selected toggle.
- **`ExtString.GetNextTextPart`** (`0x10044ad0`): the text in parts of 239
  characters, a part a call. No script calls it.
- **No script calls** `GC`'s `PushGC`, `PopGC`, `CopyGC` and `Intersect`,
  `ClipWindow`'s unit sizes, or 22 of `ComputerWindow`'s 33 natives.
