// owner: M6
// RegisterViewer tests

import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import RegisterViewer from "../RegisterViewer";

afterEach(cleanup);

function makeRegisters(overrides = {}) {
  const regs = {};
  for (let i = 0; i < 32; i += 1) {
    regs[`R${i}`] = 0;
  }
  return { ...regs, ...overrides };
}

describe("RegisterViewer", () => {
  it("renders all 32 registers R0..R31 with their values and marks R0 as const", () => {
    const regs = makeRegisters({ R1: 10, R2: 20, R3: 30 });
    const { container } = render(<RegisterViewer registers={regs} />);

    for (let i = 0; i < 32; i += 1) {
      expect(container.querySelector(`[data-register="R${i}"]`)).toBeTruthy();
    }
    expect(screen.getByText("const")).toBeTruthy();
    expect(screen.getByText("30")).toBeTruthy();
  });

  it("highlights registers that changed compared to previousRegisters", () => {
    const prev = makeRegisters({ R1: 10 });
    const curr = makeRegisters({ R1: 10, R2: 20 });

    const { container } = render(
      <RegisterViewer registers={curr} previousRegisters={prev} />
    );

    const r1Cell = container.querySelector('[data-register="R1"]');
    const r2Cell = container.querySelector('[data-register="R2"]');
    expect(r1Cell.getAttribute("data-changed")).toBeNull();
    expect(r2Cell.getAttribute("data-changed")).toBe("true");
  });

  it("handles empty or missing registers gracefully", () => {
    render(<RegisterViewer registers={null} />);
    expect(screen.getByText(/No register snapshot available yet/i)).toBeTruthy();
  });
});
