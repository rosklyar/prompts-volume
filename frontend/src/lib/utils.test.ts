import { describe, it, expect } from 'vitest'
import { cn } from './utils'

describe('cn utility function', () => {
  it('should merge class names correctly', () => {
    const result = cn('px-2 py-1', 'px-4')
    // Tailwind merge should resolve to px-4 (later class wins)
    expect(result).toBe('py-1 px-4')
  })

  it('should handle conditional classes', () => {
    const isConditional = false
    const result = cn('base-class', isConditional && 'conditional', 'always')
    expect(result).toBe('base-class always')
  })

  it('should handle empty inputs', () => {
    const result = cn()
    expect(result).toBe('')
  })
})
