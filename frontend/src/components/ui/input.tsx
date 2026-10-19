import * as React from "react";
import { cn } from "@/lib/cn";

/** Labels are sentence case, 12px — uppercase stays for machine enums. */
export function Label({
  className,
  ...props
}: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label className={cn("text-meta font-medium text-muted", className)} {...props} />
  );
}

const CONTROL =
  "h-9 w-full rounded-[2px] border border-line-strong bg-surface px-3 " +
  "text-code text-ink placeholder:text-muted " +
  "focus:border-accent focus-visible:outline-2 focus-visible:outline-offset-1 " +
  "focus-visible:outline-accent disabled:bg-surface2 disabled:text-muted";

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(CONTROL, "font-mono", className)} {...props} />;
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(CONTROL, "font-sans text-table", className)} {...props}>
      {children}
    </select>
  );
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea className={cn(CONTROL, "min-h-16 py-1.5 font-mono", className)} {...props} />
  );
}

/** Scrollers: square corners, contained scroll (tables read as documents). */
export function ScrollArea({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("overflow-auto overscroll-contain border border-line", className)} {...props} />
  );
}

/** Static placeholder — a skeleton must not pretend to be data (no shimmer). */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("border border-line bg-surface2", className)} />;
}

export function Separator({ className }: { className?: string }) {
  return <div className={cn("h-px w-full bg-line", className)} />;
}
