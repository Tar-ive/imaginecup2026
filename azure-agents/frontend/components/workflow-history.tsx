"use client"

import { useWorkflowHistory, WorkflowRun } from "@/hooks/use-workflow-history"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    Clock,
    CheckCircle,
    AlertCircle,
    PlayCircle,
    FileText,
    RefreshCw,
    UserCheck
} from "lucide-react"

export function WorkflowHistory() {
    const { history, loading, refresh } = useWorkflowHistory()

    const formatTime = (iso: string) => {
        return new Date(iso).toLocaleString()
    }

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val)
    }

    if (loading && history.length === 0) {
        return <div className="p-4 text-center text-gray-500">Loading history...</div>
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="font-semibold text-sm text-gray-700">Recent Activity</h3>
                <Button variant="ghost" size="sm" onClick={refresh}>
                    <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
                </Button>
            </div>

            <ScrollArea className="h-[400px] pr-4">
                <div className="space-y-4">
                    {history.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            No history available yet.
                        </div>
                    ) : (
                        history.slice().reverse().map((run, idx) => (
                            <div key={idx} className="border rounded-lg p-3 bg-white shadow-sm">
                                <div className="flex items-start justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        {run.triggered_by === 'user_approval' ? (
                                            <UserCheck size={16} className="text-green-600" />
                                        ) : (
                                            <PlayCircle size={16} className="text-blue-600" />
                                        )}
                                        <span className="font-medium text-sm">
                                            {run.triggered_by === 'user_approval'
                                                ? "Order Approval"
                                                : "Optimization Run"}
                                        </span>
                                    </div>
                                    <span className="text-xs text-gray-500">{formatTime(run.timestamp)}</span>
                                </div>

                                <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                                    {run.result.products_analyzed !== undefined && (
                                        <div>Analyzed: {run.result.products_analyzed} items</div>
                                    )}
                                    {run.result.orders_recommended !== undefined && (
                                        <div>Recommended: {run.result.orders_recommended} orders</div>
                                    )}
                                    {run.result.orders_created !== undefined && (
                                        <div>Created: {run.result.orders_created} POs</div>
                                    )}
                                    {run.result.total_value !== undefined && (
                                        <div className="font-semibold text-gray-800">
                                            Value: {formatCurrency(run.result.total_value)}
                                        </div>
                                    )}
                                </div>

                                {run.result.requires_approval && (
                                    <Badge variant="outline" className="mt-2 text-orange-600 border-orange-200 bg-orange-50">
                                        Requires Approval
                                    </Badge>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </ScrollArea>
        </div>
    )
}
