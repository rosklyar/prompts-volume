import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { AuthLayout } from "@/components/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const formSchema = z
  .object({
    email: z.string().email("Please enter a valid email"),
    full_name: z.string().min(1, "Full Name is required"),
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
    signUpMutation.mutate(submitData)
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Create an account</h1>
        </div>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="full_name">Full Name</Label>
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
            <Label htmlFor="confirm_password">Confirm Password</Label>
            <Input
              id="confirm_password"
              type="password"
              placeholder="Confirm Password"
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
            {signUpMutation.isPending ? "Signing up..." : "Sign Up"}
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
