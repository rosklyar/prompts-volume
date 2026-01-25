import * as React from "react"
import { createPortal } from "react-dom"
import { cn } from "@/lib/utils"

interface PopoverProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  trigger: React.ReactElement
  children: React.ReactNode
  side?: "top" | "bottom" | "left" | "right"
  align?: "start" | "center" | "end"
}

export function Popover({
  open,
  onOpenChange,
  trigger,
  children,
  side = "bottom",
  align = "center",
}: PopoverProps) {
  const [position, setPosition] = React.useState({ top: 0, left: 0 })
  const triggerRef = React.useRef<HTMLDivElement>(null)
  const popoverRef = React.useRef<HTMLDivElement>(null)

  const updatePosition = React.useCallback(() => {
    if (!triggerRef.current || !popoverRef.current) return

    const triggerRect = triggerRef.current.getBoundingClientRect()
    const popoverRect = popoverRef.current.getBoundingClientRect()

    let top = 0
    let left = 0

    // Vertical positioning
    switch (side) {
      case "top":
        top = triggerRect.top - popoverRect.height - 8
        break
      case "bottom":
        top = triggerRect.bottom + 8
        break
      case "left":
        top = triggerRect.top + triggerRect.height / 2 - popoverRect.height / 2
        left = triggerRect.left - popoverRect.width - 8
        break
      case "right":
        top = triggerRect.top + triggerRect.height / 2 - popoverRect.height / 2
        left = triggerRect.right + 8
        break
    }

    // Horizontal alignment (for top/bottom)
    if (side === "top" || side === "bottom") {
      switch (align) {
        case "start":
          left = triggerRect.left
          break
        case "center":
          left = triggerRect.left + triggerRect.width / 2 - popoverRect.width / 2
          break
        case "end":
          left = triggerRect.right - popoverRect.width
          break
      }
    }

    // Keep within viewport
    left = Math.max(8, Math.min(left, window.innerWidth - popoverRect.width - 8))
    top = Math.max(8, Math.min(top, window.innerHeight - popoverRect.height - 8))

    setPosition({ top, left })
  }, [side, align])

  // Update position when open changes
  React.useEffect(() => {
    if (open) {
      // Use requestAnimationFrame to ensure popover is rendered before measuring
      requestAnimationFrame(() => {
        requestAnimationFrame(updatePosition)
      })
    }
  }, [open, updatePosition])

  // Close on click outside
  React.useEffect(() => {
    if (!open) return

    const handleClickOutside = (event: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        onOpenChange(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("keydown", handleEscape)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleEscape)
    }
  }, [open, onOpenChange])

  return (
    <>
      <div ref={triggerRef} className="inline-block">
        {trigger}
      </div>
      {open &&
        createPortal(
          <div
            ref={popoverRef}
            className={cn(
              "fixed z-[9999] bg-white rounded-lg shadow-lg border border-gray-200",
              "animate-in fade-in-0 zoom-in-95 duration-150"
            )}
            style={{
              top: position.top,
              left: position.left,
            }}
            role="dialog"
          >
            {children}
          </div>,
          document.body
        )}
    </>
  )
}
