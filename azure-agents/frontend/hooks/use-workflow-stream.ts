"use client"

import { useEffect, useRef, useState } from "react"

export interface WorkflowEvent {
  event?: string  // Backend sends 'event' field
  type?: string   // Some events might use 'type'
  data?: any
  timestamp: number
  stage?: string
  progress?: number
  message?: string
  result?: any
  [key: string]: any  // Allow other fields
}

export function useWorkflowStream(workflowUrl: string) {
  const [events, setEvents] = useState<WorkflowEvent[]>([])
  const [isActive, setIsActive] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const hasCompletedRef = useRef(false)

  useEffect(() => {
    if (!isActive) return

    // Reset completion tracking when starting
    hasCompletedRef.current = false
    setIsComplete(false)

    try {
      console.log("[v0] Opening SSE connection to:", workflowUrl)
      const eventSource = new EventSource(workflowUrl)
      eventSourceRef.current = eventSource

      eventSource.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log("[v0] SSE event received:", data.event || data.type)

          const newEvent: WorkflowEvent = {
            ...data,
            timestamp: Date.now(),
          }
          setEvents((prev) => [...prev, newEvent])

          // Check if this is a completion event
          // Backend sends: {"event": "complete", ...}
          if (data.event === "complete" || data.type === "complete") {
            console.log("[v0] Workflow completed successfully")
            hasCompletedRef.current = true
            setIsComplete(true)
          }

          // Check for error event from backend
          if (data.event === "error" || data.type === "error") {
            console.error("[v0] Workflow error:", data.message)
            setError(data.message || "Workflow error")
          }
        } catch (e) {
          console.error("[v0] Error parsing event:", e)
        }
      })

      eventSource.addEventListener("error", () => {
        // Check if workflow completed successfully before connection closed
        if (hasCompletedRef.current) {
          console.log("[v0] SSE connection closed normally after completion")
          eventSource.close()
          setIsActive(false)
          // No error - this is normal behavior
        } else {
          console.error("[v0] SSE connection error before completion")
          setError("Connection lost before workflow completed")
          eventSource.close()
          setIsActive(false)
        }
      })

      return () => {
        eventSource.close()
      }
    } catch (e) {
      console.error("[v0] Failed to connect to workflow stream:", e)
      setError("Failed to connect to workflow stream")
      setIsActive(false)
    }
  }, [isActive, workflowUrl])

  const start = () => {
    setEvents([])
    setError(null)
    setIsComplete(false)
    hasCompletedRef.current = false
    setIsActive(true)
  }

  const stop = () => {
    setIsActive(false)
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }
  }

  return {
    events,
    isActive,
    isComplete,
    error,
    start,
    stop,
  }
}
