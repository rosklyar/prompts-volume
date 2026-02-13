import { createFileRoute, redirect, Link, useSearch, useNavigate } from "@tanstack/react-router"
import { z } from "zod"
import { isLoggedIn } from "@/hooks/useAuth"
import useAuth from "@/hooks/useAuth"
import { SettingsTabs, type SettingsTabId } from "@/components/settings/SettingsTabs"
import { BrandPreferencesForm } from "@/components/settings/BrandPreferencesForm"
import { ChangePasswordForm } from "@/components/settings/ChangePasswordForm"
import { GSCConnectionContent } from "@/components/settings/GSCConnectionCard"
import { Logo } from "@/components/Logo"
import { LogOut, User } from "lucide-react"

const profileSearchSchema = z.object({
  tab: z.enum(["brand", "password", "gsc"]).optional(),
  gsc: z.string().optional(),
  reason: z.string().optional(),
})

export const Route = createFileRoute("/profile")({
  component: Profile,
  validateSearch: profileSearchSchema,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function Profile() {
  const { logout, user } = useAuth()
  const search = useSearch({ from: "/profile" })
  const navigate = useNavigate()
  const activeTab: SettingsTabId = search.tab ?? "brand"

  const setActiveTab = (tab: SettingsTabId) => {
    navigate({ to: "/profile", search: { tab } })
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans'] flex">
      {/* Left sidebar */}
      <aside className="w-[200px] flex-shrink-0 bg-[#FDFBF7] p-6 hidden md:flex flex-col">
        <Link to="/" className="hover:opacity-80 transition-opacity">
          <Logo variant="compact" />
        </Link>
        <div className="mt-8 flex-1">
          <SettingsTabs activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-[#6B7280]
            hover:text-[#C4553D] hover:bg-[#C4553D]/5 transition-colors"
        >
          <LogOut className="w-5 h-5" strokeWidth={1.5} />
          <span className="text-sm font-medium">Sign out</span>
        </button>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 py-6 pb-12 px-4 md:px-8 lg:px-12">
          <div className="max-w-2xl">
            {/* Account identity */}
            {user && (
              <div className="flex items-center gap-3 mb-8 pb-6 border-b border-gray-200/60">
                <div className="w-9 h-9 rounded-full bg-[#C4553D]/10 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-[#C4553D]" />
                </div>
                <div className="min-w-0">
                  {user.full_name && (
                    <p className="text-sm font-medium text-[#1F2937] truncate leading-tight">
                      {user.full_name}
                    </p>
                  )}
                  <p className="text-xs text-[#6B7280] truncate leading-tight">
                    {user.email}
                  </p>
                </div>
              </div>
            )}

            {activeTab === "brand" && (
              <>
                <h1 className="text-2xl font-semibold text-[#1F2937] mb-2 font-['Fraunces']">
                  Brand Preferences
                </h1>
                <p className="text-sm text-gray-500 mb-8">
                  Default brand and competitors for new prompt groups
                </p>
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <BrandPreferencesForm />
                </div>
              </>
            )}

            {activeTab === "password" && (
              <>
                <h1 className="text-2xl font-semibold text-[#1F2937] mb-2 font-['Fraunces']">
                  Change Password
                </h1>
                <p className="text-sm text-gray-500 mb-8">
                  Update your password to keep your account secure
                </p>
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <ChangePasswordForm />
                </div>
              </>
            )}

            {activeTab === "gsc" && (
              <>
                <h1 className="text-2xl font-semibold text-[#1F2937] mb-2 font-['Fraunces']">
                  Google Search Console
                </h1>
                <p className="text-sm text-gray-500 mb-8">
                  Connect your GSC to import keywords for prompt generation
                </p>
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <GSCConnectionContent />
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
