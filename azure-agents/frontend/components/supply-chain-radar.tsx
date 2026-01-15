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
  const radarData = [
    { name: "Inventory Turnover", value: data?.inventoryTurnover || 75 },
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
