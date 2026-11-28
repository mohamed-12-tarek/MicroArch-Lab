// owner: M6
// timeline tests

import { describe, expect, it } from "vitest";
import simulateError from "../../mocks/simulate-error.json";
import simulateLoadUse from "../../mocks/simulate-load-use.json";
import simulateMemory from "../../mocks/simulate-memory.json";
import simulateSuccess from "../../mocks/simulate-success.json";
import { buildTimeline, diffState } from "../timeline";

describe("buildTimeline", () => {
  it("builds a complete 7-cycle timeline for simulate-success.json", () => {
    const timeline = buildTimeline(
      simulateSuccess.instructions,
      simulateSuccess.history
    );

    expect(timeline.totalCycles).toBe(7);
    expect(timeline.cycles).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(timeline.rows).toHaveLength(3);

    expect(timeline.rows[0].instructionId).toBe(0);
    expect(timeline.rows[0].instruction).toBe("ADDI R1, R0, 10");
    expect(timeline.rows[0].cells.map((c) => c?.stage ?? null)).toEqual([
      "IF",
      "ID",
      "EX",
      "MEM",
      "WB",
      null,
      null,
    ]);

    // Cycle 5 (index 4) has two forwards into instruction 2 (EX stage)
    const addCellCycle5 = timeline.rows[2].cells[4];
    expect(addCellCycle5.stage).toBe("EX");
    expect(addCellCycle5.forwarded).toEqual([
      {
        register: "R1",
        fromStage: "WB",
        fromInstruction: 0,
        toInstruction: 2,
      },
      {
        register: "R2",
        fromStage: "MEM",
        fromInstruction: 1,
        toInstruction: 2,
      },
    ]);
  });

  it("preserves load-use stall, frozen ID cell, and WB forwarding in simulate-load-use.json", () => {
    const timeline = buildTimeline(
      simulateLoadUse.instructions,
      simulateLoadUse.history
    );

    expect(timeline.totalCycles).toBe(9);
    expect(timeline.stallsByCycle[5]).toEqual({
      instruction_id: 3,
      register: "R2",
      reason: "Load-use hazard on R2: instruction 2 (LW R2, 0(R0)) is in EX",
    });

    // Instruction 3 stays in ID for cycle 5 (stalled) and cycle 6 (unstalled)
    const instr3Stages = timeline.rows[3].cells.map((c) => c?.stage ?? null);
    expect(instr3Stages).toEqual([
      null,
      null,
      null,
      "IF",
      "ID",
      "ID",
      "EX",
      "MEM",
      "WB",
    ]);

    expect(timeline.rows[3].cells[4].stalled).toBe(true);
    expect(timeline.rows[3].cells[5].stalled).toBe(false);

    // Cycle 4 (index 3): MEM forwarding into SW (instruction 1)
    expect(timeline.rows[1].cells[3].forwarded).toEqual([
      {
        register: "R1",
        fromStage: "MEM",
        fromInstruction: 0,
        toInstruction: 1,
      },
    ]);

    // Cycle 7 (index 6): WB forwarding into ADD (instruction 3)
    expect(timeline.rows[3].cells[6].forwarded).toEqual([
      {
        register: "R2",
        fromStage: "WB",
        fromInstruction: 2,
        toInstruction: 3,
      },
    ]);
  });

  it("handles simulate-memory.json forwarding in cycle 5 and cycle 6", () => {
    const timeline = buildTimeline(
      simulateMemory.instructions,
      simulateMemory.history
    );

    expect(timeline.totalCycles).toBe(8);
    expect(timeline.forwardsByCycle[5]).toHaveLength(2);
    expect(timeline.forwardsByCycle[6]).toHaveLength(1);
    expect(timeline.rows[2].cells[4].forwarded).toHaveLength(2);
    expect(timeline.rows[3].cells[5].forwarded[0]).toEqual({
      register: "R2",
      fromStage: "WB",
      fromInstruction: 1,
      toInstruction: 3,
    });
  });

  it("keeps duplicate instruction text as separate rows using instruction_id", () => {
    const instructions = [
      { instruction_id: 0, text: "NOP" },
      { instruction_id: 1, text: "NOP" },
    ];
    const history = [
      {
        cycle: 1,
        stages: {
          IF: { instruction_id: 0, text: "NOP", stalled: false },
          ID: null,
          EX: null,
          MEM: null,
          WB: null,
        },
        forwards: [],
        stall: null,
      },
      {
        cycle: 2,
        stages: {
          IF: { instruction_id: 1, text: "NOP", stalled: false },
          ID: { instruction_id: 0, text: "NOP", stalled: false },
          EX: null,
          MEM: null,
          WB: null,
        },
        forwards: [],
        stall: null,
      },
    ];

    const timeline = buildTimeline(instructions, history);
    expect(timeline.rows).toHaveLength(2);
    expect(timeline.rows[0].instructionId).toBe(0);
    expect(timeline.rows[1].instructionId).toBe(1);
    expect(timeline.rows[0].cells.map((c) => c?.stage ?? null)).toEqual([
      "IF",
      "ID",
    ]);
    expect(timeline.rows[1].cells.map((c) => c?.stage ?? null)).toEqual([
      null,
      "IF",
    ]);
  });

  it("handles empty history, empty instructions, error mock, and missing optional fields", () => {
    const errorTimeline = buildTimeline(
      simulateError.instructions,
      simulateError.history
    );
    expect(errorTimeline.totalCycles).toBe(0);
    expect(errorTimeline.rows).toEqual([]);

    const noHistory = buildTimeline(simulateSuccess.instructions, []);
    expect(noHistory.totalCycles).toBe(0);
    expect(noHistory.rows).toHaveLength(3);
    expect(noHistory.rows[0].cells).toEqual([]);

    const partial = buildTimeline(
      [{ instruction_id: 0, text: "ADDI R1, R0, 5" }],
      [
        {
          cycle: 1,
          stages: { IF: { instruction_id: 0 } },
        },
      ]
    );
    expect(partial.rows[0].cells[0]).toEqual({
      cycle: 1,
      stage: "IF",
      stalled: false,
      stallReason: null,
      forwarded: [],
    });
  });
});

describe("diffState", () => {
  it("detects changed registers and ignores unchanged ones", () => {
    const prev = { registers: { R0: 0, R1: 10, R2: 0 }, memory: {} };
    const curr = { registers: { R0: 0, R1: 10, R2: 20 }, memory: {} };

    expect(diffState(prev, curr)).toEqual({
      changedRegisters: ["R2"],
      changedMemory: [],
    });
  });

  it("detects newly written and updated memory addresses sorted numerically", () => {
    const prev = { registers: {}, memory: { "0": 10, "12": 40 } };
    const curr = { registers: {}, memory: { "100": 99, "12": 50, "0": 10, "4": 25 } };

    expect(diffState(prev, curr)).toEqual({
      changedRegisters: [],
      changedMemory: ["4", "12", "100"],
    });
  });

  it("handles missing previous or current state safely without mutating inputs", () => {
    const snap = { registers: { R1: 5 }, memory: { "8": 100 } };
    const snapCopy = JSON.parse(JSON.stringify(snap));

    expect(diffState(null, snap)).toEqual({
      changedRegisters: [],
      changedMemory: [],
    });
    expect(diffState(snap, null)).toEqual({
      changedRegisters: [],
      changedMemory: [],
    });
    expect(diffState({}, {})).toEqual({
      changedRegisters: [],
      changedMemory: [],
    });
    expect(snap).toEqual(snapCopy);
  });
});
