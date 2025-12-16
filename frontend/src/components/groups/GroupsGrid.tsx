/**
 * GroupsGrid - Main grid container with drag-and-drop context
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
import {
  useGroups,
  useAllGroupDetails,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useRemovePromptsFromGroup,
  useMovePrompt,
  useLoadAnswers,
} from "@/hooks/useGroups"
import { GroupCard } from "./GroupCard"
import { AddGroupCard } from "./AddGroupCard"
import { PromptItem } from "./PromptItem"
import { MAX_GROUPS, getGroupColorByIsCommon } from "./constants"

interface PromptWithAnswer extends PromptInGroup {
  answer?: EvaluationAnswer | null
  isLoading?: boolean
}

interface GroupState {
  prompts: PromptWithAnswer[]
  isLoadingAnswers: boolean
  answersLoaded: boolean
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
  const loadAnswers = useLoadAnswers()

  // Local state for answers
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

  // Sort groups: common first, then by created_at (must be before early return)
  const sortedGroups = useMemo(() => {
    if (!groupDetails) return []
    return [...groupDetails].sort((a, b) => {
      if (a.is_common && !b.is_common) return -1
      if (!a.is_common && b.is_common) return 1
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    })
  }, [groupDetails])

  // Calculate custom index for colors
  const getCustomIndex = useCallback(
    (group: GroupDetail) => {
      const customGroups = sortedGroups.filter((g) => !g.is_common)
      return customGroups.findIndex((g) => g.id === group.id)
    },
    [sortedGroups]
  )

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
    } else if (overId.includes("-")) {
      // Dropped on another prompt
      const [groupIdStr] = overId.split("-")
      targetGroupId = parseInt(groupIdStr, 10)
    }

    if (targetGroupId && targetGroupId !== sourceGroupId) {
      movePrompt.mutate({
        promptId,
        sourceGroupId,
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
      <div className="w-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedGroups.map((group) => {
            const state = groupStates[group.id]
            const prompts = getPromptsWithAnswers(group)
            const customIndex = getCustomIndex(group)

            return (
              <GroupCard
                key={group.id}
                group={group}
                customIndex={customIndex}
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

          {canAddMore && (
            <AddGroupCard
              onAdd={handleCreateGroup}
              isLoading={createGroup.isPending}
            />
          )}
        </div>
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {activePrompt && (
          <div className="w-[300px]">
            <PromptItem
              prompt={activePrompt.prompt}
              groupId={activePrompt.groupId}
              accentColor={
                getGroupColorByIsCommon(
                  sortedGroups.find((g) => g.id === activePrompt.groupId)
                    ?.is_common || false,
                  getCustomIndex(
                    sortedGroups.find(
                      (g) => g.id === activePrompt.groupId
                    ) as GroupDetail
                  )
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
