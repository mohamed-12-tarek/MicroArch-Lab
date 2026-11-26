import dataclasses

import pytest

from app.core.instruction import Instruction


def make(opcode, **kw):
    return Instruction(opcode=opcode, **kw)


# ---------- source_registers ----------
@pytest.mark.parametrize("op", ["ADD", "SUB", "AND", "OR"])
def test_r_type_sources(op):
    ins = make(op, rd="R3", rs1="R1", rs2="R2")
    assert ins.source_registers() == ["R1", "R2"]


def test_r_type_same_source_not_duplicated():
    assert make("ADD", rd="R3", rs1="R1", rs2="R1").source_registers() == ["R1"]


def test_addi_sources():
    assert make("ADDI", rd="R1", rs1="R0", immediate=10).source_registers() == ["R0"]


def test_lw_sources():
    assert make("LW", rd="R3", rs1="R2", immediate=4).source_registers() == ["R2"]


def test_sw_sources_include_base_and_value():
    ins = make("SW", rs2="R1", rs1="R2", immediate=4)
    assert sorted(ins.source_registers()) == ["R1", "R2"]


def test_nop_has_no_sources():
    assert make("NOP").source_registers() == []


# ---------- destination_register ----------
@pytest.mark.parametrize("op", ["ADD", "SUB", "AND", "OR"])
def test_r_type_destination(op):
    assert make(op, rd="R3", rs1="R1", rs2="R2").destination_register() == "R3"


def test_addi_and_lw_destination():
    assert make("ADDI", rd="R1", rs1="R0", immediate=1).destination_register() == "R1"
    assert make("LW", rd="R3", rs1="R2", immediate=4).destination_register() == "R3"


def test_sw_and_nop_have_no_destination():
    assert make("SW", rs2="R1", rs1="R2", immediate=4).destination_register() is None
    assert make("NOP").destination_register() is None


# ---------- text ----------
def test_text_all_opcodes():
    assert make("ADD", rd="R3", rs1="R1", rs2="R2").text == "ADD R3, R1, R2"
    assert make("SUB", rd="R3", rs1="R1", rs2="R2").text == "SUB R3, R1, R2"
    assert make("AND", rd="R3", rs1="R1", rs2="R2").text == "AND R3, R1, R2"
    assert make("OR", rd="R3", rs1="R1", rs2="R2").text == "OR R3, R1, R2"
    assert make("ADDI", rd="R1", rs1="R0", immediate=10).text == "ADDI R1, R0, 10"
    assert make("ADDI", rd="R1", rs1="R0", immediate=-5).text == "ADDI R1, R0, -5"
    assert make("LW", rd="R3", rs1="R2", immediate=4).text == "LW R3, 4(R2)"
    assert make("SW", rs2="R1", rs1="R2", immediate=4).text == "SW R1, 4(R2)"
    assert make("NOP").text == "NOP"


# ---------- fields / defaults / immutability ----------
def test_sw_field_mapping_matches_spec():
    ins = make("SW", rs2="R1", rs1="R2", immediate=4)
    assert (ins.opcode, ins.rs2, ins.rs1, ins.immediate, ins.rd) == ("SW", "R1", "R2", 4, None)


def test_field_names_are_the_agreed_ones():
    names = [f.name for f in dataclasses.fields(Instruction)]
    assert names == ["opcode", "rd", "rs1", "rs2", "immediate",
                     "line_number", "raw", "instruction_id"]


def test_instruction_is_immutable():
    ins = make("NOP")
    with pytest.raises(dataclasses.FrozenInstanceError):
        ins.opcode = "ADD"


def test_to_dict_contains_text_and_fields():
    d = make("LW", rd="R3", rs1="R2", immediate=4, line_number=7,
             raw="LW R3, 4(R2)", instruction_id=2).to_dict()
    assert d["text"] == "LW R3, 4(R2)"
    assert d["instruction_id"] == 2 and d["line_number"] == 7 and d["rd"] == "R3"
