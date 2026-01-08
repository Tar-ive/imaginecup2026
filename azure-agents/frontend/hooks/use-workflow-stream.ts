"use client"

import { useEffect, useRef, useState } from "react"

export interface WorkflowEvent {
  type: string
  data?: any
  timestamp: number
  stage?: string
  progress?: number
  message?: string
}

export function useWorkflowStream(workflowUrl: string) {
  const [events, setEvents] = useState<WorkflowEvent[]>([])
  const [isActive, setIsActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!isActive) return

    try {
      console.log("[v0] Opening SSE connection to:", workflowUrl)
      const eventSource = new EventSource(workflowUrl)
      eventSourceRef.current = eventSource

      eventSource.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log("[v0] SSE event received:", data.type)
          setEvents((prev) => [
            ...prev,
            {
              ...data,
              timestamp: Date.now(),
            },
          ])
        } catch (e) {
          console.error("[v0] Error parsing event:", e)
        }
      })

      eventSource.addEventListener("error", () => {
        console.error("[v0] SSE connection error")
        setError("Connection lost")
        eventSource.close()
        setIsActive(false)
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
    error,
    start,
    stop,
  }
}
