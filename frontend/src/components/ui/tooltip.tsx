import * as React from "react"
import { cn } from "@/lib/utils"

interface TooltipProps {
  content: React.ReactNode
  children: React.ReactElement
  side?: "top" | "bottom" | "left" | "right"
  disabled?: boolean
}

export function Tooltip({
  content,
  children,
  side = "top",
  disabled = false,
}: TooltipProps) {
  const [isVisible, setIsVisible] = React.useState(false)

  if (disabled || !content) {
    return children
  }

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  }

  const arrowClasses = {
    top: "top-full left-1/2 -translate-x-1/2 border-t-gray-900 border-x-transparent border-b-transparent",
    bottom: "bottom-full left-1/2 -translate-x-1/2 border-b-gray-900 border-x-transparent border-t-transparent",
    left: "left-full top-1/2 -translate-y-1/2 border-l-gray-900 border-y-transparent border-r-transparent",
    right: "right-full top-1/2 -translate-y-1/2 border-r-gray-900 border-y-transparent border-l-transparent",
  }

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div
          className={cn(
            "absolute z-50 px-2.5 py-1.5 text-xs font-medium text-white bg-gray-900 rounded-md shadow-md whitespace-nowrap",
            "animate-in fade-in-0 zoom-in-95 duration-100",
            positionClasses[side]
          )}
          role="tooltip"
        >
          {content}
          <div
            className={cn(
              "absolute w-0 h-0 border-4",
              arrowClasses[side]
            )}
          />
        </div>
      )}
    </div>
  )
}
