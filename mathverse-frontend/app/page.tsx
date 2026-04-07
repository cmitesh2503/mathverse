"use client";

import Chat from "./components/Chat";
import { useLiveTutor } from "./hooks/useLiveTutor";

export default function Page() {
  useLiveTutor((payload) => {
    window.dispatchEvent(
      new CustomEvent("liveBoard", { detail: payload })
    );
  });

  return (
    <div>
      <Chat />
    </div>
  );
}