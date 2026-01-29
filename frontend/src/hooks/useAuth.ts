import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import {
  authApi,
  onboardingApi,
  type LoginCredentials,
  type UserPublic,
  type UserRegister,
} from "@/client/api"

export const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: user, isLoading: isUserLoading } = useQuery<
    UserPublic | null,
    Error
  >({
    queryKey: ["currentUser"],
    queryFn: authApi.getCurrentUser,
    enabled: isLoggedIn(),
    retry: false,
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) => authApi.signup(data),
    // Note: No redirect on success - the signup component handles showing the
    // email verification screen
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: LoginCredentials) => {
    const response = await authApi.login(data)
    localStorage.setItem("access_token", response.access_token)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      // Check onboarding status and redirect accordingly
      try {
        const status = await onboardingApi.getStatus()
        if (!status.is_completed) {
          navigate({ to: "/onboarding" })
        } else {
          navigate({ to: "/" })
        }
      } catch {
        // If onboarding status check fails, go to dashboard
        navigate({ to: "/" })
      }
    },
  })

  const googleLogin = async (idToken: string) => {
    const response = await authApi.loginWithGoogle(idToken)
    localStorage.setItem("access_token", response.access_token)
    return response
  }

  const googleLoginMutation = useMutation({
    mutationFn: googleLogin,
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      // Check onboarding status and redirect accordingly
      try {
        const status = await onboardingApi.getStatus()
        if (!status.is_completed) {
          navigate({ to: "/onboarding" })
        } else {
          navigate({ to: "/" })
        }
      } catch {
        // If onboarding status check fails, go to dashboard
        navigate({ to: "/" })
      }
    },
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    queryClient.clear()
    navigate({ to: "/login" })
  }

  return {
    signUpMutation,
    loginMutation,
    googleLoginMutation,
    logout,
    user,
    isUserLoading,
  }
}

export default useAuth
