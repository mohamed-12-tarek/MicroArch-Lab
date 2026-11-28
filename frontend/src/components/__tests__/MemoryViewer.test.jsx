// owner: M6
// MemoryViewer tests

import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import MemoryViewer from "../MemoryViewer";

afterEach(cleanup);

describe("MemoryViewer", () => {
  it("displays memory addresses and values sorted numerically", () => {
    const memory = { "100": 9, "8": 100, "0": 40, "12": 77 };
    const { container } = render(<MemoryViewer memory={memory} />);

    const rows = Array.from(container.querySelectorAll("tbody tr"));
    const addresses = rows.map((row) => row.getAttribute("data-address"));
    const values = rows.map((row) => row.querySelectorAll("td")[1].textContent);
    expect(addresses).toEqual(["0", "8", "12", "100"]);
    expect(values).toEqual(["40", "100", "77", "9"]);
  });

  it("highlights newly written or updated addresses", () => {
    const prev = { "0": 40 };
    const curr = { "0": 40, "8": 100 };

    const { container } = render(
      <MemoryViewer memory={curr} previousMemory={prev} />
    );

    const row0 = container.querySelector('[data-address="0"]');
    const row8 = container.querySelector('[data-address="8"]');
    expect(row0.getAttribute("data-changed")).toBeNull();
    expect(row8.getAttribute("data-changed")).toBe("true");
    expect(screen.getByText("updated")).toBeTruthy();
  });

  it("displays an empty state when memory has no written addresses", () => {
    render(<MemoryViewer memory={{}} />);
    expect(
      screen.getByText(/No memory addresses have been written yet/i)
    ).toBeTruthy();
  });
});
