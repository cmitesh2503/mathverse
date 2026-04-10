"use client";

import Chat from "./components/Chat";
//import { useLiveTutor } from "./hooks/useLiveTutor";
import { useGeminiLive } from "./hooks/useGeminiLive";

export default function Page() {
 // useLiveTutor((payload) => {
  // window.dispatchEvent(
    //  new CustomEvent("liveBoard", { detail: payload })
    //);
  // });
  //useGeminiLive();
  return (
    <div>
      <Chat />
    </div>
  );
}