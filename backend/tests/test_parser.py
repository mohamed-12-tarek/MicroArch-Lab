import pytest

from app.core.parser import parse


def ok(code):
    result = parse(code)
    assert result.success, result.errors
    assert result.errors == []
    return result.instructions


def messages(code):
    result = parse(code)
    assert not result.success
    assert result.instructions == []
    return [(e.line, e.message) for e in result.errors]


# ---------- valid instructions (all 8) ----------
def test_add_sub_and_or():
    for op in ("ADD", "SUB", "AND", "OR"):
        (i,) = ok(f"{op} R3, R1, R2")
        assert (i.opcode, i.rd, i.rs1, i.rs2, i.immediate) == (op, "R3", "R1", "R2", None)


def test_addi():
    (i,) = ok("ADDI R1, R0, 10")
    assert (i.opcode, i.rd, i.rs1, i.rs2, i.immediate) == ("ADDI", "R1", "R0", None, 10)


def test_lw():
    (i,) = ok("LW R3, 4(R2)")
    assert (i.opcode, i.rd, i.rs1, i.rs2, i.immediate) == ("LW", "R3", "R2", None, 4)


def test_sw_matches_spec_example():
    (i,) = ok("SW R1, 4(R2)")
    assert (i.opcode, i.rs2, i.rs1, i.immediate, i.rd) == ("SW", "R1", "R2", 4, None)


def test_nop():
    (i,) = ok("NOP")
    assert i.opcode == "NOP" and i.rd is None and i.rs1 is None and i.rs2 is None


# ---------- formatting leniency ----------
def test_lowercase_is_normalized():
    (i,) = ok("add r3, r1, r2")
    assert i.text == "ADD R3, R1, R2"


def test_mixed_case_opcode_and_registers():
    (i,) = ok("AdDi r31, R0, 1")
    assert i.text == "ADDI R31, R0, 1"


def test_hex_immediate():
    assert ok("ADDI R1, R0, 0x1F")[0].immediate == 31
    assert ok("ADDI R1, R0, 0XFF")[0].immediate == 255


def test_negative_and_positive_sign_immediates():
    assert ok("ADDI R1, R0, -5")[0].immediate == -5
    assert ok("ADDI R1, R0, +5")[0].immediate == 5
    assert ok("ADDI R1, R0, -0x10")[0].immediate == -16


def test_negative_memory_offset():
    (i,) = ok("LW R1, -4(R2)")
    assert i.immediate == -4


def test_flexible_spacing():
    assert ok("ADD   R3 ,R1,   R2")[0].text == "ADD R3, R1, R2"
    assert ok("\tLW R3,4(R2)")[0].text == "LW R3, 4(R2)"
    assert ok("SW R1, 4 ( R2 )")[0].text == "SW R1, 4(R2)"


def test_hash_and_semicolon_comments():
    code = "# full line\nADDI R1, R0, 1  # trailing\n; another\nNOP ; trailing\n"
    ins = ok(code)
    assert [i.text for i in ins] == ["ADDI R1, R0, 1", "NOP"]


def test_raw_has_no_comment():
    assert ok("NOP   # hi")[0].raw == "NOP"


def test_crlf_line_endings_and_bom():
    ins = ok("\ufeffADDI R1, R0, 1\r\nNOP\r\n")
    assert [i.line_number for i in ins] == [1, 2]


# ---------- line numbers and ids ----------
def test_line_numbers_after_blank_and_comment_lines():
    code = "\n# c\nADDI R1, R0, 1\n\n\nADDI R2, R0, 2\n"
    ins = ok(code)
    assert [i.line_number for i in ins] == [3, 6]


def test_instruction_ids_start_at_zero_and_are_sequential():
    ins = ok("NOP\n\nNOP\nNOP")
    assert [i.instruction_id for i in ins] == [0, 1, 2]


def test_identical_instructions_are_distinct():
    a, b = ok("ADDI R1, R0, 1\nADDI R1, R0, 1")
    assert a.text == b.text and a.instruction_id != b.instruction_id


# ---------- fixed error messages ----------
def test_unsupported_instruction():
    assert messages("ADDI R1, R0, 1\nMULT R1, R2, R3") == [(2, "Unsupported instruction: MULT")]


def test_unsupported_instruction_lowercase_reported_uppercase():
    assert messages("mult r1, r2, r3") == [(1, "Unsupported instruction: MULT")]


def test_label_is_unsupported():
    assert messages("loop: NOP")[0][1].startswith("Unsupported instruction:")


def test_operand_count_too_few():
    assert messages("ADD R3, R1") == [(1, "Invalid operand count for ADD: expected 3, got 2")]


def test_operand_count_too_many():
    assert messages("ADDI R1, R0, 1, 2") == [(1, "Invalid operand count for ADDI: expected 3, got 4")]


def test_operand_count_lw_sw_nop():
    assert messages("LW R1") == [(1, "Invalid operand count for LW: expected 2, got 1")]
    assert messages("SW R1, 4(R2), R3") == [(1, "Invalid operand count for SW: expected 2, got 3")]
    assert messages("NOP R1") == [(1, "Invalid operand count for NOP: expected 0, got 1")]


def test_missing_operands_entirely():
    assert messages("ADD") == [(1, "Invalid operand count for ADD: expected 3, got 0")]


def test_invalid_register_out_of_range():
    assert messages("ADD R32, R1, R2") == [(1, "Invalid register: R32")]
    assert messages("ADD R3, r99, R2") == [(1, "Invalid register: R99")]


def test_invalid_register_names():
    assert messages("ADD X1, R1, R2") == [(1, "Invalid register: X1")]
    assert messages("ADD R3, 5, R2") == [(1, "Invalid register: 5")]
    assert messages("ADD R3, R-1, R2") == [(1, "Invalid register: R-1")]
    assert messages("ADD R3, R01, R2") == [(1, "Invalid register: R01")]


def test_register_boundaries_valid():
    ins = ok("ADD R0, R31, R0")
    assert ins[0].rd == "R0" and ins[0].rs1 == "R31"


def test_invalid_immediate():
    assert messages("ADDI R1, R0, abc") == [(1, "Invalid immediate: abc")]
    assert messages("ADDI R1, R0, 1.5") == [(1, "Invalid immediate: 1.5")]
    assert messages("ADDI R1, R0, 0x") == [(1, "Invalid immediate: 0x")]
    assert messages("ADDI R1, R0, 1_0") == [(1, "Invalid immediate: 1_0")]


def test_immediate_out_of_range():
    msg = "Immediate out of range (-32768..32767): "
    assert messages("ADDI R1, R0, 40000") == [(1, msg + "40000")]
    assert messages("ADDI R1, R0, -32769") == [(1, msg + "-32769")]
    assert messages("ADDI R1, R0, 32768") == [(1, msg + "32768")]
    assert messages("ADDI R1, R0, 0xFFFF") == [(1, msg + "0xFFFF")]


def test_immediate_range_boundaries_valid():
    assert ok("ADDI R1, R0, 32767")[0].immediate == 32767
    assert ok("ADDI R1, R0, -32768")[0].immediate == -32768


def test_huge_immediate_does_not_crash():
    result = parse("ADDI R1, R0, " + "9" * 10000)
    assert not result.success
    assert result.errors[0].message.startswith("Immediate out of range")


def test_memory_operand_errors():
    assert messages("LW R1, R2")[0][1].startswith("Invalid memory operand: R2")
    assert messages("LW R1, (R2)")[0][1].startswith("Invalid memory operand: (R2)")
    assert messages("LW R1, 4(R2")[0][1].startswith("Invalid memory operand: 4(R2")
    assert messages("LW R1, abc(R2)") == [(1, "Invalid immediate: abc")]
    assert messages("SW R1, 4(R32)") == [(1, "Invalid register: R32")]
    assert messages("SW R1, 40000(R2)")[0][1].startswith("Immediate out of range")


def test_empty_operand():
    assert messages("ADD R1, , R2") == [(1, "Empty operand in ADD")]
    assert messages("ADD R1, R2, R3,") == [(1, "Invalid operand count for ADD: expected 3, got 4")]


# ---------- empty / multiple errors / limits ----------
def test_empty_program():
    assert messages("") == [(None, "Program is empty")]


def test_whitespace_and_comments_only_is_empty():
    assert messages("\n   \n# just a comment\n; another\n") == [(None, "Program is empty")]


def test_non_string_input_is_empty_program():
    assert [e.message for e in parse(None).errors] == ["Program is empty"]


def test_three_errors_on_three_lines():
    code = "MULT R1, R2, R3\nADD R1, R2\nADDI R1, R0, abc\n"
    assert messages(code) == [
        (1, "Unsupported instruction: MULT"),
        (2, "Invalid operand count for ADD: expected 3, got 2"),
        (3, "Invalid immediate: abc"),
    ]


def test_errors_mixed_with_valid_lines_report_right_line():
    code = "NOP\n\n# c\nADD R32, R1, R2\nNOP\nBAD\n"
    assert [m[0] for m in messages(code)] == [4, 6]


def test_one_error_per_line():
    assert len(messages("ADD R32, R99, abc")) == 1


def test_200_instructions_pass():
    assert len(ok("NOP\n" * 200)) == 200


def test_201_instructions_fail():
    result = parse("NOP\n" * 201)
    assert not result.success
    assert [(e.line, e.message) for e in result.errors] == [
        (201, "Program too long: maximum 200 instructions")
    ]


def test_blank_lines_and_comments_do_not_count_toward_limit():
    assert len(ok("NOP\n\n# c\n" * 200)) == 200


# ---------- result shape / API helpers ----------
def test_result_shape_on_success_and_failure():
    good = parse("NOP")
    assert good.success is True and good.errors == []
    bad = parse("FOO")
    assert bad.success is False and bad.instructions == []
    assert bad.errors[0].line == 1 and "Unsupported" in bad.errors[0].message


def test_to_dict():
    d = parse("MULT R1, R2, R3").to_dict()
    assert d["success"] is False
    assert d["errors"] == [{"line": 1, "message": "Unsupported instruction: MULT"}]
    d = parse("ADDI R1, R0, 10").to_dict()
    assert d["instructions"][0]["text"] == "ADDI R1, R0, 10"


def test_full_sample_program():
    code = """
    # basic program
    ADDI R1, R0, 10
    ADDI R2, R0, 20
    ADD  R3, R1, R2     ; R3 = 30
    SW   R3, 8(R0)
    LW   R4, 8(R0)
    NOP
    """
    ins = ok(code)
    assert [i.text for i in ins] == [
        "ADDI R1, R0, 10", "ADDI R2, R0, 20", "ADD R3, R1, R2",
        "SW R3, 8(R0)", "LW R4, 8(R0)", "NOP",
    ]
    assert ins[2].source_registers() == ["R1", "R2"]
    assert ins[2].destination_register() == "R3"
