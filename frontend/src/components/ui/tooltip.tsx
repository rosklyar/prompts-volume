import * as React from "react"
import { createPortal } from "react-dom"
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
  const [position, setPosition] = React.useState({ top: 0, left: 0 })
  const triggerRef = React.useRef<HTMLDivElement>(null)
  const tooltipRef = React.useRef<HTMLDivElement>(null)

  if (disabled || !content) {
    return children
  }

  const updatePosition = () => {
    if (!triggerRef.current) return

    const rect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current?.getBoundingClientRect()
    const tooltipWidth = tooltipRect?.width || 200
    const tooltipHeight = tooltipRect?.height || 40

    let top = 0
    let left = 0

    switch (side) {
      case "top":
        top = rect.top - tooltipHeight - 8
        left = rect.left + rect.width / 2 - tooltipWidth / 2
        break
      case "bottom":
        top = rect.bottom + 8
        left = rect.left + rect.width / 2 - tooltipWidth / 2
        break
      case "left":
        top = rect.top + rect.height / 2 - tooltipHeight / 2
        left = rect.left - tooltipWidth - 8
        break
      case "right":
        top = rect.top + rect.height / 2 - tooltipHeight / 2
        left = rect.right + 8
        break
    }

    // Keep within viewport
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipWidth - 8))
    top = Math.max(8, top)

    setPosition({ top, left })
  }

  const handleMouseEnter = () => {
    setIsVisible(true)
    // Use requestAnimationFrame to ensure position is calculated after render
    requestAnimationFrame(updatePosition)
  }

  const arrowClasses = {
    top: "top-full left-1/2 -translate-x-1/2 border-t-gray-900 border-x-transparent border-b-transparent",
    bottom: "bottom-full left-1/2 -translate-x-1/2 border-b-gray-900 border-x-transparent border-t-transparent",
    left: "left-full top-1/2 -translate-y-1/2 border-l-gray-900 border-y-transparent border-r-transparent",
    right: "right-full top-1/2 -translate-y-1/2 border-r-gray-900 border-y-transparent border-l-transparent",
  }

  return (
    <>
      <div
        ref={triggerRef}
        className="inline-block"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={handleMouseEnter}
        onBlur={() => setIsVisible(false)}
      >
        {children}
      </div>
      {isVisible &&
        createPortal(
          <div
            ref={tooltipRef}
            className={cn(
              "fixed z-[9999] px-3 py-2 text-xs font-medium text-white bg-gray-900 rounded-lg shadow-lg whitespace-nowrap",
              "animate-in fade-in-0 zoom-in-95 duration-150"
            )}
            style={{
              top: position.top,
              left: position.left,
            }}
            role="tooltip"
          >
            {content}
            <div
              className={cn(
                "absolute w-0 h-0 border-4",
                arrowClasses[side]
              )}
            />
          </div>,
          document.body
        )}
    </>
  )
}
