/**
 * BrandLogo - Displays a favicon for a domain with letter-circle fallback.
 *
 * Uses Google's public favicon API to fetch the icon.
 * On error or missing domain, shows a colored circle with the first letter of the name.
 */

import { useState } from "react"

function hashStringToColor(str: string): string {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 55%, 45%)`
}

function faviconUrl(domain: string): string {
  let normalized = domain.trim().toLowerCase()
  for (const prefix of ["https://", "http://", "//"]) {
    if (normalized.startsWith(prefix)) {
      normalized = normalized.slice(prefix.length)
    }
  }
  normalized = normalized.replace(/\/+$/, "")
  return `https://www.google.com/s2/favicons?domain=${normalized}&sz=64`
}

interface BrandLogoProps {
  domain?: string | null
  name: string
  size?: number
}

export function BrandLogo({ domain, name, size = 32 }: BrandLogoProps) {
  const [hasError, setHasError] = useState(false)

  const showFallback = !domain || hasError

  if (showFallback) {
    const letter = name.charAt(0).toUpperCase() || "?"
    const bgColor = hashStringToColor(name)
    return (
      <div
        className="flex-shrink-0 rounded-full flex items-center justify-center text-white font-semibold select-none"
        style={{
          width: size,
          height: size,
          backgroundColor: bgColor,
          fontSize: size * 0.45,
          lineHeight: 1,
        }}
      >
        {letter}
      </div>
    )
  }

  return (
    <img
      src={faviconUrl(domain)}
      alt={`${name} logo`}
      width={size}
      height={size}
      className="flex-shrink-0 rounded-full object-contain"
      onError={() => setHasError(true)}
    />
  )
}
