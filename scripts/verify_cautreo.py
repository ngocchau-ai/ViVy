import ctypes
import os
import sys

dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "engine", "bin", "cautreo.dll"))
try:
    dll = ctypes.CDLL(dll_path)
    has_mem = hasattr(dll, "ct_context_memory_open")
    has_score = hasattr(dll, "ct_score_graph_create")
    if has_mem and has_score:
        print("OK")
        sys.exit(0)
    else:
        print("MISSING_SYMBOLS")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
