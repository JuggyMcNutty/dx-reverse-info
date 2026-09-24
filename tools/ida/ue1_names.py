"""Names for a UE1 DLL's static initializers.

A UE1 DLL registers each of its classes and natives from small functions the
C runtime calls at load, which IDA leaves as sub_XXXX. Run this in IDA (File >
Script file, or the MCP's py_exec_file), after tools/ida/ue1_types.py; it names
them by what they do:

- ?PrivateStaticClass@<class>@@0VUClass@@A: the class object of a class the
  DLL does not export (Engine.dll's AI events and pending levels), the name
  its export would have;
- <class>_StaticInit: builds the class object (UClass's native constructor);
- <class>_StaticInitAtExit: calls that and registers the destructor;
- <class>_StaticClassDestroy: the class object's destructor;
- RegisterNative_<class>_exec<name>: one GRegisterNative call.

Only functions still called sub_... and class objects with no name of their
own are renamed; running it again changes nothing. It prints what it named.
"""
import re

import ida_bytes
import ida_funcs
import ida_name
import idautils
import idc

CLASS_OBJECT = re.compile(r"PrivateStaticClass@(\w+)@@")


def set_name(ea, name):
    flags = ida_name.SN_NOWARN | ida_name.SN_NOCHECK
    return ida_name.set_name(ea, name, flags) or ida_name.set_name(ea, "%s_%X" % (name, ea), flags)


def unnamed(ea):
    return idc.get_func_name(ea).startswith("sub_")


def utf16_at(ea, limit=256):
    """The printable UTF-16 string at ea, or None."""
    s = []
    for i in range(limit):
        c = ida_bytes.get_word(ea + 2 * i)
        if c == 0:
            return "".join(s) or None
        if not 0x20 <= c < 0x7F:
            return None
        s.append(chr(c))
    return None


def ctor_calls():
    """Every call to UClass's native constructor. It is Core's: calls go to its
    import or to a jump stub of it, so every name it has counts."""
    ctors = {ea for ea, name in idautils.Names() if re.search(r"\?\?0UClass@@QAE@W4ENativeConstructor@@", name)}
    return sorted({x.frm for c in ctors for x in idautils.XrefsTo(c)
                   if x.frm not in ctors and idc.print_insn_mnem(x.frm) in ("call", "jmp")})


def class_object(call):
    """The class object a constructor call builds: `mov ecx, offset <it>`."""
    p = call
    for _ in range(16):
        p = idc.prev_head(p)
        if idc.print_insn_mnem(p) == "mov" and idc.print_operand(p, 0) == "ecx":
            return idc.get_operand_value(p, 1)
    return None


def pushed_value(p):
    """What `push` at p pushes: its operand, or what the register was last
    loaded with."""
    if idc.get_operand_type(p, 0) != idc.o_reg:
        return idc.get_operand_value(p, 0)
    reg = idc.print_operand(p, 0)
    for _ in range(16):
        p = idc.prev_head(p)
        if idc.print_insn_mnem(p) == "mov" and idc.print_operand(p, 0) == reg:
            return idc.get_operand_value(p, 1)
    return None


def name_unexported_classes(calls):
    """A class the DLL does not export has no name for its class object. Its
    constructor call pushes the class's name (the last string pushed) and its
    base (the fourth push back from the call), so the object gets the name its
    export would have, prefixed A for an actor and U for the rest. A base named
    here passes its prefix on, so this repeats until nothing more is named."""
    pending = {}
    for call in calls:
        obj = class_object(call)
        if obj is None or CLASS_OBJECT.search(idc.get_name(obj) or ""):
            continue
        f = ida_funcs.get_func(call)
        lo = f.start_ea if f else call - 0x80
        pushes, name, p = [], None, call
        while p > lo and name is None:
            p = idc.prev_head(p)
            if idc.print_insn_mnem(p) == "push":
                pushes.append(p)
                name = utf16_at(idc.get_operand_value(p, 0)) if idc.get_operand_type(p, 0) == idc.o_imm else None
        if name and len(pushes) > 3:
            pending[obj] = (name, pushed_value(pushes[3]))
    n = 0
    while pending:
        progress = False
        for obj, (name, base) in list(pending.items()):
            if base in pending:
                continue
            m = CLASS_OBJECT.search(idc.get_name(base) or "") if base is not None else None
            prefix = "A" if m and m.group(1).startswith("A") else "U"
            if set_name(obj, "?PrivateStaticClass@%s%s@@0VUClass@@A" % (prefix, name)):
                n += 1
            del pending[obj]
            progress = True
        if not progress:
            break
    return n


def name_class_inits(calls):
    """<class>_StaticInit: the function that calls UClass's native
    constructor with `mov ecx, offset <class>::PrivateStaticClass`."""
    n = 0
    for call in calls:
        f = ida_funcs.get_func(call)
        obj = class_object(call)
        if not f or not unnamed(f.start_ea) or obj is None:
            continue
        m = re.match(r"^\?PrivateStaticClass@(\w+)@@", idc.get_name(obj) or "")
        if m and set_name(f.start_ea, m.group(1) + "_StaticInit"):
            n += 1
    return n


def referenced_names(f):
    names = []
    for ea in idautils.FuncItems(f):
        for x in list(idautils.CodeRefsFrom(ea, 0)) + list(idautils.DataRefsFrom(ea)):
            names.append(idc.get_name(x) or "")
        if idc.get_operand_type(ea, 0) == idc.o_imm:
            names.append(idc.get_name(idc.get_operand_value(ea, 0)) or "")
    return " ".join(names)


def main():
    calls = ctor_calls()
    counts = {"object": name_unexported_classes(calls)}
    counts.update({"class": name_class_inits(calls), "native": 0, "atexit": 0, "destroy": 0})
    for f in list(idautils.Functions()):
        if not unnamed(f):
            continue
        refs = referenced_names(f)
        if "GRegisterNative" in refs:
            m = re.search(r"\bint([ADUXF]\w+?)exec(\w+)\b", refs)
            if m and set_name(f, "RegisterNative_%s_exec%s" % (m.group(1), m.group(2))):
                counts["native"] += 1
        elif "_atexit" in refs:
            m = re.search(r"\b(\w+)_StaticInit\b", refs)
            if m and set_name(f, m.group(1) + "_StaticInitAtExit"):
                counts["atexit"] += 1
        elif "??1UClass@@" in refs:
            m = CLASS_OBJECT.search(refs)
            if m and set_name(f, m.group(1) + "_StaticClassDestroy"):
                counts["destroy"] += 1
    left = sum(1 for f in idautils.Functions() if unnamed(f))
    print("named: %d unexported class objects, %d class inits, %d native registrations, %d atexit wrappers, "
          "%d class destructors; %d sub_ left"
          % (counts["object"], counts["class"], counts["native"], counts["atexit"], counts["destroy"], left))


main()
