import React, { useState } from "react";

type Props = {
  onNavigate: (page: string) => void;
};

export default function JeeSolveQuestion({
  onNavigate
}: Props) {

  const [file, setFile] =
    useState<File | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [result, setResult] =
    useState<any>(null);

  const [chatQuestion, setChatQuestion] =
    useState("");

  const [chatAnswer, setChatAnswer] =
    useState("");

  const handleUpload =
    async () => {

      if (!file) {

        alert(
          "Select image first"
        );

        return;
      }

      try {

        setLoading(true);

        const formData =
          new FormData();

        formData.append(
          "file",
          file
        );

        const response =
          await fetch(
            "http://localhost:8000/api/jee/solve-question",
            {
              method: "POST",
              body: formData
            }
          );

        const data =
          await response.json();

        console.log(
          "SOLVE RESPONSE",
          data
        );

          setResult(data);
          localStorage.setItem(
            "jee_question",
            data.question
          );
          
          localStorage.setItem(
            "jee_answer",
            data.answer
          );

          localStorage.setItem(
              "jee_solution",
              data.solution
          );

      } catch (err) {

        console.error(err);

        alert(
          "Solve failed"
        );

      } finally {

        setLoading(false);
      }
    };

  const askQuestion =
    async () => {

      if (
        !chatQuestion ||
        !result?.question_id
      ) {
        return;
      }

      try {

        const response =
          await fetch(
            "http://localhost:8000/api/jee/question-chat",
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json"
              },
              body: JSON.stringify({
                question_id:
                  result.question_id,
                message:
                  chatQuestion
              })
            }
          );

        const data =
          await response.json();

        console.log(
          "CHAT RESPONSE",
          data
        );

        setChatAnswer(
          data.answer ||
          data.response ||
          JSON.stringify(data)
        );

      } catch (err) {

        console.error(err);

        alert(
          "Chat failed"
        );
      }
    };

  const discussWithTutor =
    () => {

      if (
        !result?.question_id
      ) {

        alert(
          "Solve question first"
        );

        return;
      }

      localStorage.setItem(
        "jee_question_id",
        result.question_id
      );

      onNavigate(
        "voice-tutor"
      );
    };

  return (

    <div
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "40px"
      }}
    >

      <h1>
        Solve JEE Question
      </h1>

      <p>
        Upload any JEE question image.
      </p>

      <input
        type="file"
        accept="image/*"
        onChange={(e) =>
          setFile(
            e.target.files?.[0] ||
            null
          )
        }
      />

      <br />
      <br />

      <button
        onClick={
          handleUpload
        }
        disabled={
          loading
        }
      >
        {
          loading
            ? "Solving..."
            : "Solve Question"
        }
      </button>

      {
        result && (

          <div
            style={{
              marginTop:
                "40px"
            }}
          >

            <h2>
              Question
            </h2>

            <div>
              {
                result.question
              }
            </div>

            <hr />

            <h2>
              Correct Answer
            </h2>

            <div>
              {
                result.answer
              }
            </div>

            <hr />

            <h2>
              Detailed Solution
            </h2>

            <div
            style={{
                whiteSpace: "pre-wrap",
                lineHeight: "1.8",
                padding: "20px",
                border: "1px solid #ddd",
                borderRadius: "10px",
                background: "#fafafa",
                marginTop: "15px",
                fontSize: "20px"
            }}
            >
            {result.solution}
            </div>

            <hr />

            <div
              style={{
                display: "flex",
                gap: "10px",
                marginTop: "20px"
              }}
            >

              <button
                onClick={
                  discussWithTutor
                }
              >
                🎤 Discuss With Tutor
              </button>

            </div>

            <hr />

            <h2>
              💬 Ask Doubt
            </h2>

            <textarea
              rows={4}
              value={
                chatQuestion
              }
              onChange={(e) =>
                setChatQuestion(
                  e.target.value
                )
              }
              placeholder="Ask your doubt..."
              style={{
                width: "100%",
                padding: "10px"
              }}
            />

            <br />
            <br />

            <button
              onClick={
                askQuestion
              }
            >
              Ask AI Tutor
            </button>

            {
              chatAnswer && (

                <div
                  style={{
                    marginTop:
                      "20px"
                  }}
                >

                  <h3>
                    AI Tutor
                  </h3>

                  <div
                    style={{
                        whiteSpace: "pre-wrap",
                        lineHeight: "1.8",
                        padding: "20px",
                        border: "1px solid #ddd",
                        borderRadius: "10px",
                        background: "#fafafa",
                        marginTop: "10px",
                        fontSize: "15px"
                    }}
                    >
                    {chatAnswer}
                  </div>

                </div>

              )
            }

          </div>

        )
      }

    </div>
  );
}