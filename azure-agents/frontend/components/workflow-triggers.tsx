"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    Package,
    TrendingUp,
    DollarSign,
    ShoppingCart,
    Search,
    BarChart3,
    Wallet,
    LineChart,
    Settings2
} from "lucide-react"

interface WorkflowTrigger {
    id: string
    name: string
    description: string
    icon: React.ReactNode
    category: "inventory" | "market" | "financial"
    params?: Record<string, any>
}

const WORKFLOW_TRIGGERS: WorkflowTrigger[] = [
    // Inventory Workflows
    {
        id: "optimize-all",
        name: "Optimize All Inventory",
        description: "Run full optimization workflow across all products",
        icon: <Package size={20} />,
        category: "inventory",
        params: { include_all_products: true },
    },
    {
        id: "low-stock",
        name: "Analyze Low Stock",
        description: "Focus on products below reorder point",
        icon: <TrendingUp size={20} />,
        category: "inventory",
        params: { include_all_products: false },
    },
    {
        id: "price-check",
        name: "Price Check",
        description: "Scan all products for supplier price changes",
        icon: <DollarSign size={20} />,
        category: "inventory",
    },
    {
        id: "generate-orders",
        name: "Generate Orders",
        description: "Create purchase orders for products needing reorder",
        icon: <ShoppingCart size={20} />,
        category: "inventory",
        params: { auto_create_orders: false },
    },
    // Market Research Workflows  
    {
        id: "trending-segments",
        name: "Find Trending Segments",
        description: "Research trending market segments and auto-order weekly",
        icon: <Search size={20} />,
        category: "market",
    },
    {
        id: "market-analysis",
        name: "Market Analysis",
        description: "Analyze market trends and competitor positioning",
        icon: <BarChart3 size={20} />,
        category: "market",
    },
    // Financial Workflows
    {
        id: "supplier-comparison",
        name: "Supplier Comparison",
        description: "Compare supplier pricing, terms, and reliability",
        icon: <LineChart size={20} />,
        category: "financial",
    },
    {
        id: "margin-analysis",
        name: "Margin Impact Analysis",
        description: "Calculate margin impact of current prices and costs",
        icon: <DollarSign size={20} />,
        category: "financial",
    },
    {
        id: "cash-position",
        name: "Cash Position",
        description: "Current cash, pending payments, and cash flow forecast",
        icon: <Wallet size={20} />,
        category: "financial",
    },
]

interface WorkflowTriggersProps {
    onTrigger: (workflowId: string, params?: Record<string, any>) => void
    isRunning: boolean
    activeWorkflowId?: string
}

export function WorkflowTriggers({ onTrigger, isRunning, activeWorkflowId }: WorkflowTriggersProps) {
    // Control panel state
    const [maxProducts, setMaxProducts] = useState(20)
    const [forecastDays, setForecastDays] = useState(7)
    const [analysisScope, setAnalysisScope] = useState<"low-stock" | "all">("low-stock")
    const [showControls, setShowControls] = useState(false)

    const getCategoryColor = (category: string) => {
        switch (category) {
            case "inventory": return "#3498db"
            case "market": return "#9b59b6"
            case "financial": return "#27ae60"
            default: return "#95a5a6"
        }
    }

    const getCategoryLabel = (category: string) => {
        switch (category) {
            case "inventory": return "Inventory"
            case "market": return "Market Research"
            case "financial": return "Financial"
            default: return category
        }
    }

    const handleTrigger = (trigger: WorkflowTrigger) => {
        // Merge control panel params with trigger params
        const params = {
            ...trigger.params,
            max_products: maxProducts,
            forecast_days: forecastDays,
            include_all_products: analysisScope === "all",
        }
        onTrigger(trigger.id, params)
    }

    const groupedTriggers = WORKFLOW_TRIGGERS.reduce((acc, trigger) => {
        if (!acc[trigger.category]) {
            acc[trigger.category] = []
        }
        acc[trigger.category].push(trigger)
        return acc
    }, {} as Record<string, WorkflowTrigger[]>)

    return (
        <div className="space-y-4">
            {/* Control Panel */}
            <div className="border rounded-lg p-3 bg-gray-50" style={{ borderColor: "#e0e0e0" }}>
                <button
                    onClick={() => setShowControls(!showControls)}
                    className="flex items-center justify-between w-full text-left"
                >
                    <div className="flex items-center gap-2">
                        <Settings2 size={16} style={{ color: "#7f8c8d" }} />
                        <span className="text-sm font-medium" style={{ color: "#2c3e50" }}>
                            Workflow Settings
                        </span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                        {maxProducts} products • {forecastDays} days
                    </Badge>
                </button>

                {showControls && (
                    <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t" style={{ borderColor: "#e0e0e0" }}>
                        <div className="space-y-1">
                            <Label className="text-xs text-gray-500">Max Products</Label>
                            <Input
                                type="number"
                                min={1}
                                max={100}
                                value={maxProducts}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMaxProducts(Number(e.target.value))}
                                className="h-8"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs text-gray-500">Forecast Days</Label>
                            <Input
                                type="number"
                                min={1}
                                max={30}
                                value={forecastDays}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForecastDays(Number(e.target.value))}
                                className="h-8"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs text-gray-500">Analysis Scope</Label>
                            <select
                                value={analysisScope}
                                onChange={(e) => setAnalysisScope(e.target.value as "low-stock" | "all")}
                                className="w-full h-8 px-2 text-sm border rounded-md"
                                style={{ borderColor: "#e0e0e0" }}
                            >
                                <option value="low-stock">Low Stock Only</option>
                                <option value="all">All Products</option>
                            </select>
                        </div>
                    </div>
                )}
            </div>

            {/* Workflow Triggers */}
            {Object.entries(groupedTriggers).map(([category, triggers]) => (
                <div key={category}>
                    <div className="flex items-center gap-2 mb-2">
                        <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: getCategoryColor(category) }}
                        />
                        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#7f8c8d" }}>
                            {getCategoryLabel(category)}
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {triggers.map((trigger) => {
                            const isActive = activeWorkflowId === trigger.id
                            return (
                                <Button
                                    key={trigger.id}
                                    variant="outline"
                                    className="h-auto py-3 px-4 justify-start text-left bg-white hover:bg-gray-50 transition-all"
                                    style={{
                                        borderColor: isActive ? getCategoryColor(category) : "#e0e0e0",
                                        borderWidth: isActive ? 2 : 1,
                                    }}
                                    disabled={isRunning && !isActive}
                                    onClick={() => handleTrigger(trigger)}
                                >
                                    <div className="flex items-start gap-3 w-full">
                                        <div
                                            className="p-2 rounded-lg flex-shrink-0"
                                            style={{
                                                backgroundColor: `${getCategoryColor(category)}15`,
                                                color: getCategoryColor(category),
                                            }}
                                        >
                                            {trigger.icon}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <p className="font-medium text-sm" style={{ color: "#2c3e50" }}>
                                                    {trigger.name}
                                                </p>
                                                {isActive && (
                                                    <Badge
                                                        className="text-xs animate-pulse"
                                                        style={{ backgroundColor: getCategoryColor(category), color: "white" }}
                                                    >
                                                        Running
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-xs text-gray-500 mt-0.5 truncate">
                                                {trigger.description}
                                            </p>
                                        </div>
                                    </div>
                                </Button>
                            )
                        })}
                    </div>
                </div>
            ))}
        </div>
    )
}

