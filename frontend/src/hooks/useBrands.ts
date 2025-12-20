/**
 * Hook for managing brands per group (frontend-only state with localStorage persistence)
 */
import { useState, useCallback, useEffect } from "react"
import type { BrandVariation } from "@/types/groups"

const STORAGE_KEY = "group_brands"

interface GroupBrands {
  [groupId: number]: BrandVariation[]
}

export function useBrands() {
  const [groupBrands, setGroupBrands] = useState<GroupBrands>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : {}
    } catch {
      return {}
    }
  })

  // Persist to localStorage whenever brands change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(groupBrands))
    } catch {
      // Ignore storage errors
    }
  }, [groupBrands])

  const getBrands = useCallback(
    (groupId: number): BrandVariation[] => {
      return groupBrands[groupId] || []
    },
    [groupBrands]
  )

  const setBrands = useCallback((groupId: number, brands: BrandVariation[]) => {
    setGroupBrands((prev) => ({
      ...prev,
      [groupId]: brands,
    }))
  }, [])

  const addBrand = useCallback((groupId: number, brand: BrandVariation) => {
    setGroupBrands((prev) => ({
      ...prev,
      [groupId]: [...(prev[groupId] || []), brand],
    }))
  }, [])

  const updateBrand = useCallback(
    (groupId: number, index: number, brand: BrandVariation) => {
      setGroupBrands((prev) => {
        const brands = [...(prev[groupId] || [])]
        if (index >= 0 && index < brands.length) {
          brands[index] = brand
        }
        return { ...prev, [groupId]: brands }
      })
    },
    []
  )

  const removeBrand = useCallback((groupId: number, index: number) => {
    setGroupBrands((prev) => {
      const brands = [...(prev[groupId] || [])]
      if (index >= 0 && index < brands.length) {
        brands.splice(index, 1)
      }
      return { ...prev, [groupId]: brands }
    })
  }, [])

  const clearBrands = useCallback((groupId: number) => {
    setGroupBrands((prev) => {
      const newState = { ...prev }
      delete newState[groupId]
      return newState
    })
  }, [])

  return {
    getBrands,
    setBrands,
    addBrand,
    updateBrand,
    removeBrand,
    clearBrands,
  }
}
