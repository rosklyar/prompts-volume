/**
 * Topic selector with create new topic functionality
 */

import { useState } from "react"
import { X, Plus, Loader2 } from "lucide-react"
import {
  useBusinessDomains,
  useCountries,
  useTopics,
  useCreateTopic,
} from "@/hooks/useAdminPrompts"
import type { Topic } from "@/types/admin"

interface TopicSelectorProps {
  selectedTopic: Topic | null
  onTopicSelect: (topic: Topic | null) => void
}

export function TopicSelector({ selectedTopic, onTopicSelect }: TopicSelectorProps) {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newTopicTitle, setNewTopicTitle] = useState("")
  const [newTopicDescription, setNewTopicDescription] = useState("")
  const [selectedBusinessDomainId, setSelectedBusinessDomainId] = useState<number | undefined>()
  const [selectedCountryId, setSelectedCountryId] = useState<number | undefined>()

  const { data: businessDomainsData, isLoading: isLoadingBD } = useBusinessDomains()
  const { data: countriesData, isLoading: isLoadingCountries } = useCountries()
  const { data: topicsData, isLoading: isLoadingTopics } = useTopics()
  const createTopicMutation = useCreateTopic()

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const topicId = e.target.value ? parseInt(e.target.value, 10) : null
    if (topicId && topicsData) {
      const topic = topicsData.topics.find((t) => t.id === topicId)
      onTopicSelect(topic || null)
    } else {
      onTopicSelect(null)
    }
  }

  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedBusinessDomainId || !selectedCountryId) return

    createTopicMutation.mutate(
      {
        title: newTopicTitle,
        description: newTopicDescription,
        business_domain_id: selectedBusinessDomainId,
        country_id: selectedCountryId,
      },
      {
        onSuccess: (topic) => {
          onTopicSelect(topic)
          setShowCreateForm(false)
          setNewTopicTitle("")
          setNewTopicDescription("")
          setSelectedBusinessDomainId(undefined)
          setSelectedCountryId(undefined)
        },
      }
    )
  }

  const resetForm = () => {
    setShowCreateForm(false)
    setNewTopicTitle("")
    setNewTopicDescription("")
    setSelectedBusinessDomainId(undefined)
    setSelectedCountryId(undefined)
  }

  // Group topics by business domain and country
  const groupedTopics = topicsData?.topics.reduce(
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

  if (showCreateForm) {
    return (
      <div className="bg-gray-50 rounded-xl p-5 space-y-4 border border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-gray-900">New Topic</h3>
          <button
            onClick={resetForm}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleCreateTopic} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title
            </label>
            <input
              type="text"
              value={newTopicTitle}
              onChange={(e) => setNewTopicTitle(e.target.value)}
              placeholder="e.g., Смартфони і телефони"
              required
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl
                focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                placeholder:text-gray-400 outline-none transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={newTopicDescription}
              onChange={(e) => setNewTopicDescription(e.target.value)}
              placeholder="Brief description of the topic..."
              required
              rows={2}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl
                focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                placeholder:text-gray-400 outline-none transition-all resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Business Domain
              </label>
              <select
                value={selectedBusinessDomainId || ""}
                onChange={(e) =>
                  setSelectedBusinessDomainId(
                    e.target.value ? parseInt(e.target.value, 10) : undefined
                  )
                }
                required
                disabled={isLoadingBD}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl
                  focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                  outline-none transition-all bg-white disabled:bg-gray-100"
              >
                <option value="">Select...</option>
                {businessDomainsData?.business_domains.map((bd) => (
                  <option key={bd.id} value={bd.id}>
                    {bd.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Country
              </label>
              <select
                value={selectedCountryId || ""}
                onChange={(e) =>
                  setSelectedCountryId(
                    e.target.value ? parseInt(e.target.value, 10) : undefined
                  )
                }
                required
                disabled={isLoadingCountries}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl
                  focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                  outline-none transition-all bg-white disabled:bg-gray-100"
              >
                <option value="">Select...</option>
                {countriesData?.countries.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {createTopicMutation.isError && (
            <div className="p-3 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm">
              {createTopicMutation.error?.message || "Failed to create topic"}
            </div>
          )}

          <button
            type="submit"
            disabled={
              createTopicMutation.isPending ||
              !newTopicTitle ||
              !newTopicDescription ||
              !selectedBusinessDomainId ||
              !selectedCountryId
            }
            className="w-full py-2.5 bg-[#C4553D] text-white rounded-xl font-medium
              hover:bg-[#B04A35] transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center justify-center gap-2"
          >
            {createTopicMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Topic"
            )}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">Select Topic</label>
        <button
          onClick={() => setShowCreateForm(true)}
          className="text-sm text-[#C4553D] hover:underline flex items-center gap-1"
        >
          <Plus className="w-3.5 h-3.5" />
          Create New Topic
        </button>
      </div>

      <select
        value={selectedTopic?.id || ""}
        onChange={handleSelectChange}
        disabled={isLoadingTopics}
        className="w-full px-4 py-3 border border-gray-200 rounded-xl
          focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
          outline-none transition-all bg-white disabled:bg-gray-100"
      >
        <option value="">Choose a topic...</option>
        {groupedTopics &&
          Object.entries(groupedTopics).map(([groupName, topics]) => (
            <optgroup key={groupName} label={groupName}>
              {topics.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.title}
                </option>
              ))}
            </optgroup>
          ))}
      </select>

      {selectedTopic && (
        <div className="text-sm text-gray-500">
          {selectedTopic.description}
        </div>
      )}
    </div>
  )
}
