import React from "react";

type Props = {
  onNavigate: (page: any) => void;
};

export default function JeeHome({
  onNavigate
}: Props) {

  const cardStyle: React.CSSProperties = {
    border: "1px solid #ddd",
    padding: "20px",
    borderRadius: "10px",
    cursor: "pointer",
    transition: "all 0.2s ease",
    background: "#fff",
    minHeight: "140px"
  };

  return (

    <div
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "40px"
      }}
    >

      <h1
        style={{
          marginBottom: "10px"
        }}
      >
        MathVerse JEE
      </h1>

      <p
        style={{
          color: "#555",
          marginBottom: "30px"
        }}
      >
        AI Powered JEE Preparation
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit,minmax(250px,1fr))",
          gap: "20px"
        }}
      >

        {/* Solve Question */}

        <div
            onClick={() =>
                onNavigate(
                "jee-solve"
                )
            }
            style={{
                border: "1px solid #ddd",
                padding: "20px",
                borderRadius: "10px",
                cursor: "pointer"
            }}
            >
            🚀

            <h3>
                Solve Question
            </h3>

            <p>
                Upload any JEE question and
                get AI explanation.
            </p>
        </div>

        {/* Live Tutor */}

        <div
          style={cardStyle}
          onClick={() =>
            onNavigate("voice-tutor")
          }
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow =
              "0 4px 12px rgba(0,0,0,0.1)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow =
              "none";
          }}
        >
          <div
            style={{
              fontSize: "28px"
            }}
          >
            🎤
          </div>

          <h3>
            Live Tutor
          </h3>

          <p>
            Discuss doubts with voice tutor.
          </p>
        </div>

        {/* PYQ */}

        <div
          style={cardStyle}
          onClick={() => {

            alert(
              "PYQ Explorer Coming Next"
            );

          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow =
              "0 4px 12px rgba(0,0,0,0.1)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow =
              "none";
          }}
        >
          <div
            style={{
              fontSize: "28px"
            }}
          >
            📚
          </div>

          <h3>
            Practice PYQs
          </h3>

          <p>
            Chapter wise previous year questions.
          </p>
        </div>

        {/* Mock Test */}

        <div
          style={cardStyle}
          onClick={() => {

            alert(
              "Mock Tests Coming Next"
            );

          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow =
              "0 4px 12px rgba(0,0,0,0.1)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow =
              "none";
          }}
        >
          <div
            style={{
              fontSize: "28px"
            }}
          >
            📝
          </div>

          <h3>
            Mock Tests
          </h3>

          <p>
            Full JEE mock exams.
          </p>
        </div>

      </div>

      <div
        style={{
          marginTop: "40px",
          padding: "20px",
          borderRadius: "12px",
          background: "#f8fafc"
        }}
      >
        <h3>
          Current Status
        </h3>

        <ul>
          <li>✅ Firestore Question Bank</li>
          <li>✅ OCR Pipeline</li>
          <li>✅ Voice Tutor</li>
          <li>✅ Speech To Text</li>
          <li>✅ Text To Speech</li>
          <li>✅ AI Whiteboard</li>
          <li>🚧 Question Viewer</li>
          <li>🚧 PYQ Explorer</li>
          <li>🚧 Mock Tests</li>
        </ul>
      </div>

    </div>
  );
}