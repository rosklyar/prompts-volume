/**
 * Admin approvals tab - list pending prompts with batch actions
 */

import { useState, useMemo } from "react"
import { Check, X, Tag, Loader2, ChevronLeft, ChevronRight } from "lucide-react"
import { PendingPromptCard } from "./PendingPromptCard"
import {
  usePendingPrompts,
  useApprovePrompt,
  useRejectPrompt,
  useBatchApprove,
  useBatchReject,
} from "@/hooks/useAdminApprovals"
import { useTopics } from "@/hooks/useAdminPrompts"
import type { Topic } from "@/types/admin"

const PAGE_SIZE = 20

export function AdminApprovalsTab() {
  const [page, setPage] = useState(0)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [batchTopicId, setBatchTopicId] = useState<number | null>(null)
  const [showBatchTopicSelector, setShowBatchTopicSelector] = useState(false)

  // Queries
  const { data, isLoading, error } = usePendingPrompts(PAGE_SIZE, page * PAGE_SIZE)
  const { data: topicsData } = useTopics()

  // Memoize topics array to avoid recreating on every render
  const topics = useMemo(() => topicsData?.topics ?? [], [topicsData?.topics])

  // Mutations
  const approveMutation = useApprovePrompt()
  const rejectMutation = useRejectPrompt()
  const batchApproveMutation = useBatchApprove()
  const batchRejectMutation = useBatchReject()

  const isAnyMutating =
    approveMutation.isPending ||
    rejectMutation.isPending ||
    batchApproveMutation.isPending ||
    batchRejectMutation.isPending

  // Group topics for dropdown
  const groupedTopics = useMemo(() => {
    return topics.reduce(
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
  }, [topics])

  // Selection handlers
  const toggleSelection = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const selectAll = () => {
    if (data?.prompts) {
      setSelectedIds(new Set(data.prompts.map((p) => p.id)))
    }
  }

  const deselectAll = () => {
    setSelectedIds(new Set())
  }

  // Action handlers
  const handleApprove = (promptId: number, topicId?: number | null) => {
    approveMutation.mutate(
      { promptId, topicId },
      {
        onSuccess: () => {
          setSelectedIds((prev) => {
            const next = new Set(prev)
            next.delete(promptId)
            return next
          })
        },
      }
    )
  }

  const handleReject = (promptId: number) => {
    rejectMutation.mutate(promptId, {
      onSuccess: () => {
        setSelectedIds((prev) => {
          const next = new Set(prev)
          next.delete(promptId)
          return next
        })
      },
    })
  }

  const handleBatchApprove = () => {
    // Check if all selected prompts have a topic
    const selectedPrompts = data?.prompts.filter((p) => selectedIds.has(p.id)) ?? []
    const allHaveTopics = selectedPrompts.every((p) => p.topic_id !== null)

    if (!allHaveTopics && !batchTopicId) {
      setShowBatchTopicSelector(true)
      return
    }

    batchApproveMutation.mutate(
      { promptIds: Array.from(selectedIds), topicId: batchTopicId },
      {
        onSuccess: () => {
          setSelectedIds(new Set())
          setBatchTopicId(null)
          setShowBatchTopicSelector(false)
        },
      }
    )
  }

  const handleBatchReject = () => {
    batchRejectMutation.mutate(Array.from(selectedIds), {
      onSuccess: () => {
        setSelectedIds(new Set())
      },
    })
  }

  // Pagination
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const hasNextPage = page < totalPages - 1
  const hasPrevPage = page > 0

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="p-4 bg-red-50 rounded-xl border border-red-100 text-red-600 text-sm">
        Failed to load pending prompts. Please try again.
      </div>
    )
  }

  // Empty state
  if (!data?.prompts.length) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
          <Check className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">All caught up!</h3>
        <p className="text-gray-500">No pending prompts to review.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Selection toolbar */}
      <div className="flex items-center justify-between bg-white rounded-xl border border-gray-200 p-3">
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-500">
            <span className="font-medium">{data.total}</span> pending
            {selectedIds.size > 0 && (
              <span className="ml-2 text-[#C4553D]">
                ({selectedIds.size} selected)
              </span>
            )}
          </div>
          <div className="flex gap-2 text-xs">
            <button
              onClick={selectAll}
              className="text-[#C4553D] hover:underline"
            >
              Select all
            </button>
            <span className="text-gray-300">|</span>
            <button
              onClick={deselectAll}
              className="text-gray-500 hover:underline"
            >
              Deselect all
            </button>
          </div>
        </div>

        {/* Batch actions */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleBatchApprove}
              disabled={isAnyMutating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                text-green-700 bg-green-50 rounded-lg hover:bg-green-100 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {batchApproveMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Check className="w-3.5 h-3.5" />
              )}
              Approve ({selectedIds.size})
            </button>
            <button
              onClick={handleBatchReject}
              disabled={isAnyMutating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {batchRejectMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <X className="w-3.5 h-3.5" />
              )}
              Reject ({selectedIds.size})
            </button>
          </div>
        )}
      </div>

      {/* Batch topic selector modal */}
      {showBatchTopicSelector && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 animate-in fade-in duration-200">
          <div className="flex items-start gap-3">
            <Tag className="w-5 h-5 text-amber-600 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800 mb-2">
                Some prompts have no topic. Assign a topic for batch approval:
              </p>
              <select
                value={batchTopicId ?? ""}
                onChange={(e) =>
                  setBatchTopicId(
                    e.target.value ? parseInt(e.target.value, 10) : null
                  )
                }
                className="w-full px-3 py-2 border border-amber-200 rounded-lg text-sm
                  focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                  outline-none bg-white"
              >
                <option value="">Select topic for batch...</option>
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
                  onClick={() => {
                    setShowBatchTopicSelector(false)
                    setBatchTopicId(null)
                  }}
                  className="flex-1 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBatchApprove}
                  disabled={!batchTopicId || batchApproveMutation.isPending}
                  className="flex-1 px-3 py-2 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {batchApproveMutation.isPending && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}
                  Approve All
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Prompts list */}
      <div className="space-y-3">
        {data.prompts.map((prompt) => (
          <PendingPromptCard
            key={prompt.id}
            prompt={prompt}
            isSelected={selectedIds.has(prompt.id)}
            onSelect={toggleSelection}
            onApprove={handleApprove}
            onReject={handleReject}
            topics={topics}
            isActioning={
              (approveMutation.isPending &&
                approveMutation.variables?.promptId === prompt.id) ||
              (rejectMutation.isPending &&
                rejectMutation.variables === prompt.id)
            }
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <button
            onClick={() => setPage((p) => p - 1)}
            disabled={!hasPrevPage || isAnyMutating}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm text-gray-600
              border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasNextPage || isAnyMutating}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm text-gray-600
              border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}
