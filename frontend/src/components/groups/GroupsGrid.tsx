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
import type { QuarantinePrompt } from "@/types/groups"
import {
  useGroups,
  useAllGroupDetails,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useRemovePromptsFromGroup,
  useMovePrompt,
  useLoadAnswers,
  useAddPromptsToGroup,
} from "@/hooks/useGroups"
import { GroupCard } from "./GroupCard"
import { AddGroupCard } from "./AddGroupCard"
import { QuarantinePromptItem } from "./QuarantineCard"
import { PromptItem } from "./PromptItem"
import { MAX_GROUPS, getGroupColor } from "./constants"

interface PromptWithAnswer extends PromptInGroup {
  answer?: EvaluationAnswer | null
  isLoading?: boolean
}

interface GroupState {
  prompts: PromptWithAnswer[]
  isLoadingAnswers: boolean
  answersLoaded: boolean
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
  const loadAnswers = useLoadAnswers()
  const addPromptsToGroup = useAddPromptsToGroup()

  // Local state for answers
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
    createGroup.mutate(title)
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

  // Handle load answers
  const handleLoadAnswers = async (group: GroupDetail) => {
    const promptIds = group.prompts.map((p) => p.prompt_id)
    if (promptIds.length === 0) return

    // Set loading state
    setGroupStates((prev) => ({
      ...prev,
      [group.id]: {
        prompts:
          prev[group.id]?.prompts ||
          group.prompts.map((p) => ({ ...p, isLoading: true })),
        isLoadingAnswers: true,
        answersLoaded: prev[group.id]?.answersLoaded || false,
      },
    }))

    try {
      const result = await loadAnswers.mutateAsync({ promptIds })

      // Merge answers into prompts
      const promptsWithAnswers = group.prompts.map((p) => {
        const evaluation = result.results.find(
          (r) => r.prompt_id === p.prompt_id
        )
        return {
          ...p,
          answer: evaluation?.answer || null,
          isLoading: false,
        }
      })

      setGroupStates((prev) => ({
        ...prev,
        [group.id]: {
          prompts: promptsWithAnswers,
          isLoadingAnswers: false,
          answersLoaded: true,
        },
      }))
    } catch (error) {
      console.error("Failed to load answers:", error)
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

  // Loading state
  if (isLoadingGroups || isLoadingDetails) {
    return (
      <div className="w-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-[320px] rounded-2xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* User groups */}
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
                answersLoaded={state?.answersLoaded || false}
                onUpdateTitle={(title) => handleUpdateGroup(group.id, title)}
                onDeleteGroup={() => handleDeleteGroup(group.id)}
                onDeletePrompt={(promptId) =>
                  handleDeletePrompt(group.id, promptId)
                }
                onLoadAnswers={() => handleLoadAnswers(group)}
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
