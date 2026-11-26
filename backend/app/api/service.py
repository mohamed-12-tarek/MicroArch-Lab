"""Simulation service: assembly text -> parse -> run -> API response.

Owner: M1.  This is the only module that knows about both halves of the
backend: the parser (M2, ``app.core.parser``) and the pipeline runner
(M5, ``app.core.pipeline``).  The routes stay thin, and the frontend only ever
sees :class:`~app.schemas.simulation.SimulationResponse`.

Why the fallback?
-----------------
M4/M5 own ``core/pipeline.py``.  Until their ``run_simulation`` is merged this
module answers with a **placeholder** timeline (N + 4 cycles, no stalls, no
forwards, zeroed state) and sets ``engine: "mock"`` + a warning, exactly as
agreed in ``docs/api-contract.md``.  The moment the real runner appears the
same code path is used -- no changes needed here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..core.errors import (
    ALLOWED_EXTENSIONS,
    MAX_CYCLES,
    MAX_FILE_SIZE_BYTES,
    FileTooLargeError,
    InvalidFileEncodingError,
    MicroArchError,
    SimulationError,
    UnsupportedFileTypeError,
    to_error_item,
)
from ..core.instruction import Instruction
from ..core.parser import parse
from ..schemas.simulation import (
    CycleSnapshot,
    FinalState,
    HealthResponse,
    SimulationResponse,
)

logger = logging.getLogger(__name__)

STAGES = ("IF", "ID", "EX", "MEM", "WB")
REGISTER_NAMES = [f"R{i}" for i in range(32)]
API_VERSION = "1.0.0"

# The real runner is optional until M5 is merged.
try:  # pragma: no cover - depends on which branch is checked out
    from ..core.pipeline import run_simulation as _run_simulation
except (ImportError, AttributeError):  # pragma: no cover
    _run_simulation = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def engine_name() -> str:
    """``"real"`` when M5's runner is available, otherwise ``"mock"``."""
    return "real" if callable(_run_simulation) else "mock"


def health() -> HealthResponse:
    """Body of ``GET /api/health``."""
    return HealthResponse(
        status="ok",
        version=API_VERSION,
        engine=engine_name(),
        endpoints=["/api/health", "/api/simulate", "/api/simulate/upload"],
    )


def simulate_code(code: str) -> SimulationResponse:
    """Parse ``code`` and run it through the pipeline.

    Parse errors come back as ``success: false`` with every bad line listed.
    """
    parsed = parse(code)
    if not parsed.success:
        return _error_response(
            [to_error_item(error, default_type="parse") for error in parsed.errors],
            engine=engine_name(),
        )

    if not callable(_run_simulation):
        return _placeholder_response(parsed.instructions)

    try:
        raw_result = _run_simulation(parsed.instructions)
    except SimulationError as exc:
        return _error_response([exc.to_dict()], engine="real")
    except MicroArchError as exc:
        return _error_response([exc.to_dict()], engine="real")
    except Exception as exc:  # pragma: no cover - defensive integration guard
        logger.exception("Simulation engine crashed")
        return _error_response(
            [
                {
                    "line": None,
                    "message": f"Internal simulator error: {exc}",
                    "type": "internal",
                }
            ],
            engine="real",
        )

    return _success_response(raw_result, parsed.instructions)


def simulate_upload(filename: Optional[str], content: bytes) -> SimulationResponse:
    """Validate an uploaded ``.asm`` file and simulate it.

    Raises :class:`UnsupportedFileTypeError` (400),
    :class:`FileTooLargeError` (413) or :class:`InvalidFileEncodingError` (400).
    """
    name = filename or ""
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported file type: {name or '(no name)'} (expected {allowed})"
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File is too large: {len(content)} bytes "
            f"(maximum {MAX_FILE_SIZE_BYTES} bytes)"
        )

    try:
        code = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidFileEncodingError(
            f"File must be UTF-8 text: {exc}"
        ) from exc

    return simulate_code(code)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
def _error_response(
    errors: Sequence[Dict[str, Any]], engine: str = "real"
) -> SimulationResponse:
    return SimulationResponse(
        success=False,
        total_cycles=0,
        errors=list(errors),
        engine=engine,
    )


def _success_response(
    raw_result: Any, instructions: Sequence[Instruction]
) -> SimulationResponse:
    """Normalize whatever M5 returns into the documented response shape."""
    history = _normalize_history(_get(raw_result, "history", []) or [], instructions)
    total_cycles = _get(raw_result, "total_cycles", None)
    if total_cycles is None:
        total_cycles = len(history)

    if total_cycles > MAX_CYCLES:
        return _error_response(
            [
                {
                    "line": None,
                    "message": f"Simulation did not finish within {MAX_CYCLES} cycles",
                    "type": "simulation",
                }
            ],
            engine="real",
        )

    final_state = _normalize_final_state(
        _get(raw_result, "final_state", None) or _get(raw_result, "processor", None),
        history,
    )

    stall_count = _get(raw_result, "stall_count", None)
    if stall_count is None:
        stall_count = sum(1 for cycle in history if cycle["stall"] is not None)

    forward_count = _get(raw_result, "forward_count", None)
    if forward_count is None:
        forward_count = sum(len(cycle["forwards"]) for cycle in history)

    return SimulationResponse(
        success=True,
        total_cycles=int(total_cycles),
        stall_count=int(stall_count),
        forward_count=int(forward_count),
        instructions=[instruction.to_dict() for instruction in instructions],
        history=[CycleSnapshot(**cycle) for cycle in history],
        final_state=FinalState(**final_state),
        engine="real",
    )


def _placeholder_response(instructions: Sequence[Instruction]) -> SimulationResponse:
    """N + 4 cycle timeline with no stalls and no forwards (engine not merged yet)."""
    count = len(instructions)
    total_cycles = count + 4 if count else 0
    empty_registers = {name: 0 for name in REGISTER_NAMES}

    history: List[Dict[str, Any]] = []
    for cycle in range(1, total_cycles + 1):
        stages: Dict[str, Any] = {}
        for offset, stage in enumerate(STAGES):
            index = cycle - 1 - offset
            if 0 <= index < count:
                stages[stage] = {
                    "instruction_id": instructions[index].instruction_id,
                    "text": instructions[index].text,
                    "stalled": False,
                }
            else:
                stages[stage] = None
        history.append(
            {
                "cycle": cycle,
                "stages": stages,
                "forwards": [],
                "registers": dict(empty_registers),
                "memory": {},
                "completed": max(0, min(count, cycle - 4)),
                "stall": None,
            }
        )

    return SimulationResponse(
        success=True,
        total_cycles=total_cycles,
        stall_count=0,
        forward_count=0,
        instructions=[instruction.to_dict() for instruction in instructions],
        history=[CycleSnapshot(**cycle) for cycle in history],
        final_state=FinalState(registers=empty_registers, memory={}),
        warnings=[
            "Pipeline engine is not connected yet (M4/M5): "
            "this timeline is a placeholder without stalls or forwarding."
        ],
        engine="mock",
    )


# ---------------------------------------------------------------------------
# Normalization helpers (tolerant of dataclasses, dicts and pydantic models)
# ---------------------------------------------------------------------------
def _get(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _as_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            result = to_dict()
        except Exception:  # pragma: no cover - defensive
            result = None
        if isinstance(result, dict):
            return result
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return dict(attributes)
    return {}


def _normalize_history(
    raw_history: Iterable[Any], instructions: Sequence[Instruction]
) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    completed = 0
    for index, raw_cycle in enumerate(raw_history):
        data = _as_mapping(raw_cycle)

        raw_stages = data.get("stages")
        if not isinstance(raw_stages, dict):
            raw_stages = {
                stage: data.get(stage, data.get(stage.lower())) for stage in STAGES
            }
        stages = {
            stage: _normalize_slot(raw_stages.get(stage), instructions)
            for stage in STAGES
        }

        if stages["WB"] is not None:
            completed += 1

        forwards = [
            _normalize_forward(item) for item in (data.get("forwards") or [])
        ]
        forwards = [item for item in forwards if item is not None]

        cycle = data.get("cycle", index + 1)
        history.append(
            {
                "cycle": int(cycle),
                "stages": stages,
                "forwards": forwards,
                "registers": _normalize_registers(data.get("registers")),
                "memory": _normalize_memory(data.get("memory")),
                "completed": int(data.get("completed", completed)),
                "stall": _normalize_stall(data.get("stall")),
            }
        )
    return history


def _normalize_slot(
    slot: Any, instructions: Sequence[Instruction]
) -> Optional[Dict[str, Any]]:
    if slot is None:
        return None

    data = _as_mapping(slot)
    instruction = data.get("instruction")
    if instruction is not None and not isinstance(instruction, dict):
        instruction_id = getattr(instruction, "instruction_id", None)
        text = getattr(instruction, "text", "")
    else:
        instruction_id = data.get("instruction_id")
        text = data.get("text", "")

    if instruction_id is None:
        return None

    instruction_id = int(instruction_id)
    if not text:
        text = _instruction_text(instructions, instruction_id)

    return {
        "instruction_id": instruction_id,
        "text": text,
        "stalled": bool(data.get("stalled", False)),
    }


def _instruction_text(instructions: Sequence[Instruction], instruction_id: int) -> str:
    for instruction in instructions:
        if instruction.instruction_id == instruction_id:
            return instruction.text
    return f"I{instruction_id}"


def _normalize_forward(value: Any) -> Optional[Dict[str, Any]]:
    data = _as_mapping(value)
    register = data.get("register")
    if register is None:
        return None
    return {
        "register": str(register).upper(),
        "from_stage": str(data.get("from_stage", "")).upper(),
        "from_instruction": int(data.get("from_instruction", -1)),
        "to_instruction": int(data.get("to_instruction", -1)),
    }


def _normalize_stall(value: Any) -> Optional[Dict[str, Any]]:
    if value is None or value is False:
        return None
    if isinstance(value, str):
        return {"instruction_id": None, "register": None, "reason": value}

    data = _as_mapping(value)
    reason = data.get("reason") or data.get("message") or ""
    if not reason:
        return None

    instruction_id = data.get("instruction_id")
    if instruction_id is None:
        instruction = data.get("instruction")
        if instruction is not None and not isinstance(instruction, dict):
            instruction_id = getattr(instruction, "instruction_id", None)

    register = data.get("register")
    if register is None and isinstance(data.get("registers"), (list, tuple)):
        registers = list(data["registers"])
        register = registers[0] if registers else None

    return {
        "instruction_id": None if instruction_id is None else int(instruction_id),
        "register": None if register is None else str(register).upper(),
        "reason": str(reason),
    }


def _normalize_registers(value: Any) -> Dict[str, int]:
    """Always return all 32 registers so the UI has a fixed grid."""
    data = _as_mapping(value)
    # Accept a Processor / RegisterFile wrapper as well as a plain dict.
    for key in ("registers", "register_file", "regs"):
        inner = data.get(key)
        if inner is None:
            continue
        inner_map = _as_mapping(inner)
        if inner_map:
            data = inner_map
            break

    registers: Dict[str, int] = {}
    for name in REGISTER_NAMES:
        raw = data.get(name, data.get(name.lower(), 0))
        try:
            registers[name] = int(raw)
        except (TypeError, ValueError):
            registers[name] = 0
    registers["R0"] = 0
    return registers


def _normalize_memory(value: Any) -> Dict[str, int]:
    data = _as_mapping(value)
    memory: Dict[str, int] = {}
    for address, word in data.items():
        try:
            key = str(int(address))
        except (TypeError, ValueError):
            key = str(address)
        try:
            memory[key] = int(word)
        except (TypeError, ValueError):
            memory[key] = 0
    return memory


def _normalize_final_state(value: Any, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    registers = _normalize_registers(_get(value, "registers", None))
    memory = _normalize_memory(_get(value, "memory", None))

    if value is None and history:
        registers = history[-1]["registers"]
        memory = history[-1]["memory"]

    return {"registers": registers, "memory": memory}
