import { Link } from "@tanstack/react-router"
import { User } from "lucide-react"
import useAuth from "@/hooks/useAuth"
import { useUserPreferences } from "@/hooks/useOnboarding"

export function ProfileBlock() {
  const { user } = useAuth()
  const { data: preferences } = useUserPreferences()

  if (!user) return null

  const brandName = preferences?.default_brand?.name
  const email = user.email
  const tooltip = brandName ? `${brandName}\n${email}` : email

  return (
    <Link
      to="/profile"
      title={tooltip}
      className="block px-2 py-2.5 rounded-lg
        hover:bg-gray-100 transition-colors group"
    >
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-full bg-[#C4553D]/10 flex items-center justify-center shrink-0">
          <User className="w-3.5 h-3.5 text-[#C4553D]" />
        </div>
        {brandName && (
          <p className="text-sm font-medium text-[#1F2937] truncate leading-tight min-w-0">
            {brandName}
          </p>
        )}
      </div>
      <p className="text-xs text-[#6B7280] mt-1.5 break-all leading-snug">
        {email}
      </p>
    </Link>
  )
}
