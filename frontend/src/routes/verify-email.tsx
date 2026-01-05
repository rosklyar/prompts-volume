import { createFileRoute, Link, useSearch } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { AuthLayout } from "@/components/AuthLayout"
import { Button } from "@/components/ui/button"
import { authApi, ApiError } from "@/client/api"

export const Route = createFileRoute("/verify-email")({
  component: VerifyEmail,
  validateSearch: (search: Record<string, unknown>) => ({
    token: (search.token as string) || "",
  }),
})

type VerificationState =
  | "loading"
  | "success"
  | "already_verified"
  | "error"
  | "expired"

function VerifyEmail() {
  const { token } = useSearch({ from: "/verify-email" })
  const [state, setState] = useState<VerificationState>("loading")
  const [errorMessage, setErrorMessage] = useState<string>("")
  const verificationAttempted = useRef(false)

  useEffect(() => {
    if (!token) {
      setState("error")
      setErrorMessage("No verification token provided")
      return
    }

    // Prevent double-invocation in React StrictMode
    if (verificationAttempted.current) {
      return
    }
    verificationAttempted.current = true

    authApi
      .verifyEmail(token)
      .then((response) => {
        setState(
          response.status === "already_verified" ? "already_verified" : "success"
        )
      })
      .catch((error: ApiError) => {
        if (error.message.toLowerCase().includes("expired")) {
          setState("expired")
        } else {
          setState("error")
        }
        setErrorMessage(error.message)
      })
  }, [token])

  return (
    <AuthLayout>
      <div className="flex flex-col items-center gap-4 text-center">
        {state === "loading" && (
          <>
            <div className="w-16 h-16 border-4 border-gray-200 border-t-gray-900 rounded-full animate-spin" />
            <h1 className="text-2xl font-bold">Verifying your email...</h1>
          </>
        )}

        {state === "success" && (
          <>
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
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold">Email verified!</h1>
            <p className="text-gray-600">
              Your account is now active. You can log in.
            </p>
            <Button asChild className="mt-4">
              <Link to="/login">Log in to your account</Link>
            </Button>
          </>
        )}

        {state === "already_verified" && (
          <>
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold">Already verified</h1>
            <p className="text-gray-600">
              Your email is already verified. You can log in.
            </p>
            <Button asChild className="mt-4">
              <Link to="/login">Log in to your account</Link>
            </Button>
          </>
        )}

        {state === "expired" && (
          <>
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-amber-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold">Link expired</h1>
            <p className="text-gray-600">This verification link has expired.</p>
            <p className="text-sm text-gray-500">
              Please request a new verification email from the login page.
            </p>
            <Button asChild variant="outline" className="mt-4">
              <Link to="/login">Go to login</Link>
            </Button>
          </>
        )}

        {state === "error" && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold">Verification failed</h1>
            <p className="text-gray-600">
              {errorMessage || "Invalid or expired verification link."}
            </p>
            <Button asChild variant="outline" className="mt-4">
              <Link to="/login">Go to login</Link>
            </Button>
          </>
        )}
      </div>
    </AuthLayout>
  )
}

export default VerifyEmail
