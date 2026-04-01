export type ScoreRating = "Critical" | "Poor" | "Fair" | "Good" | "Excellent"

export type AuditStatus = "pending" | "discovering" | "auditing" | "completed" | "failed"

export interface DetectedSchema {
  format: string
  schema_type: string
  properties: Record<string, unknown>
}

export interface ExtractionResult {
  total_blocks: number
  formats_found: string[]
  schema_types_found: string[]
  schemas: DetectedSchema[]
}

export interface ValidationIssue {
  schema_type: string
  severity: string
  field: string | null
  message: string
}

export interface ValidationResult {
  valid_count: number
  invalid_count: number
  issues: ValidationIssue[]
}

export interface RichResultGap {
  schema_type: string
  status: string
  missing_required: string[]
  missing_recommended: string[]
}

export interface RichResultCheck {
  eligible: string[]
  gaps: RichResultGap[]
}

export interface GeoSignal {
  name: string
  present: boolean
  completeness: number
  details: string
}

export interface SameAsLink {
  platform: string
  linked: boolean
  url: string | null
}

export interface GeoReadiness {
  signals: GeoSignal[]
  same_as_links: SameAsLink[]
  overall_readiness: number
}

export interface DeprecatedSchema {
  schema_type: string
  status: string
  message: string
}

export interface JsRenderingWarning {
  framework: string
  confidence: string
  message: string
}

export interface GeneratedTemplate {
  schema_type: string
  json_ld: string
  rationale: string
}

export interface ScoreBreakdown {
  component: string
  max_points: number
  earned_points: number
}

export interface AuditScore {
  total: number
  rating: ScoreRating
  breakdown: ScoreBreakdown[]
}

// --- Per-page audit result (no templates) ---

export interface PageAuditResult {
  url: string
  extraction: ExtractionResult
  validation: ValidationResult
  rich_results: RichResultCheck
  geo_readiness: GeoReadiness
  deprecated_schemas: DeprecatedSchema[]
  js_rendering_warnings: JsRenderingWarning[]
  score: AuditScore
}

export interface PageAuditStoredResponse {
  id: number
  audit_id: number
  url: string
  score_total: number
  score_rating: ScoreRating
  result: PageAuditResult
  created_at: string
}

// --- Site-level audit ---

export interface PageSummary {
  id?: number
  url: string
  score_total: number
  score_rating: string
}

export interface SiteAuditResult {
  url: string
  site_score: AuditScore
  pages: PageSummary[]
  recommended_templates: GeneratedTemplate[]
}

export interface SiteAuditStoredResponse {
  id: number
  url: string
  status: AuditStatus
  score_total: number | null
  score_rating: ScoreRating | null
  pages_discovered: number
  pages_audited: number
  pages_total: number
  result: SiteAuditResult | null
  error_message: string | null
  created_at: string
}

// --- Progress polling ---

export interface GeoAuditProgressResponse {
  id: number
  status: AuditStatus
  url: string
  pages_discovered: number
  pages_audited: number
  pages_total: number
  error_message: string | null
}

// Legacy single-page types (kept for backward compatibility)

export interface GeoAuditResult {
  url: string
  extraction: ExtractionResult
  validation: ValidationResult
  rich_results: RichResultCheck
  geo_readiness: GeoReadiness
  deprecated_schemas: DeprecatedSchema[]
  js_rendering_warnings: JsRenderingWarning[]
  recommended_templates: GeneratedTemplate[]
  score: AuditScore
}

export interface GeoAuditStoredResponse {
  id: number
  url: string
  score_total: number
  score_rating: ScoreRating
  result: GeoAuditResult
  created_at: string
}
