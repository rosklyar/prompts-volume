/**
 * GroupCard - Full-width group section with horizontal prompt layout
 * Similar to QuarantineCard/Staging Area design
 */

import { useDroppable } from "@dnd-kit/core"
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { useState } from "react"
import type { GroupDetail, PromptInGroup, EvaluationAnswer } from "@/client/api"
import type {
  BrandVariation,
  BrandMentionResult,
  BrandVisibilityScore,
  CitationLeaderboard,
} from "@/types/groups"
import { EditableTitle } from "./EditableTitle"
import { PromptItem } from "./PromptItem"
import { ReportPanel } from "./ReportPanel"
import { BrandEditor } from "./BrandEditor"
import { ReportPreviewModal, LowBalanceModal } from "@/components/billing"
import type { ReportPreview } from "@/types/billing"
import { getGroupColor } from "./constants"

interface PromptWithAnswer extends PromptInGroup {
  answer?: EvaluationAnswer | null
  brand_mentions?: BrandMentionResult[] | null
  isLoading?: boolean
}

interface GroupCardProps {
  group: GroupDetail
  colorIndex: number
  prompts: PromptWithAnswer[]
  isLoadingAnswers: boolean
  answersLoaded: boolean
  brands: BrandVariation[]
  visibilityScores: BrandVisibilityScore[] | null
  citationLeaderboard: CitationLeaderboard | null
  onUpdateTitle: (title: string) => void
  onDeleteGroup: () => void
  onDeletePrompt: (promptId: number) => void
  onLoadReport: (includePrevious?: boolean) => void
  onBrandsChange: (brands: BrandVariation[]) => void
}

export function GroupCard({
  group,
  colorIndex,
  prompts,
  isLoadingAnswers,
  answersLoaded,
  brands,
  visibilityScores,
  citationLeaderboard,
  onUpdateTitle,
  onDeleteGroup,
  onDeletePrompt,
  onLoadReport,
  onBrandsChange,
}: GroupCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showBrandEditor, setShowBrandEditor] = useState(false)
  const [isReportCollapsed, setIsReportCollapsed] = useState(true)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [showLowBalanceModal, setShowLowBalanceModal] = useState(false)
  const [lowBalancePreview, setLowBalancePreview] = useState<ReportPreview | null>(null)
  const colors = getGroupColor(colorIndex)

  // Handle report button click - opens preview modal
  const handleReportClick = () => {
    if (prompts.length === 0) return
    setShowPreviewModal(true)
  }

  // Handle preview confirm - proceed with loading
  const handlePreviewConfirm = (includePrevious: boolean) => {
    setShowPreviewModal(false)
    onLoadReport(includePrevious)
  }

  // Handle low balance scenario from preview
  const handleNeedsTopUp = (preview: ReportPreview) => {
    setShowPreviewModal(false)
    setLowBalancePreview(preview)
    setShowLowBalanceModal(true)
  }

  // Handle partial load from low balance modal
  const handleLoadPartial = () => {
    setShowLowBalanceModal(false)
    setLowBalancePreview(null)
    onLoadReport(true) // Load what we can afford
  }

  const { setNodeRef, isOver } = useDroppable({
    id: `group-${group.id}`,
    data: {
      type: "group",
      groupId: group.id,
    },
  })

  const sortableIds = prompts.map((p) => `${group.id}-${p.prompt_id}`)

  const hasReportData = visibilityScores !== null || citationLeaderboard !== null

  return (
    <>
      <section
        className={`
          w-full rounded-2xl overflow-hidden transition-all duration-300
          ${isOver ? "scale-[1.005] shadow-lg" : ""}
        `}
        style={{
          backgroundColor: colors.bg,
          border: `2px solid ${isOver ? colors.accent : `${colors.border}40`}`,
        }}
      >
        {/* Color accent bar */}
        <div
          className="h-1.5 w-full"
          style={{ backgroundColor: colors.accent }}
        />

        <div className="px-5 py-4">
          {/* Header - horizontal layout */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <EditableTitle
                title={group.title}
                isEditable={true}
                accentColor={colors.accent}
                onSave={onUpdateTitle}
              />
              <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full bg-white/80 text-gray-500 uppercase tracking-wider">
                {prompts.length} prompt{prompts.length !== 1 ? "s" : ""}
              </span>
              {brands.length > 0 && (
                <span
                  className="text-[10px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider"
                  style={{ backgroundColor: `${colors.accent}15`, color: colors.accent }}
                >
                  {brands.length} brand{brands.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              {/* Report button - opens preview modal */}
              <button
                onClick={handleReportClick}
                disabled={isLoadingAnswers || prompts.length === 0}
                className={`
                  py-2 px-4 rounded-lg text-sm font-medium
                  transition-all duration-200 flex items-center gap-2
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
                    Refresh
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Report
                  </>
                )}
              </button>

              {/* Brand config button */}
              <button
                onClick={() => setShowBrandEditor(true)}
                className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-white/80 transition-colors"
                aria-label="Configure brands"
                title="Configure brands"
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
                    d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z"
                  />
                </svg>
              </button>

              {/* Delete button */}
              {showDeleteConfirm ? (
                <div className="flex items-center gap-1 animate-in fade-in duration-150">
                  <button
                    onClick={() => {
                      onDeleteGroup()
                      setShowDeleteConfirm(false)
                    }}
                    className="px-3 py-1.5 text-xs font-medium text-white bg-red-500
                      hover:bg-red-600 rounded-lg transition-colors"
                  >
                    Delete
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="px-3 py-1.5 text-xs font-medium text-gray-600
                      hover:bg-white/80 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="p-2 rounded-lg text-gray-400 hover:text-red-500
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
          </div>

          {/* Body - Vertical prompt list */}
          <div ref={setNodeRef}>
            <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
              {prompts.length === 0 ? (
                <div
                  className={`
                    flex items-center justify-center py-6 rounded-xl border-2 border-dashed transition-colors
                    ${isOver ? "border-solid" : ""}
                  `}
                  style={{
                    borderColor: isOver ? colors.accent : `${colors.border}25`,
                    backgroundColor: isOver ? `${colors.accent}10` : "rgba(255,255,255,0.5)",
                  }}
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
                        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                      />
                    </svg>
                    <p className="text-sm text-gray-400">
                      {isOver ? "Drop here" : "Drag prompts from staging area"}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="max-h-[220px] overflow-y-auto space-y-2 prompts-scroll">
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

          {/* Report Panel - shown when report data is loaded (at bottom) */}
          {hasReportData && (
            <div className="mt-3">
              <ReportPanel
                visibilityScores={visibilityScores || []}
                citationLeaderboard={citationLeaderboard || { domains: [], subpaths: [], total_citations: 0 }}
                accentColor={colors.accent}
                isCollapsed={isReportCollapsed}
                onToggleCollapse={() => setIsReportCollapsed(!isReportCollapsed)}
              />
            </div>
          )}
        </div>
      </section>

      {/* Brand Editor Modal */}
      {showBrandEditor && (
        <BrandEditor
          brands={brands}
          onBrandsChange={onBrandsChange}
          accentColor={colors.accent}
          onClose={() => setShowBrandEditor(false)}
        />
      )}

      {/* Report Preview Modal */}
      <ReportPreviewModal
        groupId={group.id}
        groupTitle={group.title}
        accentColor={colors.accent}
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        onConfirm={handlePreviewConfirm}
        onNeedsTopUp={handleNeedsTopUp}
      />

      {/* Low Balance Modal */}
      {lowBalancePreview && (
        <LowBalanceModal
          preview={lowBalancePreview}
          accentColor={colors.accent}
          isOpen={showLowBalanceModal}
          onClose={() => {
            setShowLowBalanceModal(false)
            setLowBalancePreview(null)
          }}
          onLoadPartial={handleLoadPartial}
        />
      )}
    </>
  )
}
