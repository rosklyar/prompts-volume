/**
 * QuarantineCard - A liminal workspace for staging prompts
 *
 * Design: "Liminal Workspace" - a full-width transitional staging area
 * with dashed borders. Prompts displayed horizontally, ready to be
 * dragged into groups below.
 */

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import type { QuarantinePrompt } from "@/types/groups"
import { QUARANTINE_COLOR } from "./constants"

interface QuarantinePromptItemProps {
  prompt: QuarantinePrompt
  onDelete: (promptId: number) => void
  isDragOverlay?: boolean
}

function QuarantinePromptItem({
  prompt,
  onDelete,
  isDragOverlay = false,
}: QuarantinePromptItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `quarantine-${prompt.prompt_id}`,
    data: {
      type: "prompt",
      prompt,
      groupId: "quarantine",
    },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`
        group relative bg-white rounded-xl border border-gray-100
        transition-all duration-200 max-w-sm
        ${isDragging ? "opacity-50 scale-[0.98]" : ""}
        ${isDragOverlay ? "shadow-xl rotate-[-2deg] scale-105" : "hover:shadow-md hover:border-[#C4553D]/30"}
      `}
    >
      <div className="flex items-start gap-2 p-3">
        {/* Drag handle */}
        <button
          {...attributes}
          {...listeners}
          className="shrink-0 mt-0.5 cursor-grab active:cursor-grabbing
            text-gray-300 hover:text-[#C4553D] transition-colors
            focus:outline-none focus:ring-2 focus:ring-offset-1 rounded"
          style={{ ["--tw-ring-color" as string]: QUARANTINE_COLOR.accent }}
          aria-label="Drag to move to a group"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
          </svg>
        </button>

        {/* Prompt content */}
        <div className="flex-1 min-w-0">
          <p className="text-[13px] leading-snug text-gray-700 line-clamp-2">
            {prompt.prompt_text}
          </p>
          {prompt.isCustom && (
            <span className="inline-flex items-center gap-1 mt-1.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-600 uppercase tracking-wide">
              <svg className="w-2 h-2" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L10 6.477l-3.763 1.505 1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.788l1.599.799L9 4.323V3a1 1 0 011-1z" />
              </svg>
              Custom
            </span>
          )}
        </div>

        {/* Delete button */}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(prompt.prompt_id)
          }}
          className="shrink-0 w-6 h-6 rounded-md flex items-center justify-center
            text-gray-300 hover:text-red-500 hover:bg-red-50
            transition-all duration-150 opacity-0 group-hover:opacity-100
            focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-red-200"
          aria-label="Remove from quarantine"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}

interface QuarantineCardProps {
  prompts: QuarantinePrompt[]
  onDeletePrompt: (promptId: number) => void
}

export function QuarantineCard({ prompts, onDeletePrompt }: QuarantineCardProps) {
  const colors = QUARANTINE_COLOR

  return (
    <section
      className="w-full rounded-2xl overflow-hidden transition-all duration-300"
      style={{
        backgroundColor: colors.bg,
        border: `2px dashed ${colors.border}50`,
      }}
    >
      {/* Dashed accent bar */}
      <div
        className="h-1 w-full"
        style={{
          background: `repeating-linear-gradient(90deg, ${colors.accent} 0px, ${colors.accent} 6px, transparent 6px, transparent 10px)`,
        }}
      />

      <div className="px-5 py-4">
        {/* Header - horizontal layout */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <svg
                className="w-5 h-5"
                style={{ color: colors.accent }}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"
                />
              </svg>
              <h3
                className="font-['Fraunces'] text-lg font-medium tracking-tight"
                style={{ color: colors.accent }}
              >
                Staging Area
              </h3>
            </div>
            <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full bg-white/80 text-gray-500 uppercase tracking-wider">
              {prompts.length} prompt{prompts.length !== 1 ? "s" : ""}
            </span>
          </div>

          <p className="text-xs text-gray-400 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            Drag to groups below
          </p>
        </div>

        {/* Body - Horizontal prompt list */}
        {prompts.length === 0 ? (
          <div
            className="flex items-center justify-center py-6 rounded-xl border-2 border-dashed"
            style={{ borderColor: `${colors.border}25`, backgroundColor: "rgba(255,255,255,0.5)" }}
          >
            <div className="text-center">
              <svg
                className="w-8 h-8 mx-auto mb-2 text-gray-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                />
              </svg>
              <p className="text-sm text-gray-400">
                Search above to add prompts
              </p>
              <p className="text-[11px] text-gray-300 mt-0.5">
                Then drag them to your groups
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {prompts.map((prompt) => (
              <QuarantinePromptItem
                key={prompt.prompt_id}
                prompt={prompt}
                onDelete={onDeletePrompt}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

// Export for drag overlay
export { QuarantinePromptItem }
