export async function POST(req: Request) {
  try {
    const { sdp } = await req.json();

    if (!sdp) {
      return new Response(
        JSON.stringify({ error: "Missing SDP" }),
        { status: 400 }
      );
    }

    // 🔥 Call Gemini Live API correctly
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:live?key=${process.env.GOOGLE_API_KEY}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/sdp",
        },
        body: sdp,
      }
    );

    const text = await response.text();

    // 🔍 Debug log (important)
    console.log("Gemini SDP length:", text?.length);

    return new Response(
      JSON.stringify({ sdp: text }),
      {
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (err: unknown) {
    console.error("❌ /api/live ERROR:", err);

    return new Response(
      JSON.stringify({ error: err instanceof Error ? err.message : "Unknown error" }),
      { status: 500 }
    );
  }
}
