# DeusExText.dll

The native half of package DeusExText: `DeusExTextParser`, which reads the
tagged text of books, datacubes, emails and bulletins, and its importer. How
it is read: [working on the binaries](README.md#working-on-the-binaries).

Not yet read.

## The binary

| Property | Value |
|---|---|
| Size | 49,152 bytes |
| Imagebase | `0x10000000` |
| SHA1 | `68ba30bf710cad79a991a22fdd271e303e3ccea0` |
| Exports | 79: 2 classes, 12 `exec` natives |

`DDeusExTextParser`'s layout comes from its script and matches its
registration; `DTextImport` is C++ only.
