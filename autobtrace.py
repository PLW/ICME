import lldb
import time

# --- ANSI color codes ---
COLOR_RESET   = "\033[0m"
COLOR_HEADER  = "\033[95m"   # Magenta header
COLOR_REASON  = "\033[93m"   # Yellow stop reason
COLOR_THREAD  = "\033[96m"   # Cyan thread label
COLOR_FUNC    = "\033[92m"   # Green function name
COLOR_FILE    = "\033[90m"   # Gray file/line
COLOR_FRAMEID = "\033[97m"   # Bright white frame index

def print_backtrace(process):
    """Print full backtrace for all threads, colorized for visibility."""
    for t in process:
        print(f"\n{COLOR_THREAD}Thread #{t.GetIndexID()}{COLOR_RESET} "
              f"(stop reason: {t.GetStopDescription(256)})")

        for f in t:
            fn = f.GetFunctionName() or f.GetSymbol().GetName() or "<unknown>"
            line_entry = f.GetLineEntry()
            if line_entry.IsValid():
                fs = line_entry.GetFileSpec()
                file_line = f"{fs.GetFilename()}:{line_entry.GetLine()}"
            else:
                file_line = ""
            print(f"  {COLOR_FRAMEID}frame #{f.GetFrameID()}: "
                  f"{COLOR_FUNC}{fn:<25}{COLOR_RESET} "
                  f"{COLOR_FILE}{file_line}{COLOR_RESET}")
    print("\n", flush=True)


def autobtrace(debugger, command, exe_ctx, result, internal_dict):
    """
    Loop: continue -> print full backtrace -> pause 4 s -> repeat until exit.
    Usage: (lldb) autobtrace
    """
    debugger.SetAsync(False)

    target = debugger.GetSelectedTarget()
    process = target.GetProcess()

    if not process or not process.IsValid():
        result.PutCString("No active process. Start the program first (e.g. 'run').")
        return

    print(f"\n{COLOR_HEADER}Starting auto-backtrace loop...{COLOR_RESET}\n", flush=True)

    while True:
        state = process.GetState()

        if state in (lldb.eStateExited, lldb.eStateDetached):
            print(f"\n{COLOR_HEADER}Program exited with status "
                  f"{process.GetExitStatus()}.{COLOR_RESET}\n", flush=True)
            break

        if state == lldb.eStateStopped:
            thread = process.GetSelectedThread()
            reason = thread.GetStopDescription(256)
            print(f"\n{COLOR_REASON}=== Stop reason: {reason} ==={COLOR_RESET}\n", flush=True)

            print_backtrace(process)

            # Pause 4 seconds for observation
            time.sleep(4)

        # Continue to next breakpoint or exit
        process.Continue()


def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand(
        'command script add -f autobtrace.autobtrace autobtrace')
    print("Registered 'autobtrace' command (colorized output, 2s pause).")
