/**
 * Create/edit modal for business domains
 */

import { useState } from "react"
import { Plus, X } from "lucide-react"
import { toast } from "sonner"
import { adminApi } from "@/client/api"
import {
  useCreateAdminBusinessDomain,
  useUpdateAdminBusinessDomain,
} from "@/hooks/useAdminDomains"
import type { AdminBusinessDomain, KeywordFilterEntry } from "@/types/admin"

const OPERATOR_LABELS: Record<string, string> = {
  gt: ">",
  gte: ">=",
  lt: "<",
  lte: "<=",
  eq: "=",
}

const OPERATORS = Object.keys(OPERATOR_LABELS) as KeywordFilterEntry["operator"][]

interface AdminDomainFormModalProps {
  domain?: AdminBusinessDomain
  onClose: () => void
  onSuccess: () => void
}

export function AdminDomainFormModal({
  domain,
  onClose,
  onSuccess,
}: AdminDomainFormModalProps) {
  const isEdit = !!domain

  const [name, setName] = useState(domain?.name ?? "")
  const [description, setDescription] = useState(domain?.description ?? "")
  const [template, setTemplate] = useState(domain?.system_prompt_template ?? "")
  const [loadingTemplate, setLoadingTemplate] = useState(false)
  const [filterEntries, setFilterEntries] = useState<KeywordFilterEntry[]>(
    domain?.keyword_filter_config ?? []
  )

  const createMutation = useCreateAdminBusinessDomain()
  const updateMutation = useUpdateAdminBusinessDomain()

  const isPending = createMutation.isPending || updateMutation.isPending
  const error = createMutation.error || updateMutation.error

  const handleLoadDefaultTemplate = async () => {
    setLoadingTemplate(true)
    try {
      const data = await adminApi.getDefaultDomainTemplate()
      setTemplate(data.template)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load template")
    } finally {
      setLoadingTemplate(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const keyword_filter_config =
      filterEntries.length > 0 ? filterEntries : undefined

    if (isEdit) {
      updateMutation.mutate(
        {
          domainId: domain.id,
          request: {
            description,
            system_prompt_template: template,
            keyword_filter_config,
          },
        },
        {
          onSuccess: () => {
            toast.success("Domain updated")
            onSuccess()
            onClose()
          },
        }
      )
    } else {
      createMutation.mutate(
        {
          name: name.trim(),
          description,
          system_prompt_template: template,
          keyword_filter_config,
        },
        {
          onSuccess: () => {
            toast.success("Domain created")
            onSuccess()
            onClose()
          },
        }
      )
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-2xl w-full max-w-2xl shadow-xl overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Accent bar */}
        <div
          className="h-1 w-full shrink-0"
          style={{
            background: "linear-gradient(90deg, #C4553D 0%, #9B4332 100%)",
          }}
        />

        <div className="p-6 overflow-y-auto">
          <h2 className="font-['Fraunces'] text-xl font-medium text-gray-900 mb-6">
            {isEdit ? "Edit Domain" : "Create Domain"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name
              </label>
              {isEdit ? (
                <div>
                  <input
                    type="text"
                    value={name}
                    readOnly
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl bg-gray-50
                      text-gray-500 outline-none cursor-not-allowed"
                  />
                  <p className="text-xs text-gray-400 mt-1">(cannot be changed)</p>
                </div>
              ) : (
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., E-commerce"
                  required
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl
                    focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                    placeholder:text-gray-400 outline-none transition-all"
                />
              )}
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of this business domain"
                rows={2}
                required
                className="w-full px-4 py-3 border border-gray-200 rounded-xl
                  focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                  placeholder:text-gray-400 outline-none transition-all resize-none"
              />
            </div>

            {/* System Prompt Template */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  System Prompt Template
                </label>
                <button
                  type="button"
                  onClick={handleLoadDefaultTemplate}
                  disabled={loadingTemplate}
                  className="text-xs text-[#C4553D] hover:text-[#B04A35] font-medium
                    disabled:opacity-50 transition-colors"
                >
                  {loadingTemplate ? "Loading..." : "Load default template"}
                </button>
              </div>
              <textarea
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                placeholder="Enter the system prompt template..."
                required
                className="w-full px-4 py-3 border border-gray-200 rounded-xl
                  focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                  placeholder:text-gray-400 outline-none transition-all
                  font-mono text-sm h-64 resize-none"
              />

              {/* Placeholder hints */}
              <div className="bg-gray-50 rounded-xl p-3 mt-2">
                <p className="text-xs text-gray-500">
                  Available placeholders:{" "}
                  <code className="bg-gray-200 px-1 py-0.5 rounded text-gray-700">{"{domain_name}"}</code>{" "}
                  <code className="bg-gray-200 px-1 py-0.5 rounded text-gray-700">{"{keywords}"}</code>{" "}
                  <code className="bg-gray-200 px-1 py-0.5 rounded text-gray-700">{"{keywords_count}"}</code>{" "}
                  <code className="bg-gray-200 px-1 py-0.5 rounded text-gray-700">{"{language}"}</code>
                </p>
              </div>
            </div>

            {/* Keyword Filter Rules */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Keyword Filter Rules
                  </label>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Filter keywords before sending to LLM
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setFilterEntries([
                      ...filterEntries,
                      { type: "word_count", operator: "gte", value: 1 },
                    ])
                  }
                  className="flex items-center gap-1 text-xs text-[#C4553D] hover:text-[#B04A35]
                    font-medium transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Rule
                </button>
              </div>

              {filterEntries.length > 0 && (
                <div className="space-y-2">
                  {filterEntries.map((entry, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-2"
                    >
                      <select
                        value={entry.type}
                        onChange={(e) => {
                          const next = [...filterEntries]
                          next[idx] = { ...next[idx], type: e.target.value }
                          setFilterEntries(next)
                        }}
                        className="px-2 py-1.5 border border-gray-200 rounded-lg text-sm
                          bg-white outline-none focus:ring-2 focus:ring-[#C4553D]/20"
                      >
                        <option value="word_count">word_count</option>
                      </select>

                      <select
                        value={entry.operator ?? "gte"}
                        onChange={(e) => {
                          const next = [...filterEntries]
                          next[idx] = {
                            ...next[idx],
                            operator: e.target.value as KeywordFilterEntry["operator"],
                          }
                          setFilterEntries(next)
                        }}
                        className="px-2 py-1.5 border border-gray-200 rounded-lg text-sm
                          bg-white outline-none focus:ring-2 focus:ring-[#C4553D]/20"
                      >
                        {OPERATORS.map((op) => (
                          <option key={op} value={op}>
                            {OPERATOR_LABELS[op!]}
                          </option>
                        ))}
                      </select>

                      <input
                        type="number"
                        value={entry.value ?? 0}
                        onChange={(e) => {
                          const next = [...filterEntries]
                          next[idx] = {
                            ...next[idx],
                            value: parseInt(e.target.value, 10) || 0,
                          }
                          setFilterEntries(next)
                        }}
                        className="w-20 px-2 py-1.5 border border-gray-200 rounded-lg text-sm
                          bg-white outline-none focus:ring-2 focus:ring-[#C4553D]/20"
                      />

                      <button
                        type="button"
                        onClick={() =>
                          setFilterEntries(filterEntries.filter((_, i) => i !== idx))
                        }
                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="p-3 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm">
                {error.message || "Something went wrong. Please try again."}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isPending}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-xl
                  text-gray-700 font-medium hover:bg-gray-50 transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending || !name.trim() || !description.trim() || !template.trim()}
                className="flex-1 px-4 py-3 bg-[#C4553D] text-white rounded-xl
                  font-medium hover:bg-[#B04A35] transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isPending ? "Saving..." : isEdit ? "Update Domain" : "Create Domain"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
