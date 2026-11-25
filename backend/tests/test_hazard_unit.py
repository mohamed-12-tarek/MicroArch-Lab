# owner: M5
# Hazard unit tests


import pytest

from app.core.hazard_unit import (
    detect_hazard,
    resolve_forwarding
)


class MockInstruction:
    """Temporary instruction object following M2's agreed interface."""

    def __init__(
        self,
        opcode,
        instruction_id,
        sources=None,
        destination=None,
        text=""
    ):
        self.opcode = opcode
        self.instruction_id = instruction_id
        self._sources = sources or []
        self._destination = destination
        self.text = text

    def source_registers(self):
        return self._sources

    def destination_register(self):
        return self._destination


# -------------------------
# Hazard Detection Tests
# -------------------------

def test_detect_load_use_hazard():
    lw = MockInstruction("LW", 0, ["R0"], "R2", "LW R2, 0(R0)")
    add = MockInstruction("ADD", 1, ["R2", "R1"], "R3")

    should_stall, message = detect_hazard(add, lw)

    assert should_stall is True
    assert message == (
        "Load-use hazard on R2: "
        "instruction 0 (LW R2, 0(R0)) is in EX"
    )


def test_no_hazard_with_alu_instruction():
    add = MockInstruction("ADD", 0, ["R1", "R2"], "R3")
    addi = MockInstruction("ADDI", 1, ["R0"], "R1")

    assert detect_hazard(add, addi) == (False, None)


def test_no_hazard_when_load_destination_is_not_used():
    lw = MockInstruction("LW", 0, ["R0"], "R2")
    add = MockInstruction("ADD", 1, ["R1", "R3"], "R4")

    assert detect_hazard(add, lw) == (False, None)


def test_hazard_when_sw_uses_loaded_value():
    lw = MockInstruction("LW", 0, ["R0"], "R2")
    sw = MockInstruction("SW", 1, ["R2", "R1"])

    should_stall, _ = detect_hazard(sw, lw)

    assert should_stall is True


def test_hazard_when_sw_uses_loaded_address_register():
    lw = MockInstruction("LW", 0, ["R0"], "R2")
    sw = MockInstruction("SW", 1, ["R1", "R2"])

    should_stall, _ = detect_hazard(sw, lw)

    assert should_stall is True


def test_no_hazard_when_load_destination_is_r0():
    lw = MockInstruction("LW", 0, ["R1"], "R0")
    add = MockInstruction("ADD", 1, ["R0", "R2"], "R3")

    assert detect_hazard(add, lw) == (False, None)


def test_no_hazard_with_missing_instructions():
    assert detect_hazard(None, None) == (False, None)


def test_register_matching_is_case_insensitive():
    lw = MockInstruction("LW", 0, ["r0"], "r2", "LW r2, 0(r0)")
    add = MockInstruction("ADD", 1, ["r2", "r1"], "r3")

    should_stall, _ = detect_hazard(add, lw)

    assert should_stall is True


# -------------------------
# Forwarding Tests
# -------------------------

def test_forwarding_from_mem():
    mem = MockInstruction("ADD", 0, ["R1", "R2"], "R3")
    ex = MockInstruction("ADD", 1, ["R3", "R4"], "R5")

    result = resolve_forwarding(ex, mem, None)

    assert result == {
        "R3": {
            "from_stage": "MEM",
            "from_instruction": 0
        }
    }


def test_forwarding_from_wb():
    wb = MockInstruction("ADDI", 0, ["R0"], "R1")
    ex = MockInstruction("ADD", 1, ["R1", "R2"], "R3")

    result = resolve_forwarding(ex, None, wb)

    assert result == {
        "R1": {
            "from_stage": "WB",
            "from_instruction": 0
        }
    }


def test_mem_has_priority_over_wb():
    mem = MockInstruction("ADD", 4, ["R1", "R2"], "R3")
    wb = MockInstruction("ADD", 5, ["R1", "R2"], "R3")
    ex = MockInstruction("ADD", 6, ["R3", "R4"], "R5")

    result = resolve_forwarding(ex, mem, wb)

    assert result["R3"]["from_stage"] == "MEM"
    assert result["R3"]["from_instruction"] == 4


def test_r0_is_never_forwarded():
    mem = MockInstruction("ADD", 0, ["R1", "R2"], "R0")
    ex = MockInstruction("ADD", 1, ["R0", "R1"], "R3")

    result = resolve_forwarding(ex, mem, None)

    assert "R0" not in result


def test_no_forwarding_when_no_dependency_exists():
    mem = MockInstruction("ADD", 0, ["R1", "R2"], "R3")
    wb = MockInstruction("ADDI", 1, ["R0"], "R4")
    ex = MockInstruction("ADD", 2, ["R5", "R6"], "R7")

    assert resolve_forwarding(ex, mem, wb) == {}


def test_forwarding_for_sw_source_registers():
    mem = MockInstruction("ADDI", 0, ["R0"], "R2")
    ex = MockInstruction("SW", 1, ["R1", "R2"], None)

    result = resolve_forwarding(ex, mem, None)

    assert result == {
        "R2": {
            "from_stage": "MEM",
            "from_instruction": 0
        }
    }


def test_lw_in_mem_raises_error_when_ex_needs_its_result():
    mem = MockInstruction("LW", 0, ["R0"], "R2")
    ex = MockInstruction("ADD", 1, ["R2", "R1"], "R3")

    with pytest.raises(RuntimeError, match="Invalid forwarding state"):
        resolve_forwarding(ex, mem, None)


def test_no_forwarding_for_empty_ex_stage():
    assert resolve_forwarding(None, None, None) == {}



def test_instruction_without_destination_does_not_create_hazard():
    # SW has no destination register.
    sw = MockInstruction("SW", 0, ["R1", "R2"], None)
    add = MockInstruction("ADD", 1, ["R1", "R2"], "R3")

    assert sw.destination_register() is None
    assert detect_hazard(add, sw) == (False, None)


def test_lw_in_ex_does_not_cause_hazard_when_id_is_none():
    lw = MockInstruction("LW", 0, ["R0"], "R2")

    assert detect_hazard(None, lw) == (False, None)
