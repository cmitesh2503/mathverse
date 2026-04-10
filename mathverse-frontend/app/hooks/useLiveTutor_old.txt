"use client";

import { useEffect, useRef, useState } from "react";

type SpeechRecognitionEvent = Event & {
  results: SpeechRecognitionResultList;
  isFinal?: boolean;
};

type SpeechRecognitionErrorEvent = Event & {
  error: string;
};

interface SpeechRecognitionResultList {
  [index: number]: SpeechRecognitionResult;
  length: number;
}

interface SpeechRecognitionResult {
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
  length: number;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionAPI;
    webkitSpeechRecognition: new () => SpeechRecognitionAPI;
  }
}

interface SpeechRecognitionAPI {
  continuous: boolean;
  interimResults: boolean;
  language: string;
  onstart?: () => void;
  onend?: () => void;
  onerror?: (event: SpeechRecognitionErrorEvent) => void;
  onresult?: (event: SpeechRecognitionEvent) => void;
  start(): void;
  stop(): void;
  abort(): void;
}

export function useLiveTutor(onWhiteboard: (data: unknown) => void) {
  console.log("✨ useLiveTutor hook initialized");
  const onWhiteboardRef = useRef(onWhiteboard);
  const sessionIdRef = useRef<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionAPI | null>(null);
  const isStartingRef = useRef(false);
  const isMountedRef = useRef(true);
  const suppressRestartRef = useRef(false);
  const restartTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");

  useEffect(() => {
    onWhiteboardRef.current = onWhiteboard;
  }, [onWhiteboard]);

  useEffect(() => {
    console.log("✨ useLiveTutor useEffect running");
    isMountedRef.current = true;
    const startSession = async () => {
      try {
        console.log("🚀 Starting Audio-Based Tutor Session with Text Processing...");

        // Get or create session
        try {
          const response = await fetch("http://localhost:8000/session/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              student_id: "audio-student-001",
              grade: 10,
            }),
          });
          const data = await response.json();
          sessionIdRef.current = data.session.session_id;
          console.log("✅ Session created:", sessionIdRef.current);
        } catch (err) {
          console.error("❌ Failed to create session:", err);
          throw err;
        }

        // Initialize Web Speech API
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          throw new Error("Speech Recognition not supported in this browser");
        }

        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;

        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.language = "en-IN";

        recognition.onstart = () => {
          console.log("🎤 Listening started");
          isStartingRef.current = false;
          setIsListening(true);
          setTranscript("");
        };

        recognition.onresult = async (event: SpeechRecognitionEvent) => {
          let interimTranscript = "";
          let finalTranscript = "";

          for (let i = event.results.length - 1; i >= 0; --i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript + " ";
            } else {
              interimTranscript += transcript;
            }
          }

          setTranscript(interimTranscript || finalTranscript);

          if (finalTranscript) {
            console.log("📝 User said:", finalTranscript);
            stopRecognition();
            await handleUserMessage(finalTranscript.trim());
            if (isMountedRef.current) {
              startRecognition();
            }
          }
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
          // Ignore "aborted" errors from cleanup or user stopping
          if (event.error === "aborted") {
            console.log("ℹ️ Speech recognition aborted (expected during cleanup)");
          } else {
            console.error("❌ Speech recognition error:", event.error);
          }
          isStartingRef.current = false;
        };

        recognition.onend = () => {
          console.log("🎤 Listening stopped");
          setIsListening(false);
          if (suppressRestartRef.current) {
            return;
          }

          // Restart listening for continuous conversation only if component is mounted
          if (isMountedRef.current && !isStartingRef.current) {
            // Clear any pending restart
            if (restartTimeoutRef.current) {
              clearTimeout(restartTimeoutRef.current);
            }
            // Use longer delay to ensure previous session fully cleaned up
            restartTimeoutRef.current = setTimeout(() => {
              if (isMountedRef.current && recognitionRef.current && !isStartingRef.current) {
                try {
                  isStartingRef.current = true;
                  recognitionRef.current.start();
                } catch (err) {
                  console.warn("⚠️ Could not restart recognition:", err);
                  isStartingRef.current = false;
                }
              }
            }, 800); // Increased from 500ms to allow proper cleanup
          }
        };

        const stopRecognition = () => {
          if (restartTimeoutRef.current) {
            clearTimeout(restartTimeoutRef.current);
            restartTimeoutRef.current = null;
          }
          if (!recognitionRef.current) {
            return;
          }
          suppressRestartRef.current = true;
          try {
            recognitionRef.current.stop();
          } catch (err) {
            console.warn("⚠️ Error stopping recognition:", err);
          }
          isStartingRef.current = false;
          setIsListening(false);
        };

        const startRecognition = () => {
          if (!recognitionRef.current || isStartingRef.current) {
            return;
          }
          suppressRestartRef.current = false;
          try {
            isStartingRef.current = true;
            recognitionRef.current.start();
          } catch (err) {
            console.warn("⚠️ Could not start recognition:", err);
            isStartingRef.current = false;
          }
        };

        // Start listening
        try {
          isStartingRef.current = true;
          recognition.start();
          console.log("🎤 Microphone listening initialized");
        } catch (err) {
          console.warn("⚠️ Error starting recognition:", err);
          isStartingRef.current = false;
        }
      } catch (err) {
        console.error("❌ Error initializing tutor session:", err);
      }
    };

    const handleUserMessage = async (userText: string) => {
      if (!sessionIdRef.current) {
        console.error("No session ID");
        return;
      }

      try {
        console.log("📤 Sending message to backend:", userText);

        // Send message to backend
        const response = await fetch("http://localhost:8000/session/message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionIdRef.current,
            message: userText,
          }),
        });

        const data = await response.json();
        const tutorResponse = data.response;

        console.log("🤖 Tutor response:", tutorResponse);

        // Update whiteboard if available
        if (data.whiteboard) {
          onWhiteboardRef.current(data.whiteboard);
        }

        // Convert response to speech and play
        await speakResponse(tutorResponse);
      } catch (err) {
        console.error("❌ Error processing message:", err);
      }
    };

    const speakResponse = async (text: string) => {
      // Use Web Speech API for text-to-speech
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 1;
      utterance.lang = "en-IN";

      // Use a female voice if available
      const voices = window.speechSynthesis.getVoices();
      const femaleVoice = voices.find(
        (voice) => voice.name.includes("Female") || voice.name.includes("woman")
      );
      if (femaleVoice) {
        utterance.voice = femaleVoice;
      }

      console.log("🔊 Playing audio response");

      return new Promise<void>((resolve) => {
        utterance.onend = () => {
          console.log("🔊 Audio playback complete");
          resolve();
        };
        window.speechSynthesis.speak(utterance);
      });
    };

    startSession();

    return () => {
      // Mark component as unmounted - prevents new operations
      isMountedRef.current = false;
      
      // Clear any pending restart timeout
      if (restartTimeoutRef.current) {
        clearTimeout(restartTimeoutRef.current);
        restartTimeoutRef.current = null;
      }
      
      // Cleanup: stop listening gracefully
      if (recognitionRef.current) {
        try {
          // Use stop() instead of abort() to avoid race conditions
          // stop() will trigger onend event, abort() triggers onerror
          recognitionRef.current.stop();
        } catch (err) {
          console.warn("⚠️ Error stopping recognition:", err);
        }
      }
      
      // Cancel any ongoing speech synthesis
      window.speechSynthesis.cancel();
    };
  }, []);

  return { isListening, transcript };
}