import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10.5px] " +
    "font-semibold uppercase tracking-wider mono",
  {
    variants: {
      variant: {
        neutral: "border-line bg-surface2 text-muted",
        info: "border-accent/40 bg-accent/10 text-accent",
        ok: "border-up/40 bg-up/10 text-up",
        deny: "border-down/40 bg-down/10 text-down",
        warn: "border-warn/40 bg-warn/10 text-warn",
        violet: "border-accent2/40 bg-accent2/10 text-accent2",
        live: "border-up/50 bg-up/15 text-up animate-pulse",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
