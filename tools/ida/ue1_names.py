"""Names for a UE1 DLL's static initializers.

A UE1 DLL registers each of its classes and natives from small functions the
C runtime calls at load, which IDA leaves as sub_XXXX. Run this in IDA (File >
Script file, or the MCP's py_exec_file), after tools/ida/ue1_types.py; it names
them by what they do:

- <class>_StaticInit: builds the class object (UClass's native constructor);
- <class>_StaticInitAtExit: calls that and registers the destructor;
- <class>_StaticClassDestroy: the class object's destructor;
- RegisterNative_<class>_exec<name>: one GRegisterNative call.

Only functions still called sub_... are renamed; running it again changes
nothing. It prints what it named.
"""
import re

import ida_funcs
import ida_name
import idautils
import idc


def set_name(ea, name):
    flags = ida_name.SN_NOWARN | ida_name.SN_NOCHECK
    return ida_name.set_name(ea, name, flags) or ida_name.set_name(ea, "%s_%X" % (name, ea), flags)


def unnamed(ea):
    return idc.get_func_name(ea).startswith("sub_")


def name_class_inits():
    """<class>_StaticInit: the function that calls UClass's native
    constructor with `mov ecx, offset <class>::PrivateStaticClass`."""
    ctor = None
    for ea, name in idautils.Names():
        if re.search(r"\?\?0UClass@@QAE@W4ENativeConstructor@@", name):
            ctor = ea
            break
    n = 0
    if ctor is None:
        return n
    for x in idautils.XrefsTo(ctor):
        if idc.print_insn_mnem(x.frm) not in ("call", "jmp"):
            continue
        f = ida_funcs.get_func(x.frm)
        if not f or not unnamed(f.start_ea):
            continue
        p = x.frm
        for _ in range(16):
            p = idc.prev_head(p)
            if idc.print_insn_mnem(p) == "mov" and idc.print_operand(p, 0) == "ecx":
                m = re.match(r"^\?PrivateStaticClass@(\w+)@@", idc.get_name(idc.get_operand_value(p, 1)) or "")
                if m and set_name(f.start_ea, m.group(1) + "_StaticInit"):
                    n += 1
                break
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
    counts = {"class": name_class_inits(), "native": 0, "atexit": 0, "destroy": 0}
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
            m = re.search(r"\?PrivateStaticClass@(\w+)@@", refs)
            if m and set_name(f, m.group(1) + "_StaticClassDestroy"):
                counts["destroy"] += 1
    left = sum(1 for f in idautils.Functions() if unnamed(f))
    print("named: %d class inits, %d native registrations, %d atexit wrappers, %d class destructors; %d sub_ left"
          % (counts["class"], counts["native"], counts["atexit"], counts["destroy"], left))


main()
