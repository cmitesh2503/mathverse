// This route is kept for potential future use
// For now, Gemini Live API is accessed directly from the browser using the official SDK

export async function POST(req: Request) {
  try {
    const body = await req.json();
    console.log("📨 /api/live called with:", Object.keys(body));

    // Currently, the browser connects directly to Gemini Live API
    // This endpoint can be used for additional processing if needed

    return new Response(
      JSON.stringify({
        status: "ok",
        message: "Gemini Live API connection handled via browser WebSocket",
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    console.error("❌ /api/live ERROR:", errMsg);

    return new Response(
      JSON.stringify({ error: `Server error: ${errMsg}` }),
      { status: 500 }
    );
  }
}