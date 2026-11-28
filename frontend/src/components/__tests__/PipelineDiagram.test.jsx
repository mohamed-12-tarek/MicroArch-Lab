// owner: M6
// PipelineDiagram tests

import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import simulateError from "../../mocks/simulate-error.json";
import simulateLoadUse from "../../mocks/simulate-load-use.json";
import simulateSuccess from "../../mocks/simulate-success.json";
import PipelineDiagram from "../PipelineDiagram";

afterEach(cleanup);

describe("PipelineDiagram", () => {
  it("renders the correct number of rows and cycle headers for simulate-success.json", () => {
    const { container } = render(
      <PipelineDiagram
        instructions={simulateSuccess.instructions}
        history={simulateSuccess.history}
        currentCycle={5}
      />
    );

    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(3);

    for (let c = 1; c <= 7; c += 1) {
      expect(screen.getByText(`C${c}`)).toBeTruthy();
    }

    // Cycle 5 has two forwards in simulate-success.json
    expect(screen.getByText(/Cycle 5 Forwarding/i)).toBeTruthy();
    expect(screen.getByText(/R1: WB \(I0\) → EX \(I2\)/)).toBeTruthy();
    expect(screen.getByText(/R2: MEM \(I1\) → EX \(I2\)/)).toBeTruthy();
  });

  it("highlights the current cycle and displays stall banner in simulate-load-use.json", () => {
    const { container } = render(
      <PipelineDiagram
        instructions={simulateLoadUse.instructions}
        history={simulateLoadUse.history}
        currentCycle={5}
      />
    );

    const activeHeader = container.querySelector("thead th.m6-cycle-header--current");
    expect(activeHeader).toBeTruthy();
    expect(activeHeader.textContent).toContain("C5");

    expect(screen.getByText(/Cycle 5 Stall/i)).toBeTruthy();
    expect(
      screen.getByText(/Load-use hazard on R2: instruction 2 \(LW R2, 0\(R0\)\) is in EX/)
    ).toBeTruthy();
  });

  it("calls onSelectCycle when clicking a cycle header", () => {
    const onSelectCycle = vi.fn();
    render(
      <PipelineDiagram
        instructions={simulateSuccess.instructions}
        history={simulateSuccess.history}
        currentCycle={1}
        onSelectCycle={onSelectCycle}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Select cycle 4" }));
    expect(onSelectCycle).toHaveBeenCalledWith(4);
  });

  it("renders empty state for empty/error responses and tolerates missing optional fields", () => {
    render(
      <PipelineDiagram
        instructions={simulateError.instructions}
        history={simulateError.history}
        currentCycle={0}
      />
    );
    expect(screen.getByText(/No pipeline timeline to display yet/i)).toBeTruthy();

    render(
      <PipelineDiagram
        instructions={[{ instruction_id: 0, text: "NOP" }]}
        history={[{ cycle: 1, stages: { IF: { instruction_id: 0 } } }]}
        currentCycle={1}
      />
    );
    expect(screen.getByText("NOP")).toBeTruthy();
  });
});
