"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
                ? "font-serif text-[1.06em] font-semibold italic tracking-normal text-emerald-100"
                : "tracking-normal text-emerald-100"
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
  const [visibleCount, setVisibleCount] = useState(0);
  const [actionNodes, setActionNodes] = useState<VisualNode[]>([]);
  const seenActionsRef = useRef<Set<string>>(new Set());
  const scrollPaneRef = useRef<HTMLDivElement | null>(null);

  const incomingActions = useMemo(
    () => [...(whiteboard?.actions || []), ...whiteboardActions],
    [whiteboard?.actions, whiteboardActions],
  );
  const hasActionProblem = useMemo(
    () =>
      incomingActions.some((action) =>
        String(action?.content || action?.expression || action?.label || "")
          .trim()
          .toLowerCase()
          .startsWith("problem:"),
      ),
    [incomingActions],
  );

  const boardSteps = useMemo(
    () =>
      steps.length
        ? steps
        : [
            ...(whiteboard?.solution_steps || []),
            ...(whiteboard?.equations || []),
            ...(whiteboard?.chalk_lines || []),
          ],
    [steps, whiteboard],
  );

  const boardSignature = `${whiteboard?.title || ""}|${whiteboard?.problem || ""}|${boardSteps.join("|")}`;

  useEffect(() => {
    seenActionsRef.current = new Set();
    setActionNodes([]);
    if (scrollPaneRef.current) {
      scrollPaneRef.current.scrollTop = 0;
    }
  }, [boardSignature]);

  useEffect(() => {
    if (!incomingActions.length) return;

    const nextNodes: VisualNode[] = [];
    const seenProblemContents = new Set(
      actionNodes
        .filter((node) => node.kind === "problem")
        .map((node) => node.content.trim().toLowerCase()),
    );
    incomingActions.forEach((action, index) => {
      const signature = `${index}:${JSON.stringify(action)}`;
      if (seenActionsRef.current.has(signature)) return;
      seenActionsRef.current.add(signature);
      const scoreUpdate = scoreFromAction(action);
      if (scoreUpdate) {
        onScoreUpdate?.(scoreUpdate);
        return;
      }
      const node = actionToNode(action, index);
      if (node) {
        if (node.kind === "problem") {
          const key = node.content.trim().toLowerCase();
          if (seenProblemContents.has(key)) return;
          seenProblemContents.add(key);
        }
        nextNodes.push(node);
      }
    });

    if (nextNodes.length) {
      setActionNodes((current) => [...current, ...nextNodes]);
    }
  }, [actionNodes, incomingActions, onScoreUpdate]);

  useEffect(() => {
    if (visibleStepCount !== undefined) return;

    setVisibleCount(0);
    if (!boardSteps.length) return;

    const timers = boardSteps.map((step, index) =>
      renderStepWithVoice(step, delayMs * index, () => {
        setVisibleCount((count) => Math.max(count, index + 1));
      }),
    );

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [boardSteps, delayMs, visibleStepCount]);

  const renderedCount = steps.length ? steps.length : visibleStepCount ?? visibleCount;
  const modeLabel = whiteboard?.mode ? whiteboard.mode.replace(/_/g, " ") : "Live board";

  const baseNodes = useMemo<VisualNode[]>(() => {
    const nodes: VisualNode[] = [];
    if (whiteboard?.problem && !hasActionProblem) {
      nodes.push({
        id: "problem",
        kind: "problem",
        label: "Problem",
        content: whiteboard.problem,
      });
    }

    boardSteps.slice(0, renderedCount).forEach((step, index) => {
      nodes.push({
        id: `step-${index}-${step}`,
        kind: isMathLike(step) ? "equation" : "step",
        label: `Step ${index + 1}`,
        content: step,
      });
    });

    if (whiteboard?.answer && renderedCount >= boardSteps.length) {
      nodes.push({
        id: "answer",
        kind: "answer",
        label: "Answer check",
        content: whiteboard.answer,
      });
    }

    return nodes;
  }, [boardSteps, hasActionProblem, renderedCount, whiteboard?.answer, whiteboard?.problem]);

  const visualNodes = useMemo(() => {
    const merged = [...baseNodes, ...actionNodes];
    const problems = merged.filter((node) => node.kind === "problem");
    const others = merged.filter((node) => node.kind !== "problem");
    return [...problems, ...others];
  }, [baseNodes, actionNodes]);

  return (
    <section className="flex h-full min-h-[540px] flex-col overflow-hidden rounded-lg border border-slate-700 bg-slate-950 shadow-2xl">
      <div className="flex items-center justify-between border-b border-slate-700 bg-slate-900 px-5 py-4">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold tracking-normal text-slate-50">{whiteboard?.title || "Smart Blackboard"}</h2>
          {whiteboard?.subtitle && <p className="mt-1 truncate text-sm tracking-normal text-slate-400">{whiteboard.subtitle}</p>}
        </div>
        <span className="shrink-0 rounded-md border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold capitalize tracking-normal text-emerald-200">
          {modeLabel}
        </span>
      </div>

      <div
        ref={scrollPaneRef}
        className="relative flex-1 overflow-auto bg-slate-900 p-5"
        style={{
          backgroundImage:
            "linear-gradient(rgba(148, 163, 184, 0.09) 1px, transparent 1px), linear-gradient(90deg, rgba(148, 163, 184, 0.09) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      >
        <div className="min-h-[760px] min-w-[760px] pb-24 pr-20">
          {visualNodes.length ? (
            <div className="relative space-y-5">
              {visualNodes.map((node, index) => (
                <div key={node.id} className="relative flex items-start gap-4">
                  <div className="relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full border border-slate-300/40 bg-slate-950 text-xs font-semibold text-slate-100">
                    {index + 1}
                  </div>
                  {index < visualNodes.length - 1 && <div className="absolute left-4 top-8 h-[calc(100%+1.25rem)] w-px bg-slate-400/30" />}
                  <div
                    className={`max-w-3xl rounded-lg border px-5 py-4 shadow-lg backdrop-blur-sm ${
                      nodeTone(node.kind)
                    } ${
                      activeStepIndex !== null && nodeStepIndex(node) === activeStepIndex
                        ? "ring-2 ring-emerald-300 shadow-[0_0_0_1px_rgba(16,185,129,0.75)]"
                        : ""
                    }`}
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">{node.label}</p>
                    <p
                      className={`mt-2 tracking-normal ${
                        node.kind === "problem"
                          ? "text-2xl font-bold leading-9 text-emerald-200"
                          : "text-xl leading-9 text-emerald-100"
                      }`}
                    >
                      <MathText forceMath={node.kind === "equation" || node.kind === "answer"}>{node.content}</MathText>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid h-full min-h-96 place-items-center">
              <div className="rounded-lg border border-dashed border-slate-500/60 bg-slate-950/70 px-6 py-5 text-sm font-medium tracking-normal text-slate-300">
                Waiting for Arvind Sir to write on the board...
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
