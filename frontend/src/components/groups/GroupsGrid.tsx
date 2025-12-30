/**
 * GroupsGrid - Main grid container with drag-and-drop context
 * Handles group-to-group prompt movement
 */

import { useState, useMemo, useCallback, useEffect } from "react"
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core"
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable"

import type { GroupDetail, PromptInGroup, EvaluationAnswer } from "@/client/api"
import type {
  BrandMentionResult,
  BrandVisibilityScore,
  CitationLeaderboard,
  BrandVariation,
} from "@/types/groups"
import {
  useGroups,
  useAllGroupDetails,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useRemovePromptsFromGroup,
  useMovePrompt,
} from "@/hooks/useGroups"
import { useGenerateReport } from "@/hooks/useBilling"
import { useInvalidateReportQueries } from "@/hooks/useReports"
import { calculateVisibilityScores } from "@/lib/report-utils"
import { GroupCard } from "./GroupCard"
import { AddGroupCard } from "./AddGroupCard"
import { PromptItem } from "./PromptItem"
import { MAX_GROUPS, getGroupColor } from "./constants"

interface PromptWithAnswer extends PromptInGroup {
  answer?: EvaluationAnswer | null
  brand_mentions?: BrandMentionResult[] | null
  isLoading?: boolean
}

interface GroupState {
  prompts: PromptWithAnswer[]
  isLoadingAnswers: boolean
  visibilityScores: BrandVisibilityScore[] | null
  citationLeaderboard: CitationLeaderboard | null
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
  const movePrompt = useMovePrompt()
  const generateReport = useGenerateReport()

  // Local state for answers and report data
  const [groupStates, setGroupStates] = useState<Record<number, GroupState>>({})

  // Track which report is selected per group (for viewing historical reports)
  // Initialize from localStorage to persist across page refreshes
  const [selectedReports, setSelectedReports] = useState<Record<number, number | null>>(
    loadSelectedReports
  )

  // Track which groups are expanded (collapsed by default)
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(loadExpandedGroups)

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

  // Active drag item
  const [activePrompt, setActivePrompt] = useState<{
    prompt: PromptWithAnswer
    groupId: number
  } | null>(null)

  // Sensors for drag
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

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

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const data = active.data.current
    if (data?.type === "prompt" && data.groupId !== "quarantine") {
      setActivePrompt({
        prompt: data.prompt,
        groupId: data.groupId as number,
      })
    }
  }

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActivePrompt(null)

    if (!over) return

    const activeData = active.data.current
    const overId = over.id as string

    if (activeData?.type !== "prompt") return

    const sourceGroupId = activeData.groupId
    const promptId = activeData.prompt.prompt_id

    // Only handle group-to-group moves
    if (sourceGroupId === "quarantine") return

    // Determine target group
    let targetGroupId: number | null = null

    if (overId.startsWith("group-")) {
      targetGroupId = parseInt(overId.replace("group-", ""), 10)
    } else if (overId.includes("-")) {
      // Dropped on another prompt
      const [groupIdStr] = overId.split("-")
      targetGroupId = parseInt(groupIdStr, 10)
    }

    if (!targetGroupId || targetGroupId === sourceGroupId) return

    // Move between groups
    movePrompt.mutate({
      promptId,
      sourceGroupId: sourceGroupId as number,
      targetGroupId,
    })
  }

  // Handle group creation
  const handleCreateGroup = (title: string, brands: BrandVariation[]) => {
    createGroup.mutate({ title, brands })
  }

  // Handle group update
  const handleUpdateGroup = (groupId: number, title: string) => {
    updateGroup.mutate({ groupId, title })
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

  // Handle load report (using billing API with charging)
  const handleLoadReport = async (group: GroupDetail, includePrevious: boolean = true) => {
    if (group.prompts.length === 0) return

    // Get brands from group (from API)
    const brands = group.brands || []

    // Set loading state
    setGroupStates((prev) => ({
      ...prev,
      [group.id]: {
        prompts:
          prev[group.id]?.prompts ||
          group.prompts.map((p) => ({ ...p, isLoading: true })),
        isLoadingAnswers: true,
        visibilityScores: prev[group.id]?.visibilityScores || null,
        citationLeaderboard: prev[group.id]?.citationLeaderboard || null,
      },
    }))

    try {
      // Use the new billing-aware generate API
      const result = await generateReport.mutateAsync({
        groupId: group.id,
        request: { include_previous: includePrevious },
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

      // Calculate visibility scores using the items from the response
      const resultsForScoring = result.items.map((item) => ({
        prompt_id: item.prompt_id,
        prompt_text: item.prompt_text,
        evaluation_id: item.evaluation_id,
        status: item.status,
        answer: item.answer,
        completed_at: item.completed_at,
        brand_mentions: item.brand_mentions,
      }))

      const visibilityScores =
        brands.length > 0
          ? calculateVisibilityScores(resultsForScoring, brands)
          : null

      setGroupStates((prev) => ({
        ...prev,
        [group.id]: {
          prompts: promptsWithAnswers,
          isLoadingAnswers: false,
          visibilityScores,
          citationLeaderboard: result.citation_leaderboard,
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
          visibilityScores: null,
          citationLeaderboard: null,
        },
      }))
    }
  }

  // Handle brands change for a group
  const handleBrandsChange = (groupId: number, brands: BrandVariation[]) => {
    // Update brands via API
    updateGroup.mutate({ groupId, brands })
    // Clear visibility scores (user must click Report to reload)
    setGroupStates((prev) => {
      const state = prev[groupId]
      if (!state) return prev
      return {
        ...prev,
        [groupId]: {
          ...state,
          visibilityScores: null,
        },
      }
    })
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
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="w-full space-y-6">
        {/* Groups section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-['Fraunces'] text-xl text-[#1F2937]">
              Your prompt groups
            </h2>
            {sortedGroups.length > 0 && (
              <span className="text-xs text-[#9CA3AF]">
                Drag prompts between groups to reorganize
              </span>
            )}
          </div>
          <div className="space-y-4">
            {/* User groups - each in its own row */}
            {sortedGroups.map((group, index) => {
              const state = groupStates[group.id]
              const prompts = getPromptsWithAnswers(group)
              const brands = group.brands || []

              return (
                <GroupCard
                  key={group.id}
                  group={group}
                  colorIndex={index}
                  prompts={prompts}
                  isLoadingAnswers={state?.isLoadingAnswers || false}
                  brands={brands}
                  visibilityScores={state?.visibilityScores || null}
                  citationLeaderboard={state?.citationLeaderboard || null}
                  selectedReportId={selectedReports[group.id] ?? null}
                  onSelectReport={(reportId) => handleSelectReport(group.id, reportId)}
                  onUpdateTitle={(title) => handleUpdateGroup(group.id, title)}
                  onDeleteGroup={() => handleDeleteGroup(group.id)}
                  onDeletePrompt={(promptId) =>
                    handleDeletePrompt(group.id, promptId)
                  }
                  onLoadReport={(includePrevious) => handleLoadReport(group, includePrevious)}
                  onBrandsChange={(brands) => handleBrandsChange(group.id, brands)}
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

      {/* Drag overlay - only for group prompts */}
      <DragOverlay>
        {activePrompt && (
          <div className="w-[300px]">
            <PromptItem
              prompt={activePrompt.prompt}
              groupId={activePrompt.groupId}
              accentColor={
                getGroupColor(
                  sortedGroups.findIndex((g) => g.id === activePrompt.groupId)
                ).accent
              }
              onDelete={() => {}}
              isDragOverlay
            />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  )
}
