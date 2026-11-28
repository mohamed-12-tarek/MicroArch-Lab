// owner: M6
// PipelineRow tests

import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PipelineRow from "../PipelineRow";

afterEach(cleanup);

function renderRow(props) {
  return render(
    <table>
      <tbody>
        <PipelineRow {...props} />
      </tbody>
    </table>
  );
}

describe("PipelineRow", () => {
  const sampleRow = {
    instructionId: 3,
    instruction: "ADD R3, R2, R0",
    cells: [
      null,
      { cycle: 2, stage: "IF", stalled: false, stallReason: null, forwarded: [] },
      {
        cycle: 3,
        stage: "ID",
        stalled: true,
        stallReason: "Load-use hazard on R2",
        forwarded: [],
      },
      {
        cycle: 4,
        stage: "EX",
        stalled: false,
        stallReason: null,
        forwarded: [
          {
            register: "R2",
            fromStage: "WB",
            fromInstruction: 2,
            toInstruction: 3,
          },
        ],
      },
    ],
  };

  it("renders instruction ID and instruction text", () => {
    renderRow({ row: sampleRow, cycles: [1, 2, 3, 4], currentCycle: 2 });

    expect(screen.getByText("I3")).toBeTruthy();
    expect(screen.getByText("ADD R3, R2, R0")).toBeTruthy();
  });

  it("renders stage cells, stall indicator, and forwarding indicator", () => {
    const { container } = renderRow({
      row: sampleRow,
      cycles: [1, 2, 3, 4],
      currentCycle: 3,
    });

    expect(screen.getByText("IF")).toBeTruthy();
    expect(screen.getByText("ID*")).toBeTruthy();
    expect(screen.getByText("STALL")).toBeTruthy();
    expect(screen.getByText("EX")).toBeTruthy();
    expect(screen.getByText("FWD")).toBeTruthy();

    const currentCell = container.querySelector('[aria-current="step"]');
    expect(currentCell).toBeTruthy();
    expect(currentCell.getAttribute("data-stalled")).toBe("true");

    const forwardedCell = container.querySelector('[data-forwarded="true"]');
    expect(forwardedCell).toBeTruthy();
    expect(forwardedCell.getAttribute("title")).toContain("R2 from WB (I2)");
  });

  it("calls onSelectCycle when a cell is clicked", () => {
    const onSelectCycle = vi.fn();
    renderRow({
      row: sampleRow,
      cycles: [1, 2, 3, 4],
      currentCycle: 1,
      onSelectCycle,
    });

    fireEvent.click(screen.getByText("EX"));
    expect(onSelectCycle).toHaveBeenCalledWith(4);
  });
});
