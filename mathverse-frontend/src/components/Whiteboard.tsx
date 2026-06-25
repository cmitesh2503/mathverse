import React from "react";

export function Whiteboard({ whiteboard }) {

  if (!whiteboard) {
    return null;
  }

  return (
    
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: "10px",
        padding: "15px",
        marginTop: "20px",
        maxHeight: "500px",
        overflowY: "auto",
        background: "#fff"
      }}
    >
      <h2>🧑‍🏫 Whiteboard</h2>

      <h3>{whiteboard.problem}</h3>

      {whiteboard.steps?.map((step, index) => (
        <div
          key={index}
          style={{
            marginBottom: "10px",
            padding: "10px",
            background: "white",
            borderRadius: "5px",
          }}
        >
          Step {index + 1}: {step}
        </div>
      ))}
    </div>
  );
}