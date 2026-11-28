// owner: M6
// Timeline table + stall banner

import React from "react";
import "../styles/theme.css";
import { STAGE_ORDER, buildTimeline } from "../utils/timeline";
import PipelineRow from "./PipelineRow";

/**
 * Displays the 5-stage pipeline execution diagram (instructions × cycles),
 * along with stage legend, current-cycle stall banner, and forwarding details.
 */
export default function PipelineDiagram({
  instructions = [],
  history = [],
  currentCycle = 0,
  onSelectCycle,
}) {
  const timeline = buildTimeline(instructions, history);
  const { totalCycles, cycles, rows, stallsByCycle, forwardsByCycle } = timeline;

  const stallCount = Object.keys(stallsByCycle).length;
  const forwardCount = Object.values(forwardsByCycle).reduce(
    (sum, list) => sum + list.length,
    0
  );

  const activeStall = stallsByCycle[currentCycle] || null;
  const activeForwards = forwardsByCycle[currentCycle] || [];
  const hasData = rows.length > 0 && totalCycles > 0;

  return (
    <section className="m6-card" aria-label="Pipeline diagram">
      <header className="m6-card-header">
        <div>
          <h2 className="m6-card-title">Pipeline Timeline</h2>
          <span className="m6-card-subtitle">
            5-stage execution trace (IF → ID → EX → MEM → WB)
          </span>
        </div>

        <div className="m6-summary-bar">
          <span className="m6-stat-chip">
            Cycles: <strong>{totalCycles}</strong>
          </span>
          <span className="m6-stat-chip">
            Stalls: <strong>{stallCount}</strong>
          </span>
          <span className="m6-stat-chip">
            Forwards: <strong>{forwardCount}</strong>
          </span>
        </div>
      </header>

      <div className="m6-legend" aria-label="Pipeline legend">
        {STAGE_ORDER.map((stage) => (
          <span key={stage} className="m6-legend-item">
            <span className={`m6-stage m6-stage--${stage.toLowerCase()}`}>
              {stage}
            </span>
          </span>
        ))}
        <span className="m6-legend-item">
          <span className="m6-stage m6-stage--stalled">ID*</span>
          <span>Stall</span>
        </span>
        <span className="m6-legend-item">
          <span className="m6-fwd-badge">FWD</span>
          <span>Forwarding</span>
        </span>
      </div>

      {!hasData ? (
        <div className="m6-empty-state">
          No pipeline timeline to display yet. Run a valid assembly program to inspect cycles.
        </div>
      ) : (
        <>
          <div className="m6-table-scroll">
            <table className="m6-pipeline-table">
              <thead>
                <tr>
                  <th scope="col" className="m6-instr-col">
                    Instruction
                  </th>
                  {cycles.map((cycleNum) => {
                    const isCurrent = cycleNum === currentCycle;
                    return (
                      <th
                        key={cycleNum}
                        scope="col"
                        className={`m6-cycle-header${
                          isCurrent ? " m6-cycle-header--current" : ""
                        }`}
                        aria-current={isCurrent ? "step" : undefined}
                      >
                        {typeof onSelectCycle === "function" ? (
                          <button
                            type="button"
                            className="m6-cycle-btn"
                            onClick={() => onSelectCycle(cycleNum)}
                            aria-label={`Select cycle ${cycleNum}`}
                          >
                            C{cycleNum}
                          </button>
                        ) : (
                          `C${cycleNum}`
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <PipelineRow
                    key={row.instructionId}
                    row={row}
                    cycles={cycles}
                    currentCycle={currentCycle}
                    onSelectCycle={onSelectCycle}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {(activeStall || activeForwards.length > 0) && (
            <div className="m6-cycle-notes">
              {activeStall && (
                <div className="m6-stall-banner" role="status">
                  <strong>Cycle {currentCycle} Stall</strong>
                  {activeStall.register ? ` (${activeStall.register})` : ""}:{" "}
                  {activeStall.reason || "Load-use hazard detected"}
                </div>
              )}

              {activeForwards.length > 0 && (
                <div className="m6-forward-banner" role="status">
                  <strong>Cycle {currentCycle} Forwarding</strong>
                  <ul className="m6-forward-list">
                    {activeForwards.map((fwd, idx) => (
                      <li key={`${fwd.register}-${fwd.fromInstruction}-${idx}`}>
                        {fwd.register}: {fwd.fromStage} (I{fwd.fromInstruction}) → EX (I
                        {fwd.toInstruction})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
