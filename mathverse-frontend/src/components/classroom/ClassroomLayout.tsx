import type { ReactNode } from "react";

type Props = {
  header: ReactNode;
  sidebar: ReactNode;
  whiteboard: ReactNode;
  tutor: ReactNode;
  controls: ReactNode;
};

export function ClassroomLayout({ header, sidebar, whiteboard, tutor, controls }: Props) {
  return (
    <main className="min-h-[calc(100vh-4rem)] bg-[#f6f8fb] text-slate-950">
      <div className="mx-auto flex max-w-[1680px] flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        {header}
        <div className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)_360px]">
          <aside className="min-w-0 xl:sticky xl:top-20 xl:self-start">{sidebar}</aside>
          <div className="min-w-0">{whiteboard}</div>
          <aside className="min-w-0 xl:sticky xl:top-20 xl:self-start">{tutor}</aside>
        </div>
      </div>
      <div className="sticky bottom-0 z-30 border-t border-slate-200 bg-white/95 px-4 py-3 shadow-2xl shadow-slate-300/40 backdrop-blur">
        <div className="mx-auto max-w-[1680px]">{controls}</div>
      </div>
    </main>
  );
}
