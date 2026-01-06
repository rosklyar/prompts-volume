import { createFileRoute, redirect, Link } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"
import { ChangePasswordForm } from "@/components/settings/ChangePasswordForm"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Logo } from "@/components/Logo"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"

export const Route = createFileRoute("/settings")({
  component: Settings,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function Settings() {
  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      {/* Header */}
      <header className="p-6 flex items-center justify-between">
        <Logo variant="compact" />
        <Link to="/">
          <Button
            variant="ghost"
            className="gap-2 text-[#9CA3AF] hover:text-[#1F2937] hover:bg-transparent transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Button>
        </Link>
      </header>

      {/* Main content */}
      <main className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-[#1F2937] mb-8 font-['Fraunces']">
          Account Settings
        </h1>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg text-[#1F2937]">Change Password</CardTitle>
            <CardDescription>
              Update your password to keep your account secure
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChangePasswordForm />
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
