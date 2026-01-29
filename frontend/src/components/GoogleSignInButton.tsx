import { useEffect, useCallback, useRef } from "react"

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
            auto_select?: boolean
            cancel_on_tap_outside?: boolean
          }) => void
          renderButton: (
            parent: HTMLElement,
            options: {
              type?: "standard" | "icon"
              theme?: "outline" | "filled_blue" | "filled_black"
              size?: "large" | "medium" | "small"
              text?: "signin_with" | "signup_with" | "continue_with" | "signin"
              shape?: "rectangular" | "pill" | "circle" | "square"
              width?: number
              logo_alignment?: "left" | "center"
            }
          ) => void
          prompt: () => void
        }
      }
    }
  }
}

interface GoogleSignInButtonProps {
  onCredentialResponse: (idToken: string) => void
  disabled?: boolean
  isLoading?: boolean
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ""

export function GoogleSignInButton({
  onCredentialResponse,
  disabled = false,
  isLoading = false,
}: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null)

  const handleCredentialResponse = useCallback(
    (response: { credential: string }) => {
      onCredentialResponse(response.credential)
    },
    [onCredentialResponse]
  )

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      console.warn("VITE_GOOGLE_CLIENT_ID is not configured")
      return
    }

    const initializeGoogle = () => {
      if (window.google?.accounts?.id && buttonRef.current) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
        })

        // Clear existing button content
        buttonRef.current.innerHTML = ""

        // Render Google's official button
        window.google.accounts.id.renderButton(buttonRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width: 400,
          logo_alignment: "left",
        })
      }
    }

    // Check if script already exists
    const existingScript = document.querySelector(
      'script[src="https://accounts.google.com/gsi/client"]'
    )

    if (existingScript && window.google?.accounts?.id) {
      initializeGoogle()
      return
    }

    if (existingScript) {
      // Script exists but not loaded yet, wait for it
      existingScript.addEventListener("load", initializeGoogle)
      return () => {
        existingScript.removeEventListener("load", initializeGoogle)
      }
    }

    // Load Google Identity Services script
    const script = document.createElement("script")
    script.src = "https://accounts.google.com/gsi/client"
    script.async = true
    script.defer = true
    script.onload = initializeGoogle
    script.onerror = () => {
      console.error("Failed to load Google Identity Services script")
    }

    document.head.appendChild(script)

    return () => {
      script.removeEventListener("load", initializeGoogle)
    }
  }, [handleCredentialResponse])

  if (!GOOGLE_CLIENT_ID) {
    return null
  }

  return (
    <div
      ref={buttonRef}
      className={`flex justify-center ${disabled || isLoading ? "opacity-50 pointer-events-none" : ""}`}
    />
  )
}
