"use client"

import { useWorkflowHistory, WorkflowRun } from "@/hooks/use-workflow-history"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    Clock,
    CheckCircle,
    AlertCircle,
    PlayCircle,
    RefreshCw,
    UserCheck,
    Package,
    DollarSign,
    History
} from "lucide-react"

export function HistoryPanel() {
    const { history, loading, refresh } = useWorkflowHistory()

    const formatTime = (iso: string) => {
        const date = new Date(iso)
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(val)
    }

    // Get recent 10 history items
    const recentHistory = history.slice().reverse().slice(0, 10)

    // Calculate summary stats
    const totalWorkflows = history.length
    const totalApproved = history.filter(h => h.triggered_by === 'user_approval').length
    const totalValue = history
        .filter(h => h.result.total_value && typeof h.result.total_value === 'number')
        .reduce((sum, h) => sum + (h.result.total_value || 0), 0)

    return (
        <Card className="h-full">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <History size={20} style={{ color: "#9b59b6" }} />
                        Workflow History
                    </CardTitle>
                    <Button variant="ghost" size="sm" onClick={refresh} disabled={loading}>
                        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {/* Summary Stats */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="p-3 rounded-lg bg-blue-50 text-center">
                        <div className="text-2xl font-bold text-blue-600">{totalWorkflows}</div>
                        <div className="text-xs text-blue-800">Total Runs</div>
                    </div>
                    <div className="p-3 rounded-lg bg-green-50 text-center">
                        <div className="text-2xl font-bold text-green-600">{totalApproved}</div>
                        <div className="text-xs text-green-800">Approved</div>
                    </div>
                    <div className="p-3 rounded-lg bg-purple-50 text-center">
                        <div className="text-lg font-bold text-purple-600">{formatCurrency(totalValue)}</div>
                        <div className="text-xs text-purple-800">Total Value</div>
                    </div>
                </div>

                {/* History List */}
                <ScrollArea className="h-[350px]">
                    <div className="space-y-3 pr-4">
                        {loading && recentHistory.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">Loading...</div>
                        ) : recentHistory.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                                No workflow history yet. Run a workflow to see results.
                            </div>
                        ) : (
                            recentHistory.map((run, idx) => (
                                <div
                                    key={run.id || idx}
                                    className="p-3 rounded-lg border bg-white shadow-sm hover:shadow-md transition-shadow"
                                >
                                    <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            {run.triggered_by === 'user_approval' ? (
                                                <div className="p-1.5 rounded bg-green-100">
                                                    <UserCheck size={14} className="text-green-600" />
                                                </div>
                                            ) : (
                                                <div className="p-1.5 rounded bg-blue-100">
                                                    <PlayCircle size={14} className="text-blue-600" />
                                                </div>
                                            )}
                                            <span className="font-medium text-sm">
                                                {run.triggered_by === 'user_approval'
                                                    ? "Order Approved"
                                                    : "Optimization Run"}
                                            </span>
                                        </div>
                                        <span className="text-xs text-gray-500">
                                            {formatTime(run.timestamp)}
                                        </span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        {run.result.products_analyzed !== undefined &&
                                            run.result.products_analyzed !== "N/A (Pending Approval)" && (
                                                <div className="flex items-center gap-1 text-gray-600">
                                                    <Package size={12} />
                                                    {run.result.products_analyzed} products
                                                </div>
                                            )}
                                        {run.result.orders_recommended !== undefined && (
                                            <div className="flex items-center gap-1 text-gray-600">
                                                {run.result.orders_recommended} orders
                                            </div>
                                        )}
                                        {run.result.orders_created !== undefined && (
                                            <div className="flex items-center gap-1 text-green-600">
                                                <CheckCircle size={12} />
                                                {run.result.orders_created} POs created
                                            </div>
                                        )}
                                        {run.result.total_value !== undefined && run.result.total_value > 0 && (
                                            <div className="flex items-center gap-1 font-semibold text-gray-800">
                                                <DollarSign size={12} />
                                                {formatCurrency(run.result.total_value)}
                                            </div>
                                        )}
                                    </div>

                                    {run.result.requires_approval && !run.triggered_by && (
                                        <Badge
                                            variant="outline"
                                            className="mt-2 text-orange-600 border-orange-200 bg-orange-50"
                                        >
                                            Pending Approval
                                        </Badge>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    )
}
