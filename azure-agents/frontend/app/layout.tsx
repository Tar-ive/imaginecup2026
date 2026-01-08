import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import "./globals.css"

const _inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "SupplyMind - AI Supply Chain Copilot",
  description:
    "Real-time supply chain optimization, inventory forecasting, and AI-powered ordering with human-in-the-loop approvals",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`font-sans antialiased`} style={{ backgroundColor: "#ecf0f1" }}>
        {children}
        <Analytics />
      </body>
    </html>
  )
}
