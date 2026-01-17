"use client"

import { useState, useEffect, useCallback } from "react"
import type { PendingApproval } from "@/components/approval-queue"

const API_PROXY = "/api/proxy"

export function useApprovals() {
    const [approvals, setApprovals] = useState<PendingApproval[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const fetchApprovals = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const response = await fetch(`${API_PROXY}/api/workflows/pending-approvals`)
            if (!response.ok) {
                // Endpoint might not exist yet - that's okay
                if (response.status === 404) {
                    console.log("[SupplyMind] Pending approvals endpoint not implemented yet")
                    setApprovals([])
                    return
                }
                throw new Error(`HTTP ${response.status}`)
            }
            const data = await response.json()
            setApprovals(Array.isArray(data) ? data : data.pending || [])
        } catch (err) {
            console.error("[SupplyMind] Error fetching approvals:", err)
            setError(err instanceof Error ? err.message : "Failed to fetch approvals")
            // Don't clear approvals on error to preserve UI state
        } finally {
            setLoading(false)
        }
    }, [])

    const approve = useCallback(async (workflowId: string) => {
        try {
            const response = await fetch(
                `${API_PROXY}/api/workflows/approvals/${workflowId}/approve`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({})
                }
            )
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }
            // Remove from local state optimistically
            setApprovals(prev => prev.filter(a => a.workflow_id !== workflowId))
            // Refresh to get updated list
            await fetchApprovals()
        } catch (err) {
            console.error("[SupplyMind] Error approving workflow:", err)
            throw err
        }
    }, [fetchApprovals])

    const reject = useCallback(async (workflowId: string, reason?: string) => {
        try {
            // Reason is optional and not currently used by backend
            const response = await fetch(
                `${API_PROXY}/api/workflows/approvals/${workflowId}/reject`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ reason })
                }
            )
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }
            // Remove from local state optimistically
            setApprovals(prev => prev.filter(a => a.workflow_id !== workflowId))
            // Refresh to get updated list
            await fetchApprovals()
        } catch (err) {
            console.error("[SupplyMind] Error rejecting workflow:", err)
            throw err
        }
    }, [fetchApprovals])

    // Initial fetch
    useEffect(() => {
        fetchApprovals()
    }, [fetchApprovals])

    // Poll for updates every 30 seconds (reduced from 10s to prevent UI flicker)
    useEffect(() => {
        const interval = setInterval(fetchApprovals, 30000)
        return () => clearInterval(interval)
    }, [fetchApprovals])

    return {
        approvals,
        loading,
        error,
        approve,
        reject,
        refresh: fetchApprovals,
    }
}
