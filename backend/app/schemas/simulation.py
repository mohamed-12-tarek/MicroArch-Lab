"""Pydantic models for the simulation endpoints.

Owner: M1.  This is the contract described in ``docs/api-contract.md``: the
request bodies, the per-cycle snapshot and the one response shape used by
``/api/simulate`` and ``/api/simulate/upload``.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..core.errors import MAX_SOURCE_CHARS
from .instruction import (
    ErrorItem,
    ForwardModel,
    InstructionModel,
    StageSlotModel,
    StallModel,
)


class SimulateRequest(BaseModel):
    """Body of ``POST /api/simulate``."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        ...,
        max_length=MAX_SOURCE_CHARS,
        description="Assembly source code. Comments with '#' or ';' are allowed.",
        examples=["ADDI R1, R0, 10\nADDI R2, R0, 20\nADD R3, R1, R2"],
    )


class StageMap(BaseModel):
    """The five pipeline stages. ``None`` means the stage is empty (bubble)."""

    model_config = ConfigDict(extra="forbid")

    IF: Optional[StageSlotModel] = None
    ID: Optional[StageSlotModel] = None
    EX: Optional[StageSlotModel] = None
    MEM: Optional[StageSlotModel] = None
    WB: Optional[StageSlotModel] = None


class CycleSnapshot(BaseModel):
    """Everything that happened during one clock cycle."""

    cycle: int = Field(..., ge=1)
    stages: StageMap
    forwards: List[ForwardModel] = Field(
        default_factory=list,
        description="Values forwarded into EX during this cycle (may be empty)",
    )
    registers: Dict[str, int] = Field(default_factory=dict, description="R0..R31")
    memory: Dict[str, int] = Field(
        default_factory=dict, description="Only written words, keyed by address"
    )
    completed: int = Field(0, description="Instructions that reached WB so far")
    stall: Optional[StallModel] = Field(
        None, description="Set only on the cycle where the pipeline froze"
    )


class FinalState(BaseModel):
    """Processor state after the last cycle."""

    registers: Dict[str, int] = Field(default_factory=dict)
    memory: Dict[str, int] = Field(default_factory=dict)


class SimulationResponse(BaseModel):
    """One shape for success *and* failure, so the frontend never branches on keys.

    * ``success: true``  -> ``total_cycles``, ``instructions``, ``history``,
      ``final_state`` are filled in.
    * ``success: false`` -> ``errors`` explains why (``history`` is empty).
    """

    success: bool
    total_cycles: int = Field(0, ge=0)
    stall_count: int = Field(0, ge=0, description="Number of Load-Use stalls")
    forward_count: int = Field(0, ge=0, description="Number of forwarded values")
    instructions: List[InstructionModel] = Field(default_factory=list)
    history: List[CycleSnapshot] = Field(default_factory=list)
    final_state: FinalState = Field(default_factory=FinalState)
    errors: List[ErrorItem] = Field(default_factory=list)
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal notices, e.g. 'engine not connected yet'",
    )
    engine: str = Field("real", description="'real' once M4/M5 are merged, else 'mock'")


class HealthResponse(BaseModel):
    """Body of ``GET /api/health``."""

    status: str = "ok"
    version: str = "1.0.0"
    engine: str = "real"
    endpoints: List[str] = Field(default_factory=list)
