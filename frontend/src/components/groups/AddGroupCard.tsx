/**
 * AddGroupCard - Full-width card for creating a new group
 */

import { useState, useRef, useEffect } from "react"

interface AddGroupCardProps {
  onAdd: (title: string) => void
  isLoading: boolean
}

export function AddGroupCard({ onAdd, isLoading }: AddGroupCardProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [title, setTitle] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isCreating && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isCreating])

  const handleSubmit = () => {
    const trimmed = title.trim()
    if (trimmed) {
      onAdd(trimmed)
      setTitle("")
      setIsCreating(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleSubmit()
    } else if (e.key === "Escape") {
      setTitle("")
      setIsCreating(false)
    }
  }

  const handleCancel = () => {
    setTitle("")
    setIsCreating(false)
  }

  if (isCreating) {
    return (
      <section
        className="w-full rounded-2xl overflow-hidden
          border-2 border-dashed border-gray-300 bg-gray-50
          animate-in fade-in duration-200"
      >
        <div className="px-5 py-4">
          <div className="flex items-center gap-4">
            <input
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter group name..."
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 font-['Fraunces'] text-lg
                bg-white border border-gray-200 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                placeholder:text-gray-400 disabled:opacity-50"
              maxLength={50}
            />
            <div className="flex gap-2">
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="py-2.5 px-4 text-sm font-medium text-gray-600
                  bg-white border border-gray-200 rounded-lg
                  hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={isLoading || !title.trim()}
                className="py-2.5 px-5 text-sm font-medium text-white
                  bg-[#C4553D] rounded-lg hover:bg-[#B34835]
                  transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                  flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  "Create Group"
                )}
              </button>
            </div>
          </div>
        </div>
      </section>
    )
  }

  return (
    <button
      onClick={() => setIsCreating(true)}
      className="w-full flex items-center justify-center gap-3 rounded-2xl
        border-2 border-dashed border-gray-200 bg-gray-50/50
        py-6 transition-all duration-300
        hover:border-[#C4553D]/40 hover:bg-[#FEF7F5]/50
        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30
        group"
    >
      <div
        className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center
          transition-all duration-300
          group-hover:bg-[#C4553D]/10 group-hover:scale-110"
      >
        <svg
          className="w-5 h-5 text-gray-400 transition-colors group-hover:text-[#C4553D]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <div className="text-left">
        <span className="text-sm font-medium text-gray-500 group-hover:text-[#C4553D] transition-colors block">
          Add New Group
        </span>
        <span className="text-xs text-gray-400">
          Up to 3 total
        </span>
      </div>
    </button>
  )
}
