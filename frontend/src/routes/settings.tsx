import { createFileRoute, redirect, Link, useSearch, useNavigate } from "@tanstack/react-router"
import { z } from "zod"
import { isLoggedIn } from "@/hooks/useAuth"
import { SettingsTabs, type SettingsTabId } from "@/components/settings/SettingsTabs"
import { BrandPreferencesForm } from "@/components/settings/BrandPreferencesForm"
import { ChangePasswordForm } from "@/components/settings/ChangePasswordForm"
import { GSCConnectionContent } from "@/components/settings/GSCConnectionCard"
import { Logo } from "@/components/Logo"

const settingsSearchSchema = z.object({
  tab: z.enum(["brand", "password", "gsc"]).optional(),
  gsc: z.string().optional(),
  reason: z.string().optional(),
})

export const Route = createFileRoute("/settings")({
  component: Settings,
  validateSearch: settingsSearchSchema,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function Settings() {
  const search = useSearch({ from: "/settings" })
  const navigate = useNavigate()
  // Use URL tab if provided, otherwise default to "brand"
  const activeTab: SettingsTabId = search.tab ?? "brand"

  const setActiveTab = (tab: SettingsTabId) => {
    navigate({ to: "/settings", search: { tab } })
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans'] flex">
      {/* Left sidebar with branding and tabs */}
      <aside className="w-[200px] flex-shrink-0 bg-[#FDFBF7] p-6 hidden md:flex flex-col">
        <Link to="/" className="hover:opacity-80 transition-opacity">
          <Logo variant="compact" />
        </Link>
        <div className="mt-8">
          <SettingsTabs activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Main content */}
        <main className="flex-1 py-6 pb-12 px-4 md:px-8 lg:px-12">
          <div className="max-w-2xl">
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
