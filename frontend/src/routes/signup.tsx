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

const formSchema = z
  .object({
    email: z.string().email("Please enter a valid email"),
    full_name: z.string().min(1, "Full name is required"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters"),
    confirm_password: z.string().min(1, "Password confirmation is required"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "The passwords don't match",
    path: ["confirm_password"],
  })

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
})

function SignUp() {
  const { signUpMutation } = useAuth()
  const [signupEmail, setSignupEmail] = useState<string | null>(null)
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
    if (signUpMutation.isPending) return
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { confirm_password: _, ...submitData } = data
    signUpMutation.mutate(submitData, {
      onSuccess: (response) => {
        setSignupEmail(response.email)
      },
    })
  }

  const handleResendVerification = async () => {
    if (!signupEmail || resendStatus !== "idle") return
    setResendStatus("sending")
    try {
      await authApi.resendVerification(signupEmail)
      setResendStatus("sent")
    } catch {
      setResendStatus("idle")
    }
  }

  // Show email confirmation screen after successful signup
  if (signupEmail) {
    return (
      <AuthLayout>
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold">Check your email</h1>
          <p className="text-gray-600">
            We've sent a verification link to{" "}
            <strong className="text-gray-900">{signupEmail}</strong>
          </p>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
            <strong>Note:</strong> The email may end up in your spam folder.
            Please check there if you don't see it in your inbox.
          </div>
          <div className="text-sm text-gray-500 mt-4">
            Didn't receive the email?{" "}
            <button
              onClick={handleResendVerification}
              disabled={resendStatus !== "idle"}
              className="underline underline-offset-4 text-gray-900 disabled:text-gray-400 disabled:cursor-not-allowed"
            >
              {resendStatus === "sending" && "Sending..."}
              {resendStatus === "sent" && "Verification email sent!"}
              {resendStatus === "idle" && "Resend verification email"}
            </button>
          </div>
          <Link
            to="/login"
            className="text-sm underline underline-offset-4 mt-2"
          >
            Back to login
          </Link>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Create an account</h1>
        </div>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="full_name">Full name</Label>
            <Input
              id="full_name"
              type="text"
              placeholder="John Doe"
              {...register("full_name")}
            />
            {errors.full_name && (
              <p className="text-xs text-red-600">
                {errors.full_name.message}
              </p>
            )}
          </div>

          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="user@example.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-red-600">{errors.email.message}</p>
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

          <div className="grid gap-2">
            <Label htmlFor="confirm_password">Confirm password</Label>
            <Input
              id="confirm_password"
              type="password"
              placeholder="Confirm password"
              {...register("confirm_password")}
            />
            {errors.confirm_password && (
              <p className="text-xs text-red-600">
                {errors.confirm_password.message}
              </p>
            )}
          </div>

          {signUpMutation.isError && (
            <p className="text-sm text-red-600 text-center">
              {signUpMutation.error?.message || "Sign up failed"}
            </p>
          )}

          <Button type="submit" disabled={signUpMutation.isPending}>
            {signUpMutation.isPending ? "Signing up..." : "Sign up"}
          </Button>
        </div>

        <div className="text-center text-sm">
          Already have an account?{" "}
          <Link to="/login" className="underline underline-offset-4">
            Log in
          </Link>
        </div>
      </form>
    </AuthLayout>
  )
}

export default SignUp
