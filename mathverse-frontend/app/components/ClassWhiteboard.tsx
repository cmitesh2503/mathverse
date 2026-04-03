"use client";

import { useEffect, useMemo, useState } from "react";

export type WhiteboardPayload = {
  title?: string;
  subtitle?: string;
  chalk_lines?: string[];
  equations?: string[];
  problem?: string;
  graph?: {
    x_min: number;
    x_max: number;
    y_min: number;
    y_max: number;
    lines?: Array<{
      label?: string;
      color?: string;
      points: Array<[number, number]>;
    }>;
    points?: Array<{
      x: number;
      y: number;
      label?: string;
      color?: string;
    }>;
  };
};

type ClassWhiteboardProps = {
  isNarrating?: boolean;
  stageMode?: "default" | "focus";
  whiteboard: WhiteboardPayload | null;
};

const BOARD_WIDTH = 360;
const BOARD_HEIGHT = 250;
const PADDING = 28;
const WHITEBOARD_TYPING_STEP = 3;
const WHITEBOARD_TYPING_INTERVAL_MS = 42;

const mapPoint = (
  x: number,
  y: number,
  graph: NonNullable<WhiteboardPayload["graph"]>
) => {
  const xRange = Math.max(1, graph.x_max - graph.x_min);
  const yRange = Math.max(1, graph.y_max - graph.y_min);
  const svgX = PADDING + ((x - graph.x_min) / xRange) * (BOARD_WIDTH - PADDING * 2);
  const svgY =
    BOARD_HEIGHT - PADDING - ((y - graph.y_min) / yRange) * (BOARD_HEIGHT - PADDING * 2);
  return { x: svgX, y: svgY };
};

const countCharacters = (items: string[]) =>
  items.reduce((total, item) => total + item.length + 1, 0);

const revealSequence = (items: string[], visibleCharacters: number) => {
  let remaining = visibleCharacters;
  return items.map((item) => {
    if (remaining <= 0) {
      return "";
    }

    const next = item.slice(0, remaining);
    remaining -= item.length + 1;
    return next;
  });
};

export default function ClassWhiteboard({
  isNarrating = false,
  stageMode = "default",
  whiteboard,
}: ClassWhiteboardProps) {
  const isFocusStage = stageMode === "focus";
  const chalkLines = useMemo(() => whiteboard?.chalk_lines ?? [], [whiteboard]);
  const equations = useMemo(() => whiteboard?.equations ?? [], [whiteboard]);
  const graph = whiteboard?.graph;
  const boardSegments = useMemo(
    () => [
      whiteboard?.title || "Ava is setting up the board",
      whiteboard?.subtitle || "Graphs, equations, and quick visual notes show up here.",
      ...equations,
      ...(whiteboard?.problem ? [whiteboard.problem] : []),
      ...chalkLines,
    ],
    [chalkLines, equations, whiteboard]
  );
  const totalCharacters = useMemo(() => countCharacters(boardSegments), [boardSegments]);
  const [revealedCharacters, setRevealedCharacters] = useState(() =>
    isNarrating ? 0 : totalCharacters
  );

  useEffect(() => {
    if (!isNarrating || revealedCharacters >= totalCharacters) {
      return;
    }

    const timer = window.setTimeout(() => {
      setRevealedCharacters((current) =>
        Math.min(totalCharacters, current + WHITEBOARD_TYPING_STEP)
      );
    }, WHITEBOARD_TYPING_INTERVAL_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [isNarrating, revealedCharacters, totalCharacters]);

  const effectiveRevealedCharacters = isNarrating ? revealedCharacters : totalCharacters;
  const revealedSegments = revealSequence(boardSegments, effectiveRevealedCharacters);
  const revealedTitle = revealedSegments[0] || "Ava is setting up the board";
  const revealedSubtitle =
    revealedSegments[1] || "Graphs, equations, and quick visual notes show up here.";
  const equationStartIndex = 2;
  const problemIndex = equationStartIndex + equations.length;
  const chalkStartIndex = problemIndex + (whiteboard?.problem ? 1 : 0);
  const revealedEquations = equations
    .map((_, index) => revealedSegments[equationStartIndex + index] || "")
    .filter(Boolean);
  const revealedProblem = whiteboard?.problem ? revealedSegments[problemIndex] || "" : "";
  const revealedChalkLines = chalkLines
    .map((_, index) => revealedSegments[chalkStartIndex + index] || "")
    .filter(Boolean);
  const revealProgress =
    totalCharacters > 0 ? effectiveRevealedCharacters / totalCharacters : 1;
  const graphOpacity = Math.max(0.16, Math.min(1, (revealProgress - 0.18) / 0.82));

  return (
    <div
      className={`rounded-[1.6rem] border border-[#19463c] bg-[linear-gradient(180deg,#173d36_0%,#102a27_100%)] text-[#eff8f2] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.06),0_20px_60px_rgba(10,26,23,0.22)] ${
        isFocusStage ? "p-5 lg:p-6" : "p-4"
      }`}
    >
      <style>{`
        @keyframes chalk-pulse {
          0%, 100% { opacity: 0.55; }
          50% { opacity: 1; }
        }
        .chalk-cursor {
          animation: chalk-pulse 1s ease-in-out infinite;
        }
      `}</style>

      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-200/85">
            Classroom Whiteboard
          </div>
          <div className={`mt-2 font-semibold ${isFocusStage ? "text-[1.8rem]" : "text-xl"}`}>
            {revealedTitle}
            {isNarrating && revealProgress < 1 && <span className="chalk-cursor ml-1">|</span>}
          </div>
          <div className={`mt-1 text-emerald-100/80 ${isFocusStage ? "text-base" : "text-sm"}`}>
            {revealedSubtitle}
          </div>
        </div>
        <div className="rounded-full border border-emerald-200/25 bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-100/80">
          {isNarrating ? "Board Writing Live" : "Focus View"}
        </div>
      </div>

      <div className={`mt-4 grid gap-4 ${isFocusStage ? "xl:grid-cols-[minmax(0,1.25fr)_340px]" : "xl:grid-cols-[minmax(0,1fr)_280px]"}`}>
        <div className={`rounded-[1.3rem] border border-white/8 bg-white/4 ${isFocusStage ? "p-4" : "p-3"}`}>
          {graph ? (
            <svg
              viewBox={`0 0 ${BOARD_WIDTH} ${BOARD_HEIGHT}`}
              className={`w-full rounded-[1rem] bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.04),transparent_55%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))] ${
                isFocusStage ? "h-[380px] xl:h-[64vh]" : "h-[250px]"
              }`}
              style={{ opacity: graphOpacity, transition: "opacity 260ms ease" }}
              preserveAspectRatio="none"
            >
              {Array.from({ length: graph.x_max - graph.x_min + 1 }).map((_, index) => {
                const xValue = graph.x_min + index;
                const point = mapPoint(xValue, graph.y_min, graph);
                return (
                  <g key={`x-${xValue}`}>
                    <line
                      x1={point.x}
                      y1={PADDING}
                      x2={point.x}
                      y2={BOARD_HEIGHT - PADDING}
                      stroke="rgba(236,253,245,0.08)"
                      strokeWidth="1"
                    />
                    <text
                      x={point.x}
                      y={BOARD_HEIGHT - 8}
                      textAnchor="middle"
                      fill="rgba(236,253,245,0.72)"
                      fontSize="10"
                    >
                      {xValue}
                    </text>
                  </g>
                );
              })}
              {Array.from({ length: graph.y_max - graph.y_min + 1 }).map((_, index) => {
                const yValue = graph.y_min + index;
                const point = mapPoint(graph.x_min, yValue, graph);
                return (
                  <g key={`y-${yValue}`}>
                    <line
                      x1={PADDING}
                      y1={point.y}
                      x2={BOARD_WIDTH - PADDING}
                      y2={point.y}
                      stroke="rgba(236,253,245,0.08)"
                      strokeWidth="1"
                    />
                    <text
                      x={12}
                      y={point.y + 4}
                      textAnchor="middle"
                      fill="rgba(236,253,245,0.72)"
                      fontSize="10"
                    >
                      {yValue}
                    </text>
                  </g>
                );
              })}

              <line
                x1={PADDING}
                y1={BOARD_HEIGHT - PADDING}
                x2={BOARD_WIDTH - PADDING}
                y2={BOARD_HEIGHT - PADDING}
                stroke="rgba(254,240,138,0.9)"
                strokeWidth="1.5"
              />
              <line
                x1={PADDING}
                y1={BOARD_HEIGHT - PADDING}
                x2={PADDING}
                y2={PADDING}
                stroke="rgba(254,240,138,0.9)"
                strokeWidth="1.5"
              />

              {graph.lines?.map((line, index) => {
                const path = line.points
                  .map(([x, y], pointIndex) => {
                    const mapped = mapPoint(x, y, graph);
                    return `${pointIndex === 0 ? "M" : "L"} ${mapped.x} ${mapped.y}`;
                  })
                  .join(" ");
                return (
                  <g key={`line-${index}`}>
                    <path
                      d={path}
                      stroke={line.color || "#60a5fa"}
                      strokeWidth="3"
                      fill="none"
                      strokeLinecap="round"
                    />
                    {line.label && (
                      <text
                        x={BOARD_WIDTH - PADDING}
                        y={PADDING + index * 16}
                        textAnchor="end"
                        fill={line.color || "#60a5fa"}
                        fontSize="11"
                        fontWeight="600"
                      >
                        {line.label}
                      </text>
                    )}
                  </g>
                );
              })}

              {graph.points?.map((point, index) => {
                const mapped = mapPoint(point.x, point.y, graph);
                return (
                  <g key={`point-${index}`}>
                    <circle
                      cx={mapped.x}
                      cy={mapped.y}
                      r="5"
                      fill={point.color || "#fef08a"}
                      stroke="#08211a"
                      strokeWidth="2"
                    />
                    {point.label && (
                      <text
                        x={mapped.x + 8}
                        y={mapped.y - 8}
                        fill={point.color || "#fef08a"}
                        fontSize="11"
                        fontWeight="600"
                      >
                        {point.label}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          ) : (
            <div
              className={`flex items-center justify-center rounded-[1rem] border border-dashed border-emerald-100/15 bg-black/10 px-6 text-center text-emerald-100/72 ${
                isFocusStage ? "h-[380px] xl:h-[64vh] text-base" : "h-[250px] text-sm"
              }`}
            >
              Ava will draw equations, steps, and graphs here as the lesson moves.
            </div>
          )}
        </div>

        <div className="space-y-3">
          {equations.length > 0 && (
            <div className="rounded-[1.2rem] border border-white/10 bg-white/6 p-3">
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-200/80">
                Board Equations
              </div>
              <div className={`mt-3 space-y-2 font-mono leading-7 text-[#fef3c7] ${isFocusStage ? "text-[17px]" : "text-[15px]"}`}>
                {revealedEquations.length > 0 ? (
                  revealedEquations.map((equation) => (
                    <div key={equation} className="rounded-xl bg-black/12 px-3 py-2">
                      {equation}
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl bg-black/12 px-3 py-2 text-emerald-50/55">
                    Ava is writing the equation...
                  </div>
                )}
              </div>
            </div>
          )}

          {whiteboard?.problem && (
            <div className={`rounded-[1.2rem] border border-amber-200/18 bg-amber-50/8 p-3 text-amber-50 ${isFocusStage ? "text-[15px]" : "text-sm"}`}>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-100/80">
                Current Problem
              </div>
              <div className="mt-2 leading-6">
                {revealedProblem || "Ava is introducing the problem..."}
              </div>
            </div>
          )}

          <div className="rounded-[1.2rem] border border-white/10 bg-white/6 p-3">
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-200/80">
              Chalk Notes
            </div>
            <div className={`mt-3 space-y-2 leading-6 text-emerald-50/88 ${isFocusStage ? "text-[15px]" : "text-sm"}`}>
              {chalkLines.length > 0 ? (
                revealedChalkLines.length > 0 ? (
                  revealedChalkLines.map((line) => (
                    <div key={line} className="rounded-xl bg-black/10 px-3 py-2">
                      {line}
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl bg-black/10 px-3 py-2 text-emerald-50/55">
                    Ava is writing the first note...
                  </div>
                )
              ) : (
                <div className="rounded-xl bg-black/10 px-3 py-2">
                  Ava will add quick notes here while explaining.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
