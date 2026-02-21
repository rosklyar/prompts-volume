/**
 * BrandVisibilityCard - Circular gauge showing brand visibility percentage
 * Magazine-style card with SVG progress ring
 */

import { useEffect, useState, useRef } from "react"
import { BrandLogo } from "@/components/BrandLogo"

interface BrandVisibilityCardProps {
  brandName: string | null
  brandDomain?: string | null
  visibilityPercent: number
  hasData: boolean
}

export function BrandVisibilityCard({
  brandName,
  brandDomain,
  visibilityPercent,
  hasData,
}: BrandVisibilityCardProps) {
  const [displayValue, setDisplayValue] = useState(0)
  const animationRef = useRef<number | null>(null)

  // Animate counter from 0 to value
  useEffect(() => {
    if (!hasData) {
      // Reset handled by effect cleanup - just return early
      return
    }

    const startTime = performance.now()
    const duration = 1000 // 1 second animation
    const startValue = 0
    const endValue = visibilityPercent

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3)
      setDisplayValue(startValue + (endValue - startValue) * easeOut)

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate)
      }
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      // Reset value on cleanup
      setDisplayValue(0)
    }
  }, [visibilityPercent, hasData])

  // SVG circle dimensions
  const size = 160
  const strokeWidth = 12
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (displayValue / 100) * circumference

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col">
      <h3 className="font-['Fraunces'] text-sm font-medium text-[#1E1E1E] uppercase tracking-wide mb-6 shrink-0">
        Brand Visibility
      </h3>

      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="relative">
          <svg
            width={size}
            height={size}
            className="transform -rotate-90"
          >
            {/* Background circle */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={hasData ? "#F3F4F6" : "#E5E7EB"}
              strokeWidth={strokeWidth}
              strokeDasharray={hasData ? "none" : "8 8"}
            />
            {/* Progress circle */}
            {hasData && (
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="#C4553D"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-1000 ease-out"
              />
            )}
          </svg>

          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {hasData ? (
              <>
                <span className="font-['Fraunces'] text-4xl font-semibold text-[#1F2937]">
                  {Math.round(displayValue)}%
                </span>
              </>
            ) : (
              <span className="text-sm text-[#9CA3AF] text-center px-4">
                No report data
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Brand name */}
      <div className="flex items-center justify-center gap-2 mt-4 shrink-0">
        {brandName && <BrandLogo domain={brandDomain} name={brandName} size={24} />}
        <p className="text-sm text-[#6B7280] font-['DM_Sans']">
          {brandName || "No brand configured"}
        </p>
      </div>
    </div>
  )
}
