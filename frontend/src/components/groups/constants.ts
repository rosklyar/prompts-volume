/**
 * Constants for Prompt Groups feature
 * Editorial/magazine-inspired color palette
 */

export const GROUP_COLORS = [
  {
    name: "Forest",
    bg: "#F0F7F4",
    border: "#4A7C59",
    accent: "#4A7C59",
    hoverBg: "#E5F0E9",
  },
  {
    name: "Lavender",
    bg: "#F5F3F7",
    border: "#6B5B7A",
    accent: "#6B5B7A",
    hoverBg: "#EBE7EF",
  },
  {
    name: "Gold",
    bg: "#FDF6E3",
    border: "#B68D40",
    accent: "#B68D40",
    hoverBg: "#F9EED4",
  },
] as const

export const QUARANTINE_COLOR = {
  name: "Quarantine",
  bg: "#FDFAF8",
  border: "#C4553D",
  accent: "#C4553D",
  hoverBg: "#FDF0EC",
  borderStyle: "dashed" as const,
}

export const MAX_GROUPS = 10
export const GRID_COLS = 3
export const GRID_ROWS = 2

export function getGroupColor(index: number) {
  return GROUP_COLORS[index % GROUP_COLORS.length]
}

/**
 * Brand color palette - used consistently across prompt tags, answer highlights, and reports
 */
export const BRAND_COLORS: BrandColor[] = [
  { bg: "#f3e8ff", text: "#7c3aed" }, // violet
  { bg: "#fce7f3", text: "#db2777" }, // pink
  { bg: "#e0f2fe", text: "#0284c7" }, // sky
  { bg: "#fef3c7", text: "#d97706" }, // amber
  { bg: "#d1fae5", text: "#059669" }, // emerald
  { bg: "#fee2e2", text: "#dc2626" }, // red
  { bg: "#e0e7ff", text: "#4f46e5" }, // indigo
  { bg: "#ccfbf1", text: "#0d9488" }, // teal
]

export interface BrandColor {
  bg: string
  text: string
}

/**
 * Get a consistent color for a brand.
 * Target brand uses the group's accent color.
 * Competitors get assigned colors from BRAND_COLORS based on their index.
 */
export function getBrandColor(
  brandName: string,
  targetBrandName: string | null | undefined,
  competitorNames: string[],
  accentColor: string
): BrandColor {
  if (brandName === targetBrandName) {
    return { bg: `${accentColor}20`, text: accentColor }
  }

  const competitorIndex = competitorNames.indexOf(brandName)
  if (competitorIndex >= 0) {
    return BRAND_COLORS[competitorIndex % BRAND_COLORS.length]
  }

  // Fallback for unknown brands
  return BRAND_COLORS[0]
}
