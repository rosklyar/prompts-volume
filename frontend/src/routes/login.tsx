import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useState } from "react"
import { AuthLayout } from "@/components/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { authApi } from "@/client/api"

const formSchema = z.object({
  username: z.string().email("Please enter a valid email"),
  password: z.string().min(1, "Password is required"),
})

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
})

function Login() {
  const { loginMutation } = useAuth()
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null)
  const [resendStatus, setResendStatus] = useState<"idle" | "sending" | "sent">(
    "idle"
  )
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return
    setUnverifiedEmail(null) // Reset
    setResendStatus("idle")
    loginMutation.mutate(data, {
      onError: (error) => {
        if (error.message.toLowerCase().includes("verify your email")) {
          setUnverifiedEmail(data.username)
        }
      },
    })
  }

  const handleResendVerification = async () => {
    if (!unverifiedEmail || resendStatus !== "idle") return
    setResendStatus("sending")
    try {
      await authApi.resendVerification(unverifiedEmail)
      setResendStatus("sent")
    } catch {
      setResendStatus("idle")
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Login to your account</h1>
        </div>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="username">Email</Label>
            <Input
              id="username"
              type="email"
              placeholder="user@example.com"
              {...register("username")}
            />
            {errors.username && (
              <p className="text-xs text-red-600">
                {errors.username.message}
              </p>
            )}
          </div>

          <div className="grid gap-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Password"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-xs text-red-600">
                {errors.password.message}
              </p>
            )}
          </div>

          {loginMutation.isError && (
            <div className="text-sm text-center">
              <p className="text-red-600">
                {loginMutation.error?.message || "Login failed"}
              </p>
              {unverifiedEmail && (
                <button
                  type="button"
                  onClick={handleResendVerification}
                  disabled={resendStatus !== "idle"}
                  className="underline underline-offset-4 mt-2 text-gray-900 disabled:text-gray-400 disabled:cursor-not-allowed"
                >
                  {resendStatus === "sending" && "Sending..."}
                  {resendStatus === "sent" && "Verification email sent!"}
                  {resendStatus === "idle" && "Resend verification email"}
                </button>
              )}
            </div>
          )}

          <Button type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Logging in..." : "Log in"}
          </Button>
        </div>

        <div className="text-center text-sm">
          Don't have an account yet?{" "}
          <Link to="/signup" className="underline underline-offset-4">
            Sign up
          </Link>
        </div>
      </form>
    </AuthLayout>
  )
}
