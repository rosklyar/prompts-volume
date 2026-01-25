import chatgptLogo from "@/assets/chatgpt-logo.svg"
import perplexityLogo from "@/assets/perplexity-logo.svg"
import geminiLogo from "@/assets/gemini-logo.svg"

export const assistantLogos: Record<string, string> = {
  ChatGPT: chatgptLogo,
  Perplexity: perplexityLogo,
  Gemini: geminiLogo,
}

export function getAssistantLogo(assistantName: string): string | null {
  return assistantLogos[assistantName] ?? null
}
