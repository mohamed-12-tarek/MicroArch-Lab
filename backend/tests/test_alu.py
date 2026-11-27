import pytest

from app.core.alu import ALU


@pytest.fixture
def alu():
    return ALU()


def test_add(alu):
    assert alu.execute("ADD", 10, 20) == 30


def test_sub(alu):
    assert alu.execute("SUB", 20, 10) == 10


def test_and(alu):
    assert alu.execute("AND", 0b1010, 0b1100) == 0b1000


def test_or(alu):
    assert alu.execute("OR", 0b1010, 0b1100) == 0b1110


def test_negative_numbers(alu):
    assert alu.execute("ADD", -10, 5) == -5


def test_32_bit_overflow(alu):
    assert alu.execute("ADD", 2147483647, 1) == -2147483648


def test_32_bit_underflow(alu):
    assert alu.execute("SUB", -2147483648, 1) == 2147483647


def test_unsupported_operation(alu):
    with pytest.raises(ValueError):
        alu.execute("MUL", 10, 20)


def test_lowercase_operation(alu):
    assert alu.execute("add", 10, 20) == 30
