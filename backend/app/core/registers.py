# owner: M3
# RegisterFile (32 regs, R0 = 0)


class RegisterFile:

    def __init__(self):
        self.registers = {
            f"R{i}": 0 for i in range(32)
        }

    @staticmethod
    def wrap_32(value: int) -> int:
        value = value & 0xFFFFFFFF

        if value >= 0x80000000:
            value -= 0x100000000

        return value

    def read(self, register_name: str) -> int:
        register_name = register_name.upper()

        if register_name not in self.registers:
            raise ValueError(
                f"Invalid register name: {register_name}"
            )

        return self.registers[register_name]

    def write(self, register_name: str, value: int) -> None:
        register_name = register_name.upper()

        if register_name not in self.registers:
            raise ValueError(
                f"Invalid register name: {register_name}"
            )

        # R0 is always zero
        if register_name == "R0":
            return

        self.registers[register_name] = self.wrap_32(value)
