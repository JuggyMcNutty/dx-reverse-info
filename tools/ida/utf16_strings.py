"""The game's strings as IDA should read them.

This build of the game is Unicode: every TEXT("...") in the DLLs is UTF-16,
and IDA takes many of them for 8-bit strings, which the decompiler then shows
as nonsense ("湅扡敬汃慯" for "EnableCloak"). Run it in IDA (File > Script file,
or the MCP's py_exec_file) after tools/ida/ue1_types.py. It redefines as
UTF-16:

- every string IDA already has, or data it named "a...", in .rdata and .data
  that reads as UTF-16;
- every other address in those sections that the code refers to and that
  reads as UTF-16.

It prints how many it redefined. Running it again changes nothing.
"""
import ida_bytes
import ida_nalt
import ida_name
import ida_segment
import ida_ua
import idautils
import idc

SECTIONS = (".rdata", ".data")


def bounds():
    out = []
    for n in SECTIONS:
        s = ida_segment.get_segm_by_name(n)
        if s:
            out.append((s.start_ea, s.end_ea))
    return out


def in_sections(ea, bs):
    for a, b in bs:
        if a <= ea < b:
            return True
    return False


def utf16_length(ea, limit=4096):
    """Characters of a printable UTF-16 string at ea, or -1."""
    n = 0
    while n < limit:
        lo = ida_bytes.get_byte(ea)
        hi = ida_bytes.get_byte(ea + 1)
        if lo == 0 and hi == 0:
            return n
        if hi != 0 or not (0x20 <= lo < 0x7F or lo in (9, 10, 13)):
            return -1
        n += 1
        ea += 2
    return -1


def make_utf16(ea):
    if ida_nalt.get_str_type(ea) == ida_nalt.STRTYPE_C_16 and ida_bytes.is_strlit(ida_bytes.get_flags(ea)):
        return False
    n = utf16_length(ea)
    if n < 2:
        return False
    ida_bytes.del_items(ea, ida_bytes.DELIT_SIMPLE, (n + 1) * 2)
    return bool(ida_bytes.create_strlit(ea, (n + 1) * 2, ida_nalt.STRTYPE_C_16))


def main():
    bs = bounds()
    fixed = 0
    # Strings and "a..." data IDA already has.
    for a, b in bs:
        ea = a
        while ea != idc.BADADDR and ea < b:
            if ea % 2 == 0 and (ida_bytes.is_strlit(ida_bytes.get_flags(ea)) or ida_name.get_name(ea).startswith("a")):
                if make_utf16(ea):
                    fixed += 1
            ea = idc.next_head(ea, b)
    # Everything else the code points at.
    targets = set()
    for f in idautils.Functions():
        for ea in idautils.FuncItems(f):
            for x in idautils.DataRefsFrom(ea):
                if x % 2 == 0 and in_sections(x, bs):
                    targets.add(x)
            insn = ida_ua.insn_t()
            if ida_ua.decode_insn(insn, ea):
                for op in insn.ops:
                    if op.type == ida_ua.o_void:
                        break
                    for v in (op.value, op.addr):
                        if v and v % 2 == 0 and in_sections(v, bs):
                            targets.add(v)
    for t in sorted(targets):
        if make_utf16(t):
            fixed += 1
    print("utf16 strings: %d redefined" % fixed)


main()
