import pytest

from app.core.memory import DataMemory


@pytest.fixture
def memory():
    return DataMemory()


def test_empty_address_returns_zero(memory):
    assert memory.load(0) == 0
    assert memory.load(100) == 0


def test_store_and_load(memory):
    memory.store(8, 100)
    assert memory.load(8) == 100


def test_last_valid_address(memory):
    memory.store(4092, 123)
    assert memory.load(4092) == 123


def test_unaligned_address(memory):
    with pytest.raises(
        ValueError,
        match="Unaligned memory address: 2"
    ):
        memory.load(2)


def test_out_of_range_address(memory):
    with pytest.raises(
        ValueError,
        match="Memory address out of range: 4096"
    ):
        memory.load(4096)


def test_negative_address(memory):
    with pytest.raises(
        ValueError,
        match="Memory address out of range: -4"
    ):
        memory.load(-4)


def test_store_32_bit_overflow(memory):
    memory.store(8, 2147483648)
    assert memory.load(8) == -2147483648


def test_invalid_store_address(memory):
    with pytest.raises(ValueError):
        memory.store(2, 100)
