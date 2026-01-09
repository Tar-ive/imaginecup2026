"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
    Eye,
    EyeOff,
    Bot,
    TrendingUp,
    DollarSign,
    ShoppingCart,
    ChevronDown,
    ChevronUp,
    Clock,
    CheckCircle,
    AlertCircle,
    Loader2
} from "lucide-react"

export interface AgentEvent {
    type: string
    agent: string | null
    event: string
    timestamp: number
    data?: {
        agent?: string
        message?: string
        delta?: string
        output?: string
        status?: string
    }
}

interface AgentState {
    name: string
    status: "idle" | "active" | "completed" | "error" | "awaiting_approval"
    currentAction?: string
    events: AgentEvent[]
}

interface AgentActivityPanelProps {
    events: AgentEvent[]
    isActive: boolean
}

const AGENT_CONFIG: Record<string, {
    icon: React.ReactNode
    color: string
    label: string
}> = {
    OrchestratorAgent: {
        icon: <Bot size={16} />,
        color: "#2c3e50",
        label: "Orchestrator",
    },
    PriceMonitoringAgent: {
        icon: <DollarSign size={16} />,
        color: "#e74c3c",
        label: "Price Monitor",
    },
    DemandForecastingAgent: {
        icon: <TrendingUp size={16} />,
        color: "#3498db",
        label: "Demand Forecaster",
    },
    AutomatedOrderingAgent: {
        icon: <ShoppingCart size={16} />,
        color: "#27ae60",
        label: "Order Agent",
    },
    ManagerAgent: {
        icon: <Bot size={16} />,
        color: "#9b59b6",
        label: "Manager",
    },
}

function getAgentConfig(agentName: string) {
    return AGENT_CONFIG[agentName] || {
        icon: <Bot size={16} />,
        color: "#95a5a6",
        label: agentName || "Unknown Agent",
    }
}

export function AgentActivityPanel({ events, isActive }: AgentActivityPanelProps) {
    const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set())
    const [showAllEvents, setShowAllEvents] = useState(false)

    // Helper function to generate messages from workflow events
    const getWorkflowEventMessage = (eventType: string | undefined, event: any): string => {
        switch (eventType) {
            case "start":
                return "Starting workflow..."
            case "init":
                return "Initializing services..."
            case "products_loaded":
                return `Loaded ${event.count || 0} products for analysis`
            case "analyzing":
                return event.message || `Analyzing products... (${event.progress || 0}%)`
            case "forecasting_complete":
                return `Completed demand forecasting for ${event.count || 0} products`
            case "generating_orders":
                return event.message || "Generating order recommendations..."
            case "complete":
                const result = event.result
                if (result) {
                    return `✅ Complete: ${result.products_needing_reorder || 0} products need reorder, $${(result.total_recommended_value || 0).toFixed(2)} total`
                }
                return "Workflow completed"
            case "error":
                return event.message || "An error occurred"
            default:
                return event.message || eventType || "Processing..."
        }
    }

    // Group events by agent or workflow stage
    const agentStates = events.reduce((acc, event) => {
        // Handle workflow stream events (backend sends 'event' field: start, products_loaded, etc.)
        const workflowEvent = (event as any).event as string | undefined

        // Determine agent name - could be from agent field, data.agent, or workflow event type
        let agentName = event.agent || event.data?.agent

        // Map workflow events to pseudo-agents for display
        if (!agentName && workflowEvent) {
            switch (workflowEvent) {
                case "start":
                case "init":
                    agentName = "OrchestratorAgent"
                    break
                case "products_loaded":
                case "analyzing":
                case "forecasting_complete":
                    agentName = "DemandForecastingAgent"
                    break
                case "generating_orders":
                    agentName = "AutomatedOrderingAgent"
                    break
                case "complete":
                case "error":
                    agentName = "OrchestratorAgent"
                    break
                default:
                    agentName = "System"
            }
        }

        agentName = agentName || "System"

        if (!acc[agentName]) {
            acc[agentName] = {
                name: agentName,
                status: "idle" as const,
                events: [],
            }
        }

        // Transform workflow event to display format
        const displayEvent: AgentEvent = {
            ...event,
            event: workflowEvent || event.event || "Unknown",
            data: {
                ...event.data,
                message: event.data?.message || (event as any).message || getWorkflowEventMessage(workflowEvent, event),
            }
        }

        acc[agentName].events.push(displayEvent)

        // Update status based on event type (agent events)
        if (event.event === "AgentRun" || event.event === "AgentDelta") {
            acc[agentName].status = "active"
            acc[agentName].currentAction = event.data?.message?.slice(0, 100)
        } else if (event.event === "WorkflowComplete" || event.event === "SuperStepCompleted") {
            acc[agentName].status = "completed"
        } else if (event.event === "Error" || event.event === "WorkflowFailed") {
            acc[agentName].status = "error"
        }

        // Handle workflow stream events for status
        if (workflowEvent) {
            if (["start", "init", "products_loaded", "analyzing", "generating_orders"].includes(workflowEvent)) {
                acc[agentName].status = "active"
                acc[agentName].currentAction = getWorkflowEventMessage(workflowEvent, event)
            } else if (workflowEvent === "complete") {
                acc[agentName].status = "completed"
                acc[agentName].currentAction = "Workflow completed"
            } else if (workflowEvent === "error") {
                acc[agentName].status = "error"
                acc[agentName].currentAction = (event as any).message || "Error occurred"
            }
        }

        return acc
    }, {} as Record<string, AgentState>)


    const toggleAgent = (agentName: string) => {
        const newExpanded = new Set(expandedAgents)
        if (newExpanded.has(agentName)) {
            newExpanded.delete(agentName)
        } else {
            newExpanded.add(agentName)
        }
        setExpandedAgents(newExpanded)
    }

    const getStatusIcon = (status: AgentState["status"]) => {
        switch (status) {
            case "active":
                return <Loader2 size={14} className="animate-spin" style={{ color: "#3498db" }} />
            case "completed":
                return <CheckCircle size={14} style={{ color: "#27ae60" }} />
            case "error":
                return <AlertCircle size={14} style={{ color: "#e74c3c" }} />
            case "awaiting_approval":
                return <Clock size={14} style={{ color: "#f39c12" }} />
            default:
                return <Clock size={14} style={{ color: "#95a5a6" }} />
        }
    }

    const getStatusBadge = (status: AgentState["status"]) => {
        const styles: Record<string, { bg: string; text: string }> = {
            active: { bg: "#3498db", text: "Active" },
            completed: { bg: "#27ae60", text: "Done" },
            error: { bg: "#e74c3c", text: "Error" },
            awaiting_approval: { bg: "#f39c12", text: "Awaiting Approval" },
            idle: { bg: "#95a5a6", text: "Idle" },
        }
        const style = styles[status] || styles.idle
        return (
            <Badge
                className="text-xs"
                style={{ backgroundColor: style.bg, color: "white" }}
            >
                {style.text}
            </Badge>
        )
    }

    const agentList = Object.values(agentStates).filter(a => a.name !== "System")

    if (!isActive && agentList.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500">
                <Bot size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">Start a workflow to see agent activity</p>
            </div>
        )
    }

    return (
        <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-sm" style={{ color: "#2c3e50" }}>
                        Agent Activity
                    </h3>
                    {isActive && (
                        <div className="flex items-center gap-1">
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            <span className="text-xs text-gray-500">Live</span>
                        </div>
                    )}
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAllEvents(!showAllEvents)}
                    className="text-xs"
                >
                    {showAllEvents ? <EyeOff size={14} /> : <Eye size={14} />}
                    <span className="ml-1">{showAllEvents ? "Hide Raw" : "Show Raw"}</span>
                </Button>
            </div>

            {/* Agent Cards */}
            <div className="space-y-2">
                {agentList.map((agent) => {
                    const config = getAgentConfig(agent.name)
                    const isExpanded = expandedAgents.has(agent.name)

                    return (
                        <div
                            key={agent.name}
                            className="border rounded-lg overflow-hidden transition-all"
                            style={{
                                borderColor: agent.status === "active" ? config.color : "#e0e0e0",
                                borderWidth: agent.status === "active" ? 2 : 1,
                            }}
                        >
                            {/* Agent Header - Tap to expand */}
                            <button
                                onClick={() => toggleAgent(agent.name)}
                                className="w-full p-3 flex items-center justify-between bg-white hover:bg-gray-50 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className="p-2 rounded-lg"
                                        style={{ backgroundColor: `${config.color}15`, color: config.color }}
                                    >
                                        {config.icon}
                                    </div>
                                    <div className="text-left">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium text-sm" style={{ color: "#2c3e50" }}>
                                                {config.label}
                                            </span>
                                            {getStatusBadge(agent.status)}
                                        </div>
                                        {agent.currentAction && (
                                            <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]">
                                                {agent.currentAction}
                                            </p>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-gray-400">
                                        {agent.events.length} events
                                    </span>
                                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </div>
                            </button>

                            {/* Expanded Event Log */}
                            {isExpanded && (
                                <div className="border-t" style={{ borderColor: "#e0e0e0" }}>
                                    <ScrollArea className="max-h-[200px]">
                                        <div className="p-2 space-y-1">
                                            {agent.events.slice(-20).map((event, idx) => (
                                                <div
                                                    key={idx}
                                                    className="text-xs p-2 rounded"
                                                    style={{ backgroundColor: "#f8f9fa" }}
                                                >
                                                    <div className="flex items-center justify-between mb-1">
                                                        <span className="font-medium" style={{ color: config.color }}>
                                                            {event.event}
                                                        </span>
                                                        <span className="text-gray-400">
                                                            {new Date(event.timestamp).toLocaleTimeString()}
                                                        </span>
                                                    </div>
                                                    {event.data?.message && (
                                                        <p className="text-gray-600 whitespace-pre-wrap break-words">
                                                            {event.data.message.slice(0, 500)}
                                                            {event.data.message.length > 500 ? "..." : ""}
                                                        </p>
                                                    )}
                                                    {event.data?.delta && (
                                                        <p className="text-gray-600">
                                                            {event.data.delta}
                                                        </p>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* Raw Events View */}
            {showAllEvents && events.length > 0 && (
                <div className="border-t pt-3" style={{ borderColor: "#e0e0e0" }}>
                    <p className="text-xs font-semibold mb-2" style={{ color: "#7f8c8d" }}>
                        RAW EVENTS ({events.length})
                    </p>
                    <ScrollArea className="h-[200px] border rounded p-2" style={{ borderColor: "#e0e0e0" }}>
                        <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                            {JSON.stringify(events.slice(-50), null, 2)}
                        </pre>
                    </ScrollArea>
                </div>
            )}
        </div>
    )
}
