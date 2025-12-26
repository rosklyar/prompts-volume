/**
 * GroupsGrid - Main grid container with drag-and-drop context
 * Handles group-to-group prompt movement
 */

import { useState, useMemo, useCallback } from "react"
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
import { calculateVisibilityScores } from "@/lib/report-utils"
import { saveReportCache, loadReportCache, clearReportCache } from "@/lib/report-storage"
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
  answersLoaded: boolean
  visibilityScores: BrandVisibilityScore[] | null
  citationLeaderboard: CitationLeaderboard | null
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

  // Load cached states from localStorage (computed, not stored in state)
  const cachedGroupStates = useMemo(() => {
    if (!groupDetails || groupDetails.length === 0) return {}

    const cachedStates: Record<number, GroupState> = {}

    groupDetails.forEach((group) => {
      const cached = loadReportCache(group.id)
      if (cached) {
        cachedStates[group.id] = {
          prompts: cached.prompts,
          isLoadingAnswers: false,
          answersLoaded: true,
          visibilityScores: cached.visibilityScores,
          citationLeaderboard: cached.citationLeaderboard,
        }
      }
    })

    return cachedStates
  }, [groupDetails])

  // Merge cached states with runtime states (runtime takes precedence)
  const mergedGroupStates = useMemo(() => {
    return { ...cachedGroupStates, ...groupStates }
  }, [cachedGroupStates, groupStates])

  // Get prompts for a group with answers merged
  // Always use group.prompts as the source of truth for which prompts exist,
  // but merge in any cached answer data we have
  const getPromptsWithAnswers = useCallback(
    (group: GroupDetail): PromptWithAnswer[] => {
      const state = mergedGroupStates[group.id]
      if (!state) {
        return group.prompts.map((p) => ({ ...p }))
      }

      // Create a map of cached answers by prompt_id
      const cachedAnswers = new Map(
        state.prompts.map((p) => [p.prompt_id, { answer: p.answer, brand_mentions: p.brand_mentions }])
      )

      // Merge: use group.prompts as source of truth, but add cached answers
      return group.prompts.map((p) => {
        const cached = cachedAnswers.get(p.prompt_id)
        return {
          ...p,
          answer: cached?.answer ?? null,
          brand_mentions: cached?.brand_mentions ?? null,
        }
      })
    },
    [mergedGroupStates]
  )

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
  const handleCreateGroup = (title: string) => {
    createGroup.mutate({ title })
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
    // Clear cached report data
    clearReportCache(groupId)
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
        answersLoaded: prev[group.id]?.answersLoaded || false,
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
          answersLoaded: true,
          visibilityScores,
          citationLeaderboard: result.citation_leaderboard,
        },
      }))

      // Cache the report data in localStorage
      saveReportCache(
        group.id,
        promptsWithAnswers,
        visibilityScores,
        result.citation_leaderboard
      )
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
              Your Prompt Groups
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
              const state = mergedGroupStates[group.id]
              const prompts = getPromptsWithAnswers(group)
              const brands = group.brands || []

              return (
                <GroupCard
                  key={group.id}
                  group={group}
                  colorIndex={index}
                  prompts={prompts}
                  isLoadingAnswers={state?.isLoadingAnswers || false}
                  answersLoaded={state?.answersLoaded || false}
                  brands={brands}
                  visibilityScores={state?.visibilityScores || null}
                  citationLeaderboard={state?.citationLeaderboard || null}
                  onUpdateTitle={(title) => handleUpdateGroup(group.id, title)}
                  onDeleteGroup={() => handleDeleteGroup(group.id)}
                  onDeletePrompt={(promptId) =>
                    handleDeletePrompt(group.id, promptId)
                  }
                  onLoadReport={(includePrevious) => handleLoadReport(group, includePrevious)}
                  onBrandsChange={(brands) => handleBrandsChange(group.id, brands)}
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
