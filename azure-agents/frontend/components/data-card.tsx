"use client"

import { useSupplyChainMetrics } from "@/hooks/use-supply-chain-metrics"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SupplyChainRadar } from "@/components/supply-chain-radar"
import { Badge } from "@/components/ui/badge"
import {
  DollarSign,
  Package,
  TrendingUp,
  AlertCircle,
  Truck,
  ShoppingCart,
  RefreshCw
} from "lucide-react"

export function DataCard() {
  const { metrics, loading, error } = useSupplyChainMetrics()

  if (loading) {
    return (
      <Card className="border-2" style={{ borderColor: "#bdc3c7" }}>
        <CardHeader style={{ backgroundColor: "#2c3e50" }}>
          <CardTitle className="text-white">Supply Chain Analytics</CardTitle>
          <CardDescription className="text-gray-300">Real-time inventory & metrics</CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex items-center justify-center py-12">
            <RefreshCw size={24} className="animate-spin text-gray-400" />
            <span className="ml-2 text-gray-500">Loading data...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-2" style={{ borderColor: "#bdc3c7" }}>
      {/* Header */}
      <CardHeader style={{ backgroundColor: "#2c3e50" }}>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-white">Supply Chain Analytics</CardTitle>
            <CardDescription className="text-gray-300">Real-time inventory & metrics</CardDescription>
          </div>
          <Badge style={{ backgroundColor: "#2ecc71" }} className="text-white">
            Live
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-6 space-y-6">
        {/* Error Banner */}
        {error && (
          <div
            className="p-3 rounded-lg flex items-start gap-2"
            style={{ backgroundColor: "#fef3cd" }}
          >
            <AlertCircle size={16} style={{ color: "#f39c12", marginTop: 2 }} />
            <p className="text-sm" style={{ color: "#856404" }}>
              Some data may be unavailable: {error}
            </p>
          </div>
        )}

        {/* KPI Cards - 2x3 Grid */}
        <div className="grid grid-cols-2 gap-3">
          {/* Total Inventory Value */}
          <div className="p-4 rounded-lg" style={{ backgroundColor: "#ecf0f1" }}>
            <div className="flex items-center gap-2 mb-2">
              <DollarSign size={18} style={{ color: "#f39c12" }} />
              <p className="text-xs text-gray-600">Inventory Value</p>
            </div>
            <p className="text-xl font-bold" style={{ color: "#2c3e50" }}>
              ${(metrics?.totalInventoryValue || 0).toLocaleString("en-US", {
                maximumFractionDigits: 0,
              })}
            </p>
          </div>

          {/* Total Products */}
          <div className="p-4 rounded-lg" style={{ backgroundColor: "#ecf0f1" }}>
            <div className="flex items-center gap-2 mb-2">
              <Package size={18} style={{ color: "#3498db" }} />
              <p className="text-xs text-gray-600">Total SKUs</p>
            </div>
            <p className="text-xl font-bold" style={{ color: "#2c3e50" }}>
              {metrics?.totalProducts || 0}
            </p>
          </div>

          {/* Active Suppliers */}
          <div className="p-4 rounded-lg" style={{ backgroundColor: "#ecf0f1" }}>
            <div className="flex items-center gap-2 mb-2">
              <Truck size={18} style={{ color: "#27ae60" }} />
              <p className="text-xs text-gray-600">Suppliers</p>
            </div>
            <p className="text-xl font-bold" style={{ color: "#2c3e50" }}>
              {metrics?.activeSuppliers || 0}
            </p>
          </div>

          {/* Low Stock Alerts */}
          <div className="p-4 rounded-lg" style={{ backgroundColor: "#ecf0f1" }}>
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle size={18} style={{ color: "#e74c3c" }} />
              <p className="text-xs text-gray-600">Low Stock</p>
            </div>
            <p className="text-xl font-bold" style={{ color: metrics?.lowStockCount ? "#e74c3c" : "#2c3e50" }}>
              {metrics?.lowStockCount || 0}
            </p>
          </div>

          {/* Pending Orders */}
          <div className="p-4 rounded-lg" style={{ backgroundColor: "#ecf0f1" }}>
            <div className="flex items-center gap-2 mb-2">
              <ShoppingCart size={18} style={{ color: "#9b59b6" }} />
              <p className="text-xs text-gray-600">Pending Orders</p>
            </div>
            <p className="text-xl font-bold" style={{ color: "#2c3e50" }}>
              {metrics?.pendingOrders || 0}
            </p>
          </div>

          {/* Stockout Risk */}
          <div className="p-4 rounded-lg" style={{ backgroundColor: "#ecf0f1" }}>
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={18} style={{ color: "#f39c12" }} />
              <p className="text-xs text-gray-600">Stockout Risk</p>
            </div>
            <p className="text-xl font-bold" style={{ color: "#2c3e50" }}>
              {metrics?.stockoutRisk || 0}%
            </p>
          </div>
        </div>

        {/* Radar Chart */}
        <div className="border rounded-lg p-4" style={{ borderColor: "#bdc3c7", backgroundColor: "#f8f9fa" }}>
          <p className="text-sm font-semibold mb-4" style={{ color: "#2c3e50" }}>
            Supply Chain Health
          </p>
          <SupplyChainRadar
            data={{
              inventoryTurnover: metrics?.inventoryTurnover || 0,
              demandAccuracy: metrics?.demandAccuracy || 0,
              supplierPerformance: metrics?.supplierPerformance || 0,
              priceCompetitiveness: metrics?.priceCompetitiveness || 0,
              stockoutRisk: metrics?.stockoutRisk || 0,
            }}
          />
        </div>

        {/* Integration Hub */}
        <div className="border-t pt-4" style={{ borderColor: "#bdc3c7" }}>
          <p className="text-sm font-semibold mb-3" style={{ color: "#2c3e50" }}>
            Data Sources
          </p>
          <div className="grid grid-cols-3 gap-2">
            {[
              { name: "Amazon API", status: "live" },
              { name: "PostgreSQL", status: "live" },
              { name: "MCP Tools", status: "live" },
              { name: "Shopify", status: "coming_soon" },
              { name: "SAP", status: "coming_soon" },
              { name: "EDI", status: "coming_soon" },
            ].map((integration) => (
              <div
                key={integration.name}
                className="p-2 rounded-lg text-center"
                style={{ backgroundColor: "#ecf0f1" }}
              >
                <p className="text-xs font-medium" style={{ color: "#2c3e50" }}>
                  {integration.name}
                </p>
                <Badge
                  variant="outline"
                  className="mt-1 text-xs"
                  style={{
                    backgroundColor: integration.status === "live" ? "#2ecc71" : "#95a5a6",
                    color: "white",
                    border: "none",
                  }}
                >
                  {integration.status === "live" ? "Live" : "Soon"}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
