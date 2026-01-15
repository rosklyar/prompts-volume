/**
 * Domain utility functions for URL normalization
 */

/**
 * Normalizes a URL or domain string to a clean domain format.
 * Removes protocol prefixes (http://, https://) and trailing slashes.
 *
 * @param url - The URL or domain string to normalize
 * @returns The normalized domain string, or empty string if input is empty
 *
 * @example
 * normalizeDomain("https://example.com/") // "example.com"
 * normalizeDomain("http://example.com")   // "example.com"
 * normalizeDomain("example.com")          // "example.com"
 * normalizeDomain("")                     // ""
 */
export function normalizeDomain(url: string): string {
  let domain = url.trim().toLowerCase()
  if (!domain) return ""
  if (domain.startsWith("http://") || domain.startsWith("https://")) {
    domain = domain.split("://")[1]
  }
  domain = domain.replace(/\/$/, "")
  return domain
}
