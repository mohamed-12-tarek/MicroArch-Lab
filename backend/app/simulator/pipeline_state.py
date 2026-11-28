from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StageSlot:
    """
    Represents one instruction inside one pipeline stage.

    Fields:
        instruction: The instruction object.
        rs1_value: Value read for source register 1.
        rs2_value: Value read for source register 2.
        alu_result: Result calculated in EX.
        write_value: Final value that will be written back to a register.
    """

    instruction: Optional[Any] = None
    rs1_value: Optional[int] = None
    rs2_value: Optional[int] = None
    alu_result: Optional[int] = None
    write_value: Optional[int] = None

    def copy(self) -> "StageSlot":
        """Return an independent copy of this stage slot."""
        return StageSlot(
            instruction=self.instruction,
            rs1_value=self.rs1_value,
            rs2_value=self.rs2_value,
            alu_result=self.alu_result,
            write_value=self.write_value,
        )

    @property
    def is_empty(self) -> bool:
        return self.instruction is None


@dataclass
class PipelineState:
    """
    Snapshot of the complete pipeline at a particular cycle.

    IF, ID, EX, MEM and WB contain StageSlot objects or None.
    pc points to the next instruction to fetch.
    forwards contains forwarding events from the current cycle.
    """

    IF: Optional[StageSlot] = None
    ID: Optional[StageSlot] = None
    EX: Optional[StageSlot] = None
    MEM: Optional[StageSlot] = None
    WB: Optional[StageSlot] = None

    pc: int = 0

    forwards: list[dict[str, Any]] = field(default_factory=list)

    stall: bool = False
    stall_reason: Optional[str] = None

    def copy(self) -> "PipelineState":
        """Return a new state without modifying the original state."""

        def copy_slot(slot: Optional[StageSlot]) -> Optional[StageSlot]:
            return slot.copy() if slot is not None else None

        return PipelineState(
            IF=copy_slot(self.IF),
            ID=copy_slot(self.ID),
            EX=copy_slot(self.EX),
            MEM=copy_slot(self.MEM),
            WB=copy_slot(self.WB),
            pc=self.pc,
            forwards=[event.copy() for event in self.forwards],
            stall=self.stall,
            stall_reason=self.stall_reason,
        )

    def is_empty(self) -> bool:
        """Return True when all pipeline stages are empty."""
        return all(
            slot is None or slot.is_empty
            for slot in (self.IF, self.ID, self.EX, self.MEM, self.WB)
        )