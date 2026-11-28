from dataclasses import dataclass

import pytest

from simulator.cycle_engine import CycleEngine, SimulationError
from simulator.pipeline_state import PipelineState, StageSlot

STAGES = ("IF", "ID", "EX", "MEM", "WB")


# ---------------- Test doubles ----------------

@dataclass(eq=False)
class FakeInstruction:
    opcode: str
    rd: str = None
    rs1: str = None
    rs2: str = None
    immediate: int = None
    line_number: int = 1
    instruction_id: int = 0
    raw: str = None

    def __post_init__(self):
        self.opcode = self.opcode.upper()
        self.raw = self.raw or self.opcode

    def source_registers(self):
        if self.opcode == "NOP":
            return []
        regs = (self.rs1,) if self.opcode in ("ADDI", "LW") else (self.rs1, self.rs2)
        return [r for r in regs if r]

    def destination_register(self):
        writes = ("ADD", "SUB", "AND", "OR", "ADDI", "LW")
        return self.rd if self.opcode in writes else None

    @property
    def text(self):
        return self.raw

    def __repr__(self):
        return self.raw


@dataclass
class FakeControlSignals:
    alu_op: str = None
    alu_src: bool = False
    reg_write: bool = False
    mem_read: bool = False
    mem_write: bool = False
    mem_to_reg: bool = False


# (alu_op, alu_src, reg_write, mem_read, mem_write, mem_to_reg)
SIGNALS = {
    **{op: (op, False, True) for op in ("ADD", "SUB", "AND", "OR")},
    "ADDI": ("ADD", True, True),
    "LW": ("ADD", True, True, True, False, True),
    "SW": ("ADD", True, False, False, True),
    "NOP": (),
}

ALU = {
    "ADD": lambda a, b: a + b,
    "SUB": lambda a, b: a - b,
    "AND": lambda a, b: a & b,
    "OR": lambda a, b: a | b,
}


def signed_32(value):
    return ((value + 0x80000000) & 0xFFFFFFFF) - 0x80000000


class FakeProcessor:
    def __init__(self):
        self.registers = {f"R{i}": 0 for i in range(32)}
        self.memory = {}

    def decode(self, instruction):
        if instruction.opcode not in SIGNALS:
            raise ValueError(f"Unsupported opcode: {instruction.opcode}")
        return FakeControlSignals(*SIGNALS[instruction.opcode])

    def read_reg(self, register):
        return self.registers[register.upper()]

    def write_reg(self, register, value):
        if register.upper() != "R0":
            self.registers[register.upper()] = signed_32(value)

    def alu_execute(self, operation, a, b):
        if operation.upper() not in ALU:
            raise ValueError(f"Unsupported ALU operation: {operation}")
        return signed_32(ALU[operation.upper()](a, b))

    def load(self, address):
        self._validate(address)
        return self.memory.get(address, 0)

    def store(self, address, value):
        self._validate(address)
        self.memory[address] = signed_32(value)

    @staticmethod
    def _validate(address):
        if not 0 <= address <= 4092:
            raise ValueError(f"Memory address out of range: {address}")
        if address % 4:
            raise ValueError(f"Unaligned memory address: {address}")


# ---------------- Helpers ----------------

def addi(rd, imm, rs1="R0"):
    return FakeInstruction("ADDI", rd, rs1, immediate=imm)


def alu(op, rd, rs1, rs2):
    return FakeInstruction(op, rd, rs1, rs2)


def add(rd, rs1, rs2):
    return alu("ADD", rd, rs1, rs2)


def lw(rd, address):
    return FakeInstruction("LW", rd, "R0", immediate=address)


def sw(rs2, address):
    return FakeInstruction("SW", rs1="R0", rs2=rs2, immediate=address)


def program(*instructions):
    """Number the instructions in order."""
    for i, ins in enumerate(instructions):
        ins.instruction_id, ins.line_number = i, i + 1
        ins.raw = f"I{i}: {ins.opcode}"
    return list(instructions)


def regs(*values):
    return {f"R{i}": v for i, v in enumerate(values, 1)}


def run_program(instructions):
    """History holds occupied cycles only, not the final empty transition."""
    processor = FakeProcessor()
    engine = CycleEngine(processor, instructions)
    state, history = PipelineState(), []
    while not engine.is_finished(state):
        state = engine.step(state)
        if not state.is_empty():
            history.append(state)
        assert len(history) <= 1000, "Pipeline did not finish within 1000 cycles"
    return processor, history, state


def events_of(history):
    return [event for state in history for event in state.forwards]


def check_registers(processor, expected):
    assert {r: processor.read_reg(r) for r in expected} == expected


LOAD_USE = program(addi("R1", 40), sw("R1", 0), lw("R2", 0), add("R3", "R2", "R0"))


# ---------------- PipelineState and StageSlot ----------------

def test_stage_slot_defaults():
    slot = StageSlot()
    for name in ("instruction", "rs1_value", "rs2_value", "alu_result", "write_value"):
        assert getattr(slot, name) is None
    assert slot.is_empty


def test_stage_slot_copy_is_independent():
    values = dict(rs1_value=10, rs2_value=20, alu_result=30, write_value=30)
    original = StageSlot(instruction=add("R1", "R2", "R3"), **values)
    copied = original.copy()
    assert copied is not original
    assert copied.instruction is original.instruction
    assert {k: getattr(copied, k) for k in values} == values
    copied.rs1_value = 999
    assert original.rs1_value == 10


def test_pipeline_state_defaults():
    state = PipelineState()
    assert all(getattr(state, s) is None for s in STAGES)
    assert state.pc == 0 and state.forwards == []
    assert state.stall is False and state.stall_reason is None
    assert state.is_empty()


def test_pipeline_state_copy_is_independent():
    instruction = add("R1", "R2", "R3")
    event = dict(register="R1", from_stage="MEM", from_instruction=0, to_instruction=1)
    original = PipelineState(IF=StageSlot(instruction=instruction), pc=1,
                             forwards=[event])
    copied = original.copy()
    assert copied is not original and copied.IF is not original.IF
    assert copied.IF.instruction is instruction
    assert copied.pc == original.pc
    assert copied.forwards == original.forwards
    assert copied.forwards is not original.forwards
    copied.IF.rs1_value = 50
    copied.forwards[0]["register"] = "R2"
    assert original.IF.rs1_value is None
    assert original.forwards[0]["register"] == "R1"


@pytest.mark.parametrize("stage", STAGES)
def test_any_occupied_stage_makes_state_non_empty(stage):
    state = PipelineState(**{stage: StageSlot(instruction=add("R1", "R2", "R3"))})
    assert not state.is_empty()


def test_empty_stage_slot_counts_as_empty():
    assert PipelineState(IF=StageSlot()).is_empty()


# ---------------- Whole programs: timing, stalls, forwards ----------------

@pytest.mark.parametrize("instructions, cycles, stalls, forwards, expected", [
    pytest.param(program(addi("R1", 10)), 5, 0, None, regs(10), id="single"),
    pytest.param(program(*(addi(f"R{i}", i) for i in range(1, 4))),
                 7, 0, None, regs(1, 2, 3), id="three-independent"),
    pytest.param(program(*(addi(f"R{i}", i) for i in range(1, 6))),
                 9, 0, None, regs(1, 2, 3, 4, 5), id="five-independent"),
    pytest.param(program(FakeInstruction("NOP"), addi("R1", 7)),
                 6, 0, None, regs(7), id="nop"),
    pytest.param(program(addi("R1", 10), addi("R2", 20), add("R3", "R1", "R2")),
                 7, 0, 2, regs(10, 20, 30), id="basic-golden"),
    pytest.param(program(addi("R1", 1), add("R2", "R1", "R1"), add("R3", "R2", "R2")),
                 7, 0, None, regs(1, 2, 4), id="short-chain"),
    pytest.param(program(addi("R1", 1), add("R2", "R1", "R1"),
                         add("R3", "R2", "R2"), add("R4", "R3", "R3")),
                 8, 0, 3, regs(1, 2, 4, 8), id="long-chain"),
    pytest.param(program(lw("R1", 0), addi("R2", 5)),
                 6, 0, None, {"R2": 5}, id="load-then-unrelated"),
    pytest.param(LOAD_USE, 9, 1, None, {"R3": 40}, id="load-use"),
])
def test_program_timing(instructions, cycles, stalls, forwards, expected):
    processor, history, final_state = run_program(instructions)
    events = events_of(history)
    assert len(history) == cycles
    assert sum(bool(s.stall) for s in history) == stalls
    if forwards is not None:
        assert len(events) == forwards
    keys = {"register", "from_stage", "from_instruction", "to_instruction"}
    assert all(set(e) == keys for e in events)
    assert final_state.is_empty()
    check_registers(processor, expected)


# ---------------- Results: arithmetic, R0, memory ----------------

def binary(op, a, b):
    return program(addi("R1", a), addi("R2", b), alu(op, "R3", "R1", "R2"))


@pytest.mark.parametrize("instructions, expected, memory", [
    pytest.param(binary("ADD", 10, 20), regs(10, 20, 30), {}, id="add"),
    pytest.param(binary("SUB", 20, 5), regs(20, 5, 15), {}, id="sub"),
    pytest.param(binary("AND", 6, 3), {"R3": 2}, {}, id="and"),
    pytest.param(binary("OR", 4, 1), {"R3": 5}, {}, id="or"),
    pytest.param(binary("ADD", 32767, 1), {"R3": 32768}, {}, id="above-16-bit"),
    pytest.param(program(addi("R0", 100), addi("R1", 5)),
                 {"R0": 0, "R1": 5}, {}, id="r0-write-ignored"),
    pytest.param(program(addi("R1", 100), sw("R1", 8), lw("R2", 8)),
                 {"R2": 100}, {8: 100}, id="sw-lw"),
    pytest.param(program(addi("R1", 55), sw("R1", 4), lw("R2", 4)),
                 {"R2": 55}, {4: 55}, id="sw-forwarded-data"),
    pytest.param(program(lw("R1", 12)), {"R1": 0}, {}, id="uninitialized-memory"),
])
def test_results(instructions, expected, memory):
    processor, _, _ = run_program(instructions)
    check_registers(processor, expected)
    assert {a: processor.memory.get(a) for a in memory} == memory


# ---------------- Stage movement ----------------

def test_instruction_moves_one_stage_per_cycle_then_drains():
    engine = CycleEngine(FakeProcessor(), program(addi("R1", 5)))
    state = PipelineState()
    for expected_stage in STAGES:
        state = engine.step(state)
        occupied = [s for s in STAGES
                    if getattr(state, s) is not None
                    and getattr(state, s).instruction is not None]
        assert occupied == [expected_stage]
        assert not engine.is_finished(state)
    state = engine.step(state)
    assert state.is_empty() and engine.is_finished(state)


def test_step_does_not_modify_old_state():
    engine = CycleEngine(FakeProcessor(), program(addi("R1", 7)))
    old = PipelineState()
    new = engine.step(old)
    assert old.pc == 0 and all(getattr(old, s) is None for s in STAGES)
    assert new.pc == 1 and new.IF is not None


def test_wb_writes_before_id_reads_in_the_same_cycle():
    producer, consumer = program(addi("R1", 77), add("R2", "R1", "R0"))
    processor = FakeProcessor()
    old = PipelineState(IF=StageSlot(instruction=consumer),
                        MEM=StageSlot(instruction=producer, write_value=77), pc=2)
    new = CycleEngine(processor, []).step(old)
    assert new.WB.instruction.instruction_id == 0
    assert processor.read_reg("R1") == 77
    assert new.ID is not None and new.ID.instruction.instruction_id == 1
    assert new.ID.rs1_value == 77


# ---------------- Stall and forwarding ----------------

def test_stall_freezes_if_and_id_and_inserts_ex_bubble():
    _, history, _ = run_program(
        program(lw("R1", 0), add("R2", "R1", "R0"), addi("R3", 5)))
    i = next(i for i, s in enumerate(history) if s.stall)
    stalled = history[i]
    assert stalled.ID is not None and stalled.ID.instruction.instruction_id == 1
    assert stalled.IF is not None and stalled.IF.instruction.instruction_id == 2
    assert stalled.EX is None
    assert stalled.pc == history[i - 1].pc


def test_load_result_is_forwarded_from_wb_after_the_stall():
    _, history, _ = run_program(LOAD_USE)
    event = next(e for e in events_of(history) if e["register"] == "R2")
    assert (event["from_stage"], event["from_instruction"],
            event["to_instruction"]) == ("WB", 2, 3)


@pytest.mark.parametrize("stage, producer, value", [
    ("MEM", addi("R1", 10), 10),
    ("WB", lw("R1", 0), 15),
])
def test_forwarding_updates_both_operands(stage, producer, value):
    producer, consumer = program(producer, add("R2", "R1", "R1"))
    source = StageSlot(instruction=producer, write_value=value,
                       alu_result=value if stage == "MEM" else None)
    mem, wb = (source, None) if stage == "MEM" else (None, source)
    ex = StageSlot(instruction=consumer, rs1_value=0, rs2_value=0)
    engine = CycleEngine(FakeProcessor(), [])

    forwarding = engine._resolve_forwarding(ex, mem, wb)
    engine._current_forwards = []
    engine._apply_forwarding(ex, mem, wb, forwarding)

    assert (ex.rs1_value, ex.rs2_value) == (value, value)
    assert engine._current_forwards == [dict(
        register="R1", from_stage=stage, from_instruction=0, to_instruction=1)]


def test_mem_has_priority_over_wb():
    older, newer, consumer = program(
        addi("R1", 10), addi("R1", 20), add("R2", "R1", "R1"))
    forwarding = CycleEngine(FakeProcessor(), [])._resolve_forwarding(
        StageSlot(instruction=consumer, rs1_value=0, rs2_value=0),
        StageSlot(instruction=newer, alu_result=20),
        StageSlot(instruction=older, write_value=10))
    assert forwarding["R1"]["from_stage"] == "MEM"
    assert forwarding["R1"]["from_instruction"] == 1


def test_r0_is_never_forwarded():
    producer, consumer = program(addi("R0", 10), addi("R1", 1))
    forwarding = CycleEngine(FakeProcessor(), [])._resolve_forwarding(
        StageSlot(instruction=consumer, rs1_value=0),
        StageSlot(instruction=producer, alu_result=10), None)
    assert "R0" not in forwarding


def test_unrelated_producers_are_not_forwarded():
    mem, wb, consumer = program(
        addi("R4", 1), addi("R5", 2), add("R3", "R1", "R2"))
    assert CycleEngine(FakeProcessor(), [])._resolve_forwarding(
        StageSlot(instruction=consumer, rs1_value=11, rs2_value=22),
        StageSlot(instruction=mem, alu_result=1),
        StageSlot(instruction=wb, write_value=2)) == {}


def test_lw_in_mem_is_not_a_forwarding_source():
    load, consumer = program(lw("R1", 0), add("R2", "R1", "R0"))
    with pytest.raises(SimulationError):
        CycleEngine(FakeProcessor(), [])._resolve_forwarding(
            StageSlot(instruction=consumer, rs1_value=0, rs2_value=0),
            StageSlot(instruction=load, alu_result=0), None)


# ---------------- Errors ----------------

@pytest.mark.parametrize("instructions, line, message", [
    pytest.param(program(addi("R1", 10), sw("R1", 2)),
                 2, "Unaligned memory address", id="unaligned-store"),
    pytest.param(program(lw("R1", 2)),
                 1, "Unaligned memory address", id="unaligned-load"),
    pytest.param([FakeInstruction("INVALID", line_number=7)],
                 7, "Unsupported opcode", id="bad-opcode"),
])
def test_errors_report_line_number(instructions, line, message):
    with pytest.raises(SimulationError) as error:
        run_program(instructions)
    assert error.value.line_number == line
    assert message in str(error.value)