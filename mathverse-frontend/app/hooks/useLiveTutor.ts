"use client";

import { useEffect, useRef } from "react";

export function useLiveTutor(onWhiteboard: (data: any) => void) {
  const pcRef = useRef<RTCPeerConnection | null>(null);

  useEffect(() => {
    const startSession = async () => {
      try {
        const pc = new RTCPeerConnection();
        pcRef.current = pc;

        // 🔊 AI voice output
        pc.ontrack = (event) => {
          const audio = document.createElement("audio");
          audio.srcObject = event.streams[0];
          audio.autoplay = true;
        };

        // 🎤 Mic input
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

        stream.getTracks().forEach((track) => pc.addTrack(track, stream));

        // 📡 Data channel
        const dc = pc.createDataChannel("events");

        dc.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === "whiteboard") {
              onWhiteboard(data.payload);
            }

            if (data.type === "control") {
              console.log("Teacher control:", data);
            }
          } catch (err) {
            console.error("Invalid data channel message", err);
          }
        };

        // SDP handshake
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
"""
        // ✅ CALL BACKEND (NO CORS ISSUE)
        const res = await fetch("/api/live", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ sdp: offer.sdp }),
        });

        console.log("API status:", res.status);

        const answer = await res.json();

        if (!answer.sdp) {
          console.error("Invalid SDP response", answer);
          return;
        }

        await pc.setRemoteDescription({
          type: "answer",
          sdp: answer.sdp,
        });
      } catch (error) {
        console.error("Live Tutor Error:", error);
      }
    };
"""
    startSession();
  }, []);
}