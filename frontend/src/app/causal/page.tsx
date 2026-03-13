"use client";

import { useState } from "react";
import { getCausalDAG, runWhatIf } from "@/lib/api";
import type { WhatIfResponse, CausalDAGResponse } from "@/lib/types";
import {
  BrainCircuit,
  Play,
  RefreshCw,
  ArrowRight,
  TrendingDown,
  ChevronDown,
  Award,
  ShieldCheck,
} from "lucide-react";

// Supported cities and target parameters
const CITIES = ["Raipur", "Bhilai", "Korba", "Bilaspur", "Durg", "Raigarh"];
const PARAMETERS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"];

function formatVarName(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Page Component ─────────────────────────────────────────
export default function CausalPage() {
  // DAG state
  const [dagLoading, setDagLoading] = useState(false);
  const [dagError, setDagError] = useState<string | null>(null);
  const [dagData, setDagData] = useState<CausalDAGResponse | null>(null);

  // What-If state
  const [city, setCity] = useState("Raipur");
  const [targetParam, setTargetParam] = useState("PM2.5");
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);
  const [whatIf, setWhatIf] = useState<WhatIfResponse | null>(null);

  // ── Handlers ─────────────────────────────────────────────
  const handleLoadDAG = async () => {
    setDagLoading(true);
    setDagError(null);
    try {
      const data = await getCausalDAG();
      setDagData(data);
    } catch (err) {
      setDagError(err instanceof Error ? err.message : "Failed to load causal DAG");
      setDagData(null);
    } finally {
      setDagLoading(false);
    }
  };

  const handleRunWhatIf = async () => {
    setSimLoading(true);
    setSimError(null);
    try {
      const data = await runWhatIf({ city, target_parameter: targetParam });
      setWhatIf(data);
    } catch (err) {
      setSimError(err instanceof Error ? err.message : "Simulation failed");
      setWhatIf(null);
    } finally {
      setSimLoading(false);
    }
  };

  // ── Render ───────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BrainCircuit className="w-6 h-6 text-primary" />
          Causal / What-If Policy Simulator
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Explore causal relationships in environmental data using NumPy SEM and
          compare policy intervention scenarios to find the most effective strategy.
        </p>
      </div>

      {/* ═══════════════════════════════════════════════════════
          Section 1: Causal DAG Visualization
          ═══════════════════════════════════════════════════════ */}
      <div className="bg-card rounded-lg border border-border p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-muted-foreground">
            Causal DAG Visualization
          </h2>
          <button
            onClick={handleLoadDAG}
            disabled={dagLoading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {dagLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <BrainCircuit className="w-4 h-4" />
            )}
            {dagLoading ? "Loading..." : "Load Causal DAG"}
          </button>
        </div>

        {/* DAG Error */}
        {dagError && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 mb-4">
            <p className="text-red-400 font-medium text-sm">DAG Error</p>
            <p className="text-muted-foreground text-sm mt-1">{dagError}</p>
          </div>
        )}

        {/* DAG Loading */}
        {dagLoading && (
          <div className="p-10 text-center">
            <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
            <p className="text-muted-foreground text-sm">Loading causal graph...</p>
          </div>
        )}

        {/* DAG Empty */}
        {!dagLoading && !dagData && !dagError && (
          <div className="p-10 text-center">
            <BrainCircuit className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
            <p className="text-muted-foreground text-sm">
              Click{" "}
              <span className="text-foreground font-medium">Load Causal DAG</span>{" "}
              to visualize the structural equation model graph.
            </p>
          </div>
        )}

        {/* DAG Results */}
        {dagData && !dagLoading && (
          <div>
            <p className="text-xs text-muted-foreground mb-3">
              {dagData.description} &mdash; {dagData.total_nodes} nodes, {dagData.total_edges} edges
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Nodes */}
              <div className="bg-muted/20 rounded-lg p-4">
                <h3 className="text-sm font-medium text-foreground mb-3">
                  Nodes ({dagData.nodes.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {dagData.nodes.map((node) => (
                    <span
                      key={node}
                      className="inline-block text-xs font-mono px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20"
                    >
                      {node}
                    </span>
                  ))}
                </div>
              </div>

              {/* Edges */}
              <div className="bg-muted/20 rounded-lg p-4">
                <h3 className="text-sm font-medium text-foreground mb-3">
                  Edges ({dagData.edges.length})
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {dagData.edges.map((edge, i) => (
                    <div
                      key={`${edge.from}-${edge.to}-${i}`}
                      className="flex items-center gap-2 text-sm font-mono"
                    >
                      <span className="text-primary">{edge.from}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      <span className="text-primary">{edge.to}</span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        w={(edge.coefficient ?? 0).toFixed(3)}
                      </span>
                    </div>
                  ))}
                  {dagData.edges.length === 0 && (
                    <p className="text-muted-foreground text-sm">No edges in the DAG.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════
          Section 2: What-If Scenario Comparison
          ═══════════════════════════════════════════════════════ */}
      <div className="bg-card rounded-lg border border-border p-5">
        <h2 className="text-sm font-medium text-muted-foreground mb-4">
          What-If Policy Scenario Comparison
        </h2>

        {/* Controls */}
        <div className="flex flex-wrap items-end gap-4 mb-6">
          {/* City selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">City</label>
            <div className="relative">
              <select
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="appearance-none w-44 rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm font-medium pr-8 focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {CITIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            </div>
          </div>

          {/* Parameter selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Target Pollutant</label>
            <div className="relative">
              <select
                value={targetParam}
                onChange={(e) => setTargetParam(e.target.value)}
                className="appearance-none w-36 rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm font-medium pr-8 focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {PARAMETERS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            </div>
          </div>

          {/* Run button */}
          <button
            onClick={handleRunWhatIf}
            disabled={simLoading}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {simLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {simLoading ? "Running..." : "Compare Scenarios"}
          </button>
        </div>

        {/* Empty state */}
        {!simLoading && !whatIf && !simError && (
          <div className="p-10 text-center">
            <Play className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
            <p className="text-muted-foreground text-sm">
              Select a city and pollutant, then click{" "}
              <span className="text-foreground font-medium">Compare Scenarios</span>{" "}
              to run 5 counterfactual policy interventions.
            </p>
          </div>
        )}
      </div>

      {/* Simulation Error */}
      {simError && (
        <div className="bg-card rounded-lg border border-red-500/30 p-5">
          <p className="text-red-400 font-medium text-sm">Simulation Error</p>
          <p className="text-muted-foreground text-sm mt-1">{simError}</p>
        </div>
      )}

      {/* Simulation Loading */}
      {simLoading && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Running 5 counterfactual scenarios via NumPy SEM...
          </p>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          Section 3: Results
          ═══════════════════════════════════════════════════════ */}
      {whatIf && !simLoading && (
        <div className="space-y-6">
          {/* Recommendation Banner */}
          {whatIf.recommendation && (
            <div className="bg-primary/5 border border-primary/20 rounded-lg p-5 flex items-start gap-4">
              <Award className="w-6 h-6 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  Optimal Intervention: {whatIf.recommendation.optimal_intervention}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                   Expected change in {whatIf.target_parameter}: {(whatIf.recommendation.expected_change ?? 0).toFixed(2)} &mdash;{" "}
                  {whatIf.recommendation.rationale}
                </p>
              </div>
            </div>
          )}

          {/* Scenario Comparison Table */}
          <div className="bg-card rounded-lg border border-border p-5">
            <h3 className="text-sm font-medium text-muted-foreground mb-1">
              Scenario Results &mdash; {whatIf.city}, {whatIf.target_parameter}
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              {whatIf.scenarios.length} policy scenarios compared via NumPy Structural Equation Model
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2.5 px-3 text-xs font-medium text-muted-foreground">Scenario</th>
                    <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Reduction</th>
                    <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Baseline</th>
                    <th className="text-center py-2.5 px-3 text-xs font-medium text-muted-foreground">&nbsp;</th>
                    <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Counterfactual</th>
                    <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Change</th>
                    <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Relative</th>
                    <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">p-value</th>
                  </tr>
                </thead>
                <tbody>
                  {whatIf.scenarios.map((sc, i) => {
                    const isReduction = sc.absolute_change < 0;
                    const effectColor = isReduction ? "text-green-400" : "text-red-400";
                    const effectBg = isReduction ? "bg-green-500/5" : "bg-red-500/5";
                    const isSignificant = sc.p_value < 0.05;

                    return (
                      <tr key={i} className={`border-b border-border/50 ${effectBg}`}>
                        <td className="py-2.5 px-3 font-medium text-foreground">
                          <div className="flex items-center gap-2">
                            {formatVarName(sc.intervention_type)}
                            {isSignificant && (
                              <span title="Statistically significant (p &lt; 0.05)"><ShieldCheck className="w-3.5 h-3.5 text-green-400" /></span>
                            )}
                          </div>
                          <p className="text-[10px] text-muted-foreground">{sc.scenario}</p>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-muted-foreground">
                          {sc.reduction_pct_applied}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-muted-foreground">
                          {sc.baseline_value.toFixed(1)}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <ArrowRight className="w-3.5 h-3.5 text-muted-foreground mx-auto" />
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-medium text-foreground">
                          {sc.counterfactual_value.toFixed(1)}
                        </td>
                        <td className={`py-2.5 px-3 text-right font-mono font-medium ${effectColor}`}>
                          {sc.absolute_change > 0 ? "+" : ""}{sc.absolute_change.toFixed(2)}
                        </td>
                        <td className={`py-2.5 px-3 text-right font-mono ${effectColor}`}>
                          {sc.relative_change_pct > 0 ? "+" : ""}{sc.relative_change_pct.toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-xs text-muted-foreground">
                          {sc.p_value.toFixed(4)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Confidence Intervals */}
            <div className="mt-4 pt-3 border-t border-border/50">
              <h4 className="text-xs font-medium text-muted-foreground mb-3">
                90% Confidence Intervals
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {whatIf.scenarios.map((sc, i) => (
                  <div
                    key={`ci-${i}`}
                    className="bg-muted/20 rounded-lg px-3 py-2 flex items-center justify-between"
                  >
                    <span className="text-xs text-muted-foreground truncate mr-2">
                      {formatVarName(sc.intervention_type)}
                    </span>
                    <span className="text-xs font-mono text-foreground whitespace-nowrap">
                      [{sc.confidence_interval[0].toFixed(1)}, {sc.confidence_interval[1].toFixed(1)}]
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Scenario Impact Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {whatIf.scenarios.map((sc, i) => {
              const isReduction = sc.absolute_change < 0;
              const borderColor = isReduction ? "border-green-500/30" : "border-red-500/30";
              const textColor = isReduction ? "text-green-400" : "text-red-400";

              return (
                <div key={`card-${i}`} className={`bg-card rounded-lg border ${borderColor} p-4 text-center`}>
                  <p className="text-xs text-muted-foreground mb-1 truncate">
                    {formatVarName(sc.intervention_type)}
                  </p>
                  <p className={`text-lg font-bold font-mono ${textColor}`}>
                    {sc.relative_change_pct > 0 ? "+" : ""}{sc.relative_change_pct.toFixed(1)}%
                  </p>
                  <div className="flex items-center justify-center gap-1 mt-1">
                    {isReduction && <TrendingDown className="w-3 h-3 text-green-400" />}
                    <p className="text-[10px] text-muted-foreground">
                      {isReduction ? "Reduction" : "Increase"}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
