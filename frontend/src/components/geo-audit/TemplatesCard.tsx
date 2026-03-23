import { useState } from "react"
import { Check, Copy } from "lucide-react"
import type { GeneratedTemplate } from "@/types/geo-audit"

interface TemplatesCardProps {
  templates: GeneratedTemplate[]
}

export function TemplatesCard({ templates }: TemplatesCardProps) {
  if (templates.length === 0) return null

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-['DM_Sans'] font-semibold text-gray-900 mb-4">
        Recommended Templates
      </h3>

      <div className="space-y-4">
        {templates.map((t, i) => (
          <TemplateBlock key={i} template={t} />
        ))}
      </div>
    </div>
  )
}

function TemplateBlock({ template }: { template: GeneratedTemplate }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(template.json_ld)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  let formatted: string
  try {
    formatted = JSON.stringify(JSON.parse(template.json_ld), null, 2)
  } catch {
    formatted = template.json_ld
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-semibold text-gray-800">{template.schema_type}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <p className="text-sm text-gray-500 mb-2">{template.rationale}</p>
      <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm font-mono">
        {formatted}
      </pre>
    </div>
  )
}
