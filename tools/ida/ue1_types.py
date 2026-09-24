#!/usr/bin/env python3
"""IDA types for Deus Ex's native classes, from the game's own script source.

Every native class declares its fields in its UnrealScript, in the order its
C++ class has them, and the game's packages (System/*.u) carry that source.
So the script gives each class's layout: UObject's 0x28 bytes, then each
class's fields in turn -- bools packed 32 to a dword, bytes packed, the rest
aligned to 4, a string 12 bytes (an FString) -- with the structs and enums
declared beside them. The SDK's generated headers have the classes of Engine
and DeusEx only, and none of the script structs; the script has everything.

The C++ name of each native class (AScriptedPawn, XWindow, DConversation)
comes from the DLLs' exports: `?PrivateStaticClass@<name>@@0VUClass@@A`.

On the host:
    python3 tools/ida/ue1_types.py --sizes            each native class's size
    python3 tools/ida/ue1_types.py --emit FILE        the C declarations
    python3 tools/ida/ue1_types.py --check DLL...     sizes against each DLL's
                                                      class registrations
    python3 tools/ida/ue1_types.py --layout CLASS...  a class's fields at their
                                                      offsets (AScriptedPawn or
                                                      ScriptedPawn)
In IDA, run this file (File > Script file, or the MCP's py_exec_file). It
declares the types, checks every class the open DLL registers against the
size it passes to UClass's constructor, and types `this` on every member
function of a declared class. The game directory is found from the database's
path (<game>/System/<dll>.i64) or PXM_GAME_DIR.
"""
import glob
import os
import re
import struct
import sys

# The packages whose native classes get types, in load order.
PACKAGES = ["Core", "Engine", "Fire", "IpDrv", "Extension", "ConSys", "DeusExText", "DeusEx"]
# The DLLs whose exports name the C++ classes.
DLLS = ["Core", "Engine", "Fire", "IpDrv", "Extension", "ConSys", "DeusExText", "DeusEx", "Render"]

VAR_MODIFIERS = {
    "config", "globalconfig", "const", "native", "private", "protected", "public",
    "transient", "travel", "editconst", "input", "localized", "export", "noexport",
    "edfindable", "deprecated", "editinline", "editinlineuse", "automated",
    "editconstarray", "editinlinenew", "cache", "skip", "init", "out", "coerce", "intrinsic",
}
C_KEYWORDS = {
    "auto", "break", "case", "char", "class", "const", "continue", "default", "delete",
    "do", "double", "else", "enum", "extern", "float", "for", "friend", "goto", "if",
    "inline", "int", "long", "new", "operator", "private", "protected", "public",
    "register", "return", "short", "signed", "sizeof", "static", "struct", "switch",
    "template", "this", "throw", "try", "typedef", "union", "unsigned", "virtual",
    "void", "volatile", "while", "bool", "true", "false", "near", "far",
}


# Classes with no script of their own (C++ only), named as object references.
INTRINSIC = {
    "level": "ULevel", "levelbase": "ULevelBase", "mesh": "UMesh", "lodmesh": "ULodMesh",
    "model": "UModel", "sound": "USound", "music": "UMusic", "primitive": "UPrimitive",
    "client": "UClient", "renderbase": "URenderBase", "renderdevice": "URenderDevice",
    "eventmanager": "UEventManager", "viewport": "UViewport", "netconnection": "UNetConnection",
    "netdriver": "UNetDriver", "audiosubsystem": "UAudioSubsystem", "input": "UInput",
    "function": "UFunction", "state": "UState", "struct": "UStruct", "field": "UField",
    "property": "UProperty", "package": "UPackage", "linker": "ULinker",
    "font": "UFont", "textbuffer": "UTextBuffer", "transbuffer": "UTransBuffer",
}


def align(n, a):
    return (n + a - 1) // a * a


# ---------------------------------------------------------------------------
# Script source

# The declaration can follow the text's length prefix on its first line.
CLASS_DECL = re.compile(r"class[ \t]+(\w+)(?:\s+(?:extends|expands)\s+(\w+)|(?=\s+native))", re.I)


def strip_comments(text):
    """Comments, directive lines (#exec) and the contents of string and name
    literals, blanked. A directive has no ';' to end it."""
    out = []
    i, n = 0, len(text)
    line_blank = True       # nothing but whitespace so far on this line
    while i < n:
        c = text[i]
        if c == "\n":
            line_blank = True
        elif not c.isspace() and c != "#":
            line_blank = False
        if c == "#" and line_blank:
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            out.append(c + c)
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


TOKEN = re.compile(r"\s*(?:(\w+)|(.))", re.S)


def tokenize(text):
    toks = []
    for m in TOKEN.finditer(text):
        t = m.group(1) or m.group(2)
        if t and not t.isspace():
            toks.append(t)
    return toks


class ScriptClass:
    def __init__(self, name, base, package, text):
        self.name, self.base, self.package, self.text = name, base, package, text
        self.native = False
        self.fields = []        # Field, in order
        self.consts = {}
        self.structs = {}       # lower name -> ScriptStruct declared here
        self.enums = {}         # lower name -> ScriptEnum declared here


class Field:
    def __init__(self, name, type_, dim):
        self.name, self.type, self.dim = name, type_, dim   # type: ("byte",) etc
        self.offset = None
        self.bit = None


class ScriptStruct:
    def __init__(self, name, base, owner):
        self.name, self.base, self.owner = name, base, owner
        self.fields = []
        self.size = None
        self.align = None
        self.cname = None


class ScriptEnum:
    def __init__(self, name, values, owner):
        self.name, self.values, self.owner = name, values, owner


class Model:
    """Every class, struct and enum the packages declare."""

    def __init__(self):
        self.classes = {}   # lower name -> ScriptClass
        self.structs = {}   # lower name -> ScriptStruct
        self.enums = {}     # lower name -> ScriptEnum
        self.warnings = []

    def warn(self, msg):
        self.warnings.append(msg)


def read_packages(system_dir, model, packages=None):
    """Every class whose script text a package carries."""
    paths = sorted(glob.glob(os.path.join(system_dir, "*.u")))
    order = {p.lower(): i for i, p in enumerate(PACKAGES)}
    paths.sort(key=lambda p: (order.get(os.path.basename(p)[:-2].lower(), 99), p))
    for path in paths:
        package = os.path.basename(path)[:-2]
        if packages and package not in packages:
            continue
        data = open(path, "rb").read()
        for chunk in data.split(b"\0"):
            if len(chunk) < 12 or b"class" not in chunk:
                continue
            raw = chunk.decode("latin-1")
            text = strip_comments(raw)
            m = CLASS_DECL.search(text)
            if not m:
                continue
            name, base = m.group(1), m.group(2)
            key = name.lower()
            if key in model.classes:
                continue
            model.classes[key] = ScriptClass(name, base, package, text[m.start():])


def parse_type(toks, i, owner, model):
    """A type starting at toks[i]: (type tuple, next index)."""
    t = toks[i]
    tl = t.lower()
    if tl in ("byte", "int", "float", "bool", "name", "string", "pointer"):
        i += 1
        if tl == "string" and i < len(toks) and toks[i] == "[":   # string[N]: the length is ignored
            while toks[i] != "]":
                i += 1
            i += 1
        return (tl,), i
    if tl == "class":
        i += 1
        if i < len(toks) and toks[i] == "<":
            while toks[i] != ">":
                i += 1
            i += 1
        return ("class",), i
    if tl == "array" and i + 1 < len(toks) and toks[i + 1] == "<":
        depth, i = 0, i + 1
        while True:
            if toks[i] == "<":
                depth += 1
            elif toks[i] == ">":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        return ("array",), i + 1
    if tl == "enum":
        e, i = parse_enum(toks, i, owner, model)
        return ("enum", e), i
    if tl == "struct":
        s, i = parse_struct(toks, i, owner, model)
        return ("struct", s), i
    return ("ident", t), i + 1


def parse_dim(toks, i, owner):
    """An optional [N] after a name: (N, next index)."""
    if i < len(toks) and toks[i] == "[":
        v = toks[i + 1]
        dim = int(v, 0) if re.match(r"^\d", v) else owner_const(owner, v)
        while toks[i] != "]":
            i += 1
        return dim, i + 1
    return 1, i


def owner_const(owner, name):
    cls = owner
    while cls is not None:
        if name.lower() in cls.consts:
            return cls.consts[name.lower()]
        cls = getattr(cls, "_base_obj", None)
    raise ValueError("unknown array size %s in %s" % (name, owner.name))


def parse_enum(toks, i, owner, model):
    # enum Name { A, B, C }
    assert toks[i].lower() == "enum"
    name = toks[i + 1]
    i += 2
    assert toks[i] == "{", (owner.name, name, toks[i:i + 5])
    i += 1
    values = []
    while toks[i] != "}":
        if toks[i] != ",":
            values.append(toks[i])
        i += 1
    e = ScriptEnum(name, values, owner)
    key = name.lower()
    if key in model.enums and model.enums[key].values != values:
        model.warn("enum %s declared twice, differently (%s, %s)" % (name, model.enums[key].owner.name, owner.name))
    model.enums.setdefault(key, e)
    owner.enums[key] = e
    return e, i + 1


def parse_struct(toks, i, owner, model):
    # struct [modifiers] Name [extends Base] { var ...; ... }
    assert toks[i].lower() == "struct"
    i += 1
    j = i
    while toks[j] != "{":
        j += 1
    head = toks[i:j]
    base = None
    if len(head) >= 3 and head[-2].lower() in ("extends", "expands"):
        base, head = head[-1], head[:-2]
    name = head[-1]
    s = ScriptStruct(name, base, owner)
    i = j + 1
    while toks[i] != "}":
        if toks[i].lower() == "var":
            i = parse_var(toks, i, owner, model, s.fields)
        elif toks[i].lower() == "struct":
            _, i = parse_struct(toks, i, owner, model)
            if toks[i] == ";":
                i += 1
        elif toks[i].lower() == "enum":
            _, i = parse_enum(toks, i, owner, model)
            if toks[i] == ";":
                i += 1
        else:
            i += 1
    key = name.lower()
    if key in model.structs:
        model.warn("struct %s declared twice (%s, %s)" % (name, model.structs[key].owner.name, owner.name))
    else:
        model.structs[key] = s
    owner.structs[key] = s
    return s, i + 1


def parse_var(toks, i, owner, model, fields):
    # var [(group)] modifiers* Type Name[N] [, Name[N]]* ;
    assert toks[i].lower() == "var"
    i += 1
    if toks[i] == "(":
        while toks[i] != ")":
            i += 1
        i += 1
    while toks[i].lower() in VAR_MODIFIERS:
        i += 1
    type_, i = parse_type(toks, i, owner, model)
    while True:
        name = toks[i]
        dim, i = parse_dim(toks, i + 1, owner)
        fields.append(Field(name, type_, dim))
        if toks[i] == ",":
            i += 1
            continue
        break
    while toks[i] != ";":
        i += 1
    return i + 1


def skip_statement(toks, i):
    """Past a statement: to its ';', or past its { } block."""
    depth = 0
    while i < len(toks):
        t = toks[i]
        if t == "{":
            depth += 1
        elif t == "}":
            depth -= 1
            if depth == 0:
                i += 1
                if i < len(toks) and toks[i] == ";":
                    i += 1
                return i
        elif t == ";" and depth == 0:
            return i + 1
        i += 1
    return i


def parse_class(cls, model):
    toks = tokenize(cls.text)
    # class Name [extends Base] modifiers ;
    i = 0
    while toks[i] != ";":
        if toks[i].lower() in ("native", "intrinsic"):
            cls.native = True
        i += 1
    i += 1
    while i < len(toks):
        t = toks[i].lower()
        if t == "var":
            i = parse_var(toks, i, cls, model, cls.fields)
        elif t == "const":
            name, val = toks[i + 1], toks[i + 3]
            if re.match(r"^\d", val):
                try:
                    cls.consts[name.lower()] = int(val, 0)
                except ValueError:
                    pass
            i = skip_statement(toks, i)
        elif t == "struct":
            _, i = parse_struct(toks, i, cls, model)
            if i < len(toks) and toks[i] == ";":
                i += 1
        elif t == "enum":
            _, i = parse_enum(toks, i, cls, model)
            if i < len(toks) and toks[i] == ";":
                i += 1
        else:
            i = skip_statement(toks, i)


# ---------------------------------------------------------------------------
# Layout

class Layout:
    def __init__(self, model, cpp_names):
        self.model = model
        self.cpp = cpp_names            # script class (lower) -> C++ name

    def resolve(self, type_, owner):
        """('byte'|'int'|...|'obj'|'struct'|'enum', key)"""
        k = type_[0]
        if k != "ident":
            if k in ("struct", "enum"):
                return type_
            return (k, None)
        name = type_[1].lower()
        if name == "object":
            return ("obj", "object")
        if name in INTRINSIC:
            return ("intrinsic", INTRINSIC[name])
        if name in self.model.classes:
            return ("obj", name)
        c = owner if isinstance(owner, ScriptClass) else owner.owner
        while c is not None:             # this class's own, then its ancestors'
            if name in c.enums:
                return ("enum", c.enums[name])
            if name in c.structs:
                return ("struct", c.structs[name])
            c = c._base_obj
        if name in self.model.enums:
            return ("enum", self.model.enums[name])
        if name in self.model.structs:
            return ("struct", self.model.structs[name])
        self.model.warn("unknown type %s in %s; taken as a pointer" % (type_[1], owner.name))
        return ("obj", None)

    def struct_layout(self, s):
        if s.size is not None:
            return
        start, algn = 0, 1
        if s.base:
            b = self.resolve(("ident", s.base), s)[1]
            s.base_obj = b
            self.struct_layout(b)
            start, algn = b.size, b.align
        end, a = self.lay(s.fields, start, s.owner)
        s.align = max(algn, a)
        s.size = align(end, s.align)

    def size_align(self, rt):
        k = rt[0]
        if k in ("byte", "enum"):
            return 1, 1
        if k == "string" or k == "array":
            return 12, 4
        if k == "struct":
            self.struct_layout(rt[1])
            return rt[1].size, rt[1].align
        return 4, 4

    def lay(self, fields, off, owner):
        prev_bool = None
        max_align = 1
        for f in fields:
            rt = self.resolve(f.type, owner)
            f.rtype = rt
            if rt[0] == "bool":
                if prev_bool is not None and prev_bool.bit < 31:
                    f.offset, f.bit = prev_bool.offset, prev_bool.bit + 1
                else:
                    off = align(off, 4)
                    f.offset, f.bit = off, 0
                    off += 4
                prev_bool = f
                max_align = max(max_align, 4)
                continue
            prev_bool = None
            size, a = self.size_align(rt)
            off = align(off, a)
            f.offset = off
            off += size * f.dim
            max_align = max(max_align, a)
        return off, max_align

    def class_layout(self, cls):
        if hasattr(cls, "size"):
            return
        start = 0
        if cls.base:
            b = self.model.classes.get(cls.base.lower())
            if b is None:
                raise ValueError("%s: base %s has no script" % (cls.name, cls.base))
            self.class_layout(b)
            start = b.size
        end, _ = self.lay(cls.fields, start, cls)
        cls.size = align(end, 4)


# ---------------------------------------------------------------------------
# PE exports (the C++ class names, and registration sizes on the host)

class PE:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        d = self.data
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        nsec = struct.unpack_from("<H", d, pe + 6)[0]
        optsz = struct.unpack_from("<H", d, pe + 20)[0]
        opt = pe + 24
        self.base = struct.unpack_from("<I", d, opt + 28)[0]
        exp_rva = struct.unpack_from("<I", d, opt + 96)[0]
        self.sections = []
        for k in range(nsec):
            s = pe + 24 + optsz + 40 * k
            name = d[s:s + 8].rstrip(b"\0").decode()
            vsize, va, rsize, raw = struct.unpack_from("<IIII", d, s + 8)
            self.sections.append((name, va, max(vsize, rsize), raw, rsize))
        self.exports = {}
        if exp_rva:
            o = self.off(exp_rva)
            nfun, nnames, afun, anames, aords = struct.unpack_from("<IIIII", d, o + 20)
            for k in range(nnames):
                nrva = struct.unpack_from("<I", d, self.off(anames) + 4 * k)[0]
                ordi = struct.unpack_from("<H", d, self.off(aords) + 2 * k)[0]
                frva = struct.unpack_from("<I", d, self.off(afun) + 4 * ordi)[0]
                no = self.off(nrva)
                name = d[no:d.index(b"\0", no)].decode("latin-1")
                self.exports[name] = self.base + frva

    def off(self, rva):
        for _, va, size, raw, rsize in self.sections:
            if va <= rva < va + size:
                return raw + rva - va
        raise ValueError("rva %x outside the sections" % rva)

    def registered_sizes(self):
        """{C++ class: size} from `push Size; push 0` shortly before
        `mov ecx, offset <class>` and a call -- UClass's native constructor
        taking (EC_NativeConstructor, Size, ...). Best effort, from the bytes:
        a class whose code does not match is left out; IDA's check reads
        them all."""
        out = {}
        d = self.data
        for name, va in self.exports.items():
            m = re.match(r"^\?PrivateStaticClass@(\w+)@@0VUClass@@A$", name)
            if not m:
                continue
            needle = b"\xB9" + struct.pack("<I", va)
            pos = d.find(needle)
            while pos >= 0 and m.group(1) not in out:
                after = d[pos + 5:pos + 17]
                if b"\xFF\x15" in after or b"\xE8" in after:
                    for p in range(pos - 6, max(pos - 32, 0), -1):
                        if d[p] != 0x68:
                            continue
                        size = struct.unpack_from("<I", d, p + 1)[0]
                        ec = d[p + 5:p + 7]
                        if size < 0x100000 and (ec[:1] in (b"\x56", b"\x57", b"\x53", b"\x55") or ec == b"\x6A\x00"):
                            out[m.group(1)] = size
                            break
                pos = d.find(needle, pos + 1)
        return out


def cpp_class_names(system_dir):
    """script class (lower) -> C++ name, from the DLLs' exports; and every
    mangled export name, for struct naming."""
    names, mangled = {}, []
    for dll in DLLS:
        path = os.path.join(system_dir, dll + ".dll")
        if not os.path.exists(path):
            continue
        pe = PE(path)
        for n in pe.exports:
            mangled.append(n)
            m = re.match(r"^\?PrivateStaticClass@(\w+)@@0VUClass@@A$", n)
            if m:
                cpp = m.group(1)
                names.setdefault(cpp[1:].lower(), cpp)
    return names, mangled


# ---------------------------------------------------------------------------
# The model, laid out

def build(game_dir):
    system_dir = os.path.join(game_dir, "System")
    model = Model()
    read_packages(system_dir, model)
    for cls in model.classes.values():
        try:
            parse_class(cls, model)
        except Exception as e:  # a script the parser cannot follow: its layout is unknown
            model.warn("%s.%s: %s" % (cls.package, cls.name, e))
            cls.fields = None
    for cls in model.classes.values():
        cls._base_obj = model.classes.get(cls.base.lower()) if cls.base else None
    cpp, mangled = cpp_class_names(system_dir)
    joined = "\n".join(mangled)
    for cls in model.classes.values():
        for st in cls.structs.values():
            st.cname = "F" + st.name
            for cand in ("F" + st.name, "X" + st.name, st.name):
                if re.search(r"[UV]%s@@" % re.escape(cand), joined):
                    st.cname = cand
                    break
    lay = Layout(model, cpp)
    natives = []
    for key, cls in model.classes.items():
        if key in cpp or cls.native:
            natives.append(cls)
    # A native class's ancestors are native too; lay them all out.
    for cls in natives:
        c = cls
        while c is not None:
            if c.fields is None:
                raise ValueError("%s: its script could not be parsed" % c.name)
            c = c._base_obj
        lay.class_layout(cls)
    return model, lay, natives, cpp


def cname_of_class(cls, cpp):
    key = cls.name.lower()
    if key in cpp:
        return cpp[key]
    c = cls
    while c is not None:
        if c.name.lower() == "actor":
            return "A" + cls.name
        c = c._base_obj
    return "U" + cls.name


# ---------------------------------------------------------------------------
# C declarations

PRELUDE = """
struct FName { int Index; };
struct FString { unsigned __int16 *Data; int ArrayNum; int ArrayMax; };
struct FArray { void *Data; int ArrayNum; int ArrayMax; };
struct UClass;
struct UStruct;
struct UState;
struct FStateFrame;
struct ULinkerLoad;
struct FFrame { void *vftable; UStruct *Node; struct UObject *Object; unsigned __int8 *Code; unsigned __int8 *Locals; };
"""

# UObject as its C++ header declares it; the script's ObjectInternal[6]
# covers the first six.
UOBJECT = """struct UObject
{
  void *vftable;
  int Index;
  UObject *HashNext;
  FStateFrame *StateFrame;
  ULinkerLoad *_Linker;
  int _LinkerIndex;
  UObject *Outer;
  unsigned int ObjectFlags;
  FName Name;
  UClass *Class;
};
"""


def emit(model, lay, natives, cpp):
    """The C declarations, and the natives' {C++ name: size}."""
    out = ["#pragma pack(push, 4)", PRELUDE]
    native_keys = {c.name.lower() for c in natives}
    class_cname = {}
    for c in model.classes.values():
        if c.name.lower() in native_keys:
            class_cname[c.name.lower()] = cname_of_class(c, cpp)

    def c_ident(n):
        return n + "_" if n.lower() in C_KEYWORDS else n

    # Which structs and enums the natives need (objects: a name can be
    # declared by more than one class).
    need_structs, need_enums = [], []

    def need_struct(st):
        if st in need_structs:
            return
        if getattr(st, "base_obj", None) is not None:
            need_struct(st.base_obj)
        for f in st.fields:
            note_field(f)
        need_structs.append(st)

    def note_field(f):
        rt = f.rtype
        if rt[0] == "struct":
            need_struct(rt[1])
        elif rt[0] == "enum" and rt[1] not in need_enums:
            need_enums.append(rt[1])

    for c in natives:
        for f in c.fields:
            note_field(f)

    # Two different types of one name: the later one takes its class's name.
    taken = {}
    for t in need_enums + need_structs:
        cname = t.cname if isinstance(t, ScriptStruct) else t.name
        if cname in taken and taken[cname] is not t:
            cname = "%s_%s" % (t.owner.name, cname)
        taken[cname] = t
        t.emit_name = cname

    # Enums; an enumerator used by two enums gets its enum's name in front.
    used = {}
    for e in need_enums:
        for v in e.values:
            used[v] = used.get(v, 0) + 1
    for e in sorted(need_enums, key=lambda e: e.emit_name):
        vals = []
        for k, v in enumerate(e.values):
            n = v if used[v] == 1 else "%s__%s" % (e.emit_name, v)
            vals.append("  %s = %d," % (n, k))
        out.append("enum %s : unsigned __int8\n{\n%s\n};" % (e.emit_name, "\n".join(vals)))

    def ctype(f):
        rt = f.rtype
        k = rt[0]
        if k == "byte":
            return "unsigned __int8"
        if k == "int":
            return "int"
        if k == "float":
            return "float"
        if k == "name":
            return "FName"
        if k == "string":
            return "FString"
        if k == "array":
            return "FArray"
        if k == "pointer":
            return "void *"
        if k == "class":
            return "UClass *"
        if k == "intrinsic":
            return rt[1] + " *"
        if k in ("enum", "struct"):
            return rt[1].emit_name
        if k == "obj":
            key = rt[1]
            c = model.classes.get(key) if key else None
            while c is not None and c.name.lower() not in class_cname:
                c = c._base_obj
            return (class_cname[c.name.lower()] if c else "UObject") + " *"
        raise ValueError(k)

    def body(fields):
        lines = []
        for f in fields:
            if f.rtype[0] == "bool":
                lines.append("  unsigned __int32 %s : 1;" % c_ident(f.name))
                continue
            dim = "[%d]" % f.dim if f.dim > 1 else ""
            lines.append("  %s %s%s;" % (ctype(f), c_ident(f.name), dim))
        return "\n".join(lines)

    out.append("struct UObject;")
    for n in sorted(set(INTRINSIC.values())):
        out.append("struct %s;" % n)
    for key in sorted(class_cname):
        if key != "object":
            out.append("struct %s;" % class_cname[key])

    for st in need_structs:
        b = getattr(st, "base_obj", None)
        head = "struct __cppobj %s : %s" % (st.emit_name, b.emit_name) if b else "struct %s" % st.emit_name
        out.append("%s\n{\n%s\n};" % (head, body(st.fields)))

    out.append(UOBJECT)
    done = {"object"}
    sizes = {"UObject": 0x28}

    def emit_class(c):
        key = c.name.lower()
        if key in done:
            return
        base = c._base_obj
        emit_class(base)
        done.add(key)
        out.append("struct __cppobj %s : %s\n{\n%s\n};" % (class_cname[key], class_cname[base.name.lower()], body(c.fields)))
        sizes[class_cname[key]] = c.size

    for c in sorted(natives, key=lambda c: c.name.lower()):
        emit_class(c)
    out.append("#pragma pack(pop)")
    return "\n".join(out) + "\n", sizes


# ---------------------------------------------------------------------------
# IDA

def ida_main():
    import ida_funcs
    import ida_nalt
    import ida_typeinf
    import idautils
    import idc

    game = os.environ.get("PXM_GAME_DIR")
    if not game:
        game = os.path.dirname(os.path.dirname(os.path.abspath(idc.get_idb_path())))
    model, lay, natives, cpp = build(game)
    text, sizes = emit(model, lay, natives, cpp)

    # Declare, one declaration at a time, so a failure names itself.
    decls = re.split(r"\n(?=(?:struct|enum) )", text.replace("#pragma pack(push, 4)\n", "").replace("#pragma pack(pop)\n", ""))
    failed = []
    for d in decls:
        if not d.strip():
            continue
        if idc.parse_decls("#pragma pack(push, 4)\n" + d + "\n#pragma pack(pop)\n", idc.PT_SILENT) != 0:
            failed.append(d.split("\n", 1)[0])
    print("declared: %d classes, %d declarations failed" % (len(sizes), len(failed)))
    for f in failed[:20]:
        print("  FAILED:", f)

    # Every class the DLL registers, against the size it gives UClass. The
    # constructor is Core's: calls go to its import or to a jump stub of it
    # (Engine.dll has one nothing calls), so every name it has counts.
    ctors = {ea for ea, name in idautils.Names() if re.search(r"\?\?0UClass@@QAE@W4ENativeConstructor@@", name)}
    results, unread = {}, []
    if ctors:
        calls = sorted({x.frm for c in ctors for x in idautils.XrefsTo(c)
                        if x.frm not in ctors and idc.print_insn_mnem(x.frm) in ("call", "jmp")})
        for ea in calls:
            # The last `mov ecx` before the call loads the class object; an
            # earlier one can load the base's (ServerCommandlet's).
            pushes, cls, obj = [], None, None
            f = ida_funcs.get_func(ea)
            lo = f.start_ea if f else ea - 0x80
            p = ea
            while p > lo and (obj is None or len(pushes) < 2):
                p = idc.prev_head(p)
                mn = idc.print_insn_mnem(p)
                if mn == "push":
                    pushes.append(p)
                elif mn == "mov" and idc.print_operand(p, 0) == "ecx" and obj is None:
                    obj = idc.get_operand_value(p, 1)
                    m = re.match(r"^\?PrivateStaticClass@(\w+)@@", idc.get_name(obj) or "")
                    cls = m.group(1) if m else None
            if cls is None or len(pushes) < 2 or idc.get_operand_type(pushes[1], 0) != idc.o_imm:
                unread.append(cls or hex(ea))
                continue
            size = idc.get_operand_value(pushes[1], 0)
            t = ida_typeinf.tinfo_t()
            got = t.get_size() if t.get_named_type(None, cls) else ida_typeinf.BADSIZE
            results[cls] = (size, None if got == ida_typeinf.BADSIZE else got)
    match = sorted(c for c, (w, g) in results.items() if g == w)
    wrong = sorted(c for c, (w, g) in results.items() if g is not None and g != w)
    nolay = sorted(c for c, (w, g) in results.items() if g is None)
    print("sizes: of %d classes registered, %d match, %d differ, %d have no layout (C++ only)"
          % (len(results), len(match), len(wrong), len(nolay)))
    for c in wrong:
        print("  %s: registered 0x%x, laid out 0x%x" % (c, results[c][0], results[c][1]))
    if nolay:
        print("  no layout:", ", ".join(nolay))
    if unread:
        print("  registrations not read:", ", ".join(unread[:20]))

    # `this` on every member function of a declared class.
    typed = 0
    for ea in idautils.Functions():
        name = idc.get_name(ea) or ""
        m = re.match(r"^\?(?:\?[0-9A-Z_]|\w+@)(\w+)@@[QUAEIM][AB]E", name)
        if not m:
            continue
        cls = m.group(1)
        st = ida_typeinf.tinfo_t()
        if not st.get_named_type(None, cls):
            continue
        tif = ida_typeinf.tinfo_t()
        if not ida_nalt.get_tinfo(tif, ea) and not ida_typeinf.guess_tinfo(tif, ea):
            continue
        fi = ida_typeinf.func_type_data_t()
        if not tif.get_func_details(fi) or fi.size() == 0:
            continue
        ptr = ida_typeinf.tinfo_t()
        ptr.create_ptr(st)
        if fi[0].type == ptr:
            continue
        fi[0].type = ptr
        new = ida_typeinf.tinfo_t()
        new.create_func(fi)
        if ida_typeinf.apply_tinfo(ea, new, ida_typeinf.TINFO_DEFINITE):
            typed += 1
    print("this: typed on %d member functions" % typed)
    for w in [w for w in model.warnings if "declared twice" not in w][:20]:
        print("  warning:", w)


def host_main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--game", default=os.path.join(here, "..", "..", "gamefiles"))
    ap.add_argument("--emit", metavar="FILE")
    ap.add_argument("--sizes", action="store_true")
    ap.add_argument("--check", nargs="+", metavar="DLL")
    ap.add_argument("--layout", nargs="+", metavar="CLASS", help="a class's fields at their offsets")
    ap.add_argument("-v", "--verbose", action="store_true", help="also names declared by more than one class")
    a = ap.parse_args(argv)
    model, lay, natives, cpp = build(a.game)
    text, sizes = emit(model, lay, natives, cpp)
    by_cpp = {v.lower(): k for k, v in cpp.items()}
    for name in a.layout or []:
        key = name.lower()
        c = model.classes.get(key) or model.classes.get(by_cpp.get(key, ""))
        if c is None:
            print("no class %s" % name)
            continue
        anc = c._base_obj
        while anc is not None:
            print("%s: 0x%x" % (anc.name, anc.size))
            anc = anc._base_obj
        print("%s (0x%x):" % (c.name, c.size))
        for f in c.fields:
            bit = " bit %d (0x%x)" % (f.bit, 1 << f.bit) if f.bit is not None else ""
            dim = "[%d]" % f.dim if f.dim > 1 else ""
            print("  0x%04x %5d  %s%s%s" % (f.offset, f.offset, f.name, dim, bit))
    status = 0
    for dll in a.check or []:
        reg = PE(dll).registered_sizes()
        ok = [c for c in reg if sizes.get(c) == reg[c]]
        bad = [c for c in reg if c in sizes and sizes[c] != reg[c]]
        absent = [c for c in reg if c not in sizes]
        print("%s: %d registrations read; %d match, %d differ, %d not laid out"
              % (os.path.basename(dll), len(reg), len(ok), len(bad), len(absent)))
        for c in sorted(bad):
            print("  %s: registered 0x%x, laid out 0x%x" % (c, reg[c], sizes[c]))
        if absent:
            print("  not laid out:", ", ".join(sorted(absent)))
        status |= 1 if bad else 0
    for w in model.warnings:
        if a.verbose or "declared twice" not in w:
            print("warning:", w, file=sys.stderr)
    return status


try:
    import idaapi  # noqa: F401
    IN_IDA = True
except ImportError:
    IN_IDA = False

if IN_IDA:
    ida_main()
elif __name__ == "__main__":
    sys.exit(host_main(sys.argv[1:]))
