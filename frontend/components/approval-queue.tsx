"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { OrderSummary } from "./order-summary"
import {
    CheckCircle,
    XCircle,
    Clock,
    Package,
    DollarSign,
    AlertTriangle,
    ChevronDown,
    ChevronUp,
    RefreshCw,
    FileText,
    Users
} from "lucide-react"

export interface PendingApproval {
    workflow_id: string
    checkpoint_id: string
    kind: string
    message: string
    context: {
        order_id?: string
        supplier?: string
        supplier_name?: string
        items?: Array<{
            asin: string
            title?: string
            quantity: number
            unit_price: number
        }>
        total?: number
        reason?: string
        // Negotiation-specific
        session_id?: string
        savings_percent?: number
        rounds_completed?: number
        email_summary?: Array<{
            direction: 'sent' | 'received'
            round: number
            subject?: string
            offer?: number
        }>
        ap2_mandate_preview?: {
            mandate_id: string
            amount: number
            currency: string
            supplier_id: string
            status: string
            expires_in: string
        }
    }
    type?: string
    created_at: string
}

interface ApprovalSuccessState {
    ordersCreated: number
    totalValue: number
    orderIds: string[]
}

interface ApprovalQueueProps {
    approvals: PendingApproval[]
    onApprove: (workflowId: string) => Promise<void>
    onReject: (workflowId: string, reason?: string) => Promise<void>
    onRefresh: () => void
    isLoading: boolean
}

export function ApprovalQueue({
    approvals,
    onApprove,
    onReject,
    onRefresh,
    isLoading
}: ApprovalQueueProps) {
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
    const [processingIds, setProcessingIds] = useState<Set<string>>(new Set())
    const [successState, setSuccessState] = useState<ApprovalSuccessState | null>(null)

    const toggleExpand = (id: string) => {
        const newExpanded = new Set(expandedItems)
        if (newExpanded.has(id)) {
            newExpanded.delete(id)
        } else {
            newExpanded.add(id)
        }
        setExpandedItems(newExpanded)
    }

    const handleApprove = async (workflowId: string, approval: PendingApproval) => {
        setProcessingIds(prev => new Set(prev).add(workflowId))
        try {
            await onApprove(workflowId)
            // Show success state with order details
            setSuccessState({
                ordersCreated: 1,
                totalValue: approval.context.total || 0,
                orderIds: [approval.context.order_id || `PO-${Date.now()}`]
            })
        } finally {
            setProcessingIds(prev => {
                const next = new Set(prev)
                next.delete(workflowId)
                return next
            })
        }
    }

    const handleReject = async (workflowId: string) => {
        setProcessingIds(prev => new Set(prev).add(workflowId))
        try {
            await onReject(workflowId)
        } finally {
            setProcessingIds(prev => {
                const next = new Set(prev)
                next.delete(workflowId)
                return next
            })
        }
    }

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(amount)
    }

    const formatTimeAgo = (dateString: string) => {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)

        if (diffMins < 1) return "Just now"
        if (diffMins < 60) return `${diffMins}m ago`
        const diffHours = Math.floor(diffMins / 60)
        if (diffHours < 24) return `${diffHours}h ago`
        return `${Math.floor(diffHours / 24)}d ago`
    }

    // Show Order Summary if we just approved something
    if (successState) {
        return (
            <div className="space-y-3">
                <OrderSummary
                    ordersCreated={successState.ordersCreated}
                    totalValue={successState.totalValue}
                    orderIds={successState.orderIds}
                    onClose={() => setSuccessState(null)}
                    onSetRepeat={(repeat) => {
                        // TODO: Store user preference for auto-approval
                        console.log("User wants auto-repeat:", repeat)
                    }}
                />
                {approvals.length > 0 && (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSuccessState(null)}
                        className="w-full"
                    >
                        View {approvals.length} more pending approval{approvals.length > 1 ? 's' : ''}
                    </Button>
                )}
            </div>
        )
    }

    if (approvals.length === 0) {
        return (
            <div className="text-center py-6">
                <CheckCircle size={32} className="mx-auto mb-2" style={{ color: "#27ae60", opacity: 0.5 }} />
                <p className="text-sm text-gray-500">No pending approvals</p>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onRefresh}
                    className="mt-2"
                    disabled={isLoading}
                >
                    <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
                    <span className="ml-1">Refresh</span>
                </Button>
            </div>
        )
    }

    return (
        <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-sm" style={{ color: "#2c3e50" }}>
                        Pending Approvals
                    </h3>
                    <Badge
                        style={{ backgroundColor: "#f39c12", color: "white" }}
                    >
                        {approvals.length}
                    </Badge>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onRefresh}
                    disabled={isLoading}
                >
                    <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
                </Button>
            </div>

            {/* Approval Cards */}
            <ScrollArea className="max-h-[400px]">
                <div className="space-y-3">
                    {approvals.map((approval) => {
                        const isExpanded = expandedItems.has(approval.workflow_id)
                        const isProcessing = processingIds.has(approval.workflow_id)

                        return (
                            <div
                                key={approval.workflow_id}
                                className="border rounded-lg overflow-hidden"
                                style={{ borderColor: "#f39c12", borderLeftWidth: 4 }}
                            >
                                {/* Approval Header */}
                                <div className="p-3 bg-white">
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-start gap-3">
                                            <div
                                                className="p-2 rounded-lg flex-shrink-0"
                                                style={{ backgroundColor: "#fef3cd" }}
                                            >
                                                <AlertTriangle size={18} style={{ color: "#f39c12" }} />
                                            </div>
                                            <div>
                                                <p className="font-medium text-sm" style={{ color: "#2c3e50" }}>
                                                    {approval.message}
                                                </p>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <Clock size={12} style={{ color: "#95a5a6" }} />
                                                    <span className="text-xs text-gray-500">
                                                        {formatTimeAgo(approval.created_at)}
                                                    </span>
                                                    {approval.context.supplier && (
                                                        <>
                                                            <span className="text-gray-300">•</span>
                                                            <span className="text-xs text-gray-500">
                                                                {approval.context.supplier}
                                                            </span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        {approval.context.total && (
                                            <div className="text-right">
                                                <p className="font-bold text-lg" style={{ color: "#2c3e50" }}>
                                                    {formatCurrency(approval.context.total)}
                                                </p>
                                                <p className="text-xs text-gray-500">Total</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Quick Actions */}
                                    <div className="flex items-center gap-2 mt-3">
                                        <Button
                                            size="sm"
                                            className="flex-1 text-white"
                                            style={{ backgroundColor: "#27ae60" }}
                                            onClick={() => handleApprove(approval.workflow_id, approval)}
                                            disabled={isProcessing}
                                        >
                                            <CheckCircle size={14} className="mr-1" />
                                            Approve
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="flex-1"
                                            style={{ borderColor: "#e74c3c", color: "#e74c3c" }}
                                            onClick={() => handleReject(approval.workflow_id)}
                                            disabled={isProcessing}
                                        >
                                            <XCircle size={14} className="mr-1" />
                                            Reject
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => toggleExpand(approval.workflow_id)}
                                        >
                                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                        </Button>
                                    </div>
                                </div>

                                {/* Expanded Details */}
                                {isExpanded && (
                                    <div
                                        className="border-t p-3"
                                        style={{ backgroundColor: "#f8f9fa", borderColor: "#e0e0e0" }}
                                    >
                                        {/* Negotiation-specific info */}
                                        {approval.type === "negotiation_approval" && (
                                            <>
                                                {/* Savings badge */}
                                                {approval.context.savings_percent && (
                                                    <div className="flex items-center gap-2 mb-3">
                                                        <Badge style={{ backgroundColor: "#27ae60", color: "white" }}>
                                                            {approval.context.savings_percent}% savings
                                                        </Badge>
                                                        <span className="text-xs text-gray-500">
                                                            after {approval.context.rounds_completed} rounds
                                                        </span>
                                                    </div>
                                                )}

                                                {/* Email Summary */}
                                                {approval.context.email_summary && (
                                                    <div className="mb-3">
                                                        <p className="text-xs font-semibold mb-2" style={{ color: "#7f8c8d" }}>
                                                            EMAIL CONVERSATION
                                                        </p>
                                                        <div className="space-y-1">
                                                            {approval.context.email_summary.map((email, idx) => (
                                                                <div
                                                                    key={idx}
                                                                    className="flex items-center gap-2 text-xs"
                                                                >
                                                                    <FileText size={12} style={{ color: email.direction === 'sent' ? '#3498db' : '#27ae60' }} />
                                                                    <span style={{ color: email.direction === 'sent' ? '#3498db' : '#27ae60' }}>
                                                                        {email.direction === 'sent' ? '→ Sent:' : '← Received:'}
                                                                    </span>
                                                                    <span className="text-gray-600">
                                                                        {email.subject || (email.offer ? `Offer: ${formatCurrency(email.offer)}` : `Round ${email.round}`)}
                                                                    </span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* AP2 Mandate Preview */}
                                                {approval.context.ap2_mandate_preview && (
                                                    <div className="mb-3">
                                                        <p className="text-xs font-semibold mb-2" style={{ color: "#7f8c8d" }}>
                                                            AP2 MANDATE PREVIEW
                                                        </p>
                                                        <div className="p-2 bg-white rounded border text-xs" style={{ borderColor: "#e0e0e0" }}>
                                                            <div className="grid grid-cols-2 gap-1">
                                                                <span className="text-gray-500">Mandate ID:</span>
                                                                <span className="font-mono">{approval.context.ap2_mandate_preview.mandate_id}</span>
                                                                <span className="text-gray-500">Amount:</span>
                                                                <span className="font-medium">{formatCurrency(approval.context.ap2_mandate_preview.amount)}</span>
                                                                <span className="text-gray-500">Status:</span>
                                                                <span>{approval.context.ap2_mandate_preview.status}</span>
                                                                <span className="text-gray-500">Expires:</span>
                                                                <span>{approval.context.ap2_mandate_preview.expires_in}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </>
                                        )}

                                        {/* Order Items (for both regular and negotiation) */}
                                        {approval.context.items && approval.context.items.length > 0 && (
                                            <>
                                                <p className="text-xs font-semibold mb-2" style={{ color: "#7f8c8d" }}>
                                                    ORDER ITEMS ({approval.context.items.length})
                                                </p>
                                                <ScrollArea className="h-[150px] overflow-auto">
                                                    <div className="space-y-2 pr-2">
                                                        {approval.context.items.map((item, idx) => (
                                                            <div
                                                                key={idx}
                                                                className="flex items-center justify-between p-2 bg-white rounded border"
                                                                style={{ borderColor: "#e0e0e0" }}
                                                            >
                                                                <div className="flex items-center gap-2">
                                                                    <Package size={14} style={{ color: "#95a5a6" }} />
                                                                    <div>
                                                                        <p className="text-sm font-medium" style={{ color: "#2c3e50" }}>
                                                                            {item.title || item.asin}
                                                                        </p>
                                                                        <p className="text-xs text-gray-500">
                                                                            ASIN: {item.asin}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                                <div className="text-right">
                                                                    <p className="text-sm font-medium" style={{ color: "#2c3e50" }}>
                                                                        {item.quantity} × {formatCurrency(item.unit_price)}
                                                                    </p>
                                                                    <p className="text-xs text-gray-500">
                                                                        {formatCurrency(item.quantity * item.unit_price)}
                                                                    </p>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </ScrollArea>
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            </ScrollArea>
        </div>
    )
}
