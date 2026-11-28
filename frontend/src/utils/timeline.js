// owner: M6
// buildTimeline + diffState

export const STAGE_ORDER = ["IF", "ID", "EX", "MEM", "WB"];

/**
 * Transform backend instructions and cycle history into a table-friendly timeline.
 * Uses `instruction_id` as the unique row key so duplicate instruction text stays separate.
 *
 * @param {Array} instructions
 * @param {Array} history
 * @returns {{
 *   totalCycles: number,
 *   cycles: number[],
 *   rows: Array,
 *   stallsByCycle: Record<number, object>,
 *   forwardsByCycle: Record<number, Array>
 * }}
 */
export function buildTimeline(instructions = [], history = []) {
  const safeInstructions = Array.isArray(instructions) ? instructions : [];
  const safeHistory = Array.isArray(history) ? history : [];

  const totalCycles = safeHistory.length;
  const cycles = safeHistory.map((entry, idx) =>
    typeof entry?.cycle === "number" ? entry.cycle : idx + 1
  );

  const rowById = new Map();
  const rows = [];

  for (const instr of safeInstructions) {
    if (!instr || instr.instruction_id == null) {
      continue;
    }
    const row = {
      instructionId: instr.instruction_id,
      instruction: instr.text || instr.raw || `I${instr.instruction_id}`,
      lineNumber: instr.line_number ?? null,
      opcode: instr.opcode ?? null,
      cells: new Array(totalCycles).fill(null),
    };
    rowById.set(instr.instruction_id, row);
    rows.push(row);
  }

  const stallsByCycle = {};
  const forwardsByCycle = {};

  for (let cycleIndex = 0; cycleIndex < safeHistory.length; cycleIndex += 1) {
    const entry = safeHistory[cycleIndex];
    const cycleNum = cycles[cycleIndex];

    const rawForwards = Array.isArray(entry?.forwards) ? entry.forwards : [];
    const normalizedForwards = rawForwards
      .filter((fwd) => fwd && fwd.register != null)
      .map((fwd) => ({
        register: fwd.register,
        fromStage: fwd.from_stage ?? "",
        fromInstruction: fwd.from_instruction ?? null,
        toInstruction: fwd.to_instruction ?? null,
      }));

    if (normalizedForwards.length > 0) {
      forwardsByCycle[cycleNum] = normalizedForwards;
    }

    if (entry?.stall) {
      stallsByCycle[cycleNum] = entry.stall;
    }

    const stages = entry?.stages || {};
    for (const stage of STAGE_ORDER) {
      const slot = stages[stage];
      if (!slot || slot.instruction_id == null) {
        continue;
      }

      const row = rowById.get(slot.instruction_id);
      if (!row) {
        continue;
      }

      const cellForwards = normalizedForwards.filter(
        (fwd) => fwd.toInstruction === slot.instruction_id
      );
      const isStalled = Boolean(slot.stalled);
      const stallReason =
        isStalled && entry?.stall?.reason ? entry.stall.reason : null;

      row.cells[cycleIndex] = {
        cycle: cycleNum,
        stage,
        stalled: isStalled,
        stallReason,
        forwarded: cellForwards,
      };
    }
  }

  return {
    totalCycles,
    cycles,
    rows,
    stallsByCycle,
    forwardsByCycle,
  };
}

/**
 * Compare two cycle snapshots and return which register names and memory
 * addresses changed from `previousSnapshot` to `currentSnapshot`.
 * Does not mutate either input object.
 *
 * @param {object|null|undefined} previousSnapshot
 * @param {object|null|undefined} currentSnapshot
 * @returns {{ changedRegisters: string[], changedMemory: string[] }}
 */
export function diffState(previousSnapshot, currentSnapshot) {
  if (!previousSnapshot || !currentSnapshot) {
    return { changedRegisters: [], changedMemory: [] };
  }

  const prevRegs =
    previousSnapshot.registers && typeof previousSnapshot.registers === "object"
      ? previousSnapshot.registers
      : {};
  const currRegs =
    currentSnapshot.registers && typeof currentSnapshot.registers === "object"
      ? currentSnapshot.registers
      : {};

  const changedRegisters = [];
  for (const reg of Object.keys(currRegs)) {
    const prevVal = Object.prototype.hasOwnProperty.call(prevRegs, reg)
      ? prevRegs[reg]
      : 0;
    if (prevVal !== currRegs[reg]) {
      changedRegisters.push(reg);
    }
  }

  const prevMem =
    previousSnapshot.memory && typeof previousSnapshot.memory === "object"
      ? previousSnapshot.memory
      : {};
  const currMem =
    currentSnapshot.memory && typeof currentSnapshot.memory === "object"
      ? currentSnapshot.memory
      : {};

  const changedMemory = [];
  for (const addr of Object.keys(currMem)) {
    const existed = Object.prototype.hasOwnProperty.call(prevMem, addr);
    if (!existed || prevMem[addr] !== currMem[addr]) {
      changedMemory.push(addr);
    }
  }

  changedMemory.sort((a, b) => Number(a) - Number(b));

  return { changedRegisters, changedMemory };
}
