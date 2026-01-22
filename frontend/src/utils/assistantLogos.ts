import chatgptLogo from "@/assets/chatgpt-logo.svg"
import perplexityLogo from "@/assets/perplexity-logo.svg"

export const assistantLogos: Record<string, string> = {
  ChatGPT: chatgptLogo,
  Perplexity: perplexityLogo,
}

export function getAssistantLogo(assistantName: string): string | null {
  return assistantLogos[assistantName] ?? null
}
