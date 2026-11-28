// owner: M6
// Run / Step / Back / Reset

import React from "react";
import "../styles/theme.css";

/**
 * Controlled navigation bar for stepping through simulation cycles.
 * Owns no simulation or playback state; delegates all actions via props.
 */
export default function CycleControls({
  currentCycle = 0,
  totalCycles = 0,
  isPlaying = false,
  onPlay,
  onPause,
  onStep,
  onBack,
  onReset,
  onSeek,
  disabled = false,
}) {
  const hasCycles = totalCycles > 0;
  const safeCurrent = hasCycles
    ? Math.min(Math.max(currentCycle, 1), totalCycles)
    : 0;

  const canBack = !disabled && hasCycles && safeCurrent > 1;
  const canStep = !disabled && hasCycles && safeCurrent < totalCycles;
  const canReset = !disabled && hasCycles && safeCurrent > 1;
  const canTogglePlay =
    !disabled && hasCycles && (isPlaying || safeCurrent < totalCycles);

  return (
    <div className="m6-controls" role="region" aria-label="Cycle controls">
      <div className="m6-controls-buttons">
        <button
          type="button"
          className="m6-btn"
          disabled={!canReset}
          onClick={() => onReset?.()}
        >
          Reset
        </button>

        <button
          type="button"
          className="m6-btn"
          disabled={!canBack}
          onClick={() => onBack?.()}
        >
          Back
        </button>

        <button
          type="button"
          className="m6-btn m6-btn--primary"
          disabled={!canTogglePlay}
          onClick={() => (isPlaying ? onPause?.() : onPlay?.())}
        >
          {isPlaying ? "Pause" : "Play"}
        </button>

        <button
          type="button"
          className="m6-btn"
          disabled={!canStep}
          onClick={() => onStep?.()}
        >
          Step
        </button>
      </div>

      <div className="m6-controls-progress">
        <span className="m6-cycle-indicator">
          Cycle {safeCurrent} / {totalCycles}
        </span>

        {typeof onSeek === "function" && (
          <input
            type="range"
            className="m6-cycle-slider"
            aria-label="Select cycle"
            min={hasCycles ? 1 : 0}
            max={totalCycles}
            value={safeCurrent}
            disabled={disabled || !hasCycles}
            onChange={(e) => onSeek(Number(e.target.value))}
          />
        )}
      </div>
    </div>
  );
}
