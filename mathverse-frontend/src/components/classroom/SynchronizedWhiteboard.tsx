import type { CSSProperties } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";
import type { DrawingInstruction, LessonEvent } from "../../services/lessonTimeline";
import type { RenderedBoardEvent } from "./LessonTimeline";

type Props = {
  chapterTitle: string;
  conceptTitle: string;
  events: RenderedBoardEvent[];
  highlightedTargetId: string | null;
  isPlaying: boolean;
};

const handwritingStyle: CSSProperties = {
  fontFamily: '"Segoe Print", "Comic Sans MS", "Bradley Hand ITC", cursive',
};

function itemTone(kind: string | undefined) {
  if (kind === "heading") return "border-blue-200 bg-blue-50/70 text-blue-950";
  if (kind === "equation") return "border-emerald-200 bg-emerald-50/80 text-emerald-950";
  if (kind === "question") return "border-amber-200 bg-amber-50/90 text-amber-950";
  if (kind === "summary") return "border-violet-200 bg-violet-50/80 text-violet-950";
  if (kind === "example") return "border-cyan-200 bg-cyan-50/80 text-cyan-950";
  return "border-slate-200 bg-white text-slate-900";
}

function evaluateExpression(expression: string, x: number) {
  const normalized = expression.toLowerCase().replace(/\s+/g, "").replace(/^y=/, "");
  if (normalized.includes("x^2")) {
    const base = x * x;
    if (normalized.includes("-4")) return base - 4;
    if (normalized.includes("+1")) return base + 1;
    return base;
  }
  if (normalized.includes("2x+1")) return 2 * x + 1;
  if (normalized.includes("x+3")) return x + 3;
  if (normalized.includes("-x")) return -x;
  return x;
}

function PlotGraphic({ expression }: { expression: string }) {
  const width = 520;
  const height = 240;
  const xMin = -5;
  const xMax = 5;
  const yMin = -6;
  const yMax = 8;
  const toX = (x: number) => ((x - xMin) / (xMax - xMin)) * width;
  const toY = (y: number) => height - ((y - yMin) / (yMax - yMin)) * height;
  const points: string[] = [];

  for (let x = xMin; x <= xMax; x += 0.25) {
    const y = evaluateExpression(expression, x);
    points.push(`${toX(x).toFixed(1)},${toY(y).toFixed(1)}`);
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full" role="img" aria-label={`Plot of ${expression}`}>
      <rect width={width} height={height} rx="18" fill="#f8fafc" />
      <path d={`M ${toX(0)} 14 V ${height - 14}`} stroke="#cbd5e1" strokeWidth="2" />
      <path d={`M 14 ${toY(0)} H ${width - 14}`} stroke="#cbd5e1" strokeWidth="2" />
      {[-4, -2, 2, 4].map((tick) => (
        <g key={tick}>
          <path d={`M ${toX(tick)} ${toY(0) - 5} V ${toY(0) + 5}`} stroke="#94a3b8" strokeWidth="1.5" />
          <text x={toX(tick)} y={toY(0) + 22} textAnchor="middle" className="fill-slate-500 text-[11px]">
            {tick}
          </text>
        </g>
      ))}
      <polyline points={points.join(" ")} fill="none" stroke="#2563eb" strokeWidth="4" strokeLinecap="round" />
      <text x="18" y="28" className="fill-slate-700 text-sm font-semibold">
        {expression}
      </text>
    </svg>
  );
}

function NumberLine({ drawing }: { drawing: Extract<DrawingInstruction, { kind: "number-line" }> }) {
  const width = 560;
  const height = 170;
  const min = drawing.min;
  const max = drawing.max;
  const left = 36;
  const right = width - 36;
  const y = 82;
  const scale = (value: number) => left + ((value - min) / Math.max(1, max - min)) * (right - left);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-44 w-full" role="img" aria-label="Number line diagram">
      <rect width={width} height={height} rx="18" fill="#f8fafc" />
      <path d={`M ${left} ${y} H ${right}`} stroke="#0f172a" strokeWidth="3" strokeLinecap="round" />
      {[...Array(max - min + 1)].map((_, index) => {
        const value = min + index;
        return (
          <g key={value}>
            <path d={`M ${scale(value)} ${y - 8} V ${y + 8}`} stroke="#64748b" strokeWidth="2" />
            <text x={scale(value)} y={y + 28} textAnchor="middle" className="fill-slate-600 text-[11px]">
              {value}
            </text>
          </g>
        );
      })}
      {drawing.intervals?.map((interval) => (
        <g key={`${interval.from}-${interval.to}`}>
          <path
            d={`M ${scale(interval.from)} ${y - 34} C ${scale(interval.from) + 40} ${y - 70}, ${scale(interval.to) - 40} ${
              y - 70
            }, ${scale(interval.to)} ${y - 34}`}
            fill="none"
            stroke="#0f766e"
            strokeWidth="3"
          />
          <text x={(scale(interval.from) + scale(interval.to)) / 2} y={28} textAnchor="middle" className="fill-teal-700 text-xs font-semibold">
            {interval.label}
          </text>
        </g>
      ))}
      {drawing.points?.map((point) => {
        const fill = point.tone === "green" ? "#10b981" : point.tone === "amber" ? "#f59e0b" : "#2563eb";
        return (
          <g key={`${point.value}-${point.label}`}>
            <circle cx={scale(point.value)} cy={y} r="9" fill={fill} />
            <text x={scale(point.value)} y={y - 18} textAnchor="middle" className="fill-slate-900 text-xs font-semibold">
              {point.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function CoordinatePlane({ drawing }: { drawing: Extract<DrawingInstruction, { kind: "coordinate-plane" }> }) {
  const width = 520;
  const height = 260;
  const min = -5;
  const max = 5;
  const toX = (x: number) => ((x - min) / (max - min)) * width;
  const toY = (y: number) => height - ((y - min) / (max - min)) * height;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full" role="img" aria-label="Coordinate plane">
      <rect width={width} height={height} rx="18" fill="#f8fafc" />
      {Array.from({ length: 11 }, (_, index) => index - 5).map((tick) => (
        <g key={tick}>
          <path d={`M ${toX(tick)} 0 V ${height}`} stroke="#e2e8f0" />
          <path d={`M 0 ${toY(tick)} H ${width}`} stroke="#e2e8f0" />
        </g>
      ))}
      <path d={`M ${toX(0)} 12 V ${height - 12}`} stroke="#94a3b8" strokeWidth="2" />
      <path d={`M 12 ${toY(0)} H ${width - 12}`} stroke="#94a3b8" strokeWidth="2" />
      {drawing.segments?.map((segment, index) => (
        <g key={`${segment.from.join(",")}-${segment.to.join(",")}-${index}`}>
          <path
            d={`M ${toX(segment.from[0])} ${toY(segment.from[1])} L ${toX(segment.to[0])} ${toY(segment.to[1])}`}
            stroke="#2563eb"
            strokeWidth="4"
            strokeLinecap="round"
          />
          {segment.label && (
            <text
              x={(toX(segment.from[0]) + toX(segment.to[0])) / 2 + 10}
              y={(toY(segment.from[1]) + toY(segment.to[1])) / 2 - 10}
              className="fill-blue-700 text-xs font-semibold"
            >
              {segment.label}
            </text>
          )}
        </g>
      ))}
      {drawing.points?.map((point) => (
        <g key={`${point.x}-${point.y}-${point.label}`}>
          <circle cx={toX(point.x)} cy={toY(point.y)} r="8" fill="#0f766e" />
          <text x={toX(point.x) + 10} y={toY(point.y) - 10} className="fill-slate-900 text-xs font-semibold">
            {point.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

function GeometryFigure({ drawing }: { drawing: Extract<DrawingInstruction, { kind: "geometry" }> }) {
  return (
    <svg viewBox="0 0 520 260" className="h-64 w-full" role="img" aria-label={`${drawing.shape} figure`}>
      <rect width="520" height="260" rx="18" fill="#f8fafc" />
      {drawing.shape === "triangle" && (
        <>
          <path d="M 110 210 L 260 46 L 430 210 Z" fill="#dbeafe" stroke="#2563eb" strokeWidth="4" strokeLinejoin="round" />
          <text x="96" y="229" className="fill-slate-900 text-sm font-bold">
            {drawing.labels?.[0] || "A"}
          </text>
          <text x="255" y="36" className="fill-slate-900 text-sm font-bold">
            {drawing.labels?.[1] || "B"}
          </text>
          <text x="437" y="229" className="fill-slate-900 text-sm font-bold">
            {drawing.labels?.[2] || "C"}
          </text>
        </>
      )}
      {drawing.shape === "circle" && <circle cx="260" cy="130" r="84" fill="#dcfce7" stroke="#16a34a" strokeWidth="4" />}
      {drawing.shape === "rectangle" && <rect x="120" y="68" width="280" height="126" rx="8" fill="#fef3c7" stroke="#d97706" strokeWidth="4" />}
      {drawing.annotations?.map((annotation, index) => (
        <text key={annotation} x="34" y={36 + index * 26} className="fill-slate-700 text-sm font-semibold">
          {annotation}
        </text>
      ))}
    </svg>
  );
}

function ArrowDiagram({ drawing }: { drawing: Extract<DrawingInstruction, { kind: "arrow" }> }) {
  return (
    <svg viewBox="0 0 520 150" className="h-40 w-full" role="img" aria-label="Flow arrow diagram">
      <defs>
        <marker id="classroom-arrowhead" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563eb" />
        </marker>
      </defs>
      <rect width="520" height="150" rx="18" fill="#f8fafc" />
      <rect x="28" y="44" width="150" height="52" rx="12" fill="#dbeafe" stroke="#93c5fd" />
      <rect x="342" y="44" width="150" height="52" rx="12" fill="#dcfce7" stroke="#86efac" />
      <path d="M 190 70 H 330" stroke="#2563eb" strokeWidth="4" markerEnd="url(#classroom-arrowhead)" />
      <text x="103" y="76" textAnchor="middle" className="fill-blue-950 text-sm font-bold">
        {drawing.from}
      </text>
      <text x="417" y="76" textAnchor="middle" className="fill-emerald-950 text-sm font-bold">
        {drawing.to}
      </text>
      {drawing.label && (
        <text x="260" y="48" textAnchor="middle" className="fill-slate-700 text-xs font-semibold">
          {drawing.label}
        </text>
      )}
    </svg>
  );
}

function AreaModel({ drawing }: { drawing: Extract<DrawingInstruction, { kind: "area-model" }> }) {
  const cells = Array.from({ length: drawing.rows * drawing.cols }, (_, index) => index);
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <div
        className="grid gap-1"
        style={{ gridTemplateColumns: `repeat(${drawing.cols}, minmax(0, 1fr))` }}
        aria-label={`${drawing.rows} by ${drawing.cols} area model`}
      >
        {cells.map((cell) => (
          <div key={cell} className="aspect-square rounded-md border border-emerald-200 bg-emerald-100" />
        ))}
      </div>
      <p className="mt-3 text-center text-sm font-semibold text-slate-700">{drawing.label}</p>
    </div>
  );
}

function Drawing({ drawing }: { drawing: DrawingInstruction }) {
  if (drawing.kind === "number-line") return <NumberLine drawing={drawing} />;
  if (drawing.kind === "coordinate-plane") return <CoordinatePlane drawing={drawing} />;
  if (drawing.kind === "geometry") return <GeometryFigure drawing={drawing} />;
  if (drawing.kind === "arrow") return <ArrowDiagram drawing={drawing} />;
  return <AreaModel drawing={drawing} />;
}

function MathContent({ content, display = false }: { content: string; display?: boolean }) {
  const parts = content.split(/(\$\$[\s\S]*?\$\$|\\\([\s\S]*?\\\)|\$[^$]+\$)/g).filter(Boolean);
  return (
    <span>
      {parts.map((part, index) => {
        const isBlock = part.startsWith("$$");
        const isInline = part.startsWith("$") || part.startsWith("\\(");
        if (!display && !isBlock && !isInline) {
          return <span key={`${part}-${index}`}>{part}</span>;
        }
        const source = isBlock ? part.slice(2, -2) : isInline ? part.slice(1, -1) : part;
        const html = katex.renderToString(source, {
          displayMode: display || isBlock,
          throwOnError: false,
          strict: "ignore",
        });
        return <span key={`${part}-${index}`} dangerouslySetInnerHTML={{ __html: html }} />;
      })}
    </span>
  );
}

function BoardEvent({ event, highlighted }: { event: LessonEvent; highlighted: boolean }) {
  if (event.type === "write") {
    return (
      <div
        id={event.id}
        className={`rounded-2xl border px-5 py-4 text-lg leading-8 shadow-sm transition ${
          itemTone(event.kind)
        } ${highlighted ? "ring-4 ring-amber-300" : ""}`}
      >
        <p style={handwritingStyle} className={event.kind === "equation" ? "text-xl font-semibold sm:text-2xl" : ""}>
          <MathContent content={event.content} display={event.kind === "equation"} />
        </p>
      </div>
    );
  }

  if (event.type === "draw") {
    return (
      <div id={event.id} className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition ${highlighted ? "ring-4 ring-amber-300" : ""}`}>
        <Drawing drawing={event.drawing} />
      </div>
    );
  }

  if (event.type === "plot") {
    return (
      <div id={event.id} className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition ${highlighted ? "ring-4 ring-amber-300" : ""}`}>
        {event.title && <p className="mb-2 text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">{event.title}</p>}
        <PlotGraphic expression={event.expression} />
      </div>
    );
  }

  return null;
}

export function SynchronizedWhiteboard({ chapterTitle, conceptTitle, events, highlightedTargetId, isPlaying }: Props) {
  return (
    <section className="flex min-h-[620px] flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-xl shadow-slate-200/70">
      <div className="flex flex-col gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Whiteboard</p>
          <h2 className="mt-1 truncate text-xl font-semibold text-slate-950">{conceptTitle}</h2>
          <p className="mt-1 text-sm text-slate-600">{chapterTitle}</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700">
          <span className={`h-2.5 w-2.5 rounded-full ${isPlaying ? "bg-emerald-500" : "bg-slate-300"}`} />
          {isPlaying ? "Lesson timeline running" : "Lesson paused"}
        </div>
      </div>

      <div className="relative flex-1 overflow-y-auto bg-[linear-gradient(#ffffff_31px,#e2e8f0_32px)] bg-[length:100%_32px] px-4 py-5 sm:px-7">
        <div className="pointer-events-none absolute inset-y-0 left-10 w-px bg-rose-100" />
        <div className="relative mx-auto flex max-w-5xl flex-col gap-4 pb-8">
          {events.length ? (
            events.map((item) => (
              <BoardEvent key={item.key} event={item.event} highlighted={Boolean(item.event.id && item.event.id === highlightedTargetId)} />
            ))
          ) : (
            <div className="grid min-h-[420px] place-items-center rounded-2xl border border-dashed border-slate-300 bg-white/80 p-8 text-center">
              <div>
                <p className="text-lg font-semibold text-slate-950">Ready for the chapter map</p>
                <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">
                  Press play to let the tutor introduce the chapter and begin the first concept.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
