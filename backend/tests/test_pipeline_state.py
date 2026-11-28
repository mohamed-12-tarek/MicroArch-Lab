from simulator.pipeline_state import PipelineState, StageSlot


class FakeInstruction:
    def __init__(self, opcode="ADD", instruction_id=0):
        self.opcode = opcode
        self.instruction_id = instruction_id


def test_stage_slot_default_values():
    slot = StageSlot()

    assert slot.instruction is None
    assert slot.rs1_value is None
    assert slot.rs2_value is None
    assert slot.alu_result is None
    assert slot.write_value is None
    assert slot.is_empty


def test_stage_slot_with_instruction_is_not_empty():
    slot = StageSlot(instruction=FakeInstruction())
    assert not slot.is_empty


def test_stage_slot_copy_is_independent():
    instruction = FakeInstruction()
    original = StageSlot(
        instruction=instruction,
        rs1_value=10,
        rs2_value=20,
        alu_result=30,
        write_value=30,
    )

    copied = original.copy()

    assert copied is not original
    # Instruction is immutable in the real project; only the slot is copied.
    assert copied.instruction is original.instruction
    assert copied.rs1_value == 10
    assert copied.rs2_value == 20
    assert copied.alu_result == 30
    assert copied.write_value == 30

    copied.rs1_value = 999
    copied.rs2_value = 888
    copied.alu_result = 777
    copied.write_value = 666

    assert original.rs1_value == 10
    assert original.rs2_value == 20
    assert original.alu_result == 30
    assert original.write_value == 30


def test_pipeline_state_default_values():
    state = PipelineState()

    assert state.IF is None
    assert state.ID is None
    assert state.EX is None
    assert state.MEM is None
    assert state.WB is None
    assert state.pc == 0
    assert state.forwards == []
    assert state.stall is False
    assert state.stall_reason is None
    assert state.is_empty()


def test_pipeline_state_copy_is_independent():
    instruction = FakeInstruction()

    original = PipelineState(
        IF=StageSlot(instruction=instruction),
        pc=1,
        forwards=[{
            "register": "R1",
            "from_stage": "MEM",
            "from_instruction": 0,
            "to_instruction": 1,
        }],
        stall=True,
        stall_reason="test reason",
    )

    copied = original.copy()

    assert copied is not original
    assert copied.IF is not original.IF
    assert copied.IF.instruction is instruction
    assert copied.pc == original.pc
    assert copied.stall is True
    assert copied.stall_reason == "test reason"
    assert copied.forwards == original.forwards
    assert copied.forwards is not original.forwards
    assert copied.forwards[0] is not original.forwards[0]

    copied.IF.rs1_value = 50
    copied.forwards[0]["register"] = "R2"
    copied.stall = False
    copied.stall_reason = None

    assert original.IF.rs1_value is None
    assert original.forwards[0]["register"] == "R1"
    assert original.stall is True
    assert original.stall_reason == "test reason"


def test_pipeline_state_is_empty_when_all_stages_are_none():
    assert PipelineState().is_empty()


def test_pipeline_state_is_not_empty_when_any_stage_is_occupied():
    for stage_name in ("IF", "ID", "EX", "MEM", "WB"):
        state = PipelineState()
        setattr(state, stage_name, StageSlot(instruction=FakeInstruction()))
        assert not state.is_empty(), f"{stage_name} was ignored by is_empty()"


def test_empty_stage_slot_counts_as_empty():
    state = PipelineState(
        IF=StageSlot(),
        ID=None,
        EX=None,
        MEM=None,
        WB=None,
    )
    assert state.is_empty()


def test_pipeline_state_copy_does_not_share_stage_slots():
    instruction = FakeInstruction()
    original = PipelineState(
        IF=StageSlot(instruction=instruction),
        ID=StageSlot(instruction=FakeInstruction(instruction_id=1)),
        EX=StageSlot(instruction=FakeInstruction(instruction_id=2)),
        MEM=StageSlot(instruction=FakeInstruction(instruction_id=3)),
        WB=StageSlot(instruction=FakeInstruction(instruction_id=4)),
    )

    copied = original.copy()

    for stage_name in ("IF", "ID", "EX", "MEM", "WB"):
        assert getattr(copied, stage_name) is not getattr(original, stage_name)
        assert (
            getattr(copied, stage_name).instruction
            is getattr(original, stage_name).instruction
        )
