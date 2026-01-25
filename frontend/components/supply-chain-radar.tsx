"use client"

import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts"

interface RadarProps {
  data?: {
    inventoryTurnover: number
    demandAccuracy: number
    supplierPerformance: number
    priceCompetitiveness: number
    stockoutRisk: number
  }
}

export function SupplyChainRadar({ data }: RadarProps) {
  // Convert inventoryTurnover ratio (typically 1-10) to a 0-100 scale
  // A turnover of 5 is considered good (maps to ~75%), 10 is excellent (100%)
  const normalizedTurnover = Math.min(100, ((data?.inventoryTurnover || 4.2) / 8) * 100)

  const radarData = [
    { name: "Inventory Turnover", value: Math.round(normalizedTurnover) },
    { name: "Demand Accuracy", value: data?.demandAccuracy || 87 },
    { name: "Supplier Performance", value: data?.supplierPerformance || 82 },
    { name: "Price Competitiveness", value: data?.priceCompetitiveness || 92 },
    { name: "Stockout Prevention", value: Math.max(0, 100 - (data?.stockoutRisk || 15)) },
  ]

  return (
    <div className="h-full">
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={radarData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <PolarGrid stroke="#bdc3c7" />
          <PolarAngleAxis dataKey="name" tick={{ fill: "#2c3e50", fontSize: 12 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#bdc3c7", fontSize: 10 }} />
          <Radar name="Supply Chain Health" dataKey="value" stroke="#3498db" fill="#3498db" fillOpacity={0.6} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
