# The config wizard

The launcher's UI. Page classes live in `DeusEx.exe`; the dialog *templates* and every
widget class live in `Window.dll` and are loaded from its `hInstanceWindow`
(`WDialog::DoModal`, `0x1090B829`). All captions come from `System/Startup.int`.

The pages' source is in the SDK, as C++ in a header: `Engine/Inc/UnEngineWin.h`
(`reference/ReleaseSDK1112f/Headers/DxHeaders.zip`) holds the six pages and
`InitEngine`, and `Window/Inc/Window.h` the wizard frame and its buttons. What
follows with an address was read in the binary; the rest -- the tie-break of
the Renderer page's default, its flush before detecting, the frame's buttons
-- is the header's, which matched the binary at every point the two were
compared (the entry tree, the order around the wizard, each page's strings and
flags, SafeOptions' defaults, the Detail thresholds).

## Entry decision tree (`InitEngine`, `0x1090AAB6`–`0x1090B7F6`)

Evaluated only when `!GIsEditor && GIsClient`. **First match wins**; if none match,
no wizard is shown and the game launches directly.

| # | Condition | Page shown | Caption key (`Startup.int`) |
|---|---|---|---|
| 1 | `-safe` **or** cmdline contains `readini` | SafeMode (2020) | `SafeMode` |
| 2 | `FirstRun < 400` | Renderer (2017) | `FirstTime` |
| 3 | `-changevideo` | Renderer (2017) | `Video` |
| 4 | no other instance running **and** `Running.ini` exists | SafeMode (2020) | `RecoveryMode` |

Addresses: `-safe`/`readini` `0x1090ABB2`/`0x1090ABD9`; `FirstRun<400` `0x1090AF35`;
`-changevideo` `0x1090B247`; `Running.ini` probe `0x1090B569`.

Then the splash closes (`ExitSplash`, `0x1090B7FC`), `WWizardDialog::Advance(page)`
(`0x1090B80E`) and `DoModal` (`0x1090B829`). `DoModal` returning **0 aborts
startup**; non-zero reopens the splash with the same bitmap (`InitSplash(NULL)`,
`0x1090B885`) and continues to launch ([`launch-flow.md`](launch-flow.md#5-initengine-0x1090a050)).

### The `FirstRun` version gates

`[FirstRun] FirstRun` is an engine-version integer, not a boolean.

| Value | Meaning |
|---|---|
| `< 220` | run savegame migration |
| `< 400` | show the first-time wizard |
| final | clamped up to **1100** and written back after the wizard (`0x1090B997`) |

Shipped `System/DeusEx.ini` has `FirstRun=0`, so a pristine install always runs the
full first-time flow.

## Page graph

```
  SafeMode (2020) ──[Run]──────→ close dialog, launch game
        │                          WConfigPageSafeMode__OnRun          0x109110F0
        ├──[Change video]───────→ Renderer (2017)
        │                          WConfigPageSafeMode__OnVideo        0x10911120
        ├──[Safe mode]──────────→ SafeOptions (2021)
        │                          WConfigPageSafeMode__OnSafeMode     0x109114A0
        └──[Web]────────────────→ ShellExecute(Startup.int "WebPage")
                                   WConfigPageSafeMode__OnWeb          0x10912FD0

  Renderer (2017) ──GetNext──→ if GameRenderDevice == D3DDrv.D3DRenderDevice
                                   → Driver (2022) ──GetNext──→ Detail (2018)
                               else
                                   → Detail (2018)
                                   WConfigPageRenderer__GetNext        0x1090E520

  Detail (2018)    ──GetNext──→ FirstTime (2019)                       0x1090FA40
  FirstTime (2019) ──GetNext──→ EndDialog(Owner, 1) = launch the game  0x1090FBC0

  SafeOptions (2021) ──GetNext──→ ShellExecute(self, flags); EndDialog(0)
                                   WConfigPageSafeOptions__GetNext     0x10911C00
```

`SafeMode`'s `GetNext` is the inherited default (returns `NULL`) — it is a pure menu
page, navigated only by its four buttons.

## The frame

`WConfigWizard` (in the binary's names `WStartupWizard`, vtable `0x10926F88`)
is Window.dll's `WWizardDialog`: a stack of pages over one dialog (104).

- **Its title** is the caption the entry tree picked (`SafeMode`, `FirstTime`,
  `Video` or `RecoveryMode`), set as it opens (`WStartupWizard__OnInitDialog`,
  `0x1090C780`). The template's own caption, `IDC_WizardDialog` ("Deus Ex
  Setup"), is replaced.
- **Its logo** is `..\Help\LogoSmall.bmp`, loaded into the static at the top
  left without checking it loaded. The GOG install has no such file, so the
  band above the page stays empty there; the SDK's `Help/` has it, 500×77.
- **Its icon** is `DeusEx.exe`'s icon group 128.
- **Four buttons** along the bottom, Back, Next, Finish and Cancel, each
  shown only while its page gives it a text: Back from the second page on
  (Window.int `BackButton`, "< &Back"); Next with the page's own text, by
  default Window.int `NextButton` ("&Next >"), "Run!" on FirstTime and
  SafeOptions (Startup.int `Run`), none on SafeMode; Finish never (no page
  gives one); Cancel always (Window.int `CancelButton`).
- **Next** asks the current page for the next one and pushes it; a page that
  returns none has ended the wizard itself or leaves it where it is. **Back**
  pops the current page and shows the one below. **Cancel**, and closing the
  window, end the wizard with 0.

## How a page gets its text

As a page (or the frame) opens, every control whose template text starts with
`IDC_` gets the text of that key in the section named after the dialog --
`[IDDIALOG_ConfigPageRenderer]` and so on -- of the class's localisation
package, `Startup.int`; `IDOK` and `IDCANCEL` get Window.int's `OkButton` and
`CancelButton`. A key with an empty value (`IDC_RenderNote=`) leaves the
control empty. The strings are the game's: the templates only name keys.

## Page inventory

| Page | Dialog ID | Size | vtable | ctor |
|---|---|---|---|---|
| `WConfigPageRenderer` | 2017 | 464 | `0x10926D70` | inline in `InitEngine` |
| `WConfigPageDetail` | 2018 | 112 | `0x10927154` | `0x1090E890` |
| `WConfigPageFirstTime` | 2019 | 52 | `0x1092727C` | inline in `0x1090FA40` |
| `WConfigPageSafeMode` | 2020 | 564 | `0x10926E7C` | inline in `InitEngine` |
| `WConfigPageSafeOptions` | 2021 | 1012 | `0x10927494` | inline in `0x109114A0` |
| `WConfigPageDriver` | 2022 | 240 | `0x10927388` | `0x1090FF90` |

Wizard-page vtable slots (from `Window/Inc/Window.h:5043`):
`+192 OnCurrent`, `+196 GetNext`, `+200 GetBackText`, `+204 GetNextText`,
`+208 GetFinishText`, `+212 GetCancelText`, `+216 GetShow`, `+220 OnCancel`.

## Page layouts

From `Window.dll`'s dialog resources, read with
[`tools/pe/dialogs.py`](tools/pe/dialogs.py). Every one uses MS Sans Serif,
8 pt. Rectangles are x, y, width, height in dialog units: across, a quarter of
the font's average character width; down, an eighth of its height -- 1.5 and
1.625 pixels for MS Sans Serif 8 pt at 96 DPI, which makes the frame's client
area 524×411.

**The frame** (104): a 349×253 popup with a caption and a system menu,
centred.

| Control | Id | Kind | Rectangle |
|---|---|---|---|
| logo | 1024 | static, bitmap, sunken frame | 6, 6 (sized to its bitmap) |
| line | -- | etched horizontal | 0, 58, 349 × 1 |
| page holder | 1061 | black frame; each page opens inside it | 3, 59, 344 × 172 |
| line | -- | etched horizontal | 0, 231, 349 × 1 |
| Back | 3 | owner-drawn button | 72, 236, 50 × 14 |
| Next | 1004 | owner-drawn button | 122, 236, 50 × 14 |
| Finish | 1005 | owner-drawn button | 182, 236, 50 × 14 |
| Cancel | 2 | owner-drawn button | 241, 236, 50 × 14 |

The four buttons are "cool" buttons (`WCoolButton`): flat, drawn by Window.dll.
The template lists them in the order Next, Cancel, Back, Finish, which is
their tab order.

**The pages** are 344×172 children of the page holder:

| Page | Control | Id | Kind | Rectangle |
|---|---|---|---|---|
| Renderer (2017) | `IDC_RenderPrompt` | 1102 | text | 7, 7, 328 × 33 |
| | `IDC_RenderList` | 1103 | list box: sorted, border, vertical scroll bar | 7, 42, 330 × 67 |
| | `IDC_Compatible` | 1109 | radio button | 7, 110, 147 × 10 |
| | `IDC_All` | 1110 | radio button | 190, 110, 147 × 10 |
| | `IDC_RenderNote` | 1104 | text | 7, 125, 328 × 41 |
| Detail (2018) | `IDC_DetailPrompt` | 1099 | text | 7, 7, 328 × 23 |
| | `IDC_DetailEdit` | 1100 | multi-line read-only edit, border | 7, 32, 330 × 110 |
| | `IDC_DetailNote` | 1101 | text | 7, 145, 328 × 21 |
| FirstTime (2019) | `IDC_Prompt` | 1002 | text | 7, 52, 328 × 75 |
| SafeMode (2020) | `IDC_SafeModePrompt` | 1105 | text | 7, 7, 330 × 65 |
| | -- | -- | group box | 7, 74, 330 × 92 |
| | `IDC_Run` | 1108 | owner-drawn button | 15, 87, 314 × 14 |
| | `IDC_SafeMode` | 1109 | owner-drawn button | 15, 106, 314 × 14 |
| | `IDC_Video` | 1110 | owner-drawn button | 15, 125, 314 × 14 |
| | `IDC_Web` | 1058 | owner-drawn button | 15, 144, 314 × 14 |
| SafeOptions (2021) | `IDC_SafeOptions` | 1107 | text | 7, 7, 330 × 10 |
| | `IDC_NoSound` | 1108 | check box | 7, 33, 330 × 10 |
| | `IDC_No3DSound` | 1109 | check box | 7, 47, 330 × 10 |
| | `IDC_No3dVideo` | 1110 | check box | 7, 61, 330 × 10 |
| | `IDC_Window` | 1112 | check box | 7, 75, 330 × 10 |
| | `IDC_Res` | 1111 | check box | 7, 89, 330 × 10 |
| | `IDC_ResetConfig` | 1113 | check box | 7, 104, 330 × 10 |
| | `IDC_NoProcessor` | 1114 | check box | 7, 119, 330 × 10 |
| | `IDC_NoJoy` | 1115 | check box | 7, 134, 330 × 10 |
| Driver (2022) | `IDC_DriverText` | 1110 | text | 7, 7, 330 × 10 |
| | `IDC_Card` | 1111 | text | 33, 24, 304 × 10 |
| | `IDC_DriverInfo` | 1112 | text | 7, 39, 330 × 96 |
| | `IDC_Web` | 1058 | text | 7, 141, 330 × 8 |
| | `IDC_WebButton` | 1113 | owner-drawn button | 7, 154, 330 × 12 |

The texts are left-aligned and wrap. SafeOptions lists `IDC_Res` before
`IDC_Window` in the template, so tabbing visits them in that order, though
`IDC_Window` is drawn above.

## Per-page behaviour

### Renderer (2017)
Controls: `IDC_RenderList` 1103 (`WListBox`), `IDC_Compatible` 1109, `IDC_All` 1110
(both `WButton`, both wired to `WConfigPageRenderer__RefreshList` `0x1090CB70`),
`IDC_RenderNote` 1104 (`WLabel`).

- **Opening** (`0x1090DDC0`): Compatible is ticked, and the list holds one
  line, Startup.int `Detecting` ("Detecting 3D video devices, please
  wait...").
- **First paint** (`OnPaint`, `0x1090DA60`): the configuration is flushed; then,
  unless `-nodetect` (`0x1090DAC6`), `Detected.ini` is deleted, `DeusEx.exe`
  is run again with `testrendev=D3DDrv.D3DRenderDevice log=Detected.log`
  (`0x1090DB18`), and the page waits for `Detected.ini` to appear, up to 30 s
  in steps of 100 ms. Only Direct3D is tested this way. Then the list is
  filled.
- **The list** (`RefreshList`): every render device registered in the `.int`
  files -- a `[Public]` line `Object=(Name=<package>.<class>,Class=Class,MetaClass=Engine.RenderDevice,Autodetect=<file>)`
  -- labelled with its `ClassCaption` from `<package>.int`, `[<class>]`. A
  device is shown with "Show all devices", or when it earns a priority: 3 if
  its `Autodetect` file is in Windows' system or Windows directory, else 2 if
  its `[<package>.<class>] DescFlags` has bit 1 (certified), else 1 for
  `SoftDrv.SoftwareRenderDevice`. The list box sorts, so the captions come out
  in alphabetical order. The one selected is the last shown with the highest
  priority, in registration order.
- **The note** is the selected device's line in Startup.int `[Descriptions]`,
  and follows the selection. A double click is Next.
- **Next** (`GetNext`, `0x1090E520`) writes the selection to `[Engine.Engine]
  GameRenderDevice` (`0x1090E671`) -- nothing if nothing is selected -- and goes
  on to Driver for Direct3D, else to Detail.

`DescFlags` bits (the SDK's `Engine/Inc/UnRenDev.h`): 1 certified, 2
incompatible, 4 low-detail world, 8 low-detail skins, 16 low-detail actors.

### Detail (2018)
One `WEdit` (`IDC_DetailEdit` 1100). `OnInitDialog` (`WConfigPageDetail__OnInitDialog`,
`0x1090EB50`) auto-configures performance settings — see [`ini-keys.md`](ini-keys.md)
— and fills the edit with one line per choice, from Startup.int:

| Line | When |
|---|---|
| `SoundLow` | no MMX, or 64 MB of memory or less (`0x1090EDA1`) |
| `SoundHigh` | otherwise |
| `SkinsLow` | under 96 MB, or the renderer's `DescFlags` has bit 8 (`0x1090F0E0`) |
| `SkinsHigh` | otherwise |
| `WorldLow` | under 64 MB, or `DescFlags` has bit 4 (`0x1090F36A`) |
| `WorldHigh` | otherwise |
| `ResHigh` | always |

### Driver (2022)
Shown **only** when Direct3D was selected. `WUrlButton` `IDC_WebButton` 1113 pointing at
`Startup.int` `Direct3DWebPage`, and `WLabel` `IDC_Card` 1111 filled by
`WConfigPageDriver__OnInitDialog` (`0x10910390`) from
`[D3DDrv.D3DRenderDevice] Description`. With no description the label keeps
its localised text, "Unknown".

### FirstTime (2019)
No bound controls (52 bytes = base + `Owner`); the prompt is static text in the
template. Its Next reads "Run!" (`0x1090FB90`); `GetNext` simply
`EndDialog(Owner->hWnd, 1)`.

### SafeMode (2020)
Four "cool" buttons in a group box, top to bottom Run, Safe mode, Change video
and Web, and no Next. The page has no initialisation of its own and its
template one prompt, so it always says Startup.int `IDC_SafeModePrompt` --
"The previous time Deus Ex was run, it was not shut down properly..." --
whether a crash or `-safe` opened it: `IDC_SafeModePrompt2` ("Deus Ex safe
mode options...") is never shown. Only the title tells the two apart. Web
opens Startup.int `WebPage` and ends the wizard with 0.

### SafeOptions (2021) — eight checkboxes
Eight `WButton`s at stride 120, starting at offset 52. Construction order and IDs
confirmed at `0x10911582`–`0x10911721`; total `48 + 4 + 8×120 = 1012` matches the
observed `GMalloc(1012)` at `0x109114C9`.

| # | Offset | hWnd | ID | Name | Intended flag |
|---|---|---|---|---|---|
| 1 | `+0x34` | `+0x38` | 1108 | `IDC_NoSound` | `-nosound` |
| 2 | `+0xAC` | `+0xB0` | 1109 | `IDC_No3DSound` | `-no3dsound` |
| 3 | `+0x124` | `+0x128` | 1110 | `IDC_No3dVideo` | `-nohard` |
| 4 | `+0x19C` | `+0x1A0` | 1112 | `IDC_Window` | `-nohard -noddraw` |
| 5 | `+0x214` | `+0x218` | 1111 | `IDC_Res` | `-defaultres` |
| 6 | `+0x28C` | `+0x290` | 1113 | `IDC_ResetConfig` | delete `<Package>.ini` |
| 7 | `+0x304` | `+0x308` | 1114 | `IDC_NoProcessor` | `-nommx -nokni -nok6` |
| 8 | `+0x37C` | `+0x380` | 1115 | `IDC_NoJoy` | `-nojoy` |

As the page opens (`WConfigPageSafeOptions__OnInitDialog`, `0x10911890`) every
box is ticked but #6, Reset. Its Next reads "Run!" (`0x10911BD0`).

`GetNext` (`0x10911C00`) reads each box with `BM_GETCHECK` (`0xF0`), appends each
ticked box's flags to a string -- a space before each, as the table shows them --
optionally deletes `<appPackage()>.ini`, then:

```
ShellExecute("open", GModuleFilename, <flags>, appBaseDir(), SW_SHOWNORMAL)
EndDialog(Owner->hWnd, 0)
```

The new process gets these flags and nothing else of the command line.
What each flag does in the engine: [`cli-flags.md`](cli-flags.md#flags-the-launcher-emits-safe-mode).

**Safe mode does not apply settings in-process — it re-executes the binary with flags
and exits.** Any port must reproduce that, or deliberately choose not to.

## ⚠ Shipped bug: three safe-mode checkboxes are dead

Verified in raw disassembly (not a decompiler artifact) — eight `BM_GETCHECK` sites in
`0x10911C00`, and their object-offset loads are:

```
0x10911C46  mov edx, [ecx+38h]    -> #1 NoSound       -nosound
0x10911D3A  mov eax, [edx+0B0h]   -> #2 No3DSound     -no3dsound
0x10911E35  mov ecx, [eax+0B0h]   -> #2 again         -nohard
0x10911F2F  mov edx, [ecx+0B0h]   -> #2 again         -nohard -noddraw
0x1091202F  mov eax, [edx+0B0h]   -> #2 again         -defaultres
0x10912148  mov ecx, [eax+308h]   -> #7 NoProcessor   -nommx -nokni -nok6
0x10912260  mov edx, [ecx+380h]   -> #8 NoJoy         -nojoy
0x10912378  mov eax, [edx+290h]   -> #6 ResetConfig   delete ini
```

Offsets `+0x128`, `+0x1A0`, `+0x218` — checkboxes **#3 No3DVideo, #4 Window, #5 Res** —
are **never read**. The SDK's source has the same five reads of box #2, so
the bug was written, not compiled in.

Consequences in the shipped game:

- Ticking *"Disable 3D sound hardware"* silently also applies `-nohard`,
  `-nohard -noddraw` **and** `-defaultres`.
- *"Disable 3D video hardware"*, *"Run the game in a window"* and
  *"Run in standard 640x480 resolution"* do nothing at all.
- With the boxes as the page opens them -- all ticked but Reset -- the flags
  come out as intended; the bug shows only when #2 differs from #3, #4 or #5.

A port should wire all eight correctly and **not** reproduce this.
