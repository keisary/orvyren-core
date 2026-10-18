import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors " +
    "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent " +
    "disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap",
  {
    variants: {
      variant: {
        default:
          "bg-accent/15 text-accent border border-accent/40 hover:bg-accent/25",
        secondary:
          "bg-surface2 text-ink border border-line hover:border-accent/50 hover:text-accent",
        ghost: "text-muted hover:text-ink hover:bg-surface2",
        danger: "bg-down/15 text-down border border-down/40 hover:bg-down/25",
      },
      size: {
        default: "h-8 px-3 text-[12.5px]",
        sm: "h-6 px-2 text-[11.5px]",
        lg: "h-9 px-4 text-[13px]",
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
