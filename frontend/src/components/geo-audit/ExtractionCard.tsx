import type { ExtractionResult } from "@/types/geo-audit"

interface ExtractionCardProps {
  extraction: ExtractionResult
}

export function ExtractionCard({ extraction }: ExtractionCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-['DM_Sans'] font-semibold text-gray-900 mb-3">
        Structured Data Extraction
      </h3>

      <p className="text-sm text-gray-600 mb-3">
        <span className="font-semibold text-gray-900">{extraction.total_blocks}</span> block{extraction.total_blocks !== 1 ? "s" : ""} found
      </p>

      {extraction.formats_found.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1.5">Formats</p>
          <div className="flex flex-wrap gap-1.5">
            {extraction.formats_found.map((f) => (
              <span
                key={f}
                className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {extraction.schema_types_found.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1.5">Schema Types</p>
          <div className="flex flex-wrap gap-1.5">
            {extraction.schema_types_found.map((t) => (
              <span
                key={t}
                className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
