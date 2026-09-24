# Core.dll

The native half of package Core: objects and names, packages and linkers,
the property and class system, configuration, and the script interpreter
with its natives (operators, conversions, string and math functions). How it
is read: [working on the binaries](README.md#working-on-the-binaries).

Not yet read.

## The binary

| Property | Value |
|---|---|
| Size | 790,528 bytes |
| Imagebase | `0x10100000` |
| SHA1 | `d03a79bb13e3b5b355df1c9b71271e026c26ef28` |
| Exports | 2,005: 32 classes, 261 `exec` functions -- the script natives and the interpreter's bytecodes |

Only 4 classes have a script of their own (`UObject`, `UCommandlet`,
`USubsystem`, `UDebugInfo`); the other 28 -- `UField`, `UStruct`, `UClass`,
the property classes, `UPackage` -- are C++ only.
