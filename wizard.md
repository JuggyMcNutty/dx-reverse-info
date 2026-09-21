# The config wizard

The launcher's UI. Page classes live in `DeusEx.exe`; the dialog *templates* and every
widget class live in `Window.dll` and are loaded from its `hInstanceWindow`
(`WDialog::DoModal`, `0x1090B829`). All captions come from `System/Startup.int`.

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

Then `WWizardDialog::Advance(page)` (`0x1090B80E`) and `DoModal` (`0x1090B829`).
`DoModal` returning **0 aborts startup**; non-zero continues to launch.

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

## Per-page behaviour

### Renderer (2017)
Controls: `IDC_RenderList` 1103 (`WListBox`), `IDC_Compatible` 1109, `IDC_All` 1110
(both `WButton`, both wired to `WConfigPageRenderer__RefreshList` `0x1090CB70`),
`IDC_RenderNote` 1104 (`WLabel`).

`OnPaint` (`0x1090DA60`) performs device detection unless `-nodetect` is given
(`0x1090DAC6`) and can `ShellExecute` a driver URL. `GetNext` writes the selection to
`[Engine.Engine] GameRenderDevice` (`0x1090E671`) before advancing.

### Detail (2018)
One `WEdit` (`IDC_Prompt` 1100). `OnInitDialog` (`WConfigPageDetail__OnInitDialog`,
`0x1090EB50`) auto-configures performance settings — see [`ini-keys.md`](ini-keys.md).

### Driver (2022)
Shown **only** when Direct3D was selected. `WUrlButton` `IDC_WebButton` 1113 pointing at
`Startup.int` `Direct3DWebPage`, and `WLabel` `IDC_Card` 1111 filled by
`WConfigPageDriver__OnInitDialog` (`0x10910390`) from
`[D3DDrv.D3DRenderDevice] Description`.

### FirstTime (2019)
No bound controls (52 bytes = base + `Owner`); the prompt is static text in the
template. `GetNext` simply `EndDialog(Owner->hWnd, 1)`.

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

`GetNext` (`0x10911C00`) reads each box with `BM_GETCHECK` (`0xF0`), assembles a flag
string, optionally deletes `<appPackage()>.ini`, then:

```
ShellExecute("open", GModuleFilename, <flags>, appBaseDir(), SW_SHOWNORMAL)
EndDialog(Owner->hWnd, 0)
```

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
are **never read**.

Consequences in the shipped game:

- Ticking *"Disable 3D sound hardware"* silently also applies `-nohard`,
  `-nohard -noddraw` **and** `-defaultres`.
- *"Disable 3D video hardware"*, *"Run the game in a window"* and
  *"Run in standard 640x480 resolution"* do nothing at all.

A port should wire all eight correctly and **not** reproduce this.
