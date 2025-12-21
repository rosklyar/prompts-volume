/**
 * GroupsGrid - Main grid container with drag-and-drop context
 * Includes quarantine space for staging prompts before organizing into groups
 */

import { useState, useMemo, useCallback, type ReactNode } from "react"
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
  QuarantinePrompt,
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
  useLoadReport,
  useAddPromptsToGroup,
} from "@/hooks/useGroups"
import { calculateVisibilityScores } from "@/lib/report-utils"
import { GroupCard } from "./GroupCard"
import { AddGroupCard } from "./AddGroupCard"
import { QuarantinePromptItem } from "./QuarantineCard"
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

interface GroupsGridProps {
  quarantinePrompts: QuarantinePrompt[]
  onRemoveFromQuarantine: (promptId: number) => void
  renderQuarantine?: () => ReactNode
}

export function GroupsGrid({
  quarantinePrompts: _quarantinePrompts,
  onRemoveFromQuarantine,
  renderQuarantine,
}: GroupsGridProps) {
  // quarantinePrompts is passed to QuarantineCard via renderQuarantine
  void _quarantinePrompts
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
  const loadReport = useLoadReport()
  const addPromptsToGroup = useAddPromptsToGroup()

  // Local state for answers and report data
  const [groupStates, setGroupStates] = useState<Record<number, GroupState>>({})

  // Active drag item
  const [activePrompt, setActivePrompt] = useState<{
    prompt: PromptWithAnswer | QuarantinePrompt
    groupId: number | "quarantine"
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

  // Get prompts for a group with answers merged
  const getPromptsWithAnswers = useCallback(
    (group: GroupDetail): PromptWithAnswer[] => {
      const state = groupStates[group.id]
      if (!state) {
        return group.prompts.map((p) => ({ ...p }))
      }
      return state.prompts
    },
    [groupStates]
  )

  const canAddMore = sortedGroups.length < MAX_GROUPS

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const data = active.data.current
    if (data?.type === "prompt") {
      setActivePrompt({
        prompt: data.prompt,
        groupId: data.groupId,
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

    // Determine target group
    let targetGroupId: number | null = null

    if (overId.startsWith("group-")) {
      targetGroupId = parseInt(overId.replace("group-", ""), 10)
    } else if (overId.includes("-") && !overId.startsWith("quarantine")) {
      // Dropped on another prompt (not quarantine prompts)
      const [groupIdStr] = overId.split("-")
      targetGroupId = parseInt(groupIdStr, 10)
    }

    if (!targetGroupId) return

    // Handle move from quarantine to group
    if (sourceGroupId === "quarantine") {
      addPromptsToGroup.mutate(
        { groupId: targetGroupId, promptIds: [promptId] },
        {
          onSuccess: () => {
            onRemoveFromQuarantine(promptId)
          },
        }
      )
    } else if (targetGroupId !== sourceGroupId) {
      // Move between groups
      movePrompt.mutate({
        promptId,
        sourceGroupId: sourceGroupId as number,
        targetGroupId,
      })
    }
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

  // Handle load report (enriched results)
  const handleLoadReport = async (group: GroupDetail) => {
    const promptIds = group.prompts.map((p) => p.prompt_id)
    if (promptIds.length === 0) return

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
      const result = await loadReport.mutateAsync({
        groupId: group.id,
        promptIds,
      })

      // Merge answers and brand mentions into prompts
      const promptsWithAnswers = group.prompts.map((p) => {
        const evaluation = result.results.find(
          (r) => r.prompt_id === p.prompt_id
        )
        return {
          ...p,
          answer: evaluation?.answer || null,
          brand_mentions: evaluation?.brand_mentions || null,
          isLoading: false,
        }
      })

      // Calculate visibility scores
      const visibilityScores =
        brands.length > 0
          ? calculateVisibilityScores(result.results, brands)
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
        {/* Quarantine section - rendered via prop for layout flexibility */}
        {renderQuarantine && renderQuarantine()}

        {/* Groups section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-['Fraunces'] text-xl text-[#1F2937]">
              Your Prompt Groups
            </h2>
            <span className="text-xs text-[#9CA3AF]">
              Drag prompts from staging to groups
            </span>
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
                answersLoaded={state?.answersLoaded || false}
                brands={brands}
                visibilityScores={state?.visibilityScores || null}
                citationLeaderboard={state?.citationLeaderboard || null}
                onUpdateTitle={(title) => handleUpdateGroup(group.id, title)}
                onDeleteGroup={() => handleDeleteGroup(group.id)}
                onDeletePrompt={(promptId) =>
                  handleDeletePrompt(group.id, promptId)
                }
                onLoadReport={() => handleLoadReport(group)}
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
          </div>
        </div>
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {activePrompt && (
          <div className="w-[300px]">
            {activePrompt.groupId === "quarantine" ? (
              <QuarantinePromptItem
                prompt={activePrompt.prompt as QuarantinePrompt}
                onDelete={() => {}}
                isDragOverlay
              />
            ) : (
              <PromptItem
                prompt={activePrompt.prompt as PromptWithAnswer}
                groupId={activePrompt.groupId as number}
                accentColor={
                  getGroupColor(
                    sortedGroups.findIndex(
                      (g) => g.id === activePrompt.groupId
                    )
                  ).accent
                }
                onDelete={() => {}}
                isDragOverlay
              />
            )}
          </div>
        )}
      </DragOverlay>
    </DndContext>
  )
}
