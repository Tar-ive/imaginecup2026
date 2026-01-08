"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
    Package,
    TrendingUp,
    DollarSign,
    ShoppingCart,
    Search,
    BarChart3,
    Wallet,
    LineChart
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

    const groupedTriggers = WORKFLOW_TRIGGERS.reduce((acc, trigger) => {
        if (!acc[trigger.category]) {
            acc[trigger.category] = []
        }
        acc[trigger.category].push(trigger)
        return acc
    }, {} as Record<string, WorkflowTrigger[]>)

    return (
        <div className="space-y-4">
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
                                    onClick={() => onTrigger(trigger.id, trigger.params)}
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
