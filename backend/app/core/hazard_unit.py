# owner: M5
# detect_hazard (RAW, stall)


def _normalize_register(register):
    """Normalize register names so R1 and r1 are treated identically."""
    if register is None:
        return None
    return register.upper()


def detect_hazard(id_instruction, ex_instruction):
    """
    Detect a load-use hazard between ID and EX.

    A stall is required when:
    - The EX instruction is LW.
    - The ID instruction reads the register written by LW.
    - The destination register is not R0.

    Returns:
        tuple: (should_stall, message)
    """
    if id_instruction is None or ex_instruction is None:
        return False, None

    # Only a load in EX can cause this hazard.
    if ex_instruction.opcode.upper() != "LW":
        return False, None

    # Get the destination register of the load.
    load_destination = _normalize_register(
        ex_instruction.destination_register()
    )

    if load_destination is None or load_destination == "R0":
        return False, None

    # Get the registers read by the instruction in ID.
    id_sources = {
        _normalize_register(register)
        for register in id_instruction.source_registers()
    }

    if load_destination not in id_sources:
        return False, None

    message = (
        f"Load-use hazard on {load_destination}: "
        f"instruction {ex_instruction.instruction_id} "
        f"({ex_instruction.text}) is in EX"
    )

    return True, message


def resolve_forwarding(ex_instruction, mem_instruction, wb_instruction):
    """
    Determine the forwarding source for each register read by EX.

    Priority:
        1. MEM stage (if it is not LW).
        2. WB stage.

    R0 is never forwarded.

    Returns:
        dict: Register names mapped to forwarding information.

    Raises:
        RuntimeError: If a MEM-stage LW is needed by EX.
    """
    forwarding = {}

    if ex_instruction is None:
        return forwarding

    # Registers read by the instruction currently in EX.
    source_registers = {
        _normalize_register(register)
        for register in ex_instruction.source_registers()
    }

    # R0 always contains zero and never needs forwarding.
    source_registers.discard(None)
    source_registers.discard("R0")

    if not source_registers:
        return forwarding

    # Check each source register independently.
    for register in source_registers:

        # First priority: MEM stage.
        if mem_instruction is not None:
            mem_destination = _normalize_register(
                mem_instruction.destination_register()
            )

            if mem_destination == register:

                # A load in MEM cannot provide its value through
                # the normal MEM forwarding path.
                if mem_instruction.opcode.upper() == "LW":
                    raise RuntimeError(
                        f"Invalid forwarding state: "
                        f"LW instruction {mem_instruction.instruction_id} "
                        f"in MEM is needed by instruction "
                        f"{ex_instruction.instruction_id} in EX"
                    )

                forwarding[register] = {
                    "from_stage": "MEM",
                    "from_instruction": mem_instruction.instruction_id
                }
                continue

        # Second priority: WB stage.
        if wb_instruction is not None:
            wb_destination = _normalize_register(
                wb_instruction.destination_register()
            )

            if wb_destination == register:
                forwarding[register] = {
                    "from_stage": "WB",
                    "from_instruction": wb_instruction.instruction_id
                }

    return forwarding

