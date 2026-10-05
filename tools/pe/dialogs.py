#!/usr/bin/env python3
"""A Windows binary's dialog templates, as text.

The original launcher's pages are dialog templates: resources in Window.dll
(the wizard frame and its six pages) and in DeusEx.exe (the splash). A
template is data -- each control's class, id, style and rectangle in dialog
units, and the dialog's font -- and this prints it, with no IDA and no
Python package beyond the standard library (from the parent folder of the
repositories, beside the game install):

    dx-reverse-info/tools/pe/dialogs.py gamefiles/System/Window.dll 104 2017 2018
    dx-reverse-info/tools/pe/dialogs.py gamefiles/System/DeusEx.exe

With no ids it prints every dialog the file has. Rectangles are x, y, width,
height in dialog units; a dialog unit is a quarter of the font's average
character width across and an eighth of its height down.
"""
import struct
import sys

RT_DIALOG = 5

# The predefined control classes, by the atom a template names them with.
ATOMS = {0x80: "Button", 0x81: "Edit", 0x82: "Static", 0x83: "ListBox",
         0x84: "ScrollBar", 0x85: "ComboBox"}

WS = [(0x10000000, "VISIBLE"), (0x08000000, "DISABLED"), (0x00800000, "BORDER"),
      (0x00200000, "VSCROLL"), (0x00100000, "HSCROLL"), (0x00020000, "GROUP"),
      (0x00010000, "TABSTOP")]
DS = [(0x0040, "SETFONT"), (0x0080, "MODALFRAME"), (0x0400, "CONTROL"),
      (0x0800, "CENTER"), (0x0004, "3DLOOK"), (0x0002, "SYSMODAL")]
WS_DIALOG = [(0x80000000, "POPUP"), (0x40000000, "CHILD"), (0x00C00000, "CAPTION"),
             (0x00080000, "SYSMENU"), (0x00040000, "THICKFRAME")]
BS_TYPES = {0: "PUSHBUTTON", 1: "DEFPUSHBUTTON", 2: "CHECKBOX", 3: "AUTOCHECKBOX",
            4: "RADIOBUTTON", 5: "3STATE", 6: "AUTO3STATE", 7: "GROUPBOX",
            9: "AUTORADIOBUTTON", 11: "OWNERDRAW"}
BS_FLAGS = [(0x0020, "LEFTTEXT"), (0x0080, "BITMAP"), (0x0100, "LEFT"),
            (0x0200, "RIGHT"), (0x0300, "CENTER"), (0x0400, "TOP"),
            (0x0800, "BOTTOM"), (0x0C00, "VCENTER"), (0x1000, "PUSHLIKE"),
            (0x2000, "MULTILINE"), (0x8000, "FLAT")]
SS_TYPES = {0: "LEFT", 1: "CENTER", 2: "RIGHT", 3: "ICON", 4: "BLACKRECT",
            5: "GRAYRECT", 6: "WHITERECT", 7: "BLACKFRAME", 8: "GRAYFRAME",
            9: "WHITEFRAME", 11: "SIMPLE", 12: "LEFTNOWORDWRAP", 14: "BITMAP",
            16: "ETCHEDHORZ", 17: "ETCHEDVERT", 18: "ETCHEDFRAME"}
SS_FLAGS = [(0x0080, "NOPREFIX"), (0x0100, "NOTIFY"), (0x0200, "CENTERIMAGE"),
            (0x1000, "SUNKEN")]
ES_FLAGS = [(0x0001, "CENTER"), (0x0002, "RIGHT"), (0x0004, "MULTILINE"),
            (0x0040, "AUTOVSCROLL"), (0x0080, "AUTOHSCROLL"), (0x0800, "READONLY"),
            (0x1000, "WANTRETURN")]
LBS_FLAGS = [(0x0001, "NOTIFY"), (0x0002, "SORT"), (0x0008, "MULTIPLESEL"),
             (0x0010, "OWNERDRAWFIXED"), (0x0040, "HASSTRINGS"),
             (0x0100, "NOINTEGRALHEIGHT"), (0x0800, "NOSEL"),
             (0x1000, "DISABLENOSCROLL")]
WS_EX = [(0x00000001, "DLGMODALFRAME"), (0x00000004, "NOPARENTNOTIFY"),
         (0x00000008, "TOPMOST"), (0x00000020, "TRANSPARENT"),
         (0x00000200, "CLIENTEDGE"), (0x00000100, "WINDOWEDGE"),
         (0x00010000, "CONTROLPARENT"), (0x00020000, "STATICEDGE")]


def flags(value, table):
    return [name for bit, name in table if value & bit == bit]


class PE:
    def __init__(self, data):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("not a PE file")
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            raise ValueError("not a PE file")
        nsect, optsize = struct.unpack_from("<H12xH", data, pe + 4 + 2)
        opt = pe + 24
        magic = struct.unpack_from("<H", data, opt)[0]
        dirs = opt + (96 if magic == 0x10B else 112)
        self.rsrc_rva = struct.unpack_from("<I", data, dirs + 2 * 8)[0]
        self.sections = []
        for i in range(nsect):
            s = opt + optsize + i * 40
            vsize, va, rawsize, raw = struct.unpack_from("<IIII", data, s + 8)
            self.sections.append((va, max(vsize, rawsize), raw))

    def offset(self, rva):
        for va, size, raw in self.sections:
            if va <= rva < va + size:
                return raw + rva - va
        raise ValueError("RVA %#x is in no section" % rva)

    def resources(self, rtype):
        """(name, language, bytes) for every resource of the type."""
        if not self.rsrc_rva:
            return []
        root = self.offset(self.rsrc_rva)
        out = []
        for tid, tsub in self._entries(root, root):
            if tid != rtype:
                continue
            for nid, nsub in self._entries(root, tsub):
                for lid, dentry in self._entries(root, nsub):
                    rva, size = struct.unpack_from("<II", self.data, dentry)
                    off = self.offset(rva)
                    out.append((nid, lid, self.data[off:off + size]))
        return out

    def _entries(self, root, directory):
        """(name or id, file offset of the subdirectory or data entry)."""
        named, ids = struct.unpack_from("<HH", self.data, directory + 12)
        for i in range(named + ids):
            name, target = struct.unpack_from("<II", self.data, directory + 16 + i * 8)
            if name & 0x80000000:
                s = root + (name & 0x7FFFFFFF)
                n = struct.unpack_from("<H", self.data, s)[0]
                name = self.data[s + 2:s + 2 + 2 * n].decode("utf-16-le")
            yield name, root + (target & 0x7FFFFFFF)


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def u8(self):
        self.pos += 1
        return self.data[self.pos - 1]

    def u16(self):
        self.pos += 2
        return struct.unpack_from("<H", self.data, self.pos - 2)[0]

    def s16(self):
        self.pos += 2
        return struct.unpack_from("<h", self.data, self.pos - 2)[0]

    def u32(self):
        self.pos += 4
        return struct.unpack_from("<I", self.data, self.pos - 4)[0]

    def text(self):
        end = self.pos
        while self.data[end:end + 2] != b"\0\0":
            end += 2
        s = self.data[self.pos:end].decode("utf-16-le")
        self.pos = end + 2
        return s

    def sz_or_ord(self):
        """A string, an ordinal (an int), or None."""
        first = struct.unpack_from("<H", self.data, self.pos)[0]
        if first == 0:
            self.pos += 2
            return None
        if first == 0xFFFF:
            self.pos += 2
            return self.u16()
        return self.text()

    def align(self):
        self.pos = (self.pos + 3) & ~3


def parse(data):
    r = Reader(data)
    ex = struct.unpack_from("<HH", data, 0) == (1, 0xFFFF)
    d = {"ex": ex}
    if ex:
        r.pos = 4
        d["help"], d["exstyle"], d["style"] = r.u32(), r.u32(), r.u32()
    else:
        d["style"], d["exstyle"] = r.u32(), r.u32()
    count = r.u16()
    d["rect"] = (r.s16(), r.s16(), r.s16(), r.s16())
    d["menu"], d["class"] = r.sz_or_ord(), r.sz_or_ord()
    d["caption"] = r.text()
    d["font"] = None
    if d["style"] & 0x0040:
        size = r.u16()
        weight = italic = 0
        if ex:
            weight, italic, _charset = r.u16(), r.u8(), r.u8()
        d["font"] = (r.text(), size, weight, italic)
    items = []
    for _ in range(count):
        r.align()
        it = {}
        if ex:
            it["help"], it["exstyle"], it["style"] = r.u32(), r.u32(), r.u32()
        else:
            it["style"], it["exstyle"] = r.u32(), r.u32()
        it["rect"] = (r.s16(), r.s16(), r.s16(), r.s16())
        it["id"] = r.u32() if ex else r.u16()
        cls = r.sz_or_ord()
        it["class"] = ATOMS.get(cls, cls) if isinstance(cls, int) else cls
        it["text"] = r.sz_or_ord()
        extra = r.u16()
        r.pos += extra
        items.append(it)
    d["items"] = items
    return d


def describe_item(it):
    style = it["style"]
    cls = it["class"] if isinstance(it["class"], str) else "#%s" % it["class"]
    low = style & 0xFFFF
    kind = []
    if cls == "Button":
        kind = [BS_TYPES.get(low & 0x0F, "type%d" % (low & 0x0F))] + flags(low & 0xFFF0, BS_FLAGS)
    elif cls == "Static":
        kind = [SS_TYPES.get(low & 0x1F, "type%d" % (low & 0x1F))] + flags(low & 0xFFE0, SS_FLAGS)
    elif cls == "Edit":
        kind = flags(low, ES_FLAGS)
    elif cls == "ListBox":
        kind = flags(low, LBS_FLAGS)
    elif low:
        kind = ["style %#06x" % low]
    kind += flags(style, WS)
    if not style & 0x10000000:
        kind.append("hidden")
    kind += ["ex:" + f for f in flags(it["exstyle"], WS_EX)]
    return cls, " ".join(kind)


def show(name, lang, d, out):
    x, y, w, h = d["rect"]
    out.write("dialog %s (language %s)%s\n" % (name, lang, "  [extended]" if d["ex"] else ""))
    out.write("  caption  %r\n" % d["caption"])
    out.write("  rect     %d,%d %dx%d\n" % (x, y, w, h))
    out.write("  style    %#010x %s\n" % (d["style"], " ".join(flags(d["style"], WS_DIALOG) + flags(d["style"], DS))))
    if d["exstyle"]:
        out.write("  exstyle  %#010x %s\n" % (d["exstyle"], " ".join(flags(d["exstyle"], WS_EX))))
    if d["class"] is not None:
        out.write("  class    %r\n" % (d["class"],))
    if d["font"]:
        face, size, weight, italic = d["font"]
        out.write("  font     %s, %d pt%s%s\n" % (face, size, ", weight %d" % weight if weight else "",
                                                ", italic" if italic else ""))
    for it in d["items"]:
        cls, kind = describe_item(it)
        x, y, w, h = it["rect"]
        text = it["text"]
        text = "" if text is None else ("#%d" % text if isinstance(text, int) else repr(text))
        out.write("  %5d  %-9s %4d,%-4d %4dx%-4d %s  %s\n" % (it["id"] if it["id"] != 0xFFFF else -1,
                                                           cls, x, y, w, h, text, kind))
    out.write("\n")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        sys.stdout.write(__doc__)
        return 2
    with open(argv[1], "rb") as f:
        pe = PE(f.read())
    want = set(argv[2:])
    found = 0
    for name, lang, data in pe.resources(RT_DIALOG):
        if want and str(name) not in want:
            continue
        show(name, lang, parse(data), sys.stdout)
        found += 1
    if not found:
        sys.stderr.write("no dialog%s in %s\n" % (" " + " ".join(sorted(want)) if want else "s", argv[1]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
