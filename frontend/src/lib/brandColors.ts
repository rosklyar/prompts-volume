export const ACCENT_COLOR = "#C4553D"

export const COMPETITOR_PALETTE = [
  "#3B82F6", // blue-500
  "#10B981", // emerald-500
  "#8B5CF6", // violet-500
  "#F59E0B", // amber-500
  "#06B6D4", // cyan-500
  "#EC4899", // pink-500
  "#84CC16", // lime-500
  "#F97316", // orange-500
]

export function buildBrandColorMap(
  competitors: { name: string; is_target_brand: boolean }[]
): Map<string, string> {
  const map = new Map<string, string>()
  let competitorIndex = 0
  for (const c of competitors) {
    if (c.is_target_brand) {
      map.set(c.name, ACCENT_COLOR)
    } else {
      map.set(c.name, COMPETITOR_PALETTE[competitorIndex % COMPETITOR_PALETTE.length])
      competitorIndex++
    }
  }
  return map
}
