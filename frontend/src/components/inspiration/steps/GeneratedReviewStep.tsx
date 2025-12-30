/**
 * GeneratedReviewStep - Step 4: Review generated prompts with similarity matching
 * Similar to BatchUploadModal review flow with radio selection
 */

import { useState, useMemo } from "react"
import {
  useAddPromptsToGroupFromInspiration,
} from "@/hooks/useInspiration"
import { useGroups, useCreateGroup } from "@/hooks/useGroups"
import { evaluationsApi } from "@/client/api"
import { GroupSelector } from "@/components/groups/GroupSelector"
import { GeneratedPromptReviewCard } from "../GeneratedPromptReviewCard"
import { getGroupColor } from "@/components/groups/constants"
import {
  ArrowLeft,
  Check,
  FolderPlus,
  Sparkles,
  ChevronRight,
  CheckCircle2,
} from "lucide-react"
import type { WizardAction } from "../InspirationModal"
import type { WizardState } from "@/types/inspiration"
import type { BrandVariation } from "@/types/groups"

interface GeneratedReviewStepProps {
  state: WizardState
  dispatch: React.Dispatch<WizardAction>
  onClose: () => void
}

export function GeneratedReviewStep({ state, dispatch, onClose }: GeneratedReviewStepProps) {
  const [showGroupSelector, setShowGroupSelector] = useState(false)
  const [pendingTopicTitle, setPendingTopicTitle] = useState<string | null>(null)
  const [addingToGroupId, setAddingToGroupId] = useState<number | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const addPromptsToGroup = useAddPromptsToGroupFromInspiration()
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups()
  const createGroup = useCreateGroup()

  const groups = groupsData?.groups ?? []

  // Calculate stats
  const stats = useMemo(() => {
    let usingMatches = 0
    let addingNew = 0
    let topicsComplete = 0

    state.generatedTopics.forEach((topic) => {
      if (topic.addedToGroupId) {
        topicsComplete++
      }
      topic.prompts.forEach((p) => {
        if (p.selectedOption === "use-match" && p.selectedMatchId) {
          usingMatches++
        } else {
          addingNew++
        }
      })
    })

    return {
      usingMatches,
      addingNew,
      topicsComplete,
      totalTopics: state.generatedTopics.length,
      totalPrompts: state.generatedTopics.reduce((sum, t) => sum + t.prompts.length, 0),
    }
  }, [state.generatedTopics])

  // Handle toggle expand for topic
  const handleToggleExpand = (topicTitle: string) => {
    dispatch({
      type: "UPDATE_GENERATED_TOPIC",
      topicTitle,
      updates: {
        isExpanded: !state.generatedTopics.find((t) => t.topicTitle === topicTitle)
          ?.isExpanded,
      },
    })
  }

  // Handle prompt selection change
  const handlePromptChange = (
    topicTitle: string,
    promptIndex: number,
    selectedOption: "keep-original" | "use-match",
    matchId: number | null
  ) => {
    dispatch({
      type: "UPDATE_GENERATED_PROMPT",
      topicTitle,
      promptIndex,
      selectedOption,
      matchId,
    })
  }

  // Handle add to group
  const handleAddToGroup = (topicTitle: string) => {
    setPendingTopicTitle(topicTitle)
    setShowGroupSelector(true)
  }

  // Handle group selection
  const handleSelectGroup = async (groupId: number) => {
    if (!pendingTopicTitle) return

    const topic = state.generatedTopics.find((t) => t.topicTitle === pendingTopicTitle)
    if (!topic) return

    setAddingToGroupId(groupId)
    setIsSubmitting(true)

    try {
      // Separate prompts into existing (use match) and new (keep original)
      const existingPromptIds: number[] = []
      const newPromptTexts: string[] = []

      topic.prompts.forEach((p) => {
        if (p.selectedOption === "use-match" && p.selectedMatchId) {
          existingPromptIds.push(p.selectedMatchId)
        } else {
          newPromptTexts.push(p.inputText)
        }
      })

      // Add existing prompts to group
      if (existingPromptIds.length > 0) {
        await addPromptsToGroup.mutateAsync({
          groupId,
          promptIds: existingPromptIds,
        })
      }

      // Create new prompts via priority prompts endpoint and add to group
      if (newPromptTexts.length > 0) {
        const result = await evaluationsApi.addPriorityPrompts(newPromptTexts)
        const newPromptIds = result.prompts.map((p) => p.prompt_id)

        await addPromptsToGroup.mutateAsync({
          groupId,
          promptIds: newPromptIds,
        })
      }

      const group = groups.find((g) => g.id === groupId)

      // Mark topic as added
      dispatch({
        type: "UPDATE_GENERATED_TOPIC",
        topicTitle: pendingTopicTitle,
        updates: {
          addedToGroupId: groupId,
          addedToGroupTitle: group?.title ?? "Group",
        },
      })

      setShowGroupSelector(false)
      setPendingTopicTitle(null)
      setAddingToGroupId(null)
      setIsSubmitting(false)
    } catch {
      dispatch({
        type: "SET_ERROR",
        error: "Failed to add prompts to group",
      })
      setAddingToGroupId(null)
      setIsSubmitting(false)
    }
  }

  // Handle creating a new group
  const handleCreateGroup = async (title: string, brands: BrandVariation[]) => {
    try {
      const newGroup = await createGroup.mutateAsync({ title, brands })
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
    setPendingTopicTitle(null)
    setAddingToGroupId(null)
  }

  // Go back to generation
  const handleBack = () => {
    dispatch({ type: "SET_STEP", step: "generate" })
  }

  // Complete - close modal and return to dashboard
  const handleComplete = () => {
    onClose()
  }

  if (state.generatedTopics.length === 0) {
    return (
      <div className="max-w-xl mx-auto">
        <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-[#FEF7F5] flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-[#C4553D]" />
          </div>
          <h3 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-2">
            No generated prompts to review
          </h3>
          <p className="text-[#6B7280] font-['DM_Sans'] mb-6">
            You haven't generated any prompts yet.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleBack}
              className="px-5 py-2.5 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] font-['DM_Sans'] transition-colors flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
            <button
              onClick={handleComplete}
              className="px-5 py-2.5 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-lg font-['DM_Sans'] transition-colors flex items-center gap-2"
            >
              <span>Complete</span>
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left column: Topic review cards */}
      <div className="lg:col-span-2 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937]">
            Review Generated Prompts
          </h2>
          <p className="text-sm text-[#6B7280] font-['DM_Sans']">
            Choose to use existing matches or add as new
          </p>
        </div>

        {state.generatedTopics.map((topic, index) => {
          const color = getGroupColor(index)

          // Already added to group
          if (topic.addedToGroupId) {
            return (
              <div
                key={topic.topicTitle}
                className="rounded-2xl border-2 border-dashed overflow-hidden"
                style={{ borderColor: color.accent, backgroundColor: `${color.bg}40` }}
              >
                <div className="px-5 py-4 flex items-center gap-4">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: `${color.accent}20` }}
                  >
                    <CheckCircle2 className="w-5 h-5" style={{ color: color.accent }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3
                      className="font-['Fraunces'] text-base font-semibold truncate"
                      style={{ color: color.accent }}
                    >
                      {topic.topicTitle}
                    </h3>
                    <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                      {topic.prompts.length} prompts added to{" "}
                      <span className="font-medium" style={{ color: color.accent }}>
                        {topic.addedToGroupTitle}
                      </span>
                    </p>
                  </div>
                  <span
                    className="px-3 py-1.5 rounded-full text-xs font-medium font-['DM_Sans']"
                    style={{ backgroundColor: `${color.accent}15`, color: color.accent }}
                  >
                    Complete
                  </span>
                </div>
              </div>
            )
          }

          // Active topic card
          return (
            <div
              key={topic.topicTitle}
              className="rounded-2xl border overflow-hidden transition-all duration-200"
              style={{
                borderColor: topic.isExpanded ? color.accent : "#E5E7EB",
                boxShadow: topic.isExpanded
                  ? `0 4px 20px -4px ${color.accent}25`
                  : "0 2px 8px -2px rgba(0,0,0,0.05)",
              }}
            >
              {/* Header */}
              <div
                className="px-5 py-4 cursor-pointer select-none transition-colors"
                style={{ backgroundColor: topic.isExpanded ? color.bg : "white" }}
                onClick={() => handleToggleExpand(topic.topicTitle)}
              >
                <div className="flex items-center gap-4">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: `${color.accent}20` }}
                  >
                    <ChevronRight
                      className="w-4 h-4 transition-transform duration-200"
                      style={{
                        color: color.accent,
                        transform: topic.isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                      }}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3
                      className="font-['Fraunces'] text-base font-semibold truncate"
                      style={{ color: topic.isExpanded ? color.accent : "#1F2937" }}
                    >
                      {topic.topicTitle}
                    </h3>
                    <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                      {topic.prompts.length} prompts generated
                    </p>
                  </div>
                </div>
              </div>

              {/* Expanded content */}
              <div
                className="overflow-hidden transition-all duration-300"
                style={{
                  maxHeight: topic.isExpanded ? "2000px" : "0",
                  opacity: topic.isExpanded ? 1 : 0,
                }}
              >
                <div className="border-t" style={{ borderColor: `${color.accent}30` }}>
                  {/* Prompts */}
                  <div className="max-h-96 overflow-y-auto divide-y divide-[#E5E7EB]/50">
                    {topic.prompts.map((prompt, promptIndex) => (
                      <GeneratedPromptReviewCard
                        key={promptIndex}
                        prompt={prompt}
                        accentColor={color.accent}
                        onChange={(selectedOption, matchId) =>
                          handlePromptChange(
                            topic.topicTitle,
                            promptIndex,
                            selectedOption,
                            matchId
                          )
                        }
                      />
                    ))}
                  </div>

                  {/* Add to group action */}
                  <div
                    className="px-5 py-4 flex items-center justify-end"
                    style={{ backgroundColor: `${color.bg}60` }}
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleAddToGroup(topic.topicTitle)
                      }}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white rounded-lg transition-all hover:shadow-md"
                      style={{ backgroundColor: color.accent }}
                    >
                      <FolderPlus className="w-4 h-4" />
                      <span className="font-['DM_Sans']">Add All to Group</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )
        })}

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
                isAddingPrompt={isSubmitting}
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
          <div className="px-5 py-4 border-b border-[#E5E7EB]/60 bg-gradient-to-br from-[#FAFAFA] to-white">
            <h3 className="font-['Fraunces'] text-base font-semibold text-[#1F2937]">
              Review Summary
            </h3>
          </div>

          <div className="p-5 space-y-4">
            <div className="flex gap-3">
              <div className="flex-1 p-3 rounded-lg bg-[#FEF7F5]">
                <p className="text-2xl font-semibold text-[#C4553D] font-['Fraunces']">
                  {stats.usingMatches}
                </p>
                <p className="text-xs text-[#6B7280] font-['DM_Sans']">using matches</p>
              </div>
              <div className="flex-1 p-3 rounded-lg bg-[#FAFAFA]">
                <p className="text-2xl font-semibold text-[#1F2937] font-['Fraunces']">
                  {stats.addingNew}
                </p>
                <p className="text-xs text-[#6B7280] font-['DM_Sans']">adding as new</p>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-[#6B7280] font-['DM_Sans']">Topics added</span>
              <span className="font-['DM_Sans'] text-sm text-[#1F2937]">
                {stats.topicsComplete} / {stats.totalTopics}
              </span>
            </div>

            <div className="h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#C4553D] transition-all duration-300"
                style={{
                  width:
                    stats.totalTopics > 0
                      ? `${(stats.topicsComplete / stats.totalTopics) * 100}%`
                      : "0%",
                }}
              />
            </div>
          </div>

          <div className="p-5 border-t border-[#E5E7EB]/60 space-y-3">
            <button
              onClick={handleComplete}
              className="w-full py-3 px-4 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-xl font-['DM_Sans'] transition-colors flex items-center justify-center gap-2"
            >
              <span>Complete</span>
              <Check className="w-4 h-4" />
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
