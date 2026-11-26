"""Assembly parser: text -> list of Instruction, or a list of errors.

Owner: M2.  Usage::

    result = parse(code)
    if result.success:
        result.instructions   # List[Instruction]
    else:
        result.errors         # List[ParseError] (line + message), all of them
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .instruction import (
    IMMEDIATE_MAX,
    IMMEDIATE_MIN,
    MAX_INSTRUCTIONS,
    R_TYPE_OPCODES,
    REGISTER_COUNT,
    SUPPORTED_OPCODES,
    Instruction,
)

# Expected operand count per opcode.
_OPERAND_COUNT = {
    **{op: 3 for op in R_TYPE_OPCODES},
    "ADDI": 3,
    "LW": 2,
    "SW": 2,
    "NOP": 0,
}

_REGISTER_RE = re.compile(r"[Rr](0|[1-9][0-9]*)")
_IMMEDIATE_RE = re.compile(r"([+-]?)(0[xX][0-9a-fA-F]+|[0-9]+)")
_MEMORY_RE = re.compile(r"(.*)\((.*)\)")


@dataclass(frozen=True)
class ParseError:
    """One parse error. ``line`` is 1-based, or None for whole-program errors."""

    line: Optional[int]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"line": self.line, "message": self.message}


@dataclass
class ParseResult:
    success: bool
    instructions: List[Instruction] = field(default_factory=list)
    errors: List[ParseError] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "instructions": [i.to_dict() for i in self.instructions],
            "errors": [e.to_dict() for e in self.errors],
        }


class _LineError(Exception):
    """Internal: a problem found while parsing a single line."""


# --------------------------------------------------------------------------
# Token helpers
# --------------------------------------------------------------------------
def _strip_comment(line: str) -> str:
    """Remove a trailing comment started by '#' or ';'."""
    cut = len(line)
    for marker in ("#", ";"):
        idx = line.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return line[:cut]


def _parse_register(token: str) -> str:
    match = _REGISTER_RE.fullmatch(token)
    if match is None or int(match.group(1)) >= REGISTER_COUNT:
        raise _LineError(f"Invalid register: {token.upper()}")
    return "R" + match.group(1)


def _parse_immediate(token: str) -> int:
    match = _IMMEDIATE_RE.fullmatch(token)
    if match is None:
        raise _LineError(f"Invalid immediate: {token}")
    sign, body = match.groups()
    try:
        value = int(body, 16) if body[:2] in ("0x", "0X") else int(body)
    except ValueError:  # absurdly long digit strings
        raise _LineError(
            f"Immediate out of range ({IMMEDIATE_MIN}..{IMMEDIATE_MAX}): {token[:20]}"
        )
    if sign == "-":
        value = -value
    if not IMMEDIATE_MIN <= value <= IMMEDIATE_MAX:
        raise _LineError(
            f"Immediate out of range ({IMMEDIATE_MIN}..{IMMEDIATE_MAX}): {token}"
        )
    return value


def _parse_memory_operand(token: str):
    """Parse ``offset(register)`` -> (immediate, register)."""
    match = _MEMORY_RE.fullmatch(token)
    offset = match.group(1).strip() if match else ""
    if match is None or offset == "":
        raise _LineError(
            f"Invalid memory operand: {token} (expected offset(register), e.g. 4(R2))"
        )
    immediate = _parse_immediate(offset)
    register = _parse_register(match.group(2).strip())
    return immediate, register


# --------------------------------------------------------------------------
# Line parsing
# --------------------------------------------------------------------------
def _parse_line(content: str, line_number: int, instruction_id: int) -> Instruction:
    """Parse one non-empty, comment-free line. Raises _LineError on problems."""
    parts = content.split(None, 1)
    opcode = parts[0].upper()

    if opcode not in SUPPORTED_OPCODES:
        raise _LineError(f"Unsupported instruction: {opcode}")

    rest = parts[1].strip() if len(parts) > 1 else ""
    operands = [o.strip() for o in rest.split(",")] if rest else []

    expected = _OPERAND_COUNT[opcode]
    if len(operands) != expected:
        raise _LineError(
            f"Invalid operand count for {opcode}: expected {expected}, got {len(operands)}"
        )
    if any(o == "" for o in operands):
        raise _LineError(f"Empty operand in {opcode}")

    common = dict(opcode=opcode, line_number=line_number, raw=content,
                  instruction_id=instruction_id)

    if opcode in R_TYPE_OPCODES:
        return Instruction(
            rd=_parse_register(operands[0]),
            rs1=_parse_register(operands[1]),
            rs2=_parse_register(operands[2]),
            **common,
        )
    if opcode == "ADDI":
        return Instruction(
            rd=_parse_register(operands[0]),
            rs1=_parse_register(operands[1]),
            immediate=_parse_immediate(operands[2]),
            **common,
        )
    if opcode == "LW":
        rd = _parse_register(operands[0])
        immediate, base = _parse_memory_operand(operands[1])
        return Instruction(rd=rd, rs1=base, immediate=immediate, **common)
    if opcode == "SW":
        value = _parse_register(operands[0])
        immediate, base = _parse_memory_operand(operands[1])
        return Instruction(rs2=value, rs1=base, immediate=immediate, **common)
    return Instruction(**common)  # NOP


def parse(code: str) -> ParseResult:
    """Parse assembly source text.

    * Comments start with ``#`` or ``;``. Blank lines are ignored.
    * At most one error is reported per line (the first one found), but errors
      from ALL lines are collected.
    * On any error, ``success`` is False and ``instructions`` is empty.
    """
    if not isinstance(code, str):
        code = ""
    code = code.lstrip("\ufeff")  # tolerate a UTF-8 BOM

    instructions: List[Instruction] = []
    errors: List[ParseError] = []
    statement_count = 0  # every non-empty line, valid or not

    for line_number, line in enumerate(code.splitlines(), start=1):
        content = _strip_comment(line).strip()
        if not content:
            continue

        statement_count += 1
        if statement_count == MAX_INSTRUCTIONS + 1:
            errors.append(ParseError(
                line_number,
                f"Program too long: maximum {MAX_INSTRUCTIONS} instructions",
            ))

        try:
            instructions.append(_parse_line(content, line_number, len(instructions)))
        except _LineError as exc:
            errors.append(ParseError(line_number, str(exc)))

    if statement_count == 0:
        errors.append(ParseError(None, "Program is empty"))

    if errors:
        return ParseResult(success=False, instructions=[], errors=errors)
    return ParseResult(success=True, instructions=instructions, errors=[])
