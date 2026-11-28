// owner: M6
// 32 registers viewer

import React from "react";
import "../styles/theme.css";
import { diffState } from "../utils/timeline";

const REGISTER_NAMES = Array.from({ length: 32 }, (_, index) => `R${index}`);

/**
 * Displays all 32 architectural registers (R0..R31), highlights changes
 * compared with the previous snapshot, and indicates that R0 stays constant 0.
 */
export default function RegisterViewer({
  registers = null,
  previousRegisters = null,
}) {
  const hasRegisters =
    registers && typeof registers === "object" && Object.keys(registers).length > 0;

  const changedSet = new Set(
    hasRegisters && previousRegisters
      ? diffState({ registers: previousRegisters }, { registers }).changedRegisters
      : []
  );

  return (
    <section className="m6-card" aria-label="Register viewer">
      <header className="m6-card-header">
        <div>
          <h2 className="m6-card-title">Registers (R0–R31)</h2>
          <span className="m6-card-subtitle">
            R0 is hardwired to 0; highlighted cells changed this cycle
          </span>
        </div>
      </header>

      {!hasRegisters ? (
        <div className="m6-empty-state">
          No register snapshot available yet.
        </div>
      ) : (
        <div className="m6-register-grid">
          {REGISTER_NAMES.map((name) => {
            const value = registers[name] ?? 0;
            const isZero = name === "R0";
            const isChanged = !isZero && changedSet.has(name);

            const itemClasses = ["m6-reg-item"];
            if (isZero) {
              itemClasses.push("m6-reg--zero");
            }
            if (isChanged) {
              itemClasses.push("m6-reg--changed");
            }

            return (
              <div
                key={name}
                className={itemClasses.join(" ")}
                data-register={name}
                data-changed={isChanged ? "true" : undefined}
                title={
                  isZero
                    ? "R0 is hardwired to 0"
                    : isChanged
                    ? `${name} updated to ${value}`
                    : `${name} = ${value}`
                }
              >
                <span className="m6-reg-name-wrap">
                  <span className="m6-reg-name">{name}</span>
                  {isZero && <span className="m6-reg-const-tag">const</span>}
                  {isChanged && (
                    <span className="m6-changed-marker" aria-label="changed">
                      Δ
                    </span>
                  )}
                </span>
                <span className="m6-reg-value">{value}</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
