from app.core.alu import ALU
from app.core.registers import RegisterFile
from app.core.memory import DataMemory
from app.core.control_unit import ControlUnit


class Processor:
    def __init__(self):
        self.alu = ALU()
        self.register_file = RegisterFile()
        self.data_memory = DataMemory()
        self.control_unit = ControlUnit()

    def read_reg(self, register_name: str) -> int:
        return self.register_file.read(register_name)

    def write_reg(self, register_name: str, value: int) -> None:
        self.register_file.write(register_name, value)

    def alu_execute(self, operation: str, a: int, b: int) -> int:
        return self.alu.execute(operation, a, b)

    def load(self, address: int) -> int:
        return self.data_memory.load(address)

    def store(self, address: int, value: int) -> None:
        self.data_memory.store(address, value)

    def decode(self, instruction):
        return self.control_unit.decode(instruction)

    def snapshot(self) -> dict:
        return {
            "registers": self.register_file.registers.copy(),
            "memory": self.data_memory.memory.copy()
        }