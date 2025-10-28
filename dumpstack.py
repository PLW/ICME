# dumpstack.py — LLDB command to dump the entire call stack with variables.
# Usage:
#   (lldb) command script import /path/dumpstack.py
#   (lldb) dumpstack [-t THREAD_INDEX] [-d MAX_DEPTH] [--all] [--max-items N]

import lldb
import shlex

def _indent(n):
    return "  " * n

def _fmt_val(val):
    """Return a compact string of value/summary/address if available."""
    if not val or not val.IsValid():
        return "<invalid>"
    v = val.GetValue() or ""
    s = val.GetSummary() or ""
    a = val.GetLoadAddress(val.GetTarget())  # returns LLDB_INVALID_ADDRESS if not loaded
    pieces = []
    if v:
        pieces.append(v)
    if s and s != v:
        pieces.append(s)
    if a != lldb.LLDB_INVALID_ADDRESS and val.GetType().IsPointerType():
        pieces.append(f"@0x{a:x}")
    return " ".join(pieces) if pieces else "<no value>"

def _should_expand(val):
    if not val or not val.IsValid():
        return False
    t = val.GetType()
    if not t.IsValid():
        return False
    # Expand if it has children (struct/class/union/array) or is a pointer/reference
    return val.MightHaveChildren() or t.IsPointerType() or t.IsReferenceType()

def _iter_children(val, max_items):
    """Yield up to max_items children, handling synthetic children if present."""
    if not val or not val.IsValid():
        return
    count = val.GetNumChildren()
    for i in range(min(count, max_items)):
        yield val.GetChildAtIndex(i)

def _dump_value(val, depth, max_depth, max_items, out_lines, visited=set()):
    """Recursive pretty-printer with depth and item limits."""
    if not val or not val.IsValid():
        out_lines.append(_indent(depth) + "<invalid value>")
        return

    ty = val.GetTypeName() or "<type?>"
    name = val.GetName() or "<unnamed>"
    line = f"{_indent(depth)}{name}: {ty} = {_fmt_val(val)}"
    out_lines.append(line)

    # Avoid infinite recursion on self-referential structures by address
    if depth >= max_depth:
        return

    # For pointers/references, deref once to show pointee fields
    t = val.GetType()
    deref = None
    if t and (t.IsPointerType() or t.IsReferenceType()):
        deref = val.Dereference()
        if deref and deref.IsValid():
            out_lines.append(_indent(depth+1) + "*pointee:")
            _dump_value(deref, depth+1, max_depth, max_items, out_lines, visited)
        return  # After showing the pointee, don't also iterate children of the pointer itself

    # Aggregate types / arrays
    if _should_expand(val):
        for child in _iter_children(val, max_items):
            _dump_value(child, depth+1, max_depth, max_items, out_lines, visited)

def _dump_frame(frame, in_scope_only, max_depth, max_items, out_lines):
    func = frame.GetFunction()
    sym  = frame.GetSymbol()
    mod  = frame.GetModule()
    file_line = ""
    line_entry = frame.GetLineEntry()
    if line_entry and line_entry.IsValid():
        fs = line_entry.GetFileSpec()
        file_line = f"{fs.GetFilename()}:{line_entry.GetLine()}"

    pc = frame.GetPCAddress()
    pc_str = pc.GetLoadAddress(frame.GetThread().GetProcess().GetTarget())
    fname = func.GetName() if func and func.IsValid() else (sym.GetName() if sym and sym.IsValid() else "<unknown>")

    out_lines.append(f"  at {fname}  (pc=0x{pc_str:x})  {file_line}")
    out_lines.append("    Arguments / Locals / Statics:")

    # Grab variables: args, locals, statics, (in-scope only or not)
    vars_list = frame.GetVariables(True,  # arguments
                               True,  # locals
                               True,  # statics
                               in_scope_only)  # in_scope_only

    # De-duplicate by name (LLDB can sometimes return overlaps)
    seen = set()
    for v in vars_list:
        n = v.GetName() or ""
        if n in seen:
            continue
        seen.add(n)
        _dump_value(v, depth=3, max_depth=max_depth, max_items=max_items, out_lines=out_lines)

def dumpstack_command(debugger, command, exe_ctx, result, internal_dict):
    """
    LLDB command entrypoint:
      dumpstack [-t THREAD_INDEX] [-d MAX_DEPTH] [--all] [--max-items N]
    """
    # Defaults
    thread_index = None
    max_depth    = 2
    in_scope_only = True
    max_items     = 64

    # Parse args
    args = shlex.split(command)
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-t", "--thread"):
            i += 1; thread_index = int(args[i])
        elif a in ("-d", "--depth"):
            i += 1; max_depth = int(args[i])
        elif a == "--all":
            in_scope_only = False
        elif a == "--max-items":
            i += 1; max_items = int(args[i])
        else:
            raise ValueError(f"unknown option: {a}")
        i += 1

    target = exe_ctx.GetTarget()
    process = exe_ctx.GetProcess()
    if not process or not process.IsValid() or process.GetState() not in (lldb.eStateStopped, lldb.eStateCrashed):
        result.PutCString("Process is not stopped; break somewhere (or 'process interrupt') first.")
        result.SetStatus(lldb.eReturnStatusFailed)
        return

    # Select thread
    if thread_index is None:
        thread = process.GetSelectedThread()
    else:
        if thread_index < 0 or thread_index >= process.GetNumThreads():
            result.PutCString(f"Invalid thread index {thread_index}; process has {process.GetNumThreads()} threads.")
            result.SetStatus(lldb.eReturnStatusFailed)
            return
        thread = process.GetThreadAtIndex(thread_index)

    if not thread or not thread.IsValid():
        result.PutCString("No valid thread selected.")
        result.SetStatus(lldb.eReturnStatusFailed)
        return

    lines = []
    lines.append(f"=== dumpstack: thread #{thread.GetIndexID()} (stop reason: {thread.GetStopReason()}) ===")
    for fi in range(thread.GetNumFrames()):
        frame = thread.GetFrameAtIndex(fi)
        lines.append(f"\nFrame #{fi}:")
        _dump_frame(frame, in_scope_only=in_scope_only, max_depth=max_depth, max_items=max_items, out_lines=lines)

    result.PutCString("\n".join(lines))
    result.SetStatus(lldb.eReturnStatusSuccess)

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f dumpstack.dumpstack_command dumpstack')
    print("Registered 'dumpstack' command. Usage: dumpstack [-t N] [-d D] [--all] [--max-items N]")

