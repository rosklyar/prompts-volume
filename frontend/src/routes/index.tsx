import { createFileRoute, redirect } from "@tanstack/react-router"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/")({
  component: Dashboard,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function Dashboard() {
  const { user, logout, isUserLoading } = useAuth()

  if (isUserLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <Button variant="outline" onClick={logout}>
            Logout
          </Button>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Card>
          <CardHeader>
            <CardTitle>Welcome back!</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p>
                <strong>Email:</strong> {user?.email}
              </p>
              {user?.full_name && (
                <p>
                  <strong>Name:</strong> {user.full_name}
                </p>
              )}
              <p>
                <strong>Role:</strong>{" "}
                {user?.is_superuser ? "Administrator" : "User"}
              </p>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
