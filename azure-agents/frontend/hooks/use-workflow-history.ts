"use client"

import { useState, useEffect, useCallback } from "react"

const API_PROXY = "/api/proxy"

export interface WorkflowRun {
    id: string
    type: string
    timestamp: string
    status: string
    triggered_by?: string
    result: {
        products_analyzed?: number
        orders_recommended?: number
        orders_created?: number
        total_value?: number
        elapsed_seconds?: number
        requires_approval?: boolean
        workflow_id?: string
    }
}

export function useWorkflowHistory() {
    const [history, setHistory] = useState<WorkflowRun[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const fetchHistory = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const response = await fetch(`${API_PROXY}/api/workflows/history`)
            if (!response.ok) {
                if (response.status === 404) {
                    setHistory([])
                    return
                }
                throw new Error(`HTTP ${response.status}`)
            }
            const data = await response.json()
            setHistory(Array.isArray(data) ? data : [])
        } catch (err) {
            console.error("[SupplyMind] Error fetching history:", err)
            setError(err instanceof Error ? err.message : "Failed to fetch history")
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchHistory()
        // Poll every 30s
        const interval = setInterval(fetchHistory, 30000)
        return () => clearInterval(interval)
    }, [fetchHistory])

    return {
        history,
        loading,
        error,
        refresh: fetchHistory
    }
}
