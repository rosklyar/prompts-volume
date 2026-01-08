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
      {/* Main logo text */}
      <div className="flex items-baseline gap-1">
        <span
          className="font-['Fraunces'] text-[#1F2937] tracking-tight"
          style={{
            fontSize: variant === "compact" ? "1.25rem" : "2rem",
            fontWeight: 300,
            letterSpacing: "-0.02em",
          }}
        >
          LLM
        </span>
        <span
          className="relative font-['Fraunces'] text-[#1F2937]"
          style={{
            fontSize: variant === "compact" ? "1.25rem" : "2rem",
            fontWeight: 600,
            letterSpacing: "0.02em",
          }}
        >
          HERO
          {/* Rust accent bar under HERO */}
          <span
            className="absolute -bottom-1 left-0 right-0 h-0.5 bg-[#C4553D] rounded-full"
            style={{
              width: "60%",
              marginLeft: "20%",
            }}
          />
        </span>
      </div>

      {/* Tagline - only shown in full variant */}
      {variant === "full" && (
        <span className="mt-3 font-['DM_Sans'] text-sm text-[#6B7280] tracking-wide">
          AI Search Intelligence
        </span>
      )}
    </div>
  )
}
