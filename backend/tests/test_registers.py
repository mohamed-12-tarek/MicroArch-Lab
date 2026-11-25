# owner: M3
# Register file tests


import pytest
from app.core.registers import RegisterFile


@pytest.fixture
def rf():
    return RegisterFile()


def test_all_registers_start_at_zero(rf):
    for i in range(32):
        assert rf.read(f"R{i}") == 0


def test_write_and_read_register(rf):
    rf.write("R1", 50)
    assert rf.read("R1") == 50


def test_r0_always_zero(rf):
    rf.write("R0", 100)
    assert rf.read("R0") == 0


def test_invalid_register_read(rf):
    with pytest.raises(ValueError):
        rf.read("R35")


def test_invalid_register_write(rf):
    with pytest.raises(ValueError):
        rf.write("R35", 100)


def test_register_names_are_case_insensitive(rf):
    rf.write("r1", 25)
    assert rf.read("R1") == 25


def test_negative_values(rf):
    rf.write("R2", -50)
    assert rf.read("R2") == -50


def test_32_bit_overflow(rf):
    rf.write("R3", 2147483648)
    assert rf.read("R3") == -2147483648


def test_32_bit_underflow(rf):
    rf.write("R4", -2147483649)
    assert rf.read("R4") == 2147483647
