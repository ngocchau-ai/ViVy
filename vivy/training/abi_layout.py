"""C10 — C-ABI layout / ownership / error-propagation contract.

Acceptance-plan C10.2: verify ABI layout/ownership/lifetime, error propagation;
DLL load được KHÔNG được coi là memory path đúng.

Contract source: `engine/include/context_memory.h`.
This module checks the Python ctypes view of those structs (as used by
`vivy/integration/cautreo_binding.py`) against the header, and
defines the ownership rules a wrapper must follow (borrowed get → copy out).

Changelog:
    2026-09-24 (Claude Code — P5 C10): Initial.
"""
from __future__ import annotations

import ctypes
from typing import Any, Mapping

# --- header constants (context_memory.h) ---------------------------------

CT_MEMORY_ID_MAX = 96
CT_MEMORY_HASH_MAX = 96
CT_MEMORY_CONTENT_MAX = 1024 * 1024

KIND_VALUES = {
    "HARD_FACT": 0,
    "TASK": 1,
    "CONSTRAINT": 2,
    "SUMMARY": 3,
}

STATUS_VALUES = {
    "OK": 0,
    "INVALID": -1,
    "NOMEM": -2,
    "IO": -3,
    "CORRUPT": -4,
    "CONFLICT": -5,
    "NOT_FOUND": -6,
}

PUT_FIELDS = [
    "id", "kind", "content", "content_len", "provenance",
    "created_at_ms", "expires_at_ms",
]
ITEM_FIELDS = [
    "id", "kind", "content", "content_len", "message_id", "tool_call_id",
    "source_offset", "source_length", "source_hash",
    "version", "created_at_ms", "updated_at_ms", "expires_at_ms", "deleted",
]
PROVENANCE_FIELDS = [
    "message_id", "tool_call_id", "source_offset", "source_length", "source_hash",
]
OPTIONS_FIELDS = ["persistence", "cold_log_path", "max_items"]


# --- ctypes mirrors of the C structs -------------------------------------


class CtMemoryProvenance(ctypes.Structure):
    _fields_ = [
        ("message_id", ctypes.c_char_p),
        ("tool_call_id", ctypes.c_char_p),
        ("source_offset", ctypes.c_uint64),
        ("source_length", ctypes.c_uint64),
        ("source_hash", ctypes.c_char_p),
    ]


class CtMemoryPut(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_char_p),
        ("kind", ctypes.c_int),
        ("content", ctypes.c_char_p),
        ("content_len", ctypes.c_size_t),
        ("provenance", CtMemoryProvenance),
        ("created_at_ms", ctypes.c_uint64),
        ("expires_at_ms", ctypes.c_uint64),
    ]


class CtMemoryItem(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_char * CT_MEMORY_ID_MAX),
        ("kind", ctypes.c_int),
        ("content", ctypes.c_char_p),
        ("content_len", ctypes.c_size_t),
        ("message_id", ctypes.c_char * CT_MEMORY_ID_MAX),
        ("tool_call_id", ctypes.c_char * CT_MEMORY_ID_MAX),
        ("source_offset", ctypes.c_uint64),
        ("source_length", ctypes.c_uint64),
        ("source_hash", ctypes.c_char * CT_MEMORY_HASH_MAX),
        ("version", ctypes.c_uint64),
        ("created_at_ms", ctypes.c_uint64),
        ("updated_at_ms", ctypes.c_uint64),
        ("expires_at_ms", ctypes.c_uint64),
        ("deleted", ctypes.c_bool),
    ]


class CtMemoryOptions(ctypes.Structure):
    _fields_ = [
        ("persistence", ctypes.c_int),
        ("cold_log_path", ctypes.c_char_p),
        ("max_items", ctypes.c_size_t),
    ]


# --- error propagation ---------------------------------------------------


class MemoryInvalid(RuntimeError):
    pass


class MemoryError(RuntimeError):
    pass


class MemoryIOError(RuntimeError):
    pass


class MemoryCorrupt(RuntimeError):
    pass


class MemoryConflict(RuntimeError):
    pass


class MemoryNotFound(RuntimeError):
    pass


_STATUS_EXC = {
    STATUS_VALUES["INVALID"]: MemoryInvalid,
    STATUS_VALUES["NOMEM"]: MemoryError,
    STATUS_VALUES["IO"]: MemoryIOError,
    STATUS_VALUES["CORRUPT"]: MemoryCorrupt,
    STATUS_VALUES["CONFLICT"]: MemoryConflict,
    STATUS_VALUES["NOT_FOUND"]: MemoryNotFound,
}


def map_status(status: int) -> BaseException | None:
    """Map a ct_memory_status_t to an exception instance (None when OK).

    Unknown codes are INVALID — fail closed rather than pretend success.
    """
    if status == STATUS_VALUES["OK"]:
        return None
    exc_cls = _STATUS_EXC.get(status, MemoryInvalid)
    return exc_cls(f"ct_memory_status={status}")


def raise_on_status(status: int) -> None:
    exc = map_status(status)
    if exc is not None:
        raise exc


# --- ownership / lifetime ------------------------------------------------


def ownership_rules() -> dict[str, Any]:
    """Documented lifetime rules a C-ABI wrapper must follow.

    get returns a BORROWED `const ct_memory_item_t *` — valid only until the
    next call or close(). A wrapper must copy content/id out before returning
    to Python. put borrows caller strings only for the duration of the call.
    close() invalidates every borrowed pointer and the handle itself.
    """
    return {
        "get_returns_borrowed_must_copy": True,
        "put_ownership": "borrowed_for_call_only",
        "retrieve_ownership": "borrowed_until_next_call_or_close",
        "close_invalidates": True,
        "dll_load_is_not_memory_correctness": True,
    }


def copy_item_out(borrowed: Any) -> dict[str, Any]:
    """Copy a borrowed ct_memory_item_t view into independent Python values."""
    raw_content = getattr(borrowed, "content", None)
    if isinstance(raw_content, (bytes, bytearray)):
        content = bytes(raw_content).decode("utf-8", errors="replace")
    elif isinstance(raw_content, str):
        content = raw_content
    else:
        content = ""
    raw_id = getattr(borrowed, "id", b"")
    if isinstance(raw_id, (bytes, bytearray)):
        item_id = bytes(raw_id).split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    else:
        item_id = str(raw_id)
    return {
        "id": item_id,
        "kind": int(getattr(borrowed, "kind", 0)),
        "content": content,
        "content_len": int(getattr(borrowed, "content_len", len(content))),
        "version": int(getattr(borrowed, "version", 0)),
        "created_at_ms": int(getattr(borrowed, "created_at_ms", 0)),
        "updated_at_ms": int(getattr(borrowed, "updated_at_ms", 0)),
    }


# --- layout check --------------------------------------------------------


def _field_names(struct: type[ctypes.Structure]) -> list[str]:
    return [f[0] for f in struct._fields_]


def check_struct_layout() -> dict[str, Any]:
    """Compare the Python ctypes view to the header field order and sizes."""
    put_fields = _field_names(CtMemoryPut)
    item_fields = _field_names(CtMemoryItem)
    prov_fields = _field_names(CtMemoryProvenance)
    opt_fields = _field_names(CtMemoryOptions)

    ok = (
        put_fields == PUT_FIELDS
        and item_fields == ITEM_FIELDS
        and prov_fields == PROVENANCE_FIELDS
        and opt_fields == OPTIONS_FIELDS
    )
    return {
        "ok": ok,
        "put_fields": put_fields,
        "item_fields": item_fields,
        "provenance_fields": prov_fields,
        "options_fields": opt_fields,
        "sizeof": {
            "CtMemoryProvenance": ctypes.sizeof(CtMemoryProvenance),
            "CtMemoryPut": ctypes.sizeof(CtMemoryPut),
            "CtMemoryItem": ctypes.sizeof(CtMemoryItem),
            "CtMemoryOptions": ctypes.sizeof(CtMemoryOptions),
        },
        "id_array_len": CT_MEMORY_ID_MAX,
        "hash_array_len": CT_MEMORY_HASH_MAX,
        "content_max": CT_MEMORY_CONTENT_MAX,
    }
