"use client";

import { useEffect } from "react";

export function useGeminiLive() {
  useEffect(() => {
    const start = async () => {
      const ws = new WebSocket(
        `wss://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:streamGenerateContent?key=${process.env.NEXT_PUBLIC_GOOGLE_API_KEY}`
      );

      ws.onopen = () => {
        console.log("✅ Connected to Gemini Live");

        ws.send(
          JSON.stringify({
            setup: {
              model: "gemini-2.0-flash-exp",
              generation_config: {
                response_modalities: ["AUDIO"],
              },
            },
          })
        );
      };

      ws.onmessage = (event) => {
        console.log("📩 Gemini:", event.data);
      };

      ws.onerror = (err) => {
        console.error("❌ WS error", err);
      };
    };

    start();
  }, []);
}