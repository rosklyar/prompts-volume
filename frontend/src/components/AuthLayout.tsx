import type { ReactNode } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Logo } from "@/components/Logo"

interface AuthLayoutProps {
  children: ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#FDFBF7] py-12 px-4 sm:px-6 lg:px-8">
      <Logo variant="full" className="mb-8" />
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">{children}</CardContent>
      </Card>
    </div>
  )
}
