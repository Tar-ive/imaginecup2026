"use client"

import { useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Play,
  Square,
  Bot,
  ClipboardCheck,
  Workflow,
  AlertCircle,
  Clock
} from "lucide-react"

import { useWorkflowStream } from "@/hooks/use-workflow-stream"
import { useApprovals } from "@/hooks/use-approvals"
import { WorkflowTriggers } from "@/components/workflow-triggers"
import { AgentActivityPanel } from "@/components/agent-activity-panel"
import { ApprovalQueue } from "@/components/approval-queue"
import { WorkflowHistory } from "@/components/workflow-history"

export function WorkflowEngineCard() {
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | undefined>()
  const [workflowUrl, setWorkflowUrl] = useState("")

  const { events, isActive, error, start, stop } = useWorkflowStream(workflowUrl)
  const {
    approvals,
    loading: approvalsLoading,
    approve,
    reject,
    refresh: refreshApprovals
  } = useApprovals()

  const handleTriggerWorkflow = useCallback((workflowId: string, params?: Record<string, any>) => {
    setActiveWorkflowId(workflowId)

    // Build URL based on workflow type
    let url = "/api/proxy-stream/api/workflows/optimize-inventory/stream"
    const queryParams = new URLSearchParams()

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        queryParams.append(key, String(value))
      })
    }

    // Different workflow types map to the same backend endpoint for now
    // Future: Add specific endpoints per workflow type
    switch (workflowId) {
      case "optimize-all":
        queryParams.set("include_all_products", "true")
        break
      case "low-stock":
        queryParams.set("include_all_products", "false")
        break
      case "generate-orders":
        queryParams.set("auto_create_orders", "false")
        break
      case "price-check":
      case "trending-segments":
      case "market-analysis":
      case "supplier-comparison":
      case "margin-analysis":
      case "cash-position":
        // These use the chat endpoint for natural language queries
        // For now, they all route to the optimization workflow
        // TODO: Implement specific endpoints for each workflow type
        break
    }

    const queryString = queryParams.toString()
    if (queryString) {
      url += `?${queryString}`
    }

    setWorkflowUrl(url)

    // Start the workflow after URL is set
    setTimeout(() => start(), 100)
  }, [start])

  const handleStop = useCallback(() => {
    stop()
    setActiveWorkflowId(undefined)
  }, [stop])

  return (
    <Card className="border-2 h-full" style={{ borderColor: "#bdc3c7" }}>
      {/* Header */}
      <CardHeader style={{ backgroundColor: "#2c3e50" }}>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-white flex items-center gap-2">
              <Workflow size={20} />
              Workflow Engine
            </CardTitle>
            <CardDescription className="text-gray-300">
              AI agent orchestration & human-in-the-loop approvals
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {isActive && (
              <Badge
                className="animate-pulse"
                style={{ backgroundColor: "#2ecc71", color: "white" }}
              >
                Running
              </Badge>
            )}
            {approvals.length > 0 && (
              <Badge style={{ backgroundColor: "#f39c12", color: "white" }}>
                {approvals.length} Pending
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <Tabs defaultValue="triggers" className="w-full">
          <TabsList className="w-full rounded-none border-b" style={{ borderColor: "#e0e0e0" }}>
            <TabsTrigger value="triggers" className="flex-1 gap-2">
              <Play size={14} />
              Workflows
            </TabsTrigger>
            <TabsTrigger value="activity" className="flex-1 gap-2">
              <Bot size={14} />
              Agent Activity
              {isActive && (
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              )}
            </TabsTrigger>
            <TabsTrigger value="approvals" className="flex-1 gap-2">
              <ClipboardCheck size={14} />
              Approvals
              {approvals.length > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 h-5 px-1.5"
                  style={{ backgroundColor: "#f39c12", color: "white" }}
                >
                  {approvals.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Workflow Triggers Tab */}
          <TabsContent value="triggers" className="p-4 mt-0">
            {isActive && (
              <div
                className="mb-4 p-3 rounded-lg flex items-center justify-between"
                style={{ backgroundColor: "#d5f5e3" }}
              >
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-sm font-medium" style={{ color: "#27ae60" }}>
                    Workflow running: {activeWorkflowId}
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleStop}
                  style={{ borderColor: "#e74c3c", color: "#e74c3c" }}
                >
                  <Square size={14} className="mr-1" />
                  Stop
                </Button>
              </div>
            )}

            <WorkflowTriggers
              onTrigger={handleTriggerWorkflow}
              isRunning={isActive}
              activeWorkflowId={activeWorkflowId}
            />
          </TabsContent>

          {/* Agent Activity Tab */}
          <TabsContent value="activity" className="p-4 mt-0">
            {error && (
              <div
                className="mb-4 p-3 rounded-lg flex items-start gap-2"
                style={{ backgroundColor: "#fadbd8" }}
              >
                <AlertCircle size={16} style={{ color: "#c0392b", marginTop: 2 }} />
                <div>
                  <p className="text-sm font-medium" style={{ color: "#c0392b" }}>
                    Connection Error
                  </p>
                  <p className="text-xs" style={{ color: "#c0392b" }}>
                    {error}
                  </p>
                </div>
              </div>
            )}

            <AgentActivityPanel
              events={events as any}
              isActive={isActive}
            />
          </TabsContent>

          {/* Approvals Tab */}
          <TabsContent value="approvals" className="p-4 mt-0">
            <ApprovalQueue
              approvals={approvals}
              onApprove={approve}
              onReject={reject}
              onRefresh={refreshApprovals}
              isLoading={approvalsLoading}
            />
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history" className="p-4 mt-0">
            <WorkflowHistory />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
