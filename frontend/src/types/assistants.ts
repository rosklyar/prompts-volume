/**
 * TypeScript types for AI Assistants
 * Maps to backend models in src/assistants/models/api_models.py
 */

export interface AIAssistant {
  id: number
  name: string
}

export interface AIAssistantListResponse {
  assistants: AIAssistant[]
}
