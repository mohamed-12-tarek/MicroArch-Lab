// owner: M6
// One instruction row

import React from "react";

function formatForwardTooltip(forwards) {
  if (!Array.isArray(forwards) || forwards.length === 0) {
    return "";
  }
  return forwards
    .map((fwd) => {
      const reg = fwd.register ?? "?";
      const fromStage = fwd.fromStage || "?";
      const fromId = fwd.fromInstruction != null ? `I${fwd.fromInstruction}` : "?";
      return `${reg} from ${fromStage} (${fromId})`;
    })
    .join("; ");
}

/**
 * Renders a single instruction row in the pipeline timeline table.
 */
export default function PipelineRow({
  row,
  cycles = [],
  currentCycle = 0,
  onSelectCycle,
}) {
  if (!row) {
    return null;
  }

  const cells = Array.isArray(row.cells) ? row.cells : [];

  return (
    <tr className="m6-pipeline-row" data-instruction-id={row.instructionId}>
      <th scope="row" className="m6-instr-col" title={row.instruction}>
        <div className="m6-instr-cell-content">
          <span className="m6-instr-id">I{row.instructionId}</span>
          <span className="m6-instr-text">{row.instruction}</span>
        </div>
      </th>

      {cells.map((cell, index) => {
        const cycleNum = cycles[index] ?? index + 1;
        const isCurrent = cycleNum === currentCycle;
        const canSelect = typeof onSelectCycle === "function";

        const cellClasses = ["m6-cell"];
        if (isCurrent) {
          cellClasses.push("m6-cell--current");
        }
        if (!cell) {
          cellClasses.push("m6-cell--empty");
        }
        if (canSelect) {
          cellClasses.push("m6-cell--clickable");
        }

        if (!cell) {
          return (
            <td
              key={cycleNum}
              className={cellClasses.join(" ")}
              aria-current={isCurrent ? "step" : undefined}
              onClick={canSelect ? () => onSelectCycle(cycleNum) : undefined}
            >
              <span className="m6-empty-dash" aria-hidden="true">
                —
              </span>
            </td>
          );
        }

        const stageName = String(cell.stage || "").toUpperCase();
        const stageKey = stageName.toLowerCase();
        const forwards = Array.isArray(cell.forwarded) ? cell.forwarded : [];
        const hasForwards = forwards.length > 0;
        const forwardSummary = formatForwardTooltip(forwards);

        const tooltipParts = [`Cycle ${cycleNum}: ${stageName}`];
        if (cell.stalled) {
          tooltipParts.push(cell.stallReason || "Stalled");
        }
        if (hasForwards) {
          tooltipParts.push(`Forwarded ${forwardSummary}`);
        }

        const stageClasses = ["m6-stage", `m6-stage--${stageKey}`];
        if (cell.stalled) {
          stageClasses.push("m6-stage--stalled");
        }

        return (
          <td
            key={cycleNum}
            className={cellClasses.join(" ")}
            aria-current={isCurrent ? "step" : undefined}
            data-stalled={cell.stalled ? "true" : undefined}
            data-forwarded={hasForwards ? "true" : undefined}
            title={tooltipParts.join(" — ")}
            onClick={canSelect ? () => onSelectCycle(cycleNum) : undefined}
          >
            <div className="m6-cell-inner">
              <span className={stageClasses.join(" ")}>
                {stageName}
                {cell.stalled ? "*" : ""}
              </span>
              {cell.stalled && (
                <span className="m6-stall-tag">STALL</span>
              )}
              {hasForwards && (
                <span
                  className="m6-fwd-badge"
                  aria-label={`Forwarded: ${forwardSummary}`}
                >
                  {forwards.length > 1 ? `FWD×${forwards.length}` : "FWD"}
                </span>
              )}
            </div>
          </td>
        );
      })}
    </tr>
  );
}
