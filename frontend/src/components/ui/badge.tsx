import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

/**
 * Badges state a domain fact in words (§4.4): the text is always there, color
 * only reinforces it — never the only channel. Machine enums keep their own
 * casing (ALLOW, ABORTED…); no uppercase transform, no mono default.
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-[2px] border px-1.5 py-0.5 " +
    "text-meta font-semibold leading-4",
  {
    variants: {
      variant: {
        /* a check that passed / a selected fact */
        ok: "border-accent bg-accent-soft text-accent",
        /* refusal (and stopped runs): anthracite inverted */
        deny: "border-ink bg-ink text-on-accent",
        /* indeterminate / human review required: outline, no hue */
        warn: "border-line-strong bg-surface text-ink",
        /* pointer to a fact (case id, catalog…) */
        info: "border-line bg-surface text-ink",
        neutral: "border-line bg-surface2 text-muted",
        violet: "border-line bg-surface2 text-muted",
        /* transport state — no pulse; the label carries the meaning */
        live: "border-accent bg-accent-soft text-accent",
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
