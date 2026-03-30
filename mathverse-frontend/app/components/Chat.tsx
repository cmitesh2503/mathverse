"use client";

import { useEffect, useRef, useState } from "react";
import { useChatStore } from "../store/useChatStore";
import ReactMarkdown from "react-markdown";

export default function Chat() {
  const ws = useRef<WebSocket | null>(null);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const {
    messages,
    addUserMessage,
    startAssistantMessage,
    appendToAssistant,
    endStreaming,
    isStreaming,
  } = useChatStore();

  // 🔌 WebSocket connection
  useEffect(() => {
    ws.current = new WebSocket("ws://127.0.0.1:8000/ws/tutor");

    ws.current.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.current.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      console.log("WS DATA:", data);

      if (data.type === "start") {
        startAssistantMessage();
      }

      if (data.type === "chunk") {
        appendToAssistant(data.content); // ⚡ real streaming (no delay)
      }

      if (data.type === "done") {
        endStreaming();
      }

      if (data.type === "info") {
        alert(data.content);
      }
    };

    return () => ws.current?.close();
  }, []);

  // 🔽 Auto scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 📤 Send message
  const sendMessage = () => {
    if (!input.trim() || !ws.current) return;

    addUserMessage(input);

    ws.current.send(
      JSON.stringify({
        session_id: "test123",
        message: input,
      })
    );

    setInput("");
  };

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <div className="space-y-3 mb-4 h-[400px] overflow-y-auto border p-3 rounded">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={
              msg.role === "user"
                ? "text-right"
                : "text-left text-blue-600 whitespace-pre-wrap"
            }
          >
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2">
        <input
          className="border p-2 flex-1 rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something..."
        />
        <button
          onClick={sendMessage}
          className="bg-black text-white px-4 rounded"
          disabled={isStreaming}
        >
          Send
        </button>
      </div>
    </div>
  );
}