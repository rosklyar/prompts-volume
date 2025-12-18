/**
 * AddGroupCard - Card for creating a new group
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
      <article
        className="flex flex-col rounded-2xl overflow-hidden
          border-2 border-dashed border-gray-300 bg-gray-50
          animate-in fade-in duration-200"
      >
        <div className="flex-1 flex flex-col items-center justify-center p-6">
          <div className="w-full max-w-[200px] space-y-4">
            <input
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Group name..."
              disabled={isLoading}
              className="w-full px-4 py-3 text-center font-['Fraunces'] text-lg
                bg-white border border-gray-200 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                placeholder:text-gray-400 disabled:opacity-50"
              maxLength={50}
            />
            <div className="flex gap-2">
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="flex-1 py-2 px-4 text-sm font-medium text-gray-600
                  bg-white border border-gray-200 rounded-lg
                  hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={isLoading || !title.trim()}
                className="flex-1 py-2 px-4 text-sm font-medium text-white
                  bg-[#C4553D] rounded-lg hover:bg-[#B34835]
                  transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                  flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  "Create"
                )}
              </button>
            </div>
          </div>
        </div>
      </article>
    )
  }

  return (
    <button
      onClick={() => setIsCreating(true)}
      className="flex flex-col items-center justify-center rounded-2xl
        border-2 border-dashed border-gray-200 bg-gray-50/50
        min-h-[200px] transition-all duration-300
        hover:border-[#C4553D]/40 hover:bg-[#FEF7F5]/50
        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30
        group"
    >
      <div
        className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center
          mb-3 transition-all duration-300
          group-hover:bg-[#C4553D]/10 group-hover:scale-110"
      >
        <svg
          className="w-7 h-7 text-gray-400 transition-colors group-hover:text-[#C4553D]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <span className="text-sm font-medium text-gray-500 group-hover:text-[#C4553D] transition-colors">
        Add Group
      </span>
      <span className="text-xs text-gray-400 mt-1">
        Up to 3 total
      </span>
    </button>
  )
}
