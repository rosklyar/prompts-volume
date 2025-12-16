/**
 * GroupCard - Individual group card with header, body, and footer
 */

import { useDroppable } from "@dnd-kit/core"
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { useState } from "react"
import type { GroupDetail, PromptInGroup, EvaluationAnswer } from "@/client/api"
import { EditableTitle } from "./EditableTitle"
import { PromptItem } from "./PromptItem"
import { getGroupColorByIsCommon } from "./constants"

interface PromptWithAnswer extends PromptInGroup {
  answer?: EvaluationAnswer | null
  isLoading?: boolean
}

interface GroupCardProps {
  group: GroupDetail
  customIndex: number
  prompts: PromptWithAnswer[]
  isLoadingAnswers: boolean
  answersLoaded: boolean
  onUpdateTitle: (title: string) => void
  onDeleteGroup: () => void
  onDeletePrompt: (promptId: number) => void
  onLoadAnswers: () => void
}

export function GroupCard({
  group,
  customIndex,
  prompts,
  isLoadingAnswers,
  answersLoaded,
  onUpdateTitle,
  onDeleteGroup,
  onDeletePrompt,
  onLoadAnswers,
}: GroupCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const colors = getGroupColorByIsCommon(group.is_common, customIndex)

  const { setNodeRef, isOver } = useDroppable({
    id: `group-${group.id}`,
    data: {
      type: "group",
      groupId: group.id,
    },
  })

  const sortableIds = prompts.map((p) => `${group.id}-${p.prompt_id}`)

  return (
    <article
      className={`
        flex flex-col rounded-2xl overflow-hidden
        border-2 transition-all duration-300
        ${isOver ? "scale-[1.02] shadow-lg" : "shadow-sm hover:shadow-md"}
      `}
      style={{
        backgroundColor: colors.bg,
        borderColor: isOver ? colors.accent : `${colors.border}40`,
      }}
    >
      {/* Color accent bar */}
      <div
        className="h-1.5 w-full"
        style={{ backgroundColor: colors.accent }}
      />

      {/* Header */}
      <div className="px-4 pt-4 pb-3 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <EditableTitle
            title={group.title || "Common"}
            isEditable={!group.is_common}
            accentColor={colors.accent}
            onSave={onUpdateTitle}
          />
          <p className="text-xs text-gray-500 mt-1">
            {prompts.length} prompt{prompts.length !== 1 ? "s" : ""}
          </p>
        </div>

        {/* Actions */}
        {!group.is_common && (
          <div className="flex items-center gap-1">
            {showDeleteConfirm ? (
              <div className="flex items-center gap-1 animate-in fade-in duration-150">
                <button
                  onClick={() => {
                    onDeleteGroup()
                    setShowDeleteConfirm(false)
                  }}
                  className="px-2 py-1 text-xs font-medium text-white bg-red-500
                    hover:bg-red-600 rounded transition-colors"
                >
                  Delete
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-2 py-1 text-xs font-medium text-gray-600
                    hover:bg-gray-100 rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="p-1.5 rounded-md text-gray-400 hover:text-red-500
                  hover:bg-red-50 transition-colors"
                aria-label="Delete group"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Body - Scrollable prompt list */}
      <div
        ref={setNodeRef}
        className="flex-1 px-3 pb-3 overflow-y-auto max-h-[280px] min-h-[120px] group-scrollbar"
      >
        <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
          {prompts.length === 0 ? (
            <div
              className={`
                h-full min-h-[100px] flex items-center justify-center
                rounded-lg border-2 border-dashed transition-colors
                ${isOver ? "border-solid" : ""}
              `}
              style={{
                borderColor: isOver ? colors.accent : `${colors.border}30`,
                backgroundColor: isOver ? `${colors.accent}10` : "transparent",
              }}
            >
              <p className="text-sm text-gray-400 text-center px-4">
                {isOver ? "Drop here" : "Drag prompts here or add from search"}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {prompts.map((prompt) => (
                <PromptItem
                  key={prompt.prompt_id}
                  prompt={prompt}
                  groupId={group.id}
                  accentColor={colors.accent}
                  onDelete={onDeletePrompt}
                />
              ))}
            </div>
          )}
        </SortableContext>
      </div>

      {/* Footer - Load Answers button */}
      <div className="px-4 pb-4 pt-2 border-t" style={{ borderColor: `${colors.border}20` }}>
        <button
          onClick={onLoadAnswers}
          disabled={isLoadingAnswers || prompts.length === 0}
          className={`
            w-full py-2.5 px-4 rounded-lg text-sm font-medium
            transition-all duration-200 flex items-center justify-center gap-2
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
          style={{
            backgroundColor: answersLoaded ? `${colors.accent}15` : colors.accent,
            color: answersLoaded ? colors.accent : "white",
          }}
        >
          {isLoadingAnswers ? (
            <>
              <div
                className="w-4 h-4 border-2 rounded-full animate-spin"
                style={{
                  borderColor: answersLoaded ? `${colors.accent}30` : "rgba(255,255,255,0.3)",
                  borderTopColor: answersLoaded ? colors.accent : "white",
                }}
              />
              Loading...
            </>
          ) : answersLoaded ? (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh Answers
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Load Answers
            </>
          )}
        </button>
      </div>
    </article>
  )
}
