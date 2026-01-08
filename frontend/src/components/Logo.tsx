import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "compact"
  className?: string
}

export function Logo({ variant = "full", className }: LogoProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center animate-in fade-in duration-500",
        className
      )}
    >
      <img
        src="/LLMHERO.svg"
        alt="LLMHERO"
        className={variant === "compact" ? "h-6" : "h-10"}
      />
      {variant === "full" && (
        <span className="mt-3 font-['DM_Sans'] text-sm text-[#6B7280] tracking-wide">
          AI Search Intelligence
        </span>
      )}
    </div>
  )
}
