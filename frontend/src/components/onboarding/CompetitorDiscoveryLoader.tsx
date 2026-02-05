/**
 * CompetitorDiscoveryLoader - Animated loading state for competitor discovery
 * Displays orbiting dots and rotating status text while AI discovers competitors
 */

import { useState, useEffect } from "react"
import { Sparkles } from "lucide-react"

const STATUS_TEXTS = [
  "Searching the web...",
  "Analyzing competitors...",
  "Generating variations...",
]

const STATUS_INTERVAL = 2500 // 2.5 seconds per status

export function CompetitorDiscoveryLoader() {
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % STATUS_TEXTS.length)
    }, STATUS_INTERVAL)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative py-12">
      {/* Orbiting dots */}
      <div className="absolute inset-0 flex items-center justify-center">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-[#C4553D]/30 rounded-full animate-orbit"
            style={{
              animationDelay: `${i * 1}s`,
            }}
          />
        ))}
      </div>

      {/* Center sparkle */}
      <div
        className="relative z-10 w-16 h-16 mx-auto rounded-full bg-[#C4553D]/10
                    flex items-center justify-center animate-pulse"
      >
        <Sparkles className="w-8 h-8 text-[#C4553D]" />
      </div>

      {/* Rotating status text */}
      <p
        key={currentIndex}
        className="mt-6 text-center text-[#6B7280] animate-fade-text"
      >
        {STATUS_TEXTS[currentIndex]}
      </p>

      {/* Progress bar (indeterminate) */}
      <div className="mt-6 mx-auto max-w-xs h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-[#C4553D]/60 rounded-full animate-pulse"
          style={{ width: "60%" }}
        />
      </div>
    </div>
  )
}
