"""Pydantic models for a single instruction, a stage slot and an API error.

Owner: M1.  These mirror :class:`app.core.instruction.Instruction` and the
parser's ``ParseError`` so the JSON is documented in one place (``/docs``).
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class InstructionModel(BaseModel):
    """One decoded assembly instruction."""

    model_config = ConfigDict(extra="forbid")

    instruction_id: int = Field(..., ge=0, description="0-based index in the program")
    opcode: str = Field(..., description="ADD/SUB/AND/OR/ADDI/LW/SW/NOP")
    rd: Optional[str] = Field(None, description="Destination register (None for SW/NOP)")
    rs1: Optional[str] = Field(None, description="First source register (base for LW/SW)")
    rs2: Optional[str] = Field(None, description="Second source register (value for SW)")
    immediate: Optional[int] = Field(None, description="Signed 16-bit immediate")
    line_number: int = Field(..., ge=1, description="1-based line in the source code")
    raw: str = Field("", description="Source line without comment, trimmed")
    text: str = Field(..., description="Normalized text, e.g. 'ADD R3, R1, R2'")

    @classmethod
    def from_instruction(cls, instruction: Any) -> "InstructionModel":
        """Build the model from a core ``Instruction``."""
        return cls(**instruction.to_dict())


class ErrorItem(BaseModel):
    """One parse / simulation / request / internal error."""

    line: Optional[int] = Field(None, description="1-based source line, or null")
    message: str = Field(..., description="Message shown to the user")
    type: str = Field(
        "parse",
        description="parse | simulation | request | internal",
    )


class StageSlotModel(BaseModel):
    """What one pipeline stage is holding during one cycle."""

    instruction_id: int
    text: str
    stalled: bool = Field(False, description="True when this slot is frozen by a stall")


class ForwardModel(BaseModel):
    """One forwarded value (a register handed to EX without waiting for WB)."""

    model_config = ConfigDict(populate_by_name=True)

    # Stored as ``register_name`` because ``register`` shadows a BaseModel
    # attribute in Pydantic; the JSON key stays ``register``.
    register_name: str = Field(
        ...,
        validation_alias=AliasChoices("register", "register_name"),
        serialization_alias="register",
        description="Register being forwarded, e.g. R1",
    )
    from_stage: str = Field(..., description="MEM or WB")
    from_instruction: int
    to_instruction: int


class StallModel(BaseModel):
    """Why the pipeline froze during this cycle."""

    model_config = ConfigDict(populate_by_name=True)

    instruction_id: Optional[int] = None
    register_name: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("register", "register_name"),
        serialization_alias="register",
        description="Register that caused the Load-Use stall",
    )
    reason: str
