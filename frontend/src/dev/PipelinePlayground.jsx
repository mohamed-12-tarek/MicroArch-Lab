// owner: M6
// Playground using mocks

import React, { useEffect, useState } from "react";
import "../styles/theme.css";
import simulateError from "../mocks/simulate-error.json";
import simulateLoadUse from "../mocks/simulate-load-use.json";
import simulateMemory from "../mocks/simulate-memory.json";
import simulateSuccess from "../mocks/simulate-success.json";
import CycleControls from "../components/CycleControls";
import MemoryViewer from "../components/MemoryViewer";
import PipelineDiagram from "../components/PipelineDiagram";
import RegisterViewer from "../components/RegisterViewer";

const SCENARIOS = {
  success: {
    label: "Basic Arithmetic + Forwarding (simulate-success.json)",
    data: simulateSuccess,
  },
  loadUse: {
    label: "Load-Use Stall + Forwarding (simulate-load-use.json)",
    data: simulateLoadUse,
  },
  memory: {
    label: "Store & Load Memory (simulate-memory.json)",
    data: simulateMemory,
  },
  error: {
    label: "Parse Error / Empty Timeline (simulate-error.json)",
    data: simulateError,
  },
};

/**
 * Development-only playground for testing all M6 visualization components
 * independently using the static mock JSON fixtures.
 */
export default function PipelinePlayground() {
  const [scenarioKey, setScenarioKey] = useState("loadUse");
  const scenario = SCENARIOS[scenarioKey];
  const simulation = scenario.data;

  const history = Array.isArray(simulation.history) ? simulation.history : [];
  const totalCycles = history.length;

  const [currentCycle, setCurrentCycle] = useState(totalCycles > 0 ? 1 : 0);
  const [isPlaying, setIsPlaying] = useState(false);

  const handleScenarioChange = (nextKey) => {
    const nextHistory = SCENARIOS[nextKey].data.history || [];
    setScenarioKey(nextKey);
    setIsPlaying(false);
    setCurrentCycle(nextHistory.length > 0 ? 1 : 0);
  };

  useEffect(() => {
    if (!isPlaying || totalCycles === 0) {
      return undefined;
    }
    if (currentCycle >= totalCycles) {
      setIsPlaying(false);
      return undefined;
    }

    const timerId = setInterval(() => {
      setCurrentCycle((prev) => {
        if (prev >= totalCycles) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 800);

    return () => clearInterval(timerId);
  }, [isPlaying, currentCycle, totalCycles]);

  const currentSnapshot =
    currentCycle >= 1 && currentCycle <= totalCycles
      ? history[currentCycle - 1]
      : null;
  const previousSnapshot =
    currentCycle >= 2 && currentCycle <= totalCycles
      ? history[currentCycle - 2]
      : null;

  return (
    <main className="m6-playground">
      <header className="m6-playground-topbar">
        <div>
          <h1 className="m6-card-title">MicroArch Lab — M6 Component Playground</h1>
          <span className="m6-card-subtitle">
            Local mock-data harness for PipelineDiagram, RegisterViewer, MemoryViewer, and CycleControls
          </span>
        </div>

        <label>
          <span className="m6-card-subtitle">Scenario: </span>
          <select
            className="m6-playground-select"
            value={scenarioKey}
            onChange={(e) => handleScenarioChange(e.target.value)}
          >
            {Object.entries(SCENARIOS).map(([key, entry]) => (
              <option key={key} value={key}>
                {entry.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      {!simulation.success && Array.isArray(simulation.errors) && (
        <div className="m6-playground-error" role="alert">
          <strong>Mock Error Response:</strong>{" "}
          {simulation.errors
            .map((err) =>
              err.line != null ? `Line ${err.line}: ${err.message}` : err.message
            )
            .join(" | ")}
        </div>
      )}

      <CycleControls
        currentCycle={currentCycle}
        totalCycles={totalCycles}
        isPlaying={isPlaying}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onStep={() => {
          setIsPlaying(false);
          setCurrentCycle((prev) => Math.min(prev + 1, totalCycles));
        }}
        onBack={() => {
          setIsPlaying(false);
          setCurrentCycle((prev) => Math.max(prev - 1, totalCycles > 0 ? 1 : 0));
        }}
        onReset={() => {
          setIsPlaying(false);
          setCurrentCycle(totalCycles > 0 ? 1 : 0);
        }}
        onSeek={(cycleNum) => {
          setIsPlaying(false);
          setCurrentCycle(cycleNum);
        }}
      />

      <PipelineDiagram
        instructions={simulation.instructions}
        history={history}
        currentCycle={currentCycle}
        onSelectCycle={(cycleNum) => {
          setIsPlaying(false);
          setCurrentCycle(cycleNum);
        }}
      />

      <div className="m6-playground-panels">
        <RegisterViewer
          registers={currentSnapshot?.registers || null}
          previousRegisters={previousSnapshot?.registers || null}
        />

        <MemoryViewer
          memory={currentSnapshot?.memory || null}
          previousMemory={previousSnapshot?.memory || null}
        />
      </div>
    </main>
  );
}
