# owner: M3
# Control unit tests

import pytest

from app.core.control_unit import ControlUnit, ControlSignals
from app.core.instruction import Instruction


@pytest.fixture
def control_unit():
    return ControlUnit()


@pytest.mark.parametrize(
    "opcode, expected",
    [
        (
            "ADD",
            ControlSignals("ADD", False, True, False, False, False)
        ),
        (
            "SUB",
            ControlSignals("SUB", False, True, False, False, False)
        ),
        (
            "AND",
            ControlSignals("AND", False, True, False, False, False)
        ),
        (
            "OR",
            ControlSignals("OR", False, True, False, False, False)
        ),
        (
            "ADDI",
            ControlSignals("ADD", True, True, False, False, False)
        ),
        (
            "LW",
            ControlSignals("ADD", True, True, True, False, True)
        ),
        (
            "SW",
            ControlSignals("ADD", True, False, False, True, False)
        ),
        (
            "NOP",
            ControlSignals(None, False, False, False, False, False)
        ),
    ],
)
def test_decode_instructions(control_unit, opcode, expected):
    instruction = Instruction(opcode=opcode)

    signals = control_unit.decode(instruction)

    assert signals == expected


def test_decode_is_case_insensitive(control_unit):
    instruction = Instruction(opcode="add")

    signals = control_unit.decode(instruction)

    assert signals.alu_op == "ADD"


def test_unsupported_instruction(control_unit):
    instruction = Instruction(opcode="MUL")

    with pytest.raises(ValueError):
        control_unit.decode(instruction)


def test_invalid_input(control_unit):
    with pytest.raises(TypeError):
        control_unit.decode("ADD")


def test_control_signals_are_immutable():
    signals = ControlSignals(
        "ADD", False, True, False, False, False
    )

    with pytest.raises(AttributeError):
        signals.reg_write = False
