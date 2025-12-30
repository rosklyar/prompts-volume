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
import { useHasFreshData, useReportHistory, useReport } from "@/hooks/useReports"
import { calculateVisibilityScores } from "@/lib/report-utils"
import { EditableTitle } from "./EditableTitle"
import { PromptItem } from "./PromptItem"
import { ReportPanel } from "./ReportPanel"
import { ReportHistoryPanel } from "./ReportHistoryPanel"
import { BrandEditor } from "./BrandEditor"
import { ReportPreviewModal, LowBalanceModal } from "@/components/billing"
import type { ReportPreview } from "@/types/billing"
import { getGroupColor } from "./constants"
import { BatchUploadModal } from "./BatchUploadModal"

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
  selectedReportId: number | null
  onSelectReport: (reportId: number | null) => void
  onUpdateTitle: (title: string) => void
  onDeleteGroup: () => void
  onDeletePrompt: (promptId: number) => void
  onLoadReport: (includePrevious?: boolean) => void
  onBrandsChange: (brands: BrandVariation[]) => void
  isExpanded: boolean
  onToggleExpand: () => void
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
  selectedReportId,
  onSelectReport,
  onUpdateTitle,
  onDeleteGroup,
  onDeletePrompt,
  onLoadReport,
  onBrandsChange,
  isExpanded,
  onToggleExpand,
}: GroupCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showBrandEditor, setShowBrandEditor] = useState(false)
  const [showBatchUpload, setShowBatchUpload] = useState(false)
  const [isReportCollapsed, setIsReportCollapsed] = useState(true)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [showLowBalanceModal, setShowLowBalanceModal] = useState(false)
  const [lowBalancePreview, setLowBalancePreview] = useState<ReportPreview | null>(null)
  const colors = getGroupColor(colorIndex)

  // Check for fresh data (for disabling Report button when no new data)
  const { hasFreshData } = useHasFreshData(
    group.id,
    prompts.length > 0
  )

  // Fetch report history to know if reports exist
  const { data: reportHistory } = useReportHistory(group.id, prompts.length > 0)
  const hasExistingReports = (reportHistory?.total ?? 0) > 0

  // Fetch selected report data when a report is selected
  const { data: selectedReport } = useReport(
    group.id,
    selectedReportId,
    selectedReportId !== null
  )

  // Merge answers from selected report into prompts
  const promptsWithSelectedReportAnswers = selectedReport
    ? prompts.map((p) => {
        const reportItem = selectedReport.items.find(
          (item) => item.prompt_id === p.prompt_id
        )
        return {
          ...p,
          answer: reportItem?.answer || null,
          brand_mentions: reportItem?.brand_mentions || null,
        }
      })
    : prompts

  // Calculate visibility scores from selected report
  const selectedReportVisibilityScores = selectedReport && brands.length > 0
    ? calculateVisibilityScores(
        selectedReport.items.map((item) => ({
          prompt_id: item.prompt_id,
          prompt_text: item.prompt_text,
          evaluation_id: item.evaluation_id,
          status: item.status,
          answer: item.answer,
          completed_at: null,
          brand_mentions: item.brand_mentions,
        })),
        brands
      )
    : null

  // Use selected report's data or passed props
  const displayVisibilityScores = selectedReportId ? selectedReportVisibilityScores : visibilityScores
  const displayCitationLeaderboard = selectedReportId ? selectedReport?.citation_leaderboard : citationLeaderboard
  const displayPrompts = selectedReportId ? promptsWithSelectedReportAnswers : prompts

  // State for no new data modal
  const [showNoNewDataModal, setShowNoNewDataModal] = useState(false)

  // Report button only disabled when loading or no prompts
  const isReportDisabled = isLoadingAnswers || prompts.length === 0

  // Check if there's no new data available
  const isNoNewData = hasFreshData === false && hasExistingReports

  // Handle report button click - check for fresh data first
  const handleReportClick = () => {
    if (prompts.length === 0) return

    // If no new data, show the no-new-data modal instead
    if (isNoNewData) {
      setShowNoNewDataModal(true)
      return
    }

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

  const sortableIds = displayPrompts.map((p) => `${group.id}-${p.prompt_id}`)

  const hasReportData = displayVisibilityScores !== null || displayCitationLeaderboard !== null

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
          <div className={`flex items-center justify-between ${isExpanded ? "mb-3" : ""}`}>
            <div className="flex items-center gap-3">
              {/* Expand/Collapse toggle */}
              <button
                onClick={onToggleExpand}
                className="p-1.5 -ml-1.5 rounded-lg hover:bg-white/80 transition-colors"
                aria-label={isExpanded ? "Collapse group" : "Expand group"}
              >
                <svg
                  className="w-4 h-4 text-gray-400 transition-transform duration-200"
                  style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
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
              {/* Report button - opens preview modal or no-data modal */}
              <button
                onClick={handleReportClick}
                disabled={isReportDisabled}
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

              {/* Batch upload button */}
              <button
                onClick={() => setShowBatchUpload(true)}
                className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-white/80 transition-colors"
                aria-label="Upload prompts from CSV"
                title="Upload prompts from CSV"
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
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
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

          {/* Collapsible content */}
          <div
            className="overflow-hidden transition-all duration-300"
            style={{
              maxHeight: isExpanded ? "2000px" : "0",
              opacity: isExpanded ? 1 : 0,
            }}
          >
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
                    {displayPrompts.map((prompt) => (
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

            {/* Report History Panel - shows list of past reports */}
            {prompts.length > 0 && (
              <ReportHistoryPanel
                groupId={group.id}
                selectedReportId={selectedReportId}
                onSelectReport={onSelectReport}
                accentColor={colors.accent}
              />
            )}

            {/* Report Panel - shown when report data is loaded (at bottom) */}
            {hasReportData && (
              <div className="mt-3">
                <ReportPanel
                  visibilityScores={displayVisibilityScores || []}
                  citationLeaderboard={displayCitationLeaderboard || { domains: [], subpaths: [], total_citations: 0 }}
                  accentColor={colors.accent}
                  isCollapsed={isReportCollapsed}
                  onToggleCollapse={() => setIsReportCollapsed(!isReportCollapsed)}
                />
              </div>
            )}
          </div>
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

      {/* Batch Upload Modal */}
      <BatchUploadModal
        groupId={group.id}
        groupTitle={group.title}
        accentColor={colors.accent}
        isOpen={showBatchUpload}
        onClose={() => setShowBatchUpload(false)}
      />

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

      {/* No New Data Modal */}
      {showNoNewDataModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowNoNewDataModal(false)}
          />

          {/* Modal */}
          <div
            className="relative bg-white rounded-2xl shadow-xl max-w-sm w-full mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
          >
            {/* Accent bar */}
            <div
              className="h-1.5 w-full"
              style={{ backgroundColor: colors.accent }}
            />

            <div className="p-6">
              {/* Icon */}
              <div
                className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center"
                style={{ backgroundColor: `${colors.accent}15` }}
              >
                <svg
                  className="w-6 h-6"
                  style={{ color: colors.accent }}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>

              {/* Title */}
              <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">
                No New Data Available
              </h3>

              {/* Description */}
              <p className="text-sm text-gray-500 text-center mb-6">
                There are no new evaluations since your last report.
                You can still view your previous reports from the history below.
              </p>

              {/* Action */}
              <button
                onClick={() => setShowNoNewDataModal(false)}
                className="w-full py-2.5 px-4 rounded-lg text-sm font-medium text-white transition-colors"
                style={{ backgroundColor: colors.accent }}
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
