# owner: M3
# ControlSignals + ControlUnit

from dataclasses import dataclass
from typing import Optional

from app.core.instruction import Instruction


@dataclass(frozen=True)
class ControlSignals:
    """Control signals generated for one instruction."""

    alu_op: Optional[str]
    alu_src: bool
    reg_write: bool
    mem_read: bool
    mem_write: bool
    mem_to_reg: bool


class ControlUnit:
    """Decode instructions and generate control signals."""

    def decode(self, instruction: Instruction) -> ControlSignals:

        if not isinstance(instruction, Instruction):
            raise TypeError("Expected an Instruction object")

        opcode = instruction.opcode.upper()

        if opcode == "ADD":
            return ControlSignals(
                alu_op="ADD",
                alu_src=False,
                reg_write=True,
                mem_read=False,
                mem_write=False,
                mem_to_reg=False
            )

        elif opcode == "SUB":
            return ControlSignals(
                alu_op="SUB",
                alu_src=False,
                reg_write=True,
                mem_read=False,
                mem_write=False,
                mem_to_reg=False
            )

        elif opcode == "AND":
            return ControlSignals(
                alu_op="AND",
                alu_src=False,
                reg_write=True,
                mem_read=False,
                mem_write=False,
                mem_to_reg=False
            )

        elif opcode == "OR":
            return ControlSignals(
                alu_op="OR",
                alu_src=False,
                reg_write=True,
                mem_read=False,
                mem_write=False,
                mem_to_reg=False
            )

        elif opcode == "ADDI":
            return ControlSignals(
                alu_op="ADD",
                alu_src=True,
                reg_write=True,
                mem_read=False,
                mem_write=False,
                mem_to_reg=False
            )

        elif opcode == "LW":
            return ControlSignals(
                alu_op="ADD",
                alu_src=True,
                reg_write=True,
                mem_read=True,
                mem_write=False,
                mem_to_reg=True
            )

        elif opcode == "SW":
            return ControlSignals(
                alu_op="ADD",
                alu_src=True,
                reg_write=False,
                mem_read=False,
                mem_write=True,
                mem_to_reg=False
            )

        elif opcode == "NOP":
            return ControlSignals(
                alu_op=None,
                alu_src=False,
                reg_write=False,
                mem_read=False,
                mem_write=False,
                mem_to_reg=False
            )

        else:
            raise ValueError(f"Unsupported instruction: {opcode}")
