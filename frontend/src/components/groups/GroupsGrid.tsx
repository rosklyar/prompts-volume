/**
 * GroupsGrid - Main grid container with drag-and-drop context
 * Handles group-to-group prompt movement
 */

import { useState, useMemo, useCallback, useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import type { GroupDetail, PromptInGroup, EvaluationAnswer } from "@/client/api"
import type {
  BrandInfo,
  CompetitorInfo,
  TopicInput,
  BrandMentionResult,
} from "@/types/groups"
import type { PromptSelection } from "@/types/billing"
import {
  useGroups,
  useAllGroupDetails,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useRemovePromptsFromGroup,
  useAddPromptsToGroup,
  useAddGSCPromptsToGroup,
  groupKeys,
} from "@/hooks/useGroups"
import { useGenerateReport } from "@/hooks/useBilling"
import { useInvalidateReportQueries } from "@/hooks/useReports"
import { GroupCard } from "./GroupCard"
import { AddGroupCard } from "./AddGroupCard"
import { PromptSelectionModal } from "./PromptSelectionModal"
import { BatchUploadModal } from "./BatchUploadModal"
import { MAX_GROUPS, getGroupColor } from "./constants"

interface PromptWithAnswer extends PromptInGroup {
  answer?: EvaluationAnswer | null
  brand_mentions?: BrandMentionResult[] | null
  isLoading?: boolean
}

interface GroupState {
  prompts: PromptWithAnswer[]
  isLoadingAnswers: boolean
}

// LocalStorage key for persisting selected reports
const SELECTED_REPORTS_KEY = "selected_reports"

// LocalStorage key for persisting expanded groups
const EXPANDED_GROUPS_KEY = "expanded_groups"

// Load selected reports from localStorage
function loadSelectedReports(): Record<number, number | null> {
  try {
    const saved = localStorage.getItem(SELECTED_REPORTS_KEY)
    if (!saved) return {}
    return JSON.parse(saved)
  } catch {
    return {}
  }
}

// Save selected reports to localStorage
function saveSelectedReports(reports: Record<number, number | null>): void {
  try {
    // Only save non-null values
    const toSave: Record<number, number> = {}
    for (const [groupId, reportId] of Object.entries(reports)) {
      if (reportId !== null) {
        toSave[Number(groupId)] = reportId
      }
    }
    localStorage.setItem(SELECTED_REPORTS_KEY, JSON.stringify(toSave))
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

// Load expanded groups from localStorage (only expanded groups are stored)
function loadExpandedGroups(): Set<number> {
  try {
    const saved = localStorage.getItem(EXPANDED_GROUPS_KEY)
    if (!saved) return new Set()
    return new Set(JSON.parse(saved))
  } catch {
    return new Set()
  }
}

// Save expanded groups to localStorage
function saveExpandedGroups(expanded: Set<number>): void {
  try {
    localStorage.setItem(EXPANDED_GROUPS_KEY, JSON.stringify([...expanded]))
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

export function GroupsGrid() {
  const queryClient = useQueryClient()

  // Fetch groups list
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups()

  // Get all group IDs
  const groupIds = useMemo(
    () => groupsData?.groups.map((g) => g.id) || [],
    [groupsData]
  )

  // Fetch all group details
  const { data: groupDetails, isLoading: isLoadingDetails } =
    useAllGroupDetails(groupIds)

  // Mutations
  const createGroup = useCreateGroup()
  const updateGroup = useUpdateGroup()
  const deleteGroup = useDeleteGroup()
  const removePrompts = useRemovePromptsFromGroup()
  const generateReport = useGenerateReport()
  const addPromptsToGroup = useAddPromptsToGroup()
  const addGSCPromptsToGroup = useAddGSCPromptsToGroup()

  // Local state for answers and report data
  const [groupStates, setGroupStates] = useState<Record<number, GroupState>>({})

  // Track which report is selected per group (for viewing historical reports)
  // Initialize from localStorage to persist across page refreshes
  const [selectedReports, setSelectedReports] = useState<Record<number, number | null>>(
    loadSelectedReports
  )

  // Track which groups are expanded (collapsed by default)
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(loadExpandedGroups)

  // Modal state for selecting prompts from topic after group creation
  const [promptSelectionModal, setPromptSelectionModal] = useState<{
    groupId: number
    groupTitle: string
    topicId: number
    topicTitle: string
  } | null>(null)

  // Modal state for batch upload after "No Topic" group creation
  const [batchUploadModal, setBatchUploadModal] = useState<{
    groupId: number
    groupTitle: string
  } | null>(null)

  // Persist selected reports to localStorage when they change
  useEffect(() => {
    saveSelectedReports(selectedReports)
  }, [selectedReports])

  // Persist expanded groups to localStorage when they change
  useEffect(() => {
    saveExpandedGroups(expandedGroups)
  }, [expandedGroups])

  // Toggle group expanded state
  const handleToggleExpand = useCallback((groupId: number) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(groupId)) {
        next.delete(groupId)
      } else {
        next.add(groupId)
      }
      return next
    })
  }, [])

  // Invalidate report queries after generating
  const invalidateReportQueries = useInvalidateReportQueries()

  // Sort groups by created_at
  const sortedGroups = useMemo(() => {
    if (!groupDetails) return []
    return [...groupDetails].sort((a, b) => {
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    })
  }, [groupDetails])

  // Get prompts for a group with answers merged from selected report
  // Answers are only shown when a report is selected
  const getPromptsWithAnswers = useCallback(
    (group: GroupDetail): PromptWithAnswer[] => {
      const state = groupStates[group.id]
      if (!state) {
        return group.prompts.map((p) => ({ ...p }))
      }

      // Create a map of answers by prompt_id from the loaded report
      const answersByPromptId = new Map(
        state.prompts.map((p) => [p.prompt_id, { answer: p.answer, brand_mentions: p.brand_mentions }])
      )

      // Merge: use group.prompts as source of truth, but add answers from selected report
      return group.prompts.map((p) => {
        const reportData = answersByPromptId.get(p.prompt_id)
        return {
          ...p,
          answer: reportData?.answer ?? null,
          brand_mentions: reportData?.brand_mentions ?? null,
        }
      })
    },
    [groupStates]
  )

  // Handle selecting a report to view
  const handleSelectReport = useCallback((groupId: number, reportId: number | null) => {
    setSelectedReports((prev) => ({
      ...prev,
      [groupId]: reportId,
    }))
  }, [])

  const canAddMore = sortedGroups.length < MAX_GROUPS

  // Handle group creation
  const handleCreateGroup = async (
    title: string,
    topic: TopicInput | null,
    brand: BrandInfo,
    competitors?: CompetitorInfo[],
    topicTitle?: string | null,
    selectedTopicPromptIds?: number[],
    selectedGSCPrompts?: string[]
  ) => {
    try {
      const newGroup = await createGroup.mutateAsync({ title, topic, brand, competitors })

      // Add selected topic prompts to group if any were selected
      if (selectedTopicPromptIds && selectedTopicPromptIds.length > 0) {
        await addPromptsToGroup.mutateAsync({
          groupId: newGroup.id,
          promptIds: selectedTopicPromptIds,
        })
      } else if (topic?.existing_topic_id && topicTitle && newGroup.topic_id) {
        // Only show modal if no prompts were pre-selected (backward compatibility)
        setPromptSelectionModal({
          groupId: newGroup.id,
          groupTitle: title,
          topicId: newGroup.topic_id,
          topicTitle: topicTitle,
        })
      }

      // Add selected GSC prompts to group if any were selected
      if (selectedGSCPrompts && selectedGSCPrompts.length > 0) {
        await addGSCPromptsToGroup.mutateAsync({
          groupId: newGroup.id,
          prompts: selectedGSCPrompts,
        })
      }

      // Show batch upload modal for "No Topic" groups so user can add own prompts
      if (topic === null) {
        setBatchUploadModal({
          groupId: newGroup.id,
          groupTitle: title,
        })
      }

      // Force refetch of all group queries to ensure UI shows added prompts
      await queryClient.refetchQueries({ queryKey: groupKeys.all })
    } catch (error) {
      console.error("Failed to create group:", error)
    }
  }

  // Handle group update
  const handleUpdateGroup = (groupId: number, title: string) => {
    updateGroup.mutate({ groupId, title })
  }

  // Handle country change
  const handleCountryChange = (groupId: number, countryId: number) => {
    updateGroup.mutate(
      { groupId, countryId },
      {
        onSuccess: () => {
          toast.success("Country updated")
        },
        onError: () => {
          toast.error("Failed to update country")
        },
      }
    )
  }

  // Handle group deletion
  const handleDeleteGroup = (groupId: number) => {
    deleteGroup.mutate(groupId)
    // Clean up local state
    setGroupStates((prev) => {
      const newState = { ...prev }
      delete newState[groupId]
      return newState
    })
    // Clean up selected report state
    setSelectedReports((prev) => {
      const newState = { ...prev }
      delete newState[groupId]
      return newState
    })
  }

  // Handle prompt deletion
  const handleDeletePrompt = (groupId: number, promptId: number) => {
    removePrompts.mutate({ groupId, promptIds: [promptId] })
    // Update local state
    setGroupStates((prev) => {
      const state = prev[groupId]
      if (!state) return prev
      return {
        ...prev,
        [groupId]: {
          ...state,
          prompts: state.prompts.filter((p) => p.prompt_id !== promptId),
        },
      }
    })
  }

  // Handle load report with selections (using billing API with charging)
  const handleLoadReport = async (
    group: GroupDetail,
    selections: PromptSelection[],
    assistantId: number
  ) => {
    if (group.prompts.length === 0) return

    // Set loading state
    setGroupStates((prev) => ({
      ...prev,
      [group.id]: {
        prompts:
          prev[group.id]?.prompts ||
          group.prompts.map((p) => ({ ...p, isLoading: true })),
        isLoadingAnswers: true,
      },
    }))

    try {
      // Use the selection-based generate API with assistant_id
      const result = await generateReport.mutateAsync({
        groupId: group.id,
        request: { selections, assistant_id: assistantId },
      })

      // Merge answers and brand mentions into prompts from the response
      const promptsWithAnswers = group.prompts.map((p) => {
        const item = result.items.find(
          (r) => r.prompt_id === p.prompt_id
        )
        return {
          ...p,
          answer: item?.answer || null,
          brand_mentions: item?.brand_mentions || null,
          isLoading: false,
        }
      })

      setGroupStates((prev) => ({
        ...prev,
        [group.id]: {
          prompts: promptsWithAnswers,
          isLoadingAnswers: false,
        },
      }))

      // Auto-select the newly generated report
      handleSelectReport(group.id, result.id)

      // Invalidate report history and comparison queries
      invalidateReportQueries(group.id)
    } catch (error) {
      console.error("Failed to load report:", error)
      setGroupStates((prev) => ({
        ...prev,
        [group.id]: {
          ...prev[group.id],
          prompts: group.prompts.map((p) => ({ ...p, isLoading: false })),
          isLoadingAnswers: false,
        },
      }))
    }
  }

  // Handle brand change for a group
  const handleBrandChange = (groupId: number, brand: BrandInfo) => {
    // Update brand via API - statistics are recalculated on-the-fly for all reports
    updateGroup.mutate(
      { groupId, brand },
      {
        onSuccess: () => {
          toast.success("Settings saved", {
            description: "All reports now reflect your brand changes",
          })
          // Invalidate report queries to refetch with new brand settings
          invalidateReportQueries(groupId)
        },
      }
    )
  }

  // Handle competitors change for a group
  const handleCompetitorsChange = (groupId: number, competitors: CompetitorInfo[]) => {
    // Update competitors via API - statistics are recalculated on-the-fly for all reports
    updateGroup.mutate(
      { groupId, competitors },
      {
        onSuccess: () => {
          toast.success("Settings saved", {
            description: "All reports now reflect your competitor changes",
          })
          // Invalidate report queries to refetch with new competitor settings
          invalidateReportQueries(groupId)
        },
      }
    )
  }

  // Loading state
  if (isLoadingGroups || isLoadingDetails) {
    return (
      <div className="w-full space-y-4">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="h-[140px] rounded-2xl bg-gray-100 animate-pulse"
          />
        ))}
      </div>
    )
  }

  return (
    <>
      <div className="w-full space-y-6">
        {/* Groups section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-['Fraunces'] text-xl text-[#1F2937]">
              Your prompt groups
            </h2>
          </div>
          <div className="space-y-4">
            {/* User groups - each in its own row */}
            {sortedGroups.map((group, index) => {
              const state = groupStates[group.id]
              const prompts = getPromptsWithAnswers(group)

              return (
                <GroupCard
                  key={group.id}
                  group={group}
                  colorIndex={index}
                  prompts={prompts}
                  isLoadingAnswers={state?.isLoadingAnswers || false}
                  brand={group.brand}
                  competitors={group.competitors || []}
                  selectedReportId={selectedReports[group.id] ?? null}
                  onSelectReport={(reportId) => handleSelectReport(group.id, reportId)}
                  onUpdateTitle={(title) => handleUpdateGroup(group.id, title)}
                  onDeleteGroup={() => handleDeleteGroup(group.id)}
                  onDeletePrompt={(promptId) =>
                    handleDeletePrompt(group.id, promptId)
                  }
                  onLoadReport={(selections, assistantId) => handleLoadReport(group, selections, assistantId)}
                  onBrandChange={(brand) => handleBrandChange(group.id, brand)}
                  onCompetitorsChange={(competitors) => handleCompetitorsChange(group.id, competitors)}
                  onCountryChange={(countryId) => handleCountryChange(group.id, countryId)}
                  isExpanded={expandedGroups.has(group.id)}
                  onToggleExpand={() => handleToggleExpand(group.id)}
                />
              )
            })}

            {/* Add group card - only if under limit */}
            {canAddMore && (
              <AddGroupCard
                onAdd={handleCreateGroup}
                isLoading={createGroup.isPending}
              />
            )}

            {/* Empty state when no groups */}
            {sortedGroups.length === 0 && !canAddMore && (
              <div className="text-center py-12 text-[#9CA3AF]">
                <p className="text-sm">No groups yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Prompt selection modal - shown after creating group with topic */}
      {promptSelectionModal && (
        <PromptSelectionModal
          groupId={promptSelectionModal.groupId}
          groupTitle={promptSelectionModal.groupTitle}
          topicId={promptSelectionModal.topicId}
          topicTitle={promptSelectionModal.topicTitle}
          accentColor={getGroupColor(sortedGroups.length).accent}
          isOpen={true}
          onClose={() => setPromptSelectionModal(null)}
        />
      )}

      {/* Batch upload modal - shown after creating group with no topic */}
      {batchUploadModal && (
        <BatchUploadModal
          groupId={batchUploadModal.groupId}
          groupTitle={batchUploadModal.groupTitle}
          accentColor={getGroupColor(sortedGroups.length).accent}
          isOpen={true}
          onClose={() => setBatchUploadModal(null)}
        />
      )}
    </>
  )
}
