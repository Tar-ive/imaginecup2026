"use client"

import { useState, useEffect } from "react"
import { DataCard } from "@/components/data-card"
import { WorkflowEngineCard } from "@/components/workflow-engine-card"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, BarChart3 } from "lucide-react"

export default function Dashboard() {
  const [isMobile, setIsMobile] = useState(false)
  const [showDataPanel, setShowDataPanel] = useState(true)

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 1024
      setIsMobile(mobile)
      // Auto-collapse data panel on mobile
      if (mobile) {
        setShowDataPanel(false)
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
          // Mobile: Stacked layout with collapsible data panel
          <div className="space-y-6">
            {/* Data Panel Toggle for Mobile */}
            <Button
              variant="outline"
              className="w-full"
              onClick={() => setShowDataPanel(!showDataPanel)}
            >
              <BarChart3 size={16} className="mr-2" />
              {showDataPanel ? "Hide Analytics" : "Show Analytics"}
            </Button>

            {showDataPanel && <DataCard />}
            <WorkflowEngineCard />
          </div>
        ) : (
          // Desktop: Workflow-focused layout with optional data sidebar
          <div className="flex gap-6">
            {/* Workflow Engine - Primary Focus */}
            <div className={`transition-all duration-300 ${showDataPanel ? 'flex-1' : 'w-full'}`}>
              <WorkflowEngineCard />
            </div>

            {/* Data Panel - Collapsible Sidebar */}
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
