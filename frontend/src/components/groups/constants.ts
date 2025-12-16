/**
 * Constants for Prompt Groups feature
 * Editorial/magazine-inspired color palette
 */

export const GROUP_COLORS = [
  {
    name: "Common",
    bg: "#FEF7F5",
    border: "#C4553D",
    accent: "#C4553D",
    hoverBg: "#FDF0EC",
  },
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
  {
    name: "Slate",
    bg: "#F2F7F9",
    border: "#4A6572",
    accent: "#4A6572",
    hoverBg: "#E5EEF2",
  },
  {
    name: "Terra",
    bg: "#FFF5F2",
    border: "#D4785D",
    accent: "#D4785D",
    hoverBg: "#FFEBE5",
  },
] as const

export const MAX_GROUPS = 6
export const GRID_COLS = 3
export const GRID_ROWS = 2

export function getGroupColor(index: number) {
  return GROUP_COLORS[index % GROUP_COLORS.length]
}

export function getGroupColorByIsCommon(isCommon: boolean, customIndex: number) {
  if (isCommon) return GROUP_COLORS[0]
  // Custom groups use colors 1-5
  return GROUP_COLORS[(customIndex % 5) + 1]
}
