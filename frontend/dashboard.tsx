"use client"

import { useState, useEffect } from "react"
import { DataCard } from "@/components/data-card"
import { WorkflowEngineCard } from "@/components/workflow-engine-card"
import { HistoryPanel } from "@/components/history-panel"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, BarChart3, History } from "lucide-react"

export default function Dashboard() {
  const [isMobile, setIsMobile] = useState(false)
  const [showDataPanel, setShowDataPanel] = useState(true)
  const [showHistoryPanel, setShowHistoryPanel] = useState(true)

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 1024
      setIsMobile(mobile)
      // Auto-collapse panels on mobile
      if (mobile) {
        setShowDataPanel(false)
        setShowHistoryPanel(false)
      }
    }

    handleResize()
    window.addEventListener("resize", handleResize)

    return () => {
      window.removeEventListener("resize", handleResize)
    }
  }, [])

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#ecf0f1" }}>
      {/* Header */}
      <header
        className="border-b-4"
        style={{ backgroundColor: "#2c3e50", borderBottomColor: "#2ecc71" }}
      >
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-white">SupplyMind</h1>
              <p className="text-sm mt-1" style={{ color: "#bdc3c7" }}>
                Your AI-powered supply chain copilot
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Toggle History Panel Button */}
              {!isMobile && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowHistoryPanel(!showHistoryPanel)}
                  className="text-white hover:bg-white/10"
                >
                  <History size={16} className="mr-2" />
                  {showHistoryPanel ? "Hide History" : "Show History"}
                </Button>
              )}
              {/* Toggle Data Panel Button */}
              {!isMobile && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowDataPanel(!showDataPanel)}
                  className="text-white hover:bg-white/10"
                >
                  <BarChart3 size={16} className="mr-2" />
                  {showDataPanel ? "Hide Analytics" : "Show Analytics"}
                  {showDataPanel ? <ChevronRight size={16} className="ml-1" /> : <ChevronLeft size={16} className="ml-1" />}
                </Button>
              )}
              <div className="text-right">
                <p className="text-sm text-white font-medium">Supply Chain Intelligence</p>
                <p className="text-xs mt-1" style={{ color: "#bdc3c7" }}>
                  {new Date().toLocaleDateString("en-US", {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isMobile ? (
          // Mobile: Stacked layout with collapsible panels
          <div className="space-y-6">
            {/* Panel Toggles for Mobile */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowHistoryPanel(!showHistoryPanel)}
              >
                <History size={16} className="mr-2" />
                {showHistoryPanel ? "Hide History" : "Show History"}
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowDataPanel(!showDataPanel)}
              >
                <BarChart3 size={16} className="mr-2" />
                {showDataPanel ? "Hide Analytics" : "Show Analytics"}
              </Button>
            </div>

            {showHistoryPanel && <HistoryPanel />}
            {showDataPanel && <DataCard />}
            <WorkflowEngineCard />
          </div>
        ) : (
          // Desktop: Three-column layout with sidebars
          <div className="flex gap-6">
            {/* History Panel - Left Sidebar */}
            {showHistoryPanel && (
              <div className="w-[350px] flex-shrink-0 transition-all duration-300">
                <HistoryPanel />
              </div>
            )}

            {/* Workflow Engine - Primary Focus */}
            <div className="flex-1 transition-all duration-300">
              <WorkflowEngineCard />
            </div>

            {/* Data Panel - Right Sidebar */}
            {showDataPanel && (
              <div className="w-[450px] flex-shrink-0 transition-all duration-300">
                <DataCard />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t" style={{ borderColor: "#bdc3c7" }}>
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <p>SupplyMind v1.0 • Powered by Microsoft Agent Framework</p>
            <p>
              Backend:{" "}
              <span className="font-mono">
                {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
              </span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
