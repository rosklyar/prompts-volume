import { useMutation } from "@tanstack/react-query"
import { authApi, type UpdatePasswordRequest } from "@/client/api"

export function useChangePassword() {
  const mutation = useMutation({
    mutationFn: (data: UpdatePasswordRequest) => authApi.updatePassword(data),
  })

  return {
    changePassword: mutation.mutate,
    changePasswordAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    error: mutation.error,
    reset: mutation.reset,
  }
}
