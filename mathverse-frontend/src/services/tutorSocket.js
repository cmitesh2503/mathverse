export function connectToTutorWebSocket({ sessionId, grade, userId, onMessage, onError, onClose }) {
  // Append the user_id context dynamically into the endpoint parameter signature
  const wsUrl = `ws://localhost:8000/ws/tutor?session_id=${sessionId}&grade=${grade}&user_id=${userId}`;
  
  console.log(`Connecting to secured channel: ${wsUrl}`);
  const socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("Secure connection channel opened successfully.");
  };

  socket.onmessage = (event) => {
    const data = json.parse(event.data);
    
    // Intercept backend-level subscription guard failures gracefully
    if (data.type === 'error') {
      console.error("Access restriction flagged by core server:", data.message);
      if (onError) onError(data.message);
      return;
    }
    
    if (onMessage) onMessage(data);
  };

  socket.onerror = (error) => {
    console.error("WebSocket connection failure anomaly:", error);
  };

  socket.onclose = (event) => {
    console.log(`Connection dropped. Event context code: ${event.code}`);
    if (onClose) onClose(event);
  };

  return socket;
}