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
      if (lower.startsWith("chapter no:")) model.chapterNo = line.split(":", 2)[1]?.trim() || "-";
      else if (lower.startsWith("chapter name:")) model.chapterName = line.split(":", 2)[1]?.trim() || "-";
      else if (lower.startsWith("topic name:")) model.topicName = line.split(":", 2)[1]?.trim() || "-";
      else if (lower.startsWith("exercise no:")) model.exerciseNo = line.split(":", 2)[1]?.trim() || "-";
      else if (lower.startsWith("problem no:")) model.problemNo = line.split(":", 2)[1]?.trim() || "-";
      else if (lower.startsWith("problem statement:")) model.problemStatement = line.split(":", 2)[1]?.trim() || "-";
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

      <div ref={scrollPaneRef} className="relative flex-1 overflow-auto bg-slate-900 p-5">
        <div className="mx-auto max-w-4xl rounded-lg border-4 border-slate-700 bg-slate-950 p-4">
          <div className="grid grid-cols-2 gap-3 text-sm text-slate-200 md:grid-cols-3">
            <p><span className="font-semibold">Chapter no:</span> {boardModel.chapterNo}</p>
            <p><span className="font-semibold">Chapter name:</span> {boardModel.chapterName}</p>
            <p><span className="font-semibold">Topic name:</span> {boardModel.topicName}</p>
            <p className="md:col-span-3"><span className="font-semibold">Exercise no:</span> {boardModel.exerciseNo}</p>
          </div>

          <div className="mt-4 rounded-md border-2 border-slate-600 bg-slate-900 p-4">
            <p className="text-xl font-bold text-emerald-300">
              Problem no: {boardModel.problemNo} : "{boardModel.problemStatement}"
            </p>

            <p className="mt-4 text-base font-bold text-white">Solution</p>
            {boardModel.solutionSteps.length ? (
              <div className="mt-2 space-y-2">
                {boardModel.solutionSteps.map((step, index) => {
                  const stepIndex = nodeStepIndex({ id: `s-${index}`, kind: "step", label: step, content: step });
                  return (
                    <p
                      key={`${step}-${index}`}
                      className={`rounded px-2 py-1 text-lg text-emerald-100 ${
                        activeStepIndex !== null && stepIndex === activeStepIndex ? "ring-2 ring-emerald-300" : ""
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
        </div>
      </div>
    </section>
  );
}
