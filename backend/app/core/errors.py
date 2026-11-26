"""Shared error types and limits for the MicroArch Lab backend.

Owner: M1.  Every layer (parser, components, engine, API) raises one of the
exceptions below so that the API can turn *any* failure into the same JSON
shape::

    {"line": 2, "message": "Unsupported instruction: MULT", "type": "parse"}

``type`` is one of ``parse`` · ``simulation`` · ``request`` · ``internal``.

The three error categories the API knows about
----------------------------------------------
1. **Parse errors** (M2) — collected by :func:`app.core.parser.parse`; they are
   data, not exceptions, and the API returns them with ``success: false``.
2. **Simulation errors** (M3/M4/M5) — a runtime problem tied to one
   instruction.  Raise :class:`SimulationError` with the ``Instruction`` so the
   response always carries its source ``line``.
3. **Request errors** (M1) — bad file type / too large / not UTF-8.  These map
   to a real HTTP status (400 / 413) instead of ``success: false``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Limits shared by the API, the parser and the runner.
# ---------------------------------------------------------------------------
MAX_SOURCE_CHARS = 100_000  # hard cap for the /api/simulate body
MAX_FILE_SIZE_BYTES = 100 * 1024  # 100 KB, per the spec
ALLOWED_EXTENSIONS = frozenset({".asm"})
MAX_CYCLES = 1000  # the runner gives up after this many cycles


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class MicroArchError(Exception):
    """Base class for every error raised on purpose by this project."""

    error_type = "internal"
    status_code = 500

    def to_dict(self) -> Dict[str, Any]:
        return {"line": None, "message": str(self), "type": self.error_type}


# ---------------------------------------------------------------------------
# Simulation errors (raised by M3 / M4 / M5)
# ---------------------------------------------------------------------------
class SimulationError(MicroArchError):
    """A runtime problem tied to one instruction.

    Parameters
    ----------
    message:
        Human readable text, shown as-is by the frontend.
    instruction:
        The ``Instruction`` that caused the problem (preferred).  Its
        ``line_number`` and ``instruction_id`` are copied automatically.
    line / instruction_id:
        Explicit overrides when no instruction object is available.
    """

    error_type = "simulation"
    status_code = 422

    def __init__(
        self,
        message: str,
        *,
        instruction: Any = None,
        line: Optional[int] = None,
        instruction_id: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        if instruction is not None:
            if line is None:
                line = getattr(instruction, "line_number", None)
            if instruction_id is None:
                instruction_id = getattr(instruction, "instruction_id", None)
        # A line of 0 means "unknown" in the Instruction model.
        self.line = line or None
        self.instruction_id = instruction_id
        self.instruction = instruction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "message": str(self),
            "type": self.error_type,
        }


class HazardError(SimulationError):
    """The pipeline reached a state that the hazard unit should have blocked."""

    error_type = "internal"


class MemoryAccessError(SimulationError):
    """Unaligned or out-of-range data-memory access."""


class InternalSimulationError(MicroArchError):
    """A bug in the simulator itself (never the user's fault)."""

    error_type = "internal"
    status_code = 500


# ---------------------------------------------------------------------------
# Request errors (raised by the API layer)
# ---------------------------------------------------------------------------
class RequestError(MicroArchError):
    """Bad input that is *not* the user's assembly code."""

    error_type = "request"
    status_code = 400


class UnsupportedFileTypeError(RequestError):
    """The uploaded file is not a ``.asm`` file."""

    status_code = 400


class FileTooLargeError(RequestError):
    """The uploaded file is bigger than :data:`MAX_FILE_SIZE_BYTES`."""

    status_code = 413


class InvalidFileEncodingError(RequestError):
    """The uploaded file is not valid UTF-8 text."""

    status_code = 400


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def to_error_item(error: Any, default_type: str = "internal") -> Dict[str, Any]:
    """Normalize anything error-like into the JSON error shape.

    Accepts a dict, a :class:`MicroArchError`, a parser ``ParseError``
    (anything with ``to_dict``) or a plain exception.
    """
    if isinstance(error, dict):
        item = dict(error)
        item.setdefault("line", None)
        item.setdefault("message", "")
        item.setdefault("type", default_type)
        return item

    to_dict = getattr(error, "to_dict", None)
    if callable(to_dict):
        return to_error_item(to_dict(), default_type=default_type)

    return {"line": None, "message": str(error), "type": default_type}
