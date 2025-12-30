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
