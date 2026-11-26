"""Instruction model for the MicroArch Lab assembly simulator.

Owner: M2.  Everyone (M3, M4, M5, M1) depends on this file, so the field
names and method names below must not change.

Field mapping per opcode
------------------------
ADD/SUB/AND/OR  ADD R3, R1, R2   -> rd=R3, rs1=R1, rs2=R2
ADDI            ADDI R1, R0, 10  -> rd=R1, rs1=R0, immediate=10
LW              LW R3, 4(R2)     -> rd=R3, rs1=R2 (base), immediate=4
SW              SW R1, 4(R2)     -> rs2=R1 (value), rs1=R2 (base), immediate=4, rd=None
NOP             NOP              -> everything None
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

R_TYPE_OPCODES = ("ADD", "SUB", "AND", "OR")
SUPPORTED_OPCODES = R_TYPE_OPCODES + ("ADDI", "LW", "SW", "NOP")

REGISTER_COUNT = 32
IMMEDIATE_MIN = -32768
IMMEDIATE_MAX = 32767
MAX_INSTRUCTIONS = 200


@dataclass(frozen=True)
class Instruction:
    """One decoded assembly instruction (immutable)."""

    opcode: str
    rd: Optional[str] = None
    rs1: Optional[str] = None
    rs2: Optional[str] = None
    immediate: Optional[int] = None
    line_number: int = 0  # 1-based line in the source code
    raw: str = ""  # source line without comment, trimmed
    instruction_id: int = 0  # index in the program, starts at 0

    def source_registers(self) -> List[str]:
        """Registers this instruction reads, in order, without duplicates.

        R0 is NOT filtered out here; the hazard unit decides to ignore it.
        """
        if self.opcode in R_TYPE_OPCODES or self.opcode == "SW":
            candidates = [self.rs1, self.rs2]
        elif self.opcode in ("ADDI", "LW"):
            candidates = [self.rs1]
        else:  # NOP (or anything without sources)
            candidates = []

        result: List[str] = []
        for reg in candidates:
            if reg is not None and reg not in result:
                result.append(reg)
        return result

    def destination_register(self) -> Optional[str]:
        """Register this instruction writes, or None (SW and NOP)."""
        if self.opcode in ("SW", "NOP"):
            return None
        return self.rd

    @property
    def text(self) -> str:
        """Normalized text, e.g. ``ADD R3, R1, R2``."""
        op = self.opcode
        if op in R_TYPE_OPCODES:
            return f"{op} {self.rd}, {self.rs1}, {self.rs2}"
        if op == "ADDI":
            return f"{op} {self.rd}, {self.rs1}, {self.immediate}"
        if op == "LW":
            return f"{op} {self.rd}, {self.immediate}({self.rs1})"
        if op == "SW":
            return f"{op} {self.rs2}, {self.immediate}({self.rs1})"
        return op  # NOP

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly representation (used by the API layer)."""
        return {
            "instruction_id": self.instruction_id,
            "opcode": self.opcode,
            "rd": self.rd,
            "rs1": self.rs1,
            "rs2": self.rs2,
            "immediate": self.immediate,
            "line_number": self.line_number,
            "raw": self.raw,
            "text": self.text,
        }
