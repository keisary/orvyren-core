import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

/**
 * Controls: 36px (compact 32px), 2px radius, flat — no glow, no shadow.
 * Press feedback scales to 0.96 over 150ms ease-out (motion-safe; disabled
 * never scales). Focus = 2px accent outline, never a glow.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 rounded-[2px] border font-medium " +
    "transition-[background-color,border-color,color,transform,opacity] duration-150 ease-out " +
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent " +
    "disabled:pointer-events-none disabled:border-line disabled:bg-surface2 disabled:text-muted " +
    "motion-safe:enabled:active:scale-[0.96] whitespace-nowrap",
  {
    variants: {
      variant: {
        default:
          "border-accent bg-accent text-on-accent hover:bg-accent-hover hover:border-accent-hover",
        secondary:
          "border-line bg-surface text-ink hover:border-line-strong hover:bg-surface2",
        ghost: "border-transparent bg-transparent text-muted hover:bg-surface2 hover:text-ink",
        danger: "border-ink bg-ink text-on-accent hover:opacity-90",
      },
      size: {
        default: "h-9 px-3.5 text-[14px]",
        sm: "h-8 px-3 text-[12px]",
        lg: "h-10 px-4 text-[14px]",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";
