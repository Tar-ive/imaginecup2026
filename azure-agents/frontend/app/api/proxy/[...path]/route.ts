// Server-side proxy to handle CORS and forward requests to backend
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  // Next.js 15: params is now async and must be awaited
  const { path } = await params
  const pathString = path.join("/")

  try {
    const url = new URL(request.url)
    const queryString = url.search
    const backendUrl = `${BACKEND_URL}/${pathString}${queryString}`

    console.log("[v0] Proxying GET request to:", backendUrl)

    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    console.error("[v0] Proxy error:", error)
    return Response.json({ error: "Failed to fetch from backend" }, { status: 500 })
  }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  // Next.js 15: params is now async and must be awaited
  const { path } = await params
  const pathString = path.join("/")

  try {
    const body = await request.json()
    const backendUrl = `${BACKEND_URL}/${pathString}`

    console.log("[v0] Proxying POST request to:", backendUrl)

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    console.error("[v0] Proxy error:", error)
    return Response.json({ error: "Failed to fetch from backend" }, { status: 500 })
  }
}
