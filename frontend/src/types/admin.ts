/**
 * Admin dashboard types
 */

export interface UserWithBalance {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  available_balance: number
  expiring_soon_amount: number
  expiring_soon_at: string | null
}

export interface AdminUsersListResponse {
  users: UserWithBalance[]
  total: number
}

export interface AdminTopUpRequest {
  amount: number
  expires_at?: string | null
  note?: string | null
}
