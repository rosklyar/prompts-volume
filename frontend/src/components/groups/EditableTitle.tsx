/**
 * EditableTitle - Inline editable group title
 */

import { useState, useRef, useEffect } from "react"

interface EditableTitleProps {
  title: string
  isEditable: boolean
  accentColor: string
  onSave: (newTitle: string) => void
}

export function EditableTitle({
  title,
  isEditable,
  accentColor,
  onSave,
}: EditableTitleProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [value, setValue] = useState(title)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  useEffect(() => {
    setValue(title)
  }, [title])

  const handleSave = () => {
    const trimmed = value.trim()
    if (trimmed && trimmed !== title) {
      onSave(trimmed)
    } else {
      setValue(title)
    }
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleSave()
    } else if (e.key === "Escape") {
      setValue(title)
      setIsEditing(false)
    }
  }

  if (!isEditable) {
    return (
      <h3
        className="font-['Fraunces'] text-lg font-medium truncate"
        style={{ color: accentColor }}
      >
        {title}
      </h3>
    )
  }

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className="font-['Fraunces'] text-lg font-medium w-full bg-transparent
          border-b-2 focus:outline-none transition-colors"
        style={{
          color: accentColor,
          borderColor: accentColor,
        }}
        maxLength={50}
      />
    )
  }

  return (
    <button
      onClick={() => setIsEditing(true)}
      className="group/title flex items-center gap-2 text-left w-full min-w-0"
    >
      <h3
        className="font-['Fraunces'] text-lg font-medium truncate min-w-0"
        style={{ color: accentColor }}
      >
        {title}
      </h3>
      <svg
        className="w-3.5 h-3.5 opacity-0 group-hover/title:opacity-100 transition-opacity shrink-0"
        style={{ color: accentColor }}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
        />
      </svg>
    </button>
  )
}
