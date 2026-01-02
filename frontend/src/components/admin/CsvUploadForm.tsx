/**
 * CSV file upload component for prompts with review step
 */

import { useState, useRef, useCallback } from "react"
import {
  Upload,
  FileCheck,
  X,
  CheckCircle,
  Loader2,
  AlertCircle,
  Search,
} from "lucide-react"
import { useAnalyzePrompts } from "@/hooks/useAdminPrompts"
import { PromptReviewStep } from "./PromptReviewStep"
import type { Topic, PromptUploadResponse } from "@/types/admin"
import type { BatchAnalyzeResponse } from "@/types/batch-upload"

interface CsvUploadFormProps {
  selectedTopic: Topic | null
}

interface ParsedFile {
  file: File
  prompts: string[]
}

type UploadStep = "select" | "review" | "success"

export function CsvUploadForm({ selectedTopic }: CsvUploadFormProps) {
  const [step, setStep] = useState<UploadStep>("select")
  const [parsedFile, setParsedFile] = useState<ParsedFile | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<BatchAnalyzeResponse | null>(null)
  const [uploadResult, setUploadResult] = useState<PromptUploadResponse | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const analyzeMutation = useAnalyzePrompts()

  const parseAndValidateFile = useCallback(async (file: File) => {
    setParseError(null)
    setAnalysisResult(null)
    setUploadResult(null)
    setStep("select")

    try {
      const content = await file.text()
      const lines = content.trim().split(/\r?\n/)

      // Get non-empty lines
      const prompts = lines
        .map((line) => line.trim())
        .filter((line) => line.length > 0)

      if (prompts.length === 0) {
        setParseError("File has no prompts")
        return
      }

      setParsedFile({ file, prompts })
    } catch {
      setParseError("Failed to read file")
    }
  }, [])

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        parseAndValidateFile(file)
      }
    },
    [parseAndValidateFile]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)

      const file = e.dataTransfer.files?.[0]
      if (file) {
        parseAndValidateFile(file)
      }
    },
    [parseAndValidateFile]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleAnalyze = () => {
    if (!parsedFile) return

    analyzeMutation.mutate(parsedFile.prompts, {
      onSuccess: (result) => {
        setAnalysisResult(result)
        setStep("review")
      },
    })
  }

  const handleClearFile = () => {
    setParsedFile(null)
    setParseError(null)
    setAnalysisResult(null)
    setStep("select")
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleReset = () => {
    setUploadResult(null)
    setParsedFile(null)
    setParseError(null)
    setAnalysisResult(null)
    setStep("select")
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleUploadSuccess = (result: PromptUploadResponse) => {
    setUploadResult(result)
    setStep("success")
  }

  const handleBackToFile = () => {
    setAnalysisResult(null)
    setStep("select")
  }

  // Success state
  if (step === "success" && uploadResult) {
    return (
      <div className="border border-green-200 rounded-xl p-5 bg-green-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
            <CheckCircle className="w-6 h-6 text-green-600" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-green-900">Upload Complete!</p>
            <p className="text-sm text-green-700">
              {uploadResult.total_uploaded} prompts added to "{uploadResult.topic_title}"
            </p>
          </div>
        </div>
        <button
          onClick={handleReset}
          className="mt-4 w-full py-2.5 border border-green-300 text-green-700 rounded-xl
            font-medium hover:bg-green-100 transition-colors"
        >
          Upload Another File
        </button>
      </div>
    )
  }

  // Review step
  if (step === "review" && analysisResult && parsedFile && selectedTopic) {
    return (
      <PromptReviewStep
        items={analysisResult.items}
        prompts={parsedFile.prompts}
        selectedTopic={selectedTopic}
        onBack={handleBackToFile}
        onSuccess={handleUploadSuccess}
      />
    )
  }

  // Disabled state (no topic selected)
  if (!selectedTopic) {
    return (
      <div
        className="border-2 border-dashed border-gray-200 rounded-xl p-8
          text-center opacity-50 cursor-not-allowed"
      >
        <Upload className="w-10 h-10 mx-auto text-gray-300 mb-3" />
        <p className="text-gray-400">Select a topic first to upload prompts</p>
      </div>
    )
  }

  // File selected state - ready for analysis
  if (parsedFile) {
    return (
      <div className="border border-gray-200 rounded-xl p-5 bg-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center flex-shrink-0">
            <FileCheck className="w-5 h-5 text-green-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate">{parsedFile.file.name}</p>
            <p className="text-sm text-gray-500">{parsedFile.prompts.length} prompts detected</p>
          </div>
          <button
            onClick={handleClearFile}
            disabled={analyzeMutation.isPending}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {analyzeMutation.isError && (
          <div className="mt-4 p-3 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm flex items-start gap-2">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span>{analyzeMutation.error?.message || "Analysis failed"}</span>
          </div>
        )}

        <button
          onClick={handleAnalyze}
          disabled={analyzeMutation.isPending}
          className="w-full mt-4 py-3 bg-[#C4553D] text-white rounded-xl
            font-medium hover:bg-[#B04A35] transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
            flex items-center justify-center gap-2"
        >
          {analyzeMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing for duplicates...
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              Analyze {parsedFile.prompts.length} Prompts
            </>
          )}
        </button>

        <p className="mt-2 text-xs text-gray-500 text-center">
          We'll check for duplicates and similar prompts before uploading
        </p>
      </div>
    )
  }

  // Enabled state - ready for file selection
  return (
    <div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.txt,text/plain"
        onChange={handleFileSelect}
        className="hidden"
      />

      <div
        onClick={() => fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-xl p-8
          text-center cursor-pointer transition-colors group
          ${
            isDragging
              ? "border-[#C4553D] bg-[#C4553D]/5"
              : "border-gray-300 hover:border-[#C4553D]/50 hover:bg-[#C4553D]/5"
          }`}
      >
        <Upload
          className={`w-10 h-10 mx-auto mb-3 transition-colors
            ${isDragging ? "text-[#C4553D]" : "text-gray-400 group-hover:text-[#C4553D]"}`}
        />
        <p className="text-gray-600 mb-1">Drag & drop file here</p>
        <p className="text-sm text-gray-400">or click to browse</p>
        <p className="text-xs text-gray-400 mt-2">
          One prompt per line (.txt or .csv)
        </p>
      </div>

      {parseError && (
        <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{parseError}</span>
        </div>
      )}
    </div>
  )
}
