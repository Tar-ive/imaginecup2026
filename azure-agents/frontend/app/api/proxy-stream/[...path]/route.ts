// Server-side SSE proxy for streaming endpoints
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  // Next.js 15: params is now async and must be awaited
  const { path } = await params
  const pathString = path.join("/")

  // Preserve query string for streaming endpoints
  const url = new URL(request.url)
  const queryString = url.search
  const backendUrl = `${BACKEND_URL}/${pathString}${queryString}`

  console.log("[v0] Proxying SSE stream to:", backendUrl)

  try {
    const response = await fetch(backendUrl)

    if (!response.body) {
      return new Response("Stream unavailable", { status: 500 })
    }

    // Return the stream directly with SSE headers
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "Access-Control-Allow-Origin": "*",
      },
    })
  } catch (error) {
    console.error("[v0] SSE proxy error:", error)
    return new Response(`event: error\ndata: ${JSON.stringify({ error: "Stream failed" })}\n\n`, {
      headers: {
        "Content-Type": "text/event-stream",
      },
    })
  }
}
