"use client";

import { useEffect, useMemo, useRef } from "react";
import type { WhiteboardAction, WhiteboardState } from "../services/api";

type VisualNode = {
  id: string;
  kind: "problem" | "step" | "equation" | "text" | "shape" | "graph" | "answer";
  label: string;
  content: string;
};

type Props = {
  steps: string[];
  whiteboard?: WhiteboardState | null;
  whiteboardActions?: WhiteboardAction[];
  delayMs?: number;
  visibleStepCount?: number;
  activeStepIndex?: number | null;
  onScoreUpdate?: (update: { score: number; correct: number; wrong: number }) => void;
};

export function renderStepWithVoice(step: string, delay: number, onRender: () => void) {
  return window.setTimeout(onRender, Math.max(0, delay + step.length * 12));
}

export function addStep(steps: string[], step: string) {
  return step && !steps.includes(step) ? [...steps, step] : steps;
}

function stripMathDelimiters(value: string) {
  return value
    .replace(/^\$\$?|\$\$?$/g, "")
    .replace(/^\\\(|\\\)$/g, "")
    .replace(/^\\\[|\\\]$/g, "");
}

function toSuperscript(value: string) {
  const map: Record<string, string> = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "+": "⁺",
    "-": "⁻",
    n: "ⁿ",
  };
  return value
    .split("")
    .map((char) => map[char] || char)
    .join("");
}

function formatLatex(value: string) {
  return stripMathDelimiters(value)
    .replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, "($1)/($2)")
    .replace(/\\sqrt\{([^{}]+)\}/g, "√($1)")
    .replace(/\\left|\\right/g, "")
    .replace(/\\cdot/g, "·")
    .replace(/\\times/g, "×")
    .replace(/\\div/g, "÷")
    .replace(/\\pm/g, "±")
    .replace(/\\theta/g, "θ")
    .replace(/\\alpha/g, "α")
    .replace(/\\beta/g, "β")
    .replace(/\\pi/g, "π")
    .replace(/\^\{([^{}]+)\}/g, (_, power: string) => toSuperscript(power))
    .replace(/\^([0-9n+-])/g, (_, power: string) => toSuperscript(power))
    .replace(/_\{([^{}]+)\}/g, "[$1]")
    .replace(/_([A-Za-z0-9])/g, "[$1]")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function actionTextValue(action: WhiteboardAction) {
  return String(
    action.content ||
      action.expression ||
      action.label ||
      action.text ||
      action.value ||
      action.message ||
      "",
  ).trim();
}

function valueAfterColon(value: string) {
  const text = String(value || "");
  const index = text.indexOf(":");
  return index >= 0 ? text.slice(index + 1).trim() : text.trim();
}

function renderImageFigure(action: WhiteboardAction) {
  const raw = String(action.base64 || action.content || "").trim();
  if (!raw) return null;
  const src = raw.startsWith("data:") ? raw : `data:image/png;base64,${raw}`;
  return (
    <div className="flex h-72 items-center justify-center rounded-md border border-slate-700 bg-slate-800 p-2">
      <img src={src} alt="Problem figure" className="max-h-full max-w-full object-contain" />
    </div>
  );
}

function isDiagramInstructionText(value: string) {
  const lower = String(value || "").trim().toLowerCase();
  return (
    lower.startsWith("diagram:") ||
    lower.startsWith("figure:") ||
    lower.startsWith("figure/diagram:")
  );
}

function isShortDiagramLabel(value: string) {
  const text = String(value || "").trim();
  if (!text) return false;
  const lower = text.toLowerCase();
  if (
    lower.startsWith("what is given:") ||
    lower.startsWith("what needs to be found:") ||
    lower.startsWith("figure/diagram:") ||
    lower.startsWith("figure hint:") ||
    lower.startsWith("diagram:") ||
    lower.startsWith("solution:") ||
    lower.startsWith("chapter") ||
    lower.startsWith("topic") ||
    lower.startsWith("exercise") ||
    lower.startsWith("problem statement:") ||
    lower.startsWith("problem no:") ||
    lower.startsWith("source:")
  ) {
    return false;
  }
  if (/^step\s+\d+/i.test(text)) return false;
  if (/^source:/i.test(text)) return false;
  if (text.length <= 20) return true;
  return /^[A-Za-z0-9()\-_=]{1,24}$/.test(text);
}

function isDrawingStepLine(value: string) {
  return /(draw|mark|join|label|construct|figure|diagram|tangent|chord|radius|point|common factor|common prime|hcf|gcd)/i.test(String(value || ""));
}

function startsWithAny(value: string, prefixes: string[]) {
  const lower = String(value || "").trim().toLowerCase();
  return prefixes.some((prefix) => lower.startsWith(prefix));
}

function toFiniteNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function diagramStroke(value: string | undefined, fallback: string) {
  const color = String(value || "").trim().toLowerCase();
  if (!color) return fallback;
  if (color.includes("green")) return "#34d399";
  if (color.includes("blue") || color.includes("sky")) return "#60a5fa";
  if (color.includes("red")) return "#f87171";
  if (color.includes("orange")) return "#fb923c";
  if (color.includes("pink") || color.includes("violet") || color.includes("purple")) return "#e879f9";
  if (color.includes("yellow")) return "#facc15";
  if (color.includes("black")) return "#e2e8f0";
  return fallback;
}

function isDiagramTagged(action: WhiteboardAction) {
  if (!action.metadata || typeof action.metadata !== "object") return false;
  return Boolean((action.metadata as Record<string, unknown>).diagram);
}

function diagramPhase(action: WhiteboardAction, fallbackOrder: number) {
  if (!action.metadata || typeof action.metadata !== "object") return fallbackOrder;
  const raw = (action.metadata as Record<string, unknown>).diagram_phase;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallbackOrder;
}

function diagramStep(action: WhiteboardAction) {
  if (!action.metadata || typeof action.metadata !== "object") return null;
  const raw = (action.metadata as Record<string, unknown>).diagram_step;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function renderSVGFromPrimitives(
  primitiveActions: WhiteboardAction[],
  stepLines: string[],
  activeStepIndex: number | null,
) {
  if (!primitiveActions.length) {
    return (
      <svg viewBox="0 0 260 170" className="w-full h-40 bg-slate-800 rounded-md border border-slate-700" />
    );
  }

  const orderedActions = [...primitiveActions].sort((a, b) => diagramPhase(a, 0) - diagramPhase(b, 0));
  const lines = stepLines.filter((line) => String(line || "").trim());
  const clampedIndex =
    activeStepIndex !== null && lines.length
      ? Math.max(0, Math.min(lines.length - 1, activeStepIndex))
      : null;
  const currentStepNumber = (() => {
    if (clampedIndex === null) return null;
    const line = String(lines[clampedIndex] || "").trim();
    const match = /^step\s+(\d+)/i.exec(line);
    if (match) return Number(match[1]);
    return clampedIndex + 1;
  })();

  const hasStepMappedPrimitives = orderedActions.some((action) => diagramStep(action) !== null);
  let visibleActions: WhiteboardAction[] = [];
  if (hasStepMappedPrimitives && currentStepNumber !== null) {
    visibleActions = orderedActions.filter((action) => {
      const mappedStep = diagramStep(action);
      return mappedStep === null || mappedStep <= currentStepNumber;
    });
  }

  if (hasStepMappedPrimitives && currentStepNumber === null) {
    visibleActions = orderedActions;
  }

  if (!hasStepMappedPrimitives) {
  let progress = 1;
  if (clampedIndex !== null) {
    const drawingLines = lines.filter((line) => isDrawingStepLine(line));
    if (drawingLines.length) {
      const covered = lines.slice(0, clampedIndex + 1).filter((line) => isDrawingStepLine(line)).length;
      progress = Math.max(0.18, Math.min(1, covered / drawingLines.length));
    } else if (lines.length) {
      progress = Math.max(0.18, Math.min(1, (clampedIndex + 1) / lines.length));
    }
  }

  const visibleCount = Math.max(1, Math.ceil(orderedActions.length * progress));
    visibleActions = orderedActions.slice(0, visibleCount);
  }

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  const touch = (x: number, y: number) => {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  };

  visibleActions.forEach((action) => {
    const name = String(action.action || "").toLowerCase();
    if (name === "draw_line") {
      touch(toFiniteNumber(action.x1), toFiniteNumber(action.y1));
      touch(toFiniteNumber(action.x2), toFiniteNumber(action.y2));
      return;
    }
    if (name === "draw_angle") {
      const x = toFiniteNumber(action.x);
      const y = toFiniteNumber(action.y);
      const r = Math.max(1, toFiniteNumber(action.radius, 1));
      touch(x - r, y - r);
      touch(x + r, y + r);
      return;
    }
    if (name === "draw_circle") {
      const x = toFiniteNumber(action.x);
      const y = toFiniteNumber(action.y);
      const r = Math.max(1, toFiniteNumber(action.radius, 1));
      touch(x - r, y - r);
      touch(x + r, y + r);
      return;
    }
    if (name === "highlight_element") {
      touch(toFiniteNumber(action.x1), toFiniteNumber(action.y1));
      touch(toFiniteNumber(action.x2), toFiniteNumber(action.y2));
      return;
    }
    if (name === "write_text") {
      const label = String(action.label || "");
      if (isShortDiagramLabel(label) || isDiagramTagged(action)) {
        touch(toFiniteNumber(action.x), toFiniteNumber(action.y));
      }
    }
  });

  if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) {
    minX = 0;
    minY = 0;
    maxX = 260;
    maxY = 170;
  }

  const width = 260;
  const height = 170;
  const padding = 14;
  const spanX = Math.max(1, maxX - minX);
  const spanY = Math.max(1, maxY - minY);
  const scale = Math.min((width - padding * 2) / spanX, (height - padding * 2) / spanY);
  const offsetX = padding - minX * scale + ((width - padding * 2) - spanX * scale) / 2;
  const offsetY = padding - minY * scale + ((height - padding * 2) - spanY * scale) / 2;
  const sx = (x: number) => x * scale + offsetX;
  const sy = (y: number) => y * scale + offsetY;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-72 bg-slate-800 rounded-md border border-slate-700">
      {visibleActions.map((action, index) => {
        const name = String(action.action || "").toLowerCase();
        if (name === "highlight_element") {
          const x1 = sx(toFiniteNumber(action.x1));
          const y1 = sy(toFiniteNumber(action.y1));
          const x2 = sx(toFiniteNumber(action.x2));
          const y2 = sy(toFiniteNumber(action.y2));
          const left = Math.min(x1, x2);
          const top = Math.min(y1, y2);
          const w = Math.max(1, Math.abs(x2 - x1));
          const h = Math.max(1, Math.abs(y2 - y1));
          return (
            <rect
              key={`diagram-highlight-${index}`}
              x={left}
              y={top}
              width={w}
              height={h}
              fill={diagramStroke(action.color, "#94a3b8")}
              opacity={toFiniteNumber(action.opacity, 0.32)}
              rx={2}
            />
          );
        }

        if (name === "draw_line") {
          const x1 = sx(toFiniteNumber(action.x1));
          const y1 = sy(toFiniteNumber(action.y1));
          const x2 = sx(toFiniteNumber(action.x2));
          const y2 = sy(toFiniteNumber(action.y2));
          const stroke = diagramStroke(action.color, "#93c5fd");
          const thickness = Math.max(1, toFiniteNumber(action.thickness, 2));
          const lineLabel = String(action.label || "").trim();
          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2;
          return (
            <g key={`diagram-line-${index}`}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={stroke} strokeWidth={thickness} />
              {isShortDiagramLabel(lineLabel) ? (
                <text x={midX + 4} y={midY - 4} fill="#cbd5e1" fontSize="10" fontWeight={600}>
                  {lineLabel}
                </text>
              ) : null}
            </g>
          );
        }

        if (name === "draw_angle") {
          const cx = toFiniteNumber(action.x);
          const cy = toFiniteNumber(action.y);
          const radius = Math.max(1, toFiniteNumber(action.radius, 1));
          const start = (toFiniteNumber(action.start_angle) * Math.PI) / 180;
          const end = (toFiniteNumber(action.end_angle) * Math.PI) / 180;
          const px1 = sx(cx + radius * Math.cos(start));
          const py1 = sy(cy - radius * Math.sin(start));
          const px2 = sx(cx + radius * Math.cos(end));
          const py2 = sy(cy - radius * Math.sin(end));
          const largeArc = Math.abs(end - start) > Math.PI ? 1 : 0;
          const sweepFlag = end >= start ? 0 : 1;
          const angleLabel = String(action.label || "").trim();
          return (
            <g key={`diagram-angle-${index}`}>
              <path
                d={`M ${px1} ${py1} A ${radius * scale} ${radius * scale} 0 ${largeArc} ${sweepFlag} ${px2} ${py2}`}
                fill="none"
                stroke={diagramStroke(action.color, "#fbbf24")}
                strokeWidth={1.5}
              />
              {isShortDiagramLabel(angleLabel) ? (
                <text x={sx(cx)} y={sy(cy)} fill="#fef3c7" fontSize="10" fontWeight={600}>
                  {angleLabel}
                </text>
              ) : null}
            </g>
          );
        }

        if (name === "draw_circle") {
          const cx = sx(toFiniteNumber(action.x));
          const cy = sy(toFiniteNumber(action.y));
          const r = Math.max(1, toFiniteNumber(action.radius, 1)) * scale;
          const stroke = diagramStroke(action.color, "#f472b6");
          const thickness = Math.max(1, toFiniteNumber(action.thickness, 2));
          const circleLabel = String(action.label || "").trim();
          return (
            <g key={`diagram-circle-${index}`}>
              <circle cx={cx} cy={cy} r={r} stroke={stroke} strokeWidth={thickness} fill="none" />
              {isShortDiagramLabel(circleLabel) ? (
                <text x={cx + r + 4} y={cy} fill="#cbd5e1" fontSize="10" fontWeight={600}>
                  {circleLabel}
                </text>
              ) : null}
            </g>
          );
        }

        if (name === "write_text") {
          const label = String(action.label || "").trim();
          if (!isShortDiagramLabel(label) && !isDiagramTagged(action)) return null;
          return (
            <text
              key={`diagram-text-${index}`}
              x={sx(toFiniteNumber(action.x))}
              y={sy(toFiniteNumber(action.y))}
              fill={diagramStroke(action.color, "#e2e8f0")}
              fontSize={Math.max(9, Math.min(13, toFiniteNumber(action.font_size, 11)))}
              fontWeight={650}
            >
              {label}
            </text>
          );
        }

        return null;
      })}
    </svg>
  );
}

function renderSVGForHint(hint: string) {
  const text = String(hint || "").toLowerCase();
  if (!text.trim()) {
    return (
      <svg viewBox="0 0 200 120" className="w-full h-72 bg-slate-800 rounded-md border border-slate-700">
        <line x1="20" y1="100" x2="180" y2="100" stroke="#94f3c7" strokeWidth="1" />
        <line x1="20" y1="100" x2="20" y2="10" stroke="#94f3c7" strokeWidth="1" />
      </svg>
    );
  }

  // Handle algebraic split hints like "a = bq + r" or "split dividend into quotient-part plus remainder"
  if (text.includes("a = bq") || text.includes("a = bq + r") || text.includes("split dividend") || (text.includes("quotient") && text.includes("remainder"))) {
    // Visualize a dividend split into quotient-part and remainder as a bar graph
    return (
      <svg viewBox="0 0 300 80" className="w-full h-72 bg-slate-800 rounded-md border border-slate-700">
        <rect x="16" y="20" width="268" height="28" rx="4" fill="#0f172a" stroke="#334155" />
        {/* quotient part (left) - 70% */}
        <rect x="18" y="22" width="188" height="24" rx="3" fill="#60a5fa" />
        {/* remainder part (right) - 30% */}
        <rect x="206" y="22" width="80" height="24" rx="3" fill="#f97316" />
        <text x="30" y="18" fill="#9ae6b4" fontSize="11" fontFamily="monospace">Quotient part (b × q)</text>
        <text x="212" y="18" fill="#ffd7b5" fontSize="11" fontFamily="monospace">Remainder (r)</text>
        <text x="150" y="64" fill="#cbd5e1" fontSize="12" fontFamily="monospace" textAnchor="middle">a = bq + r (visual split)</text>
      </svg>
    );
  }

  // Simple primitives: axes, circle, triangle, line, parabola
  if (text.includes("axis") || text.includes("axes") || text.includes("coordinate") || text.includes("graph")) {
    return (
      <svg viewBox="0 0 200 120" className="w-full h-72 bg-slate-800 rounded-md border border-slate-700">
        <g transform="translate(0,0)">
          <line x1="20" y1="100" x2="180" y2="100" stroke="#94f3c7" strokeWidth="1" />
          <line x1="20" y1="100" x2="20" y2="10" stroke="#94f3c7" strokeWidth="1" />
          {/* sample parabola */}
          <path d="M20 90 C60 30, 120 30, 180 50" stroke="#60a5fa" strokeWidth="2" fill="none" />
        </g>
      </svg>
    );
  }
  if (text.includes("circle") && text.includes("tangent")) {
    return (
      <svg viewBox="0 0 220 140" className="w-full h-72 bg-slate-800 rounded-md border border-slate-700">
        <circle cx="95" cy="70" r="34" stroke="#f472b6" strokeWidth="2" fill="none" />
        <line x1="155" y1="70" x2="130" y2="44" stroke="#60a5fa" strokeWidth="2" />
        <line x1="155" y1="70" x2="130" y2="96" stroke="#60a5fa" strokeWidth="2" />
        <line x1="95" y1="70" x2="155" y2="70" stroke="#9ae6b4" strokeWidth="1.5" />
        <line x1="95" y1="70" x2="130" y2="44" stroke="#9ae6b4" strokeWidth="1.5" />
        <line x1="95" y1="70" x2="130" y2="96" stroke="#9ae6b4" strokeWidth="1.5" />
        <line x1="130" y1="44" x2="130" y2="96" stroke="#f59e0b" strokeWidth="1.5" />
        <text x="88" y="66" fill="#e2e8f0" fontSize="10" fontWeight={700}>O</text>
        <text x="160" y="68" fill="#e2e8f0" fontSize="10" fontWeight={700}>A</text>
        <text x="133" y="40" fill="#e2e8f0" fontSize="10" fontWeight={700}>P</text>
        <text x="133" y="108" fill="#e2e8f0" fontSize="10" fontWeight={700}>Q</text>
      </svg>
    );
  }
  if (text.includes("circle") || text.includes("circ")) {
    return (
      <svg viewBox="0 0 200 120" className="w-full h-72 bg-slate-800 rounded-md border border-slate-700">
        <circle cx="100" cy="60" r="36" stroke="#f472b6" strokeWidth="2" fill="none" />
        <line x1="100" y1="60" x2="136" y2="60" stroke="#f472b6" strokeWidth="1" />
      </svg>
    );
  }
  if (text.includes("triangle") || /\bconstruct(ion)?\b/.test(text)) {
    return (
      <svg viewBox="0 0 200 120" className="w-full h-72 bg-slate-800 rounded-md border border-slate-700">
        <polygon points="40,90 160,90 100,20" stroke="#f97316" strokeWidth="2" fill="none" />
      </svg>
    );
  }
  // fallback: show hint text inside a box
  return (
    <div className="w-full h-72 rounded-md border border-slate-700 bg-slate-800 p-3 text-sm text-slate-300">{hint}</div>
  );
}

function isMathLike(value: string) {
  return /[=^_\\]|x²|√|π|θ|α|β/.test(value);
}

function MathText({ children, forceMath = false }: { children: string; forceMath?: boolean }) {
  const source = children || "";
  const parts = source.split(/(\$\$?[\s\S]+?\$\$?|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\])/g).filter(Boolean);

  if (!parts.length) return null;

  return (
    <>
      {parts.map((part, index) => {
        const math = forceMath || /^\$\$?|^\\\(|^\\\[/.test(part) || isMathLike(part);
        return (
          <span
            key={`${part}-${index}`}
            className={
              math
                ? "font-serif text-[1.06em] font-semibold italic tracking-normal text-inherit"
                : "tracking-normal text-inherit"
            }
          >
            {math ? formatLatex(part) : part}
          </span>
        );
      })}
    </>
  );
}

function actionToNode(action: WhiteboardAction, index: number): VisualNode | null {
  const actionName = (action.action || "").toLowerCase();
  const content =
    action.content ||
    action.expression ||
    action.label ||
    (action as WhiteboardAction & { text?: string; value?: string; message?: string }).text ||
    (action as WhiteboardAction & { text?: string; value?: string; message?: string }).value ||
    (action as WhiteboardAction & { text?: string; value?: string; message?: string }).message ||
    "";
  const label = action.action.replace(/_/g, " ");

  if (["clear", "clear_board", "erase", "reset_board"].includes(actionName)) {
    return null;
  }

  if (["draw_text", "write", "write_text", "add_text", "text"].includes(actionName)) {
    if (!content) return null;
    const isProblemLine = String(content).trim().toLowerCase().startsWith("problem:");
    return {
      id: `action-${index}-${action.action}-${content}`,
      kind: isProblemLine ? "problem" : isMathLike(content) ? "equation" : "text",
      label: isProblemLine ? "Problem" : "Tutor note",
      content,
    };
  }

  if (actionName === "write_equation") {
    if (!content) return null;
    return {
      id: `action-${index}-${action.action}-${content}`,
      kind: "equation",
      label: "Equation",
      content,
    };
  }

  if (["draw_coordinate_axes", "plot_curve"].includes(actionName)) {
    return {
      id: `action-${index}-${action.action}-${content}`,
      kind: "graph",
      label,
      content: content || "Graph element added",
    };
  }

  if (!content) return null;

  return {
    id: `action-${index}-${action.action}-${content}`,
    kind: "shape",
    label,
    content,
  };
}

function scoreFromAction(action: WhiteboardAction) {
  if (action.action !== "update_score") return null;
  const toNumber = (value: unknown) => {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  return {
    score: toNumber(action.score),
    correct: toNumber(action.correct),
    wrong: toNumber(action.wrong),
  };
}

function nodeTone(kind: VisualNode["kind"]) {
  if (kind === "problem") return "border-amber-200/40 bg-amber-200/10";
  if (kind === "equation") return "border-cyan-200/40 bg-cyan-200/10";
  if (kind === "answer") return "border-emerald-200/40 bg-emerald-200/10";
  if (kind === "shape" || kind === "graph") return "border-violet-200/40 bg-violet-200/10";
  return "border-slate-100/25 bg-slate-100/10";
}

function nodeStepIndex(node: VisualNode): number | null {
  const fromLabel = /step\s+(\d+)/i.exec(node.label || "");
  if (fromLabel) return Math.max(0, Number(fromLabel[1]) - 1);
  const fromContent = /^step\s+(\d+)/i.exec((node.content || "").trim());
  if (fromContent) return Math.max(0, Number(fromContent[1]) - 1);
  return null;
}

export function Whiteboard({
  steps,
  whiteboard,
  whiteboardActions = [],
  delayMs = 950,
  visibleStepCount,
  activeStepIndex = null,
  onScoreUpdate,
}: Props) {
  const scrollPaneRef = useRef<HTMLDivElement | null>(null);

  const incomingActions = useMemo(
    () => (whiteboardActions.length ? whiteboardActions : whiteboard?.actions || []),
    [whiteboard?.actions, whiteboardActions],
  );
  const boardSignature = `${whiteboard?.title || ""}|${whiteboard?.problem || ""}|${JSON.stringify(incomingActions)}`;

  useEffect(() => {
    if (scrollPaneRef.current) {
      scrollPaneRef.current.scrollTop = 0;
    }
  }, [boardSignature]);

  const modeLabel = whiteboard?.mode ? whiteboard.mode.replace(/_/g, " ") : "Live board";

  const boardModel = useMemo(() => {
    const model = {
      chapterNo: "-",
      chapterName: "-",
      topicName: "-",
      exerciseNo: "-",
      problemNo: "-",
      problemStatement: "-",
      solutionSteps: [] as string[],
      finalAnswer: "",
    };

    const lastClearIndex = incomingActions.reduce((last, action, index) => {
      const name = String(action?.action || "").toLowerCase();
      return ["clear", "clear_board", "erase", "reset_board"].includes(name) ? index : last;
    }, -1);
    const currentActions = lastClearIndex >= 0 ? incomingActions.slice(lastClearIndex + 1) : incomingActions;
    const lines = currentActions
      .map((action) => {
        const scoreUpdate = scoreFromAction(action);
        if (scoreUpdate) onScoreUpdate?.(scoreUpdate);
        const content =
          action.content ||
          action.expression ||
          action.label ||
          (action as WhiteboardAction & { text?: string; value?: string; message?: string }).text ||
          (action as WhiteboardAction & { text?: string; value?: string; message?: string }).value ||
          (action as WhiteboardAction & { text?: string; value?: string; message?: string }).message ||
          "";
        return String(content || "").trim();
      })
      .filter(Boolean);

    let currentStepBlock: string[] = [];
    let latestStepBlock: string[] = [];
    for (const line of lines) {
      const lower = line.toLowerCase();
      if (lower.startsWith("chapter no:")) model.chapterNo = valueAfterColon(line) || "-";
      else if (lower.startsWith("chapter name:")) model.chapterName = valueAfterColon(line) || "-";
      else if (lower.startsWith("chapter:")) model.chapterName = valueAfterColon(line) || "-";
      else if (lower.startsWith("topic name:")) model.topicName = valueAfterColon(line) || "-";
      else if (lower.startsWith("topic:")) model.topicName = valueAfterColon(line) || "-";
      else if (lower.startsWith("exercise no:")) model.exerciseNo = valueAfterColon(line) || "-";
      else if (lower.startsWith("problem no:")) {
        const remainder = valueAfterColon(line) || "-";
        const match = /^([^:]+):\s*(.+)$/.exec(remainder);
        if (match) {
          model.problemNo = match[1].trim() || "-";
          model.problemStatement = match[2].trim() || "-";
        } else {
          model.problemNo = remainder;
        }
      }
      else if (lower.startsWith("problem statement:")) model.problemStatement = valueAfterColon(line) || "-";
      else if (lower.startsWith("step ")) {
        const n = Number((/^step\s+(\d+)/i.exec(line)?.[1] || "0"));
        if (n === 1 && currentStepBlock.length) {
          latestStepBlock = currentStepBlock;
          currentStepBlock = [];
        }
        currentStepBlock.push(line);
      }
      else if (lower.startsWith("final answer:")) model.finalAnswer = line;
    }
    model.solutionSteps = (currentStepBlock.length ? currentStepBlock : latestStepBlock).slice(0, 14);
    return model;
  }, [incomingActions, onScoreUpdate]);

  const diagramActions = useMemo(
    () => incomingActions.filter((action) => {
      const name = String(action?.action || "").toLowerCase();
      if (["draw_shape", "draw_coordinate_axes", "plot_curve", "draw_circle", "draw_line", "draw_angle", "highlight_element"].includes(name)) return true;
      return isDiagramInstructionText(actionTextValue(action));
    }),
    [incomingActions],
  );
  const diagramImageAction = useMemo(
    () => undefined,
    [diagramActions],
  );
  const diagramHintText = useMemo(() => {
    const directHint = diagramActions
      .map((action) => actionTextValue(action))
      .find((text) => isDiagramInstructionText(text));
    if (directHint) {
      return directHint.replace(/^(Diagram|Figure)[:\s]*/i, "");
    }
    const drawShapeHint = diagramActions
      .filter((action) => String(action.action || "").toLowerCase() === "draw_shape")
      .map((action) => actionTextValue(action))
      .find((text) => Boolean(text));
    return drawShapeHint || "";
  }, [diagramActions]);
  const diagramPrimitiveActions = useMemo(() => {
    const lastClearIndex = incomingActions.reduce((last, action, index) => {
      const name = String(action?.action || "").toLowerCase();
      return ["clear", "clear_board", "erase", "reset_board"].includes(name) ? index : last;
    }, -1);
    const currentActions = lastClearIndex >= 0 ? incomingActions.slice(lastClearIndex + 1) : incomingActions;
    const primitives = currentActions.filter((action) =>
      ["draw_line", "draw_circle", "draw_angle", "highlight_element", "write_text"].includes(String(action?.action || "").toLowerCase()),
    );
    const taggedPrimitives = primitives.filter((action) => isDiagramTagged(action));
    return taggedPrimitives.length ? taggedPrimitives : primitives;
  }, [incomingActions]);
  const hasPrimitiveGeometry = useMemo(
    () =>
      diagramPrimitiveActions.some((action) =>
        ["draw_line", "draw_circle", "draw_angle", "highlight_element"].includes(String(action.action || "").toLowerCase()),
      ),
    [diagramPrimitiveActions],
  );
  const hasDiagramVisuals = diagramActions.length > 0 || hasPrimitiveGeometry;
  const conceptBoardLines = useMemo(() => {
    const lastClearIndex = incomingActions.reduce((last, action, index) => {
      const name = String(action?.action || "").toLowerCase();
      return ["clear", "clear_board", "erase", "reset_board"].includes(name) ? index : last;
    }, -1);
    const currentActions = lastClearIndex >= 0 ? incomingActions.slice(lastClearIndex + 1) : incomingActions;
    return currentActions
      .filter((action) => {
        if (isDiagramTagged(action)) return false;
        const name = String(action?.action || "").toLowerCase();
        return ["draw_text", "write", "write_text", "add_text", "text", "write_equation"].includes(name);
      })
      .map((action) =>
        String(
          action.content ||
            action.expression ||
            action.label ||
            (action as WhiteboardAction & { text?: string; value?: string; message?: string }).text ||
            (action as WhiteboardAction & { text?: string; value?: string; message?: string }).value ||
            (action as WhiteboardAction & { text?: string; value?: string; message?: string }).message ||
            "",
        ).trim(),
      )
      .filter(Boolean)
      .filter((line) =>
        !startsWithAny(line, [
          "chapter no:",
          "chapter name:",
          "chapter:",
          "topic name:",
          "topic:",
          "exercise no:",
          "problem no:",
          "solution:",
          "diagram:",
          "figure:",
          "source:",
          "board build:",
        ]),
      );
  }, [incomingActions]);
  const hasExerciseProblem =
    boardModel.exerciseNo !== "-" ||
    boardModel.problemNo !== "-" ||
    boardModel.problemStatement !== "-";
  const isConceptBoard =
    !hasExerciseProblem &&
    (String(whiteboard?.mode || "").toLowerCase() === "concept" ||
    (!boardModel.solutionSteps.length &&
      boardModel.problemNo === "-" &&
      boardModel.problemStatement === "-" &&
      conceptBoardLines.length > 0));

  return (
    <section className="flex h-full min-h-[720px] flex-col overflow-hidden rounded-lg border border-slate-700 bg-slate-950 shadow-2xl">
      <div className="flex items-center justify-between border-b border-slate-700 bg-slate-900 px-5 py-4">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold tracking-normal text-slate-50">{whiteboard?.title || "Smart Blackboard"}</h2>
          {whiteboard?.subtitle && <p className="mt-1 truncate text-sm tracking-normal text-slate-400">{whiteboard.subtitle}</p>}
        </div>
        <span className="shrink-0 rounded-md border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold capitalize tracking-normal text-emerald-200">
          {modeLabel}
        </span>
      </div>

      <div ref={scrollPaneRef} className="relative flex-1 overflow-auto bg-slate-900 p-6">
        <div className="mx-auto w-full max-w-none rounded-lg border-4 border-slate-700 bg-slate-950 p-5">
          {isConceptBoard ? (
            <div className="space-y-4">
              {hasDiagramVisuals ? (
                <div className="grid gap-3">
                  <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                    {diagramImageAction
                      ? renderImageFigure(diagramImageAction)
                      : hasPrimitiveGeometry
                        ? renderSVGFromPrimitives(diagramPrimitiveActions, conceptBoardLines, activeStepIndex)
                        : renderSVGForHint(diagramHintText)}
                    {diagramHintText ? (
                      <p className="mt-2 text-base text-slate-400">
                        <span className="font-semibold text-slate-100">Figure:</span>{" "}
                        <MathText>{diagramHintText}</MathText>
                      </p>
                    ) : null}
                  </div>
                </div>
              ) : null}

              <div className="space-y-3">
                {conceptBoardLines.map((line, index) => {
                  const lower = line.toLowerCase();
                  const isHeading =
                    lower.startsWith("chapter:") ||
                    lower.startsWith("topic:");
                  const isTheory = lower.startsWith("theory:");
                  const isProblemStatement = lower.startsWith("problem statement:") || lower.startsWith("problem:");
                  const stepIndex = nodeStepIndex({ id: `c-${index}`, kind: "step", label: line, content: line });
                  const latestStepIndex = conceptBoardLines.reduce((latest, item, itemIndex) => {
                    const candidate = nodeStepIndex({ id: `c-latest-${itemIndex}`, kind: "step", label: item, content: item });
                    return candidate !== null ? itemIndex : latest;
                  }, -1);
                  const isActive =
                    (activeStepIndex !== null && stepIndex === activeStepIndex) ||
                    (activeStepIndex === null && index === latestStepIndex);
                  return (
                    <div
                      key={`${line}-${index}`}
                      className={`rounded-md px-4 py-3 ${
                        isProblemStatement
                          ? "border border-emerald-300/40 bg-emerald-300/10 text-xl font-bold leading-9 text-emerald-100"
                          : isActive
                          ? "border border-emerald-300/70 bg-emerald-300/10 text-lg font-semibold leading-8 text-white ring-2 ring-emerald-300/70"
                          : isTheory
                          ? "border border-emerald-200/25 bg-emerald-200/10 text-xl font-bold leading-9 text-emerald-100"
                          : isHeading
                          ? "border border-emerald-200/25 bg-emerald-200/10 text-lg font-semibold leading-8 text-emerald-100"
                          : "border border-slate-700/80 bg-slate-900 text-lg leading-8 text-white"
                      }`}
                    >
                      <MathText>{line}</MathText>
                    </div>
                  );
                })}
              </div>

            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-3 text-base text-slate-200">
                <p><span className="font-semibold text-emerald-200">Exercise no:</span> {boardModel.exerciseNo}</p>
              </div>

              <div className="mt-4 rounded-md border border-slate-700 bg-slate-900 p-4">
                <p className="text-xl font-bold leading-9 text-emerald-200">
                  {boardModel.problemNo !== "-" ? `Problem no: ${boardModel.problemNo}: ` : "Problem statement: "}
                  <MathText>{boardModel.problemStatement}</MathText>
                </p>

                {hasDiagramVisuals ? (
                  <div className="mt-4 grid gap-3">
                    <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                      {diagramImageAction
                        ? renderImageFigure(diagramImageAction)
                        : hasPrimitiveGeometry
                          ? renderSVGFromPrimitives(diagramPrimitiveActions, boardModel.solutionSteps, activeStepIndex)
                          : renderSVGForHint(diagramHintText)}
                      {diagramHintText ? (
                        <p className="mt-2 text-base text-slate-400">
                          <span className="font-semibold text-slate-100">Figure hint:</span>{" "}
                          <MathText>{diagramHintText}</MathText>
                        </p>
                      ) : null}
                    </div>
                  </div>
                ) : null}

            <p className="mt-4 text-lg font-bold text-white">Solution</p>
            {boardModel.solutionSteps.length ? (
              <div className="mt-2 space-y-2">
                {boardModel.solutionSteps.map((step, index) => {
                  const stepIndex = nodeStepIndex({ id: `s-${index}`, kind: "step", label: step, content: step });
                  const isActive = activeStepIndex !== null && stepIndex === activeStepIndex;
                  return (
                    <p
                      key={`${step}-${index}`}
                      className={`rounded border px-4 py-3 text-lg leading-8 ${
                        isActive
                          ? "border-emerald-300/70 bg-emerald-300/10 text-white ring-2 ring-emerald-300/70"
                          : "border-slate-700/70 bg-slate-950/70 text-white"
                      }`}
                    >
                      <MathText>{step}</MathText>
                    </p>
                  );
                })}
              </div>
            ) : (
              <p className="mt-2 text-slate-300">Waiting for solution steps...</p>
            )}

            {boardModel.finalAnswer ? <p className="mt-4 text-lg font-semibold text-cyan-200">{boardModel.finalAnswer}</p> : null}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
