"use client";

import { useEffect, useRef, useState } from "react";
import { useChatStore } from "../store/useChatStore";
import ReactMarkdown from "react-markdown";

export default function Chat() {
  const ws = useRef<WebSocket | null>(null);
  const [input, setInput] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [grade, setGrade] = useState(10);
  const [tutorStatus, setTutorStatus] = useState("Waiting for student...");
  const [wsStatus, setWsStatus] = useState("Connecting to tutor...");
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [speechRecognitionSupported, setSpeechRecognitionSupported] = useState(false);
  const [useBiDi, setUseBiDi] = useState(false);
  const [isBiDiStreaming, setIsBiDiStreaming] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const {
    messages,
    addUserMessage,
    startAssistantMessage,
    appendToAssistant,
    endStreaming,
  } = useChatStore();

  // 🔌 WebSocket connection
  useEffect(() => {
    console.log("Connecting to WebSocket...");

    const socket = new WebSocket("ws://localhost:8000/ws/tutor");
    ws.current = socket;

    socket.onopen = () => {
      console.log("✅ WebSocket connected");
      setWsStatus("WebSocket connected");
      setTutorStatus("Student arrived — Lesson starting...");

      // 🎓 No auto-message - backend starts lesson automatically like real classroom
    };

    socket.onerror = (err) => {
      console.error("❌ WebSocket error:", err);
      setWsStatus("WebSocket error - see console");
      setTutorStatus("Unable to connect to tutor; check backend and console");
    };

    socket.onclose = () => {
      console.log("⚠️ WebSocket closed");
      setWsStatus("WebSocket disconnected");
      setTutorStatus("Tutor disconnected. Refresh to reconnect.");
    };

    socket.onclose = () => {
      console.log("⚠️ WebSocket closed");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      console.log("WS DATA:", data);

      if (data.type === "start") {
        startAssistantMessage();
      }

      if (data.type === "chunk") {
        appendToAssistant(data.content);
      }

      if (data.type === "done") {
        endStreaming();
        setTutorStatus("Tutor is waiting for your input...");
        speakLastMessage();
      }

      // fallback handling
      if (data.type === "explanation" || data.type === "info") {
        startAssistantMessage();
        appendToAssistant(data.content);
        endStreaming();
        setTutorStatus("Tutor is waiting for your input...");
      }

      if (data.type === "chunk") {
        setTutorStatus("Tutor is speaking...");
      }

    };

    return () => {
      socket.close();
    };
  }, []);

  // � Start camera and microphone for AI tutor avatar feed
  useEffect(() => {
    let localStream: MediaStream | null = null;

    async function enableCameraAndMic() {
      try {
        localStream = await navigator.mediaDevices.getUserMedia({ 
          video: true, 
          audio: true 
        });
        setVideoStream(localStream);
        if (videoRef.current) {
          videoRef.current.srcObject = localStream;
        }
        console.log("✅ Camera and microphone enabled");
      } catch (err) {
        console.warn("Camera/microphone not available or permission denied", err);
        setTutorStatus("Camera/microphone permission needed for full experience");
      }
    }

    enableCameraAndMic();

    return () => {
      if (localStream) {
        localStream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  // �🔽 Auto scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // �️ Speech recognition setup
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSpeechRecognitionSupported(true);
      const r = new SpeechRecognition();
      r.lang = "en-US";
      r.interimResults = false;
      r.maxAlternatives = 1;
      r.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        sendMessage(transcript); // send immediately as soon as speech recognition returns
      };
      r.onend = () => {
        setIsListening(false);
      };
      recognitionRef.current = r;
    } else {
      setSpeechRecognitionSupported(false);
    }
  }, []);

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      setIsListening(true);
      recognitionRef.current.start();
    }
  };

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  const startBiDiStreaming = () => {
    if (!videoStream || !ws.current) return;
    if (!window.MediaRecorder) {
      console.warn("BiDi not supported: MediaRecorder missing");
      return;
    }

    // Extract audio track from video stream
    const audioTracks = videoStream.getAudioTracks();
    if (audioTracks.length === 0) {
      console.error("No audio track available in stream");
      alert("No audio input detected. Please check your microphone permissions.");
      return;
    }

    // Create audio-only stream
    const audioStream = new MediaStream([audioTracks[0]]);

    // Find a supported MIME type for audio recording
    const mimeTypes = [
      "audio/webm;codecs=opus",
      "audio/webm;codecs=vp8",
      "audio/webm",
      "audio/mp4",
      "audio/ogg",
      ""  // browser default
    ];

    let selectedMimeType = "";
    for (const mimeType of mimeTypes) {
      if (!mimeType || MediaRecorder.isTypeSupported(mimeType)) {
        selectedMimeType = mimeType;
        break;
      }
    }

    console.log("Using MIME type:", selectedMimeType || "browser default");

    try {
      const options: MediaRecorderOptions = selectedMimeType 
        ? { mimeType: selectedMimeType } 
        : {};

      const recorder = new MediaRecorder(audioStream, options);
      
      recorder.ondataavailable = (event) => {
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
        if (event.data.size === 0) return;

        const reader = new FileReader();
        reader.onloadend = () => {
          const base64Data = (reader.result as string).split(",")[1];
          ws.current?.send(JSON.stringify({ type: "audio_chunk", data: base64Data }));
        };
        reader.readAsDataURL(event.data);
      };

      recorder.onerror = (event) => {
        console.error("MediaRecorder error:", event.error);
        setIsBiDiStreaming(false);
      };

      recorder.start(1000); // send data every 1 sec
      setMediaRecorder(recorder);
      setIsBiDiStreaming(true);
      console.log("BiDi streaming started with audio-only stream");
    } catch (err) {
      console.error("Failed to start MediaRecorder:", err);
      setIsBiDiStreaming(false);
    }
  };

  const stopBiDiStreaming = () => {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    setMediaRecorder(null);
    setIsBiDiStreaming(false);
  };

  // �🎤 TTS function with avatar speaking animation
  const speakLastMessage = () => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.role === "assistant") {
      console.log("🎤 Speaking message:", lastMessage.content.substring(0, 50) + "...");
      
      if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
        console.warn('Speech Synthesis not supported in this browser');
        setIsSpeaking(false);
        return;
      }

      const utterance = new SpeechSynthesisUtterance(lastMessage.content);
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v => /en(-|_)?/i.test(v.lang)) || voices[0];
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onstart = () => {
        console.log("🎤 TTS started");
        setIsSpeaking(true);
      };
      utterance.onend = () => {
        console.log("🎤 TTS ended");
        setIsSpeaking(false);
      };
      utterance.onerror = (err) => {
        console.error("🎤 TTS error:", err);
        setIsSpeaking(false);
      };

      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      
      const trySpeak = () => {
        if (!window.speechSynthesis) {
          console.warn('SpeechSynthesis not available');
          setIsSpeaking(false);
          return;
        }

        try {
          window.speechSynthesis.speak(utterance);
        } catch (err) {
          console.error("🎤 TTS failed:", err);
          setIsSpeaking(false);
        }
      };

      // Some browsers require user gesture before audio playback; call once directly.
      const playUtterance = () => {
        if (window.speechSynthesis.getVoices().length === 0) {
          window.speechSynthesis.onvoiceschanged = () => {
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v => /en(-|_)?/i.test(v.lang)) || voices[0];
            if (preferredVoice) {
              utterance.voice = preferredVoice;
            }
            trySpeak();
          };
        } else {
          trySpeak();
        }
      };

      playUtterance();
    }
  };

  // 📤 Send message
  const sendMessage = (overrideText?: string) => {
    const messageText = (overrideText ?? input).trim();
    if (!messageText) return;

    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.log("❌ WebSocket not ready");
      return;
    }

    addUserMessage(messageText);

    ws.current.send(
      JSON.stringify({
        session_id: "test123",
        message: messageText,
        grade: grade,
      })
    );

    setInput("");
  };

  return (
    <div className="p-4 max-w-2xl mx-auto">
      {/* Grade Selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Select Grade:</label>
        <select
          value={grade}
          onChange={(e) => setGrade(parseInt(e.target.value))}
          className="border p-2 rounded"
        >
          {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
            <option key={g} value={g}>
              Grade {g}
            </option>
          ))}
        </select>
      </div>

      {/* Animated AI Avatar - Math Teacher Persona */}
      <style>{`
        @keyframes mouth-talk {
          0%, 100% { height: 8px; transform: scaleY(1); }
          50% { height: 16px; transform: scaleY(1.5); }
        }
        @keyframes eye-blink {
          0%, 49%, 100% { height: 16px; }
          50% { height: 2px; }
        }
        @keyframes head-nod {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          25% { transform: translateY(-2px) rotate(-1deg); }
          75% { transform: translateY(2px) rotate(1deg); }
        }
        @keyframes pointer-gesture {
          0%, 100% { transform: rotate(0deg); }
          25% { transform: rotate(-10deg); }
          75% { transform: rotate(10deg); }
        }
        @keyframes speaking-glow {
          0%, 100% { box-shadow: 0 0 10px rgba(59, 130, 246, 0.3); }
          50% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.8); }
        }
        .avatar-speaking {
          animation: head-nod 1s ease-in-out infinite, speaking-glow 0.5s ease-in-out infinite;
        }
        .mouth-speaking {
          animation: mouth-talk 0.2s ease-in-out infinite;
        }
        .teacher-pointer {
          animation: pointer-gesture 1.5s ease-in-out infinite;
        }
      `}</style>

      <div className="flex justify-center mb-4">
        <div className="relative">
          {/* Camera Feed */}
          <video
            ref={videoRef}
            autoPlay
            muted
            className={`w-32 h-40 rounded-lg border-4 border-blue-400 object-cover transition-all duration-300 ${videoStream ? 'block' : 'hidden'}`}
          />
          
          {/* Human-like AI Avatar (fallback when no camera) */}
          <div className={`w-32 h-40 rounded-lg border-4 bg-gradient-to-b from-skin-100 to-skin-200 flex flex-col items-center justify-center absolute top-0 left-0 transition-all duration-300 ${videoStream ? 'hidden' : 'block'} ${isSpeaking ? 'avatar-speaking border-blue-600' : 'border-blue-400'}`}>
            <svg
              width="120"
              height="140"
              viewBox="0 0 120 140"
              className="rounded-lg"
            >
              {/* Background */}
              <rect width="120" height="140" fill="url(#skinGradient)" rx="8" />

              {/* Hair */}
              <path
                d="M20 25 Q60 15 100 25 Q110 35 105 50 Q95 45 85 50 Q75 45 65 50 Q55 45 45 50 Q35 45 25 50 Q20 40 20 25"
                fill="#8B4513"
              />

              {/* Face */}
              <ellipse cx="60" cy="70" rx="35" ry="40" fill="url(#skinGradient)" />

              {/* Eyes */}
              <circle cx="50" cy="65" r="4" fill="#000" className={isSpeaking ? 'animate-pulse' : ''} />
              <circle cx="70" cy="65" r="4" fill="#000" className={isSpeaking ? 'animate-pulse' : ''} />

              {/* Eyebrows */}
              <rect x="45" y="55" width="10" height="2" fill="#8B4513" rx="1" />
              <rect x="65" y="55" width="10" height="2" fill="#8B4513" rx="1" />

              {/* Nose */}
              <ellipse cx="60" cy="75" rx="2" ry="3" fill="#D2691E" />

              {/* Mouth */}
              <ellipse
                cx="60"
                cy="85"
                rx="8"
                ry={isSpeaking ? "6" : "3"}
                fill="#DC143C"
                className={isSpeaking ? 'mouth-speaking' : ''}
              />

              {/* Shirt/Collar */}
              <rect x="25" y="110" width="70" height="25" fill="#4169E1" rx="5" />
              <rect x="35" y="105" width="50" height="10" fill="#4169E1" rx="3" />

              {/* Glasses */}
              <circle cx="50" cy="65" r="8" fill="none" stroke="#C0C0C0" strokeWidth="2" />
              <circle cx="70" cy="65" r="8" fill="none" stroke="#C0C0C0" strokeWidth="2" />
              <line x1="58" y1="65" x2="62" y2="65" stroke="#C0C0C0" strokeWidth="2" />

              {/* Speaking indicator dots */}
              {isSpeaking && (
                <g>
                  <circle cx="45" cy="125" r="2" fill="#FF6B6B" className="animate-bounce" style={{ animationDelay: '0s' }} />
                  <circle cx="60" cy="125" r="2" fill="#FF6B6B" className="animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <circle cx="75" cy="125" r="2" fill="#FF6B6B" className="animate-bounce" style={{ animationDelay: '0.2s' }} />
                </g>
              )}

              {/* Gradients */}
              <defs>
                <linearGradient id="skinGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#FDBCB4" />
                  <stop offset="100%" stopColor="#E8B4A2" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>
      </div>

      {/* Tutor Status Card */}
      <div className="flex justify-center mb-4">
        <div className="w-full max-w-sm p-3 rounded-lg border-2 border-blue-300 bg-blue-50 text-center">
          <div className="text-sm font-bold text-blue-700">Ava - Math Teacher</div>
          <div className="text-xs text-gray-600 mt-1">{tutorStatus}</div>
          <div className="text-xs text-gray-700 mt-1">WS Status: {wsStatus}</div>
          {isSpeaking && <div className="text-xs text-green-600 mt-2 animate-pulse">🎓 Teaching...</div>}

          <div className="mt-3 flex items-center justify-center gap-2">
            <label className="text-xs font-medium">BiDi live:</label>
            <input
              type="checkbox"
              checked={useBiDi}
              onChange={(e) => {
                const enabled = e.target.checked;
                setUseBiDi(enabled);

                if (enabled) {
                  stopListening();
                  startBiDiStreaming();
                } else {
                  stopBiDiStreaming();
                }
              }}
            />
          </div>
          <div className="mt-2 flex justify-center gap-2">
            {speechRecognitionSupported ? (
              <>
                <button
                  onClick={isListening ? stopListening : startListening}
                  disabled={useBiDi}
                  className={`text-xs px-2 py-1 rounded ${isListening ? 'bg-red-500 text-white' : 'bg-green-500 text-white'} ${useBiDi ? 'opacity-50 cursor-not-allowed' : ''}`}>
                  {isListening ? 'Stop Listening' : 'Start Voice Input'}
                </button>
                <span className="text-xs text-gray-600">Mic ready for voice chat</span>
              </>
            ) : (
              <span className="text-xs text-orange-600">Voice input not supported</span>
            )}
          </div>
          <div className="mt-1 text-xs text-gray-700">{useBiDi ? (isBiDiStreaming ? 'BiDi streaming active' : 'BiDi enabled') : 'BiDi off'} | Type input also works.</div>
        </div>
      </div>

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
          className="border-2 border-blue-300 p-2 flex-1 rounded-lg focus:outline-none focus:border-blue-500"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask your tutor a question..."
        />

        <button
          onClick={sendMessage}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 rounded-lg font-semibold"
        >
          Send
        </button>
      </div>
    </div>
  );
}