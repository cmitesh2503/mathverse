import React, {
useState,
useRef,
useEffect
} from "react";

import { Whiteboard } from "../components/Whiteboard";

function JeeVoiceTutor() {

const [questionId] =
useState(
localStorage.getItem(
"jee_question_id"
) || ""
    );
  
const question =
  localStorage.getItem("jee_question") || "";

const answer =
  localStorage.getItem("jee_answer") || "";

const solution =
  localStorage.getItem("jee_solution") || "";

const [connected, setConnected] =
useState(false);

const [messages, setMessages] =
useState([]);

const [transcript, setTranscript] =
useState("");

const [recording, setRecording] =
useState(false);

const [mediaRecorder, setMediaRecorder] =
useState(null);

const [whiteboardSteps, setWhiteboardSteps] =
useState([]);

const [whiteboardData, setWhiteboardData] =
useState(null);

const wsRef = useRef(null);

useEffect(() => {


if (
  questionId &&
  !connected
) {

  connectTutor();

}


}, []);

const connectTutor = () => {


const ws = new WebSocket(
  "ws://localhost:8000/api/jee/live-tutor"
);

ws.onopen = () => {

  console.log(
    "Tutor Connected"
  );

  ws.send(
    questionId
  );

  setConnected(
    true
  );
};

ws.onmessage = async (event) => {

  console.log(
    "RAW:",
    event.data
  );

  try {

    const data =
      JSON.parse(
        event.data
      );

    if (
      data.whiteboard
    ) {

      console.log(
        "WHITEBOARD RECEIVED",
        data.whiteboard
      );

      setWhiteboardData(
        data.whiteboard
      );

      setWhiteboardSteps(
        data.whiteboard.steps || []
      );
    }

    setMessages(
      prev => [
        ...prev,
        {
          role: "Tutor",
          text:
            data.explanation
        }
      ]
    );

    await speak(
      data.explanation
    );

  } catch {

    setMessages(
      prev => [
        ...prev,
        {
          role: "Tutor",
          text:
            event.data
        }
      ]
    );

    await speak(
      event.data
    );
  }
};

ws.onerror = (err) => {

  console.log(
    "WebSocket Error",
    err
  );
};

ws.onclose = () => {

  console.log(
    "Tutor Disconnected"
  );

  setConnected(
    false
  );
};

wsRef.current = ws;


};

const startRecording = async () => {


const stream =
  await navigator.mediaDevices.getUserMedia({
    audio: true
  });

const recorder =
  new MediaRecorder(
    stream
  );

const chunks = [];

recorder.ondataavailable =
  (event) => {

    chunks.push(
      event.data
    );
  };

recorder.onstop =
  async () => {

    const blob =
      new Blob(
        chunks,
        {
          type:
            "audio/webm"
        }
      );

    const formData =
      new FormData();

    formData.append(
      "audio",
      blob,
      "voice.webm"
    );

    const response =
      await fetch(
        "http://localhost:8000/api/jee/voice",
        {
          method: "POST",
          body: formData
        }
      );

    const data =
      await response.json();

    setTranscript(
      data.transcript
    );

    if (
      wsRef.current &&
      connected
    ) {

      wsRef.current.send(
        data.transcript
      );
    }
  };

recorder.start();

setMediaRecorder(
  recorder
);

setRecording(
  true
);


};

const stopRecording = () => {


if (
  mediaRecorder
) {

  mediaRecorder.stop();

  setRecording(
    false
  );
}


};

const speak = async (
text
) => {


try {

  const response =
    await fetch(
      "http://localhost:8000/api/jee/tts",
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json"
        },
        body: JSON.stringify({
          text
        })
      }
    );

  const blob =
    await response.blob();

  const url =
    URL.createObjectURL(
      blob
    );

  const audio =
    new Audio(url);

  await audio.play();

} catch (err) {

  console.log(
    err
  );
}


};

return (


<div
  style={{
    maxWidth: "900px",
    margin: "auto",
    padding: "20px"
  }}
>

  <h2>
    MathVerse JEE Voice Tutor
  </h2>

  <div
    style={{
      background:"#eef7ff",
      padding:"15px",
      borderRadius:"10px",
      marginBottom:"20px"
    }}
  >

  <h3>Current Question</h3>

  <div style={{whiteSpace:"pre-wrap"}}>
  {question}
  </div>

  <hr />

  <b>Correct Answer</b>

  <div>
  {answer}
  </div>

  <details style={{marginTop:"15px"}}>

  <summary>
  Show Detailed Solution
  </summary>

  <div
  style={{
  whiteSpace:"pre-wrap",
  marginTop:"10px"
  }}
  >
  {solution}
  </div>

  </details>

  </div>

  <div
    style={{
      marginBottom:
        "15px",
      fontWeight:
        "bold",
      color:
        connected
          ? "green"
          : "red"
    }}
  >
    {
      connected
        ? "Tutor Connected"
        : "Connecting..."
    }
  </div>

  <button
    onClick={
      startRecording
    }
    disabled={
      recording
    }
  >
    🎤 Start Recording
  </button>

  <button
    onClick={
      stopRecording
    }
    disabled={
      !recording
    }
    style={{
      marginLeft:
        "10px"
    }}
  >
    ⏹ Stop Recording
  </button>

  <hr />

  <h3>
    Transcript
  </h3>

  <pre>
    {transcript}
  </pre>

  <Whiteboard
    steps={
      whiteboardSteps
    }
    whiteboard={
      whiteboardData
    }
  />

  <hr />

  <h3>
    Tutor Responses
  </h3>

  {
    messages.map(
      (
        msg,
        index
      ) => (
        <div
          key={index}
          style={{
            marginBottom:
              "10px"
          }}
        >
          <b>
            {msg.role}:
          </b>{" "}
          {msg.text}
        </div>
      )
    )
  }

</div>


);
}

export default JeeVoiceTutor;
