import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ChangePasswordForm } from "./ChangePasswordForm"

// Mock the API
vi.mock("@/client/api", () => ({
  authApi: {
    updatePassword: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
      this.name = "ApiError"
    }
  },
}))

import { authApi, ApiError } from "@/client/api"

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe("ChangePasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders all password fields", () => {
    render(<ChangePasswordForm />, { wrapper: createWrapper() })

    expect(screen.getByLabelText("Current password")).toBeInTheDocument()
    expect(screen.getByLabelText("New password")).toBeInTheDocument()
    expect(screen.getByLabelText("Confirm new password")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /change password/i })
    ).toBeInTheDocument()
  })

  it("shows validation error when current password is empty", async () => {
    render(<ChangePasswordForm />, { wrapper: createWrapper() })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("New password"), "newpassword123")
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpassword123"
    )
    await user.click(screen.getByRole("button", { name: /change password/i }))

    expect(
      await screen.findByText(/current password is required/i)
    ).toBeInTheDocument()
  })

  it("shows validation error for short new password", async () => {
    render(<ChangePasswordForm />, { wrapper: createWrapper() })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Current password"), "oldpass123")
    await user.type(screen.getByLabelText("New password"), "short")
    await user.type(screen.getByLabelText("Confirm new password"), "short")
    await user.click(screen.getByRole("button", { name: /change password/i }))

    expect(
      await screen.findByText(/password must be at least 8 characters/i)
    ).toBeInTheDocument()
  })

  it("shows validation error for mismatched passwords", async () => {
    render(<ChangePasswordForm />, { wrapper: createWrapper() })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Current password"), "oldpass123")
    await user.type(screen.getByLabelText("New password"), "newpassword123")
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "differentpassword"
    )
    await user.click(screen.getByRole("button", { name: /change password/i }))

    expect(
      await screen.findByText(/passwords don't match/i)
    ).toBeInTheDocument()
  })

  it("submits form with valid data", async () => {
    vi.mocked(authApi.updatePassword).mockResolvedValue({
      message: "Password updated successfully",
    })

    render(<ChangePasswordForm />, { wrapper: createWrapper() })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Current password"), "oldpassword123")
    await user.type(screen.getByLabelText("New password"), "newpassword456")
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpassword456"
    )
    await user.click(screen.getByRole("button", { name: /change password/i }))

    await waitFor(() => {
      expect(authApi.updatePassword).toHaveBeenCalledWith({
        current_password: "oldpassword123",
        new_password: "newpassword456",
      })
    })
  })

  it("shows success message after password change", async () => {
    vi.mocked(authApi.updatePassword).mockResolvedValue({
      message: "Password updated successfully",
    })

    render(<ChangePasswordForm />, { wrapper: createWrapper() })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Current password"), "oldpassword123")
    await user.type(screen.getByLabelText("New password"), "newpassword456")
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpassword456"
    )
    await user.click(screen.getByRole("button", { name: /change password/i }))

    expect(
      await screen.findByText(/password changed successfully/i)
    ).toBeInTheDocument()
  })

  it("shows error message for incorrect current password", async () => {
    vi.mocked(authApi.updatePassword).mockRejectedValue(
      new ApiError(400, "Incorrect password")
    )

    render(<ChangePasswordForm />, { wrapper: createWrapper() })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Current password"), "wrongpassword")
    await user.type(screen.getByLabelText("New password"), "newpassword456")
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpassword456"
    )
    await user.click(screen.getByRole("button", { name: /change password/i }))

    expect(await screen.findByText(/incorrect password/i)).toBeInTheDocument()
  })

  it("disables submit button while pending", async () => {
    // Create a promise that won't resolve immediately
    let resolvePromise: (value: { message: string }) => void
    const pendingPromise = new Promise<{ message: string }>((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(authApi.updatePassword).mockReturnValue(pendingPromise)

    render(<ChangePasswordForm />, { wrapper: createWrapper() })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Current password"), "oldpassword123")
    await user.type(screen.getByLabelText("New password"), "newpassword456")
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpassword456"
    )
    await user.click(screen.getByRole("button", { name: /change password/i }))

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /changing password/i })
      ).toBeDisabled()
    })

    // Resolve the promise to clean up
    resolvePromise!({ message: "Success" })
  })
})
