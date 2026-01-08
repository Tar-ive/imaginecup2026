// Real backend API client for SupplyMind using Next.js API proxy
const API_PROXY = "/api/proxy"

export async function fetchProducts() {
  try {
    const response = await fetch(`${API_PROXY}/products`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    console.error("[v0] Error fetching products:", error)
    return { products: [] }
  }
}

export async function fetchSuppliers() {
  try {
    const response = await fetch(`${API_PROXY}/suppliers`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    console.error("[v0] Error fetching suppliers:", error)
    return { suppliers: [] }
  }
}

export async function fetchPrices(asin: string) {
  try {
    const response = await fetch(`${API_PROXY}/prices/live-amazon/${asin}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    console.error("[v0] Error fetching prices for", asin, error)
    return null
  }
}

export async function fetchOrders() {
  try {
    const response = await fetch(`${API_PROXY}/orders`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    console.error("[v0] Error fetching orders:", error)
    return { purchase_orders: [] }
  }
}

export async function triggerWorkflow() {
  try {
    const response = await fetch(`${API_PROXY}/api/workflows/optimize-inventory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    console.error("[v0] Error triggering workflow:", error)
    return null
  }
}
