// owner: M6
// CycleControls tests

import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CycleControls from "../CycleControls";

afterEach(cleanup);

describe("CycleControls", () => {
  it("displays current and total cycles and triggers navigation callbacks", () => {
    const onPlay = vi.fn();
    const onStep = vi.fn();
    const onBack = vi.fn();
    const onReset = vi.fn();
    const onSeek = vi.fn();

    render(
      <CycleControls
        currentCycle={3}
        totalCycles={7}
        isPlaying={false}
        onPlay={onPlay}
        onStep={onStep}
        onBack={onBack}
        onReset={onReset}
        onSeek={onSeek}
      />
    );

    expect(screen.getByText("Cycle 3 / 7")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    fireEvent.click(screen.getByRole("button", { name: "Step" }));
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    fireEvent.change(screen.getByLabelText("Select cycle"), {
      target: { value: "5" },
    });

    expect(onPlay).toHaveBeenCalledTimes(1);
    expect(onStep).toHaveBeenCalledTimes(1);
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(onReset).toHaveBeenCalledTimes(1);
    expect(onSeek).toHaveBeenCalledWith(5);
  });

  it("calls onPause when isPlaying is true", () => {
    const onPause = vi.fn();
    render(
      <CycleControls
        currentCycle={2}
        totalCycles={7}
        isPlaying={true}
        onPause={onPause}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(onPause).toHaveBeenCalledTimes(1);
  });

  it("disables Back/Reset at cycle 1, Step/Play at last cycle, and all controls when disabled", () => {
    const { rerender } = render(
      <CycleControls currentCycle={1} totalCycles={7} isPlaying={false} />
    );

    expect(screen.getByRole("button", { name: "Back" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Reset" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Step" }).disabled).toBe(false);
    expect(screen.getByRole("button", { name: "Play" }).disabled).toBe(false);

    rerender(
      <CycleControls currentCycle={7} totalCycles={7} isPlaying={false} />
    );
    expect(screen.getByRole("button", { name: "Step" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Play" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Back" }).disabled).toBe(false);

    rerender(
      <CycleControls
        currentCycle={3}
        totalCycles={7}
        isPlaying={false}
        disabled={true}
      />
    );
    expect(screen.getByRole("button", { name: "Reset" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Back" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Play" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Step" }).disabled).toBe(true);
  });
});
