/**
 * Individual pending prompt card with approve/reject actions
 */

import { useState } from "react"
import { Check, X, Tag, Users, Loader2 } from "lucide-react"
import type { PendingPromptResponse, Topic } from "@/types/admin"

interface PendingPromptCardProps {
  prompt: PendingPromptResponse
  isSelected: boolean
  onSelect: (id: number) => void
  onApprove: (promptId: number, topicId?: number | null) => void
  onReject: (promptId: number) => void
  topics: Topic[]
  isActioning: boolean
}

export function PendingPromptCard({
  prompt,
  isSelected,
  onSelect,
  onApprove,
  onReject,
  topics,
  isActioning,
}: PendingPromptCardProps) {
  const [showTopicDropdown, setShowTopicDropdown] = useState(false)
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(
    prompt.topic_id
  )

  const handleApproveClick = () => {
    if (!prompt.topic_id) {
      // Show dropdown to select topic
      setShowTopicDropdown(true)
    } else {
      onApprove(prompt.id, prompt.topic_id)
    }
  }

  const handleConfirmApprove = () => {
    onApprove(prompt.id, selectedTopicId)
    setShowTopicDropdown(false)
  }

  // Group topics for dropdown
  const groupedTopics = topics.reduce(
    (acc, topic) => {
      const key = `${topic.business_domain_name} (${topic.country_name})`
      if (!acc[key]) {
        acc[key] = []
      }
      acc[key].push(topic)
      return acc
    },
    {} as Record<string, Topic[]>
  )

  return (
    <div
      className={`border rounded-xl p-4 transition-all ${
        isSelected
          ? "border-[#C4553D] bg-[#C4553D]/5"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <button
          onClick={() => onSelect(prompt.id)}
          disabled={isActioning}
          className={`flex-shrink-0 w-5 h-5 mt-0.5 rounded border flex items-center justify-center transition-colors
            ${
              isSelected
                ? "bg-[#C4553D] border-[#C4553D]"
                : "border-gray-300 hover:border-gray-400"
            }
            disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isSelected && <Check className="w-3 h-3 text-white" />}
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-900">{prompt.prompt_text}</p>

          {/* Metadata */}
          <div className="mt-2 flex flex-wrap gap-2">
            {/* Topic badge */}
            {prompt.topic_title ? (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-md">
                <Tag className="w-3 h-3" />
                {prompt.topic_title}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-50 text-amber-700 text-xs rounded-md">
                <Tag className="w-3 h-3" />
                No topic assigned
              </span>
            )}

            {/* Groups badge */}
            {prompt.group_titles.length > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-md">
                <Users className="w-3 h-3" />
                {prompt.group_titles.length === 1
                  ? prompt.group_titles[0]
                  : `${prompt.group_titles.length} groups`}
              </span>
            )}
          </div>

          {/* Topic selection dropdown (shown when approving without topic) */}
          {showTopicDropdown && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200 animate-in fade-in duration-200">
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Assign a topic before approving
              </label>
              <select
                value={selectedTopicId ?? ""}
                onChange={(e) =>
                  setSelectedTopicId(
                    e.target.value ? parseInt(e.target.value, 10) : null
                  )
                }
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm
                  focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                  outline-none bg-white"
              >
                <option value="">Select topic...</option>
                {Object.entries(groupedTopics).map(([groupName, groupTopics]) => (
                  <optgroup key={groupName} label={groupName}>
                    {groupTopics.map((topic) => (
                      <option key={topic.id} value={topic.id}>
                        {topic.title}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => setShowTopicDropdown(false)}
                  className="flex-1 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmApprove}
                  disabled={!selectedTopicId}
                  className="flex-1 px-3 py-2 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  Confirm
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        {!showTopicDropdown && (
          <div className="flex-shrink-0 flex gap-2">
            <button
              onClick={handleApproveClick}
              disabled={isActioning}
              className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
              title="Approve"
            >
              {isActioning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={() => onReject(prompt.id)}
              disabled={isActioning}
              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              title="Reject"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
