import { cn } from "@/lib/utils";

const variants = {
  default: "bg-primary/20 text-primary border-primary/30",
  success: "bg-success/20 text-success border-success/30",
  warning: "bg-warning/20 text-warning border-warning/30",
  error: "bg-error/20 text-error border-error/30",
  muted: "bg-border/40 text-muted border-border/60",
  pm: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  frontend: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  seo: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  backend: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  qa: "bg-pink-500/20 text-pink-300 border-pink-500/30",
  build: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
};

type Variant = keyof typeof variants;

export function Badge({ children, variant = "default", className }: {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span className={cn(
      "inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium border",
      variants[variant],
      className
    )}>
      {children}
    </span>
  );
}
