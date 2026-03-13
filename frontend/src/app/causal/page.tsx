"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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

// ── Node classification for coloring ──────────────────────
const POLLUTANTS = new Set(["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3"]);
const DRIVERS = new Set(["industrial_emissions", "traffic_volume"]);
const METEOROLOGY = new Set(["wind_speed", "rainfall", "temperature"]);
// green_belt_area is an intervention

function nodeColor(name: string): string {
  if (POLLUTANTS.has(name)) return "#ef4444"; // red
  if (DRIVERS.has(name)) return "#f97316";    // orange
  if (METEOROLOGY.has(name)) return "#3b82f6"; // blue
  return "#22c55e";                             // green (interventions)
}

function nodeCategory(name: string): string {
  if (POLLUTANTS.has(name)) return "Pollutant";
  if (DRIVERS.has(name)) return "Source";
  if (METEOROLOGY.has(name)) return "Meteorology";
  return "Intervention";
}

// ── Force-directed layout types ───────────────────────────
interface SimNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function runForceLayout(
  nodeIds: string[],
  edges: Array<{ from: string; to: string; coefficient: number }>,
  width: number,
  height: number,
  iterations = 300
): SimNode[] {
  const cx = width / 2;
  const cy = height / 2;
  const nodes: SimNode[] = nodeIds.map((id, i) => {
    // Start with a circular layout for stability
    const angle = (2 * Math.PI * i) / nodeIds.length;
    const r = Math.min(width, height) * 0.3;
    return { id, x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle), vx: 0, vy: 0 };
  });

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const repulsionStrength = 8000;
  const attractionStrength = 0.005;
  const idealEdgeLength = 120;
  const damping = 0.85;
  const padding = 50;

  for (let iter = 0; iter < iterations; iter++) {
    const alpha = 1 - iter / iterations; // cooling
    // Repulsion (all pairs)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = (repulsionStrength * alpha) / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        nodes[i].vx -= fx;
        nodes[i].vy -= fy;
        nodes[j].vx += fx;
        nodes[j].vy += fy;
      }
    }
    // Attraction (edges)
    for (const edge of edges) {
      const a = nodeMap.get(edge.from);
      const b = nodeMap.get(edge.to);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const displacement = dist - idealEdgeLength;
      const force = attractionStrength * displacement * alpha;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }
    // Center gravity
    for (const n of nodes) {
      n.vx += (cx - n.x) * 0.001 * alpha;
      n.vy += (cy - n.y) * 0.001 * alpha;
    }
    // Apply velocities
    for (const n of nodes) {
      n.vx *= damping;
      n.vy *= damping;
      n.x += n.vx;
      n.y += n.vy;
      // Keep in bounds
      n.x = Math.max(padding, Math.min(width - padding, n.x));
      n.y = Math.max(padding, Math.min(height - padding, n.y));
    }
  }
  return nodes;
}

// ── DAG Graph SVG Component ──────────────────────────────
function DAGGraph({ dag }: { dag: CausalDAGResponse }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<number | null>(null);
  const [dimensions, setDimensions] = useState({ width: 900, height: 520 });

  // Measure container
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      setDimensions({ width: Math.max(600, width), height: 520 });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Run force layout
  const layoutNodes = runForceLayout(dag.nodes, dag.edges, dimensions.width, dimensions.height);
  const nodeMap = new Map(layoutNodes.map((n) => [n.id, n]));

  // Compute connected edges per node
  const connectedEdges = useCallback(
    (nodeId: string): number[] =>
      dag.edges
        .map((e, i) => (e.from === nodeId || e.to === nodeId ? i : -1))
        .filter((i) => i >= 0),
    [dag.edges]
  );

  const nodeRadius = 24;

  // Arrowhead offset so it doesn't overlap the target node circle
  function edgePath(fromNode: SimNode, toNode: SimNode) {
    const dx = toNode.x - fromNode.x;
    const dy = toNode.y - fromNode.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist === 0) return { x1: fromNode.x, y1: fromNode.y, x2: toNode.x, y2: toNode.y };
    const offsetStart = nodeRadius + 4;
    const offsetEnd = nodeRadius + 10;
    return {
      x1: fromNode.x + (dx / dist) * offsetStart,
      y1: fromNode.y + (dy / dist) * offsetStart,
      x2: toNode.x - (dx / dist) * offsetEnd,
      y2: toNode.y - (dy / dist) * offsetEnd,
    };
  }

  return (
    <div ref={containerRef} className="w-full">
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        className="w-full rounded-lg"
        style={{ background: "rgba(0,0,0,0.03)" }}
      >
        <defs>
          <marker
            id="arrowGreen"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#22c55e" />
          </marker>
          <marker
            id="arrowRed"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
          </marker>
          <marker
            id="arrowHighlight"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#facc15" />
          </marker>
        </defs>

        {/* Edges */}
        {dag.edges.map((edge, i) => {
          const fromN = nodeMap.get(edge.from);
          const toN = nodeMap.get(edge.to);
          if (!fromN || !toN) return null;
          const { x1, y1, x2, y2 } = edgePath(fromN, toN);
          const isNegative = edge.coefficient < 0;
          const isHighlighted =
            hoveredEdge === i ||
            (hoveredNode !== null &&
              (edge.from === hoveredNode || edge.to === hoveredNode));
          const strokeWidth = Math.max(1.5, Math.abs(edge.coefficient) * 5);
          const marker = isHighlighted
            ? "url(#arrowHighlight)"
            : isNegative
            ? "url(#arrowGreen)"
            : "url(#arrowRed)";

          return (
            <g key={`edge-${i}`}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={isHighlighted ? "#facc15" : isNegative ? "#22c55e" : "#ef4444"}
                strokeWidth={isHighlighted ? strokeWidth + 1 : strokeWidth}
                opacity={
                  hoveredNode !== null && !isHighlighted
                    ? 0.1
                    : hoveredEdge !== null && !isHighlighted
                    ? 0.15
                    : 0.6
                }
                markerEnd={marker}
                strokeDasharray={isNegative ? "6 3" : undefined}
                className="transition-opacity duration-150"
              />
              {/* Invisible wider line for hover */}
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="transparent"
                strokeWidth={12}
                onMouseEnter={() => setHoveredEdge(i)}
                onMouseLeave={() => setHoveredEdge(null)}
                className="cursor-pointer"
              />
              {/* Weight label on hover */}
              {isHighlighted && (
                <text
                  x={(x1 + x2) / 2}
                  y={(y1 + y2) / 2 - 8}
                  textAnchor="middle"
                  fill="#facc15"
                  fontSize="11"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  w={edge.coefficient.toFixed(2)}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {layoutNodes.map((node) => {
          const isHighlighted =
            hoveredNode === node.id ||
            (hoveredEdge !== null &&
              (dag.edges[hoveredEdge]?.from === node.id ||
                dag.edges[hoveredEdge]?.to === node.id));
          const isConnected =
            hoveredNode !== null &&
            hoveredNode !== node.id &&
            connectedEdges(hoveredNode).some(
              (ei) =>
                dag.edges[ei].from === node.id ||
                dag.edges[ei].to === node.id
            );
          const dimmed =
            (hoveredNode !== null && !isHighlighted && !isConnected) ||
            (hoveredEdge !== null && !isHighlighted);

          const color = nodeColor(node.id);
          const displayName = node.id.length > 12
            ? node.id.replace(/_/g, "\n")
            : node.id;
          const lines = displayName.split("\n");

          return (
            <g
              key={node.id}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              className="cursor-pointer"
              opacity={dimmed ? 0.2 : 1}
              style={{ transition: "opacity 150ms" }}
            >
              {/* Glow */}
              {isHighlighted && (
                <circle cx={node.x} cy={node.y} r={nodeRadius + 6} fill={color} opacity={0.2} />
              )}
              {/* Node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r={nodeRadius}
                fill={isHighlighted ? color : `${color}33`}
                stroke={color}
                strokeWidth={isHighlighted ? 3 : 2}
              />
              {/* Label */}
              {lines.map((line, li) => (
                <text
                  key={li}
                  x={node.x}
                  y={node.y + (li - (lines.length - 1) / 2) * 11}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill={isHighlighted ? "#fff" : "#1a1a2e"}
                  fontSize={node.id.length > 10 ? "8" : "10"}
                  fontFamily="monospace"
                  fontWeight={isHighlighted ? "bold" : "normal"}
                >
                  {line}
                </text>
              ))}
            </g>
          );
        })}

        {/* Hovered node tooltip */}
        {hoveredNode && (() => {
          const n = nodeMap.get(hoveredNode);
          if (!n) return null;
          const inEdges = dag.edges.filter((e) => e.to === hoveredNode);
          const outEdges = dag.edges.filter((e) => e.from === hoveredNode);
          const cat = nodeCategory(hoveredNode);
          const tooltipWidth = 200;
          const tooltipX = n.x + nodeRadius + 12 > dimensions.width - tooltipWidth
            ? n.x - nodeRadius - tooltipWidth - 12
            : n.x + nodeRadius + 12;
          const tooltipY = Math.max(10, Math.min(n.y - 20, dimensions.height - 80));

          return (
            <foreignObject x={tooltipX} y={tooltipY} width={tooltipWidth} height={100}>
              <div
                style={{
                  background: "rgba(255,255,255,0.97)",
                  border: `1px solid ${nodeColor(hoveredNode)}44`,
                  borderRadius: 8,
                  padding: "8px 10px",
                  fontSize: 11,
                  color: "#1a1a2e",
                  fontFamily: "monospace",
                  lineHeight: 1.5,
                }}
              >
                <div style={{ fontWeight: "bold", color: nodeColor(hoveredNode), marginBottom: 2 }}>
                  {hoveredNode}
                </div>
                <div style={{ color: "#5a6570", fontSize: 10 }}>{cat}</div>
                <div style={{ marginTop: 4, fontSize: 10, color: "#5a6570" }}>
                  {inEdges.length} incoming &middot; {outEdges.length} outgoing
                </div>
              </div>
            </foreignObject>
          );
        })()}

        {/* Hovered edge tooltip */}
        {hoveredEdge !== null && (() => {
          const edge = dag.edges[hoveredEdge];
          if (!edge) return null;
          const fromN = nodeMap.get(edge.from);
          const toN = nodeMap.get(edge.to);
          if (!fromN || !toN) return null;
          const mx = (fromN.x + toN.x) / 2;
          const my = (fromN.y + toN.y) / 2 + 8;

          return (
            <foreignObject x={mx - 110} y={my} width={220} height={60}>
              <div
                style={{
                  background: "rgba(255,255,255,0.97)",
                  border: "1px solid #facc1544",
                  borderRadius: 8,
                  padding: "6px 10px",
                  fontSize: 10,
                  color: "#1a1a2e",
                  fontFamily: "monospace",
                  lineHeight: 1.5,
                  textAlign: "center",
                }}
              >
                <span style={{ color: "#ca8a04" }}>{edge.from}</span>
                {" → "}
                <span style={{ color: "#ca8a04" }}>{edge.to}</span>
                <div style={{ color: "#5a6570", marginTop: 2 }}>{edge.description}</div>
              </div>
            </foreignObject>
          );
        })()}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 mt-3 px-1">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: "#ef4444" }} />
          <span className="text-[10px] text-muted-foreground">Pollutant</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: "#f97316" }} />
          <span className="text-[10px] text-muted-foreground">Source</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: "#3b82f6" }} />
          <span className="text-[10px] text-muted-foreground">Meteorology</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: "#22c55e" }} />
          <span className="text-[10px] text-muted-foreground">Intervention</span>
        </div>
        <div className="flex items-center gap-1.5 ml-4">
          <span className="w-5 border-t-2 border-red-500" />
          <span className="text-[10px] text-muted-foreground">Positive effect</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-5 border-t-2 border-dashed border-green-500" />
          <span className="text-[10px] text-muted-foreground">Negative effect (mitigates)</span>
        </div>
      </div>
    </div>
  );
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

  // Auto-load DAG on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setDagLoading(true);
      setDagError(null);
      try {
        const data = await getCausalDAG();
        if (!cancelled) setDagData(data);
      } catch (err) {
        if (!cancelled) {
          setDagError(err instanceof Error ? err.message : "Failed to load causal DAG");
          setDagData(null);
        }
      } finally {
        if (!cancelled) setDagLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

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
            Structural Equation Model — Causal DAG
          </h2>
          {dagData && (
            <span className="text-xs text-muted-foreground">
              {dagData.total_nodes} nodes &middot; {dagData.total_edges} edges
            </span>
          )}
        </div>

        {/* DAG Error */}
        {dagError && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 mb-4">
            <p className="text-red-700 font-medium text-sm">DAG Error</p>
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

        {/* DAG Graph */}
        {dagData && !dagLoading && <DAGGraph dag={dagData} />}
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
          <p className="text-red-700 font-medium text-sm">Simulation Error</p>
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
                    const effectColor = isReduction ? "text-green-700" : "text-red-700";
                    const effectBg = isReduction ? "bg-green-500/5" : "bg-red-500/5";
                    const isSignificant = sc.p_value < 0.05;

                    return (
                      <tr key={i} className={`border-b border-border/50 ${effectBg}`}>
                        <td className="py-2.5 px-3 font-medium text-foreground">
                          <div className="flex items-center gap-2">
                            {formatVarName(sc.intervention_type)}
                            {isSignificant && (
                              <span title="Statistically significant (p &lt; 0.05)"><ShieldCheck className="w-3.5 h-3.5 text-green-700" /></span>
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
              const borderColor = isReduction ? "border-green-600/30" : "border-red-600/30";
              const textColor = isReduction ? "text-green-700" : "text-red-700";

              return (
                <div key={`card-${i}`} className={`bg-card rounded-lg border ${borderColor} p-4 text-center`}>
                  <p className="text-xs text-muted-foreground mb-1 truncate">
                    {formatVarName(sc.intervention_type)}
                  </p>
                  <p className={`text-lg font-bold font-mono ${textColor}`}>
                    {sc.relative_change_pct > 0 ? "+" : ""}{sc.relative_change_pct.toFixed(1)}%
                  </p>
                  <div className="flex items-center justify-center gap-1 mt-1">
                    {isReduction && <TrendingDown className="w-3 h-3 text-green-700" />}
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
