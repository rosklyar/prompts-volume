import { createFileRoute, redirect } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"
import { LinearOnboarding } from "@/components/onboarding/LinearOnboarding"

interface OnboardingSearch {
  gsc?: string
}

export const Route = createFileRoute("/onboarding")({
  component: Onboarding,
  validateSearch: (search: Record<string, unknown>): OnboardingSearch => ({
    gsc: search.gsc as string | undefined,
  }),
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function Onboarding() {
  const { gsc } = Route.useSearch()
  return <LinearOnboarding initialGscConnected={gsc === "connected"} />
}

export default Onboarding
