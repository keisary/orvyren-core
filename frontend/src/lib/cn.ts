import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * Our type-scale tokens (`text-body`, `text-meta`, …) are font-SIZE classes.
 * Without declaring them, tailwind-merge treats `text-body` as a rival of
 * `text-on-accent` and drops the COLOR of primary buttons — light text on
 * green at 2.13:1 instead of the intended 7.27:1 (Astra-5, correction 3).
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "page-title",
            "section-title",
            "body",
            "table",
            "meta",
            "kpi",
            "verdict",
            "code",
          ],
        },
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
