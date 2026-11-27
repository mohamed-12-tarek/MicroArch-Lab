class ALU:

    @staticmethod
    def wrap_32(value: int) -> int:
        value = value & 0xFFFFFFFF

        if value >= 0x80000000:
            value -= 0x100000000

        return value

    def execute(self, operation: str, a: int, b: int) -> int:
        operation = operation.upper()

        if operation == "ADD":
            result = a + b

        elif operation == "SUB":
            result = a - b

        elif operation == "AND":
            result = a & b

        elif operation == "OR":
            result = a | b

        else:
            raise ValueError(f"Unsupported ALU operation: {operation}")

        return self.wrap_32(result)
