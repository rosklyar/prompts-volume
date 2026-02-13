import { createFileRoute, redirect } from "@tanstack/react-router"
import { z } from "zod"
import { isLoggedIn } from "@/hooks/useAuth"

const settingsSearchSchema = z.object({
  tab: z.enum(["brand", "password", "gsc"]).optional(),
  gsc: z.string().optional(),
  reason: z.string().optional(),
})

export const Route = createFileRoute("/settings")({
  component: () => null,
  validateSearch: settingsSearchSchema,
  beforeLoad: async ({ search }) => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
    throw redirect({ to: "/profile", search })
  },
})
