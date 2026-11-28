// owner: M6
// Memory viewer

import React from "react";
import "../styles/theme.css";
import { diffState } from "../utils/timeline";

/**
 * Displays written data memory words sorted numerically by address,
 * highlighting addresses written or updated since the previous cycle.
 */
export default function MemoryViewer({
  memory = null,
  previousMemory = null,
}) {
  const safeMemory = memory && typeof memory === "object" ? memory : {};

  // Sort addresses numerically (e.g., 0, 4, 8, 12, 100) rather than alphabetically.
  const entries = Object.entries(safeMemory).sort(
    ([addrA], [addrB]) => Number(addrA) - Number(addrB)
  );

  const changedSet = new Set(
    previousMemory
      ? diffState({ memory: previousMemory }, { memory: safeMemory }).changedMemory
      : []
  );

  return (
    <section className="m6-card" aria-label="Memory viewer">
      <header className="m6-card-header">
        <div>
          <h2 className="m6-card-title">Data Memory</h2>
          <span className="m6-card-subtitle">
            Aligned word addresses (0–4092); unwritten words default to 0
          </span>
        </div>
      </header>

      {entries.length === 0 ? (
        <div className="m6-empty-state">
          No memory addresses have been written yet. Unwritten words read as 0.
        </div>
      ) : (
        <div className="m6-memory-table-wrap">
          <table className="m6-memory-table">
            <thead>
              <tr>
                <th scope="col">Address</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([address, value]) => {
                const isChanged = changedSet.has(address);
                return (
                  <tr
                    key={address}
                    className={isChanged ? "m6-mem-row--changed" : undefined}
                    data-address={address}
                    data-changed={isChanged ? "true" : undefined}
                  >
                    <td>
                      {address}
                      {isChanged && (
                        <span className="m6-mem-updated-badge">updated</span>
                      )}
                    </td>
                    <td>{value}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
