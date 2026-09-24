# DeusExText.dll

The native half of package DeusExText: `DeusExTextParser`, which breaks the
tagged text of books, datacubes, newspapers, emails, bulletins and the credits
into tokens for the script, and the editor's importer of those texts. How it
was read: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 49,152 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `68ba30bf710cad79a991a22fdd271e303e3ccea0` |
| Exports | 79: 2 classes, 12 `exec` natives |
| Functions | 145 |

It registers both classes it exports. `DDeusExTextParser`'s layout comes from
its script and matches its registration; `DTextImport` is C++ only. The SDK
has both headers (`DeusExText/Inc/`), and they match. No other DLL imports
from it: the script is its only user.

## Classes

| Class | Base | Size | Natives |
|---|---|---|---|
| `DDeusExTextParser` | `UObject` | 0xc0 | 12: `OpenText` 2210, `CloseText` 2211, `ProcessText` 2212, `IsEOF` 2213, `GetText` 2214, `GotoLabel` 2215, `GetTag` 2216, `GetName` 2217, `GetColor` 2218, `GetEmailInfo` 2219, `GetFileInfo` 2220, `SetPlayerName` 2221 |
| `DTextImport` | `UObject` | 0x2c | -- (C++ only: the importer) |

The SDK's header also numbers a `GetText` 2200 that nothing registers.

## The game's texts

`DeusExText.u` holds 492 `ExtString`s, one a text, each named after the file
it was imported from: 143 datacubes, 78 books and 37 newspapers, 122 emails
and 66 accounts' lists of them, 35 bulletins and 9 boards' lists of them, the
credits and the quotes. The SDK has the sources of missions 0 to 2
(`reference/ReleaseSDK1112f/DeusExText/Text/`).

The script reads them in three places, each making a parser, opening a text
and calling `ProcessText` until it returns false:

- **`InformationDevices`** (books, datacubes, newspapers) adds a text window
  to the HUD's information window for each paragraph, and to it each text and
  player name. `JL`, `JC` and `JR` align the current window; the three colour
  tags colour it. A datacube (`bAddToVault`) also keeps the text as a note,
  with a line break for each `P` token but the first; as the parser swallows
  a text's first `<P>` (below), the note runs its first two paragraphs
  together.
- **`ComputerUIWindow`**: an account's list is the text
  `<mission>_EmailMenu_<user>`, and each of its `EMAIL` tags a row, ten at
  most, naming the email's own text. A public computer's `bulletinTag` names
  a list of `FILE` tags the same way. An email or bulletin is its text, and a
  line break for each paragraph, in one window; other tags do nothing.
- **`CreditsScrollWindow`** and **`QuotesWindow`**: a line for each token of
  text, a header for the one after a `B`; a quote's speaker set apart at its
  colon.

## Parsing

`ProcessText` (`0x10001780`) parses one token (`ParseTextBlock`,
`0x10001a20`), which `GetTag` and `GetText` then give; it returns false once
the text is used up, on the call after the last token.

- **A token** is one tag, or the text up to the next tag, with each CR and LF
  made a space. Nothing is trimmed: the line break before a tag ends the text
  before it in two spaces, and a line break alone between two tags is a token
  of two spaces.
- **The first `<P>`** of a text is swallowed: the token is whatever follows
  it. Text before it is dropped; tags before it come through.
- **A tag** runs from `<` to the first `>` (`ParseTag`, `0x10001cc0`). It is
  the first of 30 names, in the order of `EDeusExTextTags`, that its content
  starts with, case sensitive (`GDeusExTextTagNames`, `0x1000a070`): `TEXT`,
  `FILE`, `EMAIL`, `NOTE`, `/NOTE`, `GOAL`, `/GOAL`, `COMMENT`, `/COMMENT`,
  `PLAYERNAME`, `PLAYERFIRSTNAME`, `NP`, `JC`, `JL`, `JR`, `DC`, `C`, `/C`,
  `P`, `B`, `/B`, `U`, `/U`, `I`, `/I`, `G`, `F`, `L`, `/<`, `/>`. So
  `<LOG ERROR>` is an `L`. Content that starts with none of them is passed
  over, and the token has no tag (`TT_None`).

### What each tag does

`ParseToken` (`0x10001f80`):

- **`FILE=name,description`** and **`EMAIL=name,subject,from,to,cc`**: the
  fields, split at commas and trimmed of spaces (`ParseFile`, `0x10002380`;
  `ParseEmail`, `0x10002560`). A missing field is empty; a comma in a field
  cuts it there. `GetFileInfo` and `GetEmailInfo` give the last ones read,
  whatever the token. `ParseEmail` tests the tag, not the `=` it looked for,
  so an `EMAIL` with no `=` would crash; the game has none.
- **`NOTE`**, **`GOAL`** and **`COMMENT`** read on to their end tag
  (`FindEndTag`, `0x10002ba0`) and give no text: all three hide what they
  hold, and the token's tag is then the end tag's. With no end tag, the rest
  of the text is hidden. The tags inside are parsed, and the character after
  each is skipped, so an end tag straight after another tag is missed; no
  comment in the game holds a tag.
- **`PLAYERNAME`** and **`PLAYERFIRSTNAME`**: the name given to
  `SetPlayerName` (`0x10001460`), and the part of it before its first space.
- **`DC`**, **`C`** and **`/C`** (`ParseColor`, `0x100028c0`): the three
  numbers after `=`, or black without one. `GetColor` (`0x100019c0`) gives
  them after `DC` or `C`, and after `/C` the colour the parser was made with:
  black, as nothing sets it. The alpha is whatever byte was left there.
- **`G=name`** and **`F=name`**: a name, which `GetName` (`0x10001980`) gives
  after a `NOTE`, `G`, `F` or `L`; `L` sets none.
- **`/<`** and **`/>`**: a `<` and a `>` as text.
- The rest (`TEXT`, `NP`, `JC`, `JL`, `JR`, `P`, `B`, `/B`, `U`, `/U`, `I`,
  `/I`, `L`) are only their tag.

### Opening and the rest

- **`OpenText(name, package)`** (`0x10001240`) loads `ExtString`
  `<package>.<name>`, copies its text and deletes the object it loaded, so
  each open reads the package again. With no package, or an empty one, the
  package is `DeusExText`. It starts a text with no paragraph yet; the last
  tag, name, colour, file and email stay from before.
- **`CloseText`** (`0x10001430`) frees the copy. **`IsEOF`** (`0x100018c0`)
  is whether the text is used up.
- **`GotoLabel`** (`0x10001960`) does nothing and returns false.

## In the game's texts

- **Tags:** 16 of the 30 are used: `P` 3,955, `B` 642 and `/B` 536, `DC`
  399, `JC` 215, `COMMENT` 173 and `/COMMENT` 171, `EMAIL` 137, `I` and `/I`
  98, `FILE` 35, `PLAYERNAME` 12, `PLAYERFIRSTNAME` 10, `JL` 3, `JR` 2, and
  one `L`, the `<LOG ERROR>` of a Paris bulletin, which is hidden. Every `DC`
  is white and comes before its text's first `<P>`: in a book or datacube it
  colours the first paragraph's window, beside the information window's
  near-white for the rest, and the computer screens ignore it. Two more are
  no tag at all, a `CYPHERBLOCK=<"...">` and an `AUTHBLOK=<"...">` whose
  bracketed code is hidden.
- **Comments:** 172 texts have one, the designers' notes of where a datacube,
  book or bulletin lies ("Datacube in Alex's office") or whose inbox an email
  is.
- **Lists:** at most 5 emails in an account's list and 8 bulletins on a
  board. 15 `EMAIL` tags have no cc field. `09_EmailMenu_ShipOps` holds one
  empty `EMAIL`, after a comment it never closes (its end is a second
  `<COMMENT>`): the reading runs past the end of the text, so what that
  account lists depends on the memory after it.

## The importer

`ImportAllDeusExTextFiles(package)` (`0x10004950`), a plain C export, imports
every directory under `Text\`, `ImportDeusExTextDirectory(package, dir)`
(`0x10004b60`) every `Text\<dir>\*.txt` and `ImportDeusExTextFile(package,
file)` (`0x10004e30`) one file, through a transient `DTextImport`.
`ImportFile` (`0x10005090`) widens the 8-bit file to UTF-16 and makes an
`ExtString` in the package named after the file, up to its first dot. They
are the editor's; the game never runs them.

## The database

`gamefiles/System/DeusExText.dll.i64` has the class layouts, the UTF-16
strings and the initializers' names ([working on the binaries](README.md#working-on-the-binaries)).
By hand it has the tag names (`GDeusExTextTagNames`), the string and array
helpers (`FString_*`, `TArray_FString_*`) and the deleting destructors. Each
function above carries a one-line comment.
