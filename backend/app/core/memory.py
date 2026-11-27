class DataMemory:

    def __init__(self):
        self.memory = {}

    def _validate_address(self, address: int) -> None:

        if address < 0 or address > 4092:
            raise ValueError(
                f"Memory address out of range: {address} "
                "(valid range 0..4092)"
            )

        if address % 4 != 0:
            raise ValueError(
                f"Unaligned memory address: {address} "
                "(must be a multiple of 4)"
            )

    def load(self, address: int) -> int:
        self._validate_address(address)

        return self.memory.get(address, 0)

    def store(self, address: int, value: int) -> None:
        self._validate_address(address)

        value = value & 0xFFFFFFFF

        if value >= 0x80000000:
            value -= 0x100000000

        self.memory[address] = value
