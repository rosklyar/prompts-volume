import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useEffect } from "react"
import { useChangePassword } from "@/hooks/useChangePassword"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/client/api"

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string().min(1, "Please confirm your new password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  })

type ChangePasswordFormData = z.infer<typeof changePasswordSchema>

export function ChangePasswordForm() {
  const { changePassword, isPending, isSuccess, isError, error, reset } =
    useChangePassword()

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset: resetForm,
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  })

  // Auto-reset success state after 3 seconds
  useEffect(() => {
    if (isSuccess) {
      const timer = setTimeout(() => {
        reset()
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [isSuccess, reset])

  const onSubmit = (data: ChangePasswordFormData) => {
    if (isPending) return
    changePassword(
      {
        current_password: data.current_password,
        new_password: data.new_password,
      },
      {
        onSuccess: () => {
          resetForm()
        },
      }
    )
  }

  // Extract error message from API error
  const getErrorMessage = () => {
    if (!error) return null
    if (error instanceof ApiError) {
      return error.message
    }
    return "Failed to change password"
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
      {/* Success message */}
      {isSuccess && (
        <div
          className="flex items-center gap-3 p-4 rounded-lg bg-[#C4553D]/5 border border-[#C4553D]/20
            animate-in fade-in slide-in-from-top-2 duration-300"
        >
          <div className="w-8 h-8 rounded-full bg-[#C4553D]/10 flex items-center justify-center shrink-0">
            <svg
              className="w-4 h-4 text-[#C4553D]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <p className="text-sm font-medium text-[#C4553D]">
            Password changed successfully
          </p>
        </div>
      )}

      {/* API error message */}
      {isError && (
        <div
          className="flex items-center gap-3 p-4 rounded-lg bg-red-50 border border-red-200
            animate-in fade-in slide-in-from-top-2 duration-300"
        >
          <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center shrink-0">
            <svg
              className="w-4 h-4 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <p className="text-sm font-medium text-red-600">{getErrorMessage()}</p>
        </div>
      )}

      <div className="grid gap-4">
        {/* Current password */}
        <div className="grid gap-2">
          <Label htmlFor="current_password" className="text-[#1F2937]">
            Current password
          </Label>
          <Input
            id="current_password"
            type="password"
            placeholder="Enter your current password"
            autoComplete="current-password"
            className="focus-visible:ring-[#C4553D]/30"
            {...register("current_password")}
          />
          {errors.current_password && (
            <p className="text-xs text-red-600">
              {errors.current_password.message}
            </p>
          )}
        </div>

        {/* New password */}
        <div className="grid gap-2">
          <Label htmlFor="new_password" className="text-[#1F2937]">
            New password
          </Label>
          <Input
            id="new_password"
            type="password"
            placeholder="Enter your new password"
            autoComplete="new-password"
            className="focus-visible:ring-[#C4553D]/30"
            {...register("new_password")}
          />
          {errors.new_password && (
            <p className="text-xs text-red-600">{errors.new_password.message}</p>
          )}
          <p className="text-xs text-[#9CA3AF]">
            Must be at least 8 characters
          </p>
        </div>

        {/* Confirm new password */}
        <div className="grid gap-2">
          <Label htmlFor="confirm_password" className="text-[#1F2937]">
            Confirm new password
          </Label>
          <Input
            id="confirm_password"
            type="password"
            placeholder="Confirm your new password"
            autoComplete="new-password"
            className="focus-visible:ring-[#C4553D]/30"
            {...register("confirm_password")}
          />
          {errors.confirm_password && (
            <p className="text-xs text-red-600">
              {errors.confirm_password.message}
            </p>
          )}
        </div>
      </div>

      <Button
        type="submit"
        disabled={isPending}
        className="mt-2 bg-[#C4553D] hover:bg-[#B04835] text-white transition-colors"
      >
        {isPending ? (
          <span className="flex items-center gap-2">
            <svg
              className="w-4 h-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Changing password...
          </span>
        ) : (
          "Change password"
        )}
      </Button>
    </form>
  )
}
