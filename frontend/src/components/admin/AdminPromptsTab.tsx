/**
 * Admin prompts tab - combines topic selector and CSV upload
 */

import { useState } from "react"
import { TopicSelector } from "./TopicSelector"
import { CsvUploadForm } from "./CsvUploadForm"
import type { Topic } from "@/types/admin"

export function AdminPromptsTab() {
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null)

  return (
    <div className="space-y-8">
      {/* Topic Selection Section */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">1. Select Topic</h2>
        <TopicSelector
          selectedTopic={selectedTopic}
          onTopicSelect={setSelectedTopic}
        />
      </div>

      {/* CSV Upload Section */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">2. Upload Prompts</h2>
        <CsvUploadForm selectedTopic={selectedTopic} />
      </div>

      {/* Help text */}
      <div className="text-sm text-gray-500 space-y-2">
        <p>
          <strong>File Format:</strong> Plain text file with one prompt per line.
        </p>
        <p>
          <strong>Example:</strong>
        </p>
        <pre className="bg-gray-50 rounded-lg p-3 text-xs font-mono overflow-x-auto">
          Купити смартфон в Україні зі швидкою доставкою{"\n"}
          Де купити iPhone найдешевше{"\n"}
          Найкращі телефони 2025 року
        </pre>
      </div>
    </div>
  )
}
