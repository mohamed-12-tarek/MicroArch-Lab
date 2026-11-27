import pytest

from app.core.processor import Processor
from app.core.instruction import Instruction


@pytest.fixture
def processor():
    return Processor()


def test_processor_has_required_methods(processor):
    required_methods = [
        "read_reg",
        "write_reg",
        "alu_execute",
        "load",
        "store",
        "decode",
        "snapshot"
    ]

    for method in required_methods:
        assert callable(getattr(processor, method))


def test_read_register(processor):
    assert processor.read_reg("R1") == 0


def test_write_and_read_register(processor):
    processor.write_reg("R1", 30)

    assert processor.read_reg("R1") == 30


def test_register_zero_cannot_be_modified(processor):
    processor.write_reg("R0", 100)

    assert processor.read_reg("R0") == 0


def test_alu_execute(processor):
    assert processor.alu_execute("ADD", 10, 20) == 30


def test_alu_execute_wraps_32_bits(processor):
    assert processor.alu_execute("ADD", 2147483647, 1) == -2147483648


def test_store_and_load(processor):
    processor.store(8, 100)

    assert processor.load(8) == 100


def test_load_uninitialized_memory(processor):
    assert processor.load(12) == 0


def test_invalid_memory_address(processor):
    with pytest.raises(
        ValueError,
        match=r"Unaligned memory address: 2 \(must be a multiple of 4\)"
    ):
        processor.load(2)


def test_decode_add_instruction(processor):
    instruction = Instruction(
        opcode="ADD",
        rd="R3",
        rs1="R1",
        rs2="R2"
    )

    signals = processor.decode(instruction)

    assert signals.alu_op == "ADD"
    assert signals.alu_src is False
    assert signals.reg_write is True


def test_snapshot(processor):
    processor.write_reg("R1", 25)
    processor.store(8, 100)

    result = processor.snapshot()

    assert result["registers"]["R1"] == 25
    assert result["memory"][8] == 100


def test_snapshot_returns_independent_copies(processor):
    processor.write_reg("R1", 25)
    processor.store(8, 100)

    result = processor.snapshot()

    result["registers"]["R1"] = 999
    result["memory"][8] = 999

    assert processor.read_reg("R1") == 25
    assert processor.load(8) == 100