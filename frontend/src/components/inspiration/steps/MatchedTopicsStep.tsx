/**
 * MatchedTopicsStep - Step 2: Review matched topics and load prompts from DB
 * Two-column layout with topic cards and summary panel
 */

import { useState, useMemo } from "react"
import { useLoadTopicPrompts, useAddPromptsToGroupFromInspiration } from "@/hooks/useInspiration"
import { useGroups, useCreateGroup } from "@/hooks/useGroups"
import { TopicCard } from "../TopicCard"
import { GroupSelector } from "@/components/groups/GroupSelector"
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Check,
  Package,
} from "lucide-react"
import type { WizardAction } from "../InspirationModal"
import type { WizardState, TopicWithPrompts, PromptSelectionState } from "@/types/inspiration"
import type { BrandVariation } from "@/types/groups"

interface MatchedTopicsStepProps {
  state: WizardState
  dispatch: React.Dispatch<WizardAction>
  onClose: () => void
}

export function MatchedTopicsStep({ state, dispatch, onClose }: MatchedTopicsStepProps) {
  const [showGroupSelector, setShowGroupSelector] = useState(false)
  const [pendingTopicId, setPendingTopicId] = useState<number | null>(null)
  const [addingToGroupId, setAddingToGroupId] = useState<number | null>(null)

  const loadTopicPrompts = useLoadTopicPrompts()
  const addPromptsToGroup = useAddPromptsToGroupFromInspiration()
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups()
  const createGroup = useCreateGroup()

  const groups = groupsData?.groups ?? []
  const hasUnmatchedTopics = (state.metaInfo?.topics.unmatched_topics.length ?? 0) > 0

  // Calculate summary stats
  const stats = useMemo(() => {
    let totalSelected = 0
    let topicsWithSelections = 0

    state.matchedTopics.forEach((topic) => {
      const selectedCount = topic.prompts.filter((p) => p.isSelected).length
      totalSelected += selectedCount
      if (selectedCount > 0) topicsWithSelections++
    })

    return {
      totalSelected,
      topicsWithSelections,
      totalTopics: state.matchedTopics.length,
    }
  }, [state.matchedTopics])

  // Handle loading prompts for a topic
  const handleLoadPrompts = async (topic: TopicWithPrompts) => {
    dispatch({
      type: "UPDATE_MATCHED_TOPIC",
      topicId: topic.topicId,
      updates: { isLoading: true, isExpanded: true },
    })

    try {
      const response = await loadTopicPrompts.mutateAsync([topic.topicId])
      const topicData = response.topics.find((t) => t.topic_id === topic.topicId)

      const prompts: PromptSelectionState[] =
        topicData?.prompts.map((p) => ({
          promptId: p.id,
          promptText: p.prompt_text,
          isSelected: false,
        })) ?? []

      dispatch({
        type: "UPDATE_MATCHED_TOPIC",
        topicId: topic.topicId,
        updates: { prompts, isLoading: false },
      })
    } catch {
      dispatch({
        type: "UPDATE_MATCHED_TOPIC",
        topicId: topic.topicId,
        updates: { isLoading: false },
      })
      dispatch({
        type: "SET_ERROR",
        error: "Failed to load prompts for this topic",
      })
    }
  }

  // Handle toggle expand
  const handleToggleExpand = (topicId: number) => {
    const topic = state.matchedTopics.find((t) => t.topicId === topicId)
    if (!topic) return

    // If not loaded yet, load prompts
    if (topic.prompts.length === 0 && !topic.isLoading) {
      handleLoadPrompts(topic)
    } else {
      dispatch({
        type: "UPDATE_MATCHED_TOPIC",
        topicId,
        updates: { isExpanded: !topic.isExpanded },
      })
    }
  }

  // Handle adding selected prompts to group
  const handleAddToGroup = (topicId: number) => {
    setPendingTopicId(topicId)
    setShowGroupSelector(true)
  }

  // Handle group selection
  const handleSelectGroup = async (groupId: number) => {
    if (!pendingTopicId) return

    const topic = state.matchedTopics.find((t) => t.topicId === pendingTopicId)
    if (!topic) return

    const selectedPromptIds = topic.prompts
      .filter((p) => p.isSelected)
      .map((p) => p.promptId)

    if (selectedPromptIds.length === 0) return

    setAddingToGroupId(groupId)

    try {
      await addPromptsToGroup.mutateAsync({
        groupId,
        promptIds: selectedPromptIds,
      })

      const group = groups.find((g) => g.id === groupId)

      // Mark topic as added
      dispatch({
        type: "UPDATE_MATCHED_TOPIC",
        topicId: pendingTopicId,
        updates: {
          addedToGroupId: groupId,
          addedToGroupTitle: group?.title ?? "Group",
          // Deselect all prompts after adding
          prompts: topic.prompts.map((p) => ({ ...p, isSelected: false })),
        },
      })

      setShowGroupSelector(false)
      setPendingTopicId(null)
      setAddingToGroupId(null)
    } catch {
      dispatch({
        type: "SET_ERROR",
        error: "Failed to add prompts to group",
      })
      setAddingToGroupId(null)
    }
  }

  // Handle creating a new group
  const handleCreateGroup = async (title: string, brands: BrandVariation[]) => {
    try {
      const newGroup = await createGroup.mutateAsync({ title, brands })
      // After creating, select it
      await handleSelectGroup(newGroup.id)
    } catch {
      dispatch({
        type: "SET_ERROR",
        error: "Failed to create group",
      })
    }
  }

  // Handle cancel group selector
  const handleCancelGroupSelector = () => {
    setShowGroupSelector(false)
    setPendingTopicId(null)
    setAddingToGroupId(null)
  }

  // Navigate to generation step
  const handleContinue = () => {
    dispatch({ type: "SET_STEP", step: "generate" })
  }

  // Go back to configure
  const handleBack = () => {
    dispatch({ type: "SET_STEP", step: "configure" })
  }

  if (state.matchedTopics.length === 0) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-[#FEF7F5] flex items-center justify-center mx-auto mb-4">
            <Package className="w-8 h-8 text-[#C4553D]" />
          </div>
          <h3 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-2">
            No matched topics found
          </h3>
          <p className="text-[#6B7280] font-['DM_Sans'] mb-6">
            We couldn't find any existing topics in our database for your domain.
            {hasUnmatchedTopics
              ? " But we found some topics to generate prompts for!"
              : " Try a different domain or country."}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleBack}
              className="px-5 py-2.5 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] font-['DM_Sans'] transition-colors"
            >
              Go Back
            </button>
            {hasUnmatchedTopics && (
              <button
                onClick={handleContinue}
                className="px-5 py-2.5 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-lg font-['DM_Sans'] transition-colors flex items-center gap-2"
              >
                <span>Generate Prompts</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left column: Topic cards */}
      <div className="lg:col-span-2 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937]">
            Matched Topics ({state.matchedTopics.length})
          </h2>
          <p className="text-sm text-[#6B7280] font-['DM_Sans']">
            Click to load prompts from our database
          </p>
        </div>

        {state.matchedTopics.map((topic, index) => (
          <TopicCard
            key={topic.topicId}
            topic={topic}
            colorIndex={index}
            onToggleExpand={() => handleToggleExpand(topic.topicId)}
            onTogglePrompt={(promptId) =>
              dispatch({
                type: "TOGGLE_PROMPT_SELECTION",
                topicId: topic.topicId,
                promptId,
              })
            }
            onSelectAll={() =>
              dispatch({ type: "SELECT_ALL_PROMPTS", topicId: topic.topicId })
            }
            onDeselectAll={() =>
              dispatch({ type: "DESELECT_ALL_PROMPTS", topicId: topic.topicId })
            }
            onAddToGroup={() => handleAddToGroup(topic.topicId)}
          />
        ))}

        {/* Group selector overlay */}
        {showGroupSelector && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              className="absolute inset-0 bg-black/20 backdrop-blur-sm"
              onClick={handleCancelGroupSelector}
            />
            <div className="relative z-10 w-full max-w-md">
              <GroupSelector
                groups={groups}
                isLoadingGroups={isLoadingGroups}
                onSelectGroup={handleSelectGroup}
                onCreateGroup={handleCreateGroup}
                onCancel={handleCancelGroupSelector}
                isAddingPrompt={addPromptsToGroup.isPending}
                isCreatingGroup={createGroup.isPending}
                addingToGroupId={addingToGroupId}
              />
            </div>
          </div>
        )}
      </div>

      {/* Right column: Summary panel */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 overflow-hidden sticky top-6">
          {/* Summary header */}
          <div className="px-5 py-4 border-b border-[#E5E7EB]/60 bg-gradient-to-br from-[#FAFAFA] to-white">
            <h3 className="font-['Fraunces'] text-base font-semibold text-[#1F2937]">
              Selection Summary
            </h3>
          </div>

          {/* Stats */}
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#6B7280] font-['DM_Sans']">
                Selected prompts
              </span>
              <span className="font-['Fraunces'] text-2xl font-semibold text-[#C4553D]">
                {stats.totalSelected}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-[#6B7280] font-['DM_Sans']">
                Topics with selections
              </span>
              <span className="font-['DM_Sans'] text-sm text-[#1F2937]">
                {stats.topicsWithSelections} / {stats.totalTopics}
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#C4553D] transition-all duration-300"
                style={{
                  width:
                    stats.totalTopics > 0
                      ? `${(stats.topicsWithSelections / stats.totalTopics) * 100}%`
                      : "0%",
                }}
              />
            </div>

            {/* Unmatched topics info */}
            {hasUnmatchedTopics && (
              <div className="pt-4 border-t border-[#E5E7EB]/60">
                <div className="flex items-center gap-2 text-sm text-[#6B7280] font-['DM_Sans']">
                  <Sparkles className="w-4 h-4 text-[#C4553D]" />
                  <span>
                    {state.metaInfo?.topics.unmatched_topics.length} topics available
                    for generation
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="p-5 border-t border-[#E5E7EB]/60 space-y-3">
            <button
              onClick={hasUnmatchedTopics ? handleContinue : onClose}
              className="w-full py-3 px-4 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-xl font-['DM_Sans'] transition-colors flex items-center justify-center gap-2"
            >
              {hasUnmatchedTopics ? (
                <>
                  <span>Continue to Generation</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              ) : (
                <>
                  <span>Done</span>
                  <Check className="w-4 h-4" />
                </>
              )}
            </button>

            <button
              onClick={handleBack}
              className="w-full py-3 px-4 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] hover:bg-[#FAFAFA] rounded-xl font-['DM_Sans'] transition-colors flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
