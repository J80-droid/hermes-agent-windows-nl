import { type RefObject, useLayoutEffect } from "react";

/**
 * Positions a portaled dropdown above its anchor without a `style` attribute
 * (avoids webhint no-inline-styles on drop-up menus).
 */
export function useDropUpFixedPosition(
  enabled: boolean,
  anchorRef: RefObject<HTMLElement | null>,
  floatingRef: RefObject<HTMLElement | null>,
) {
  useLayoutEffect(() => {
    if (!enabled) return;

    const anchor = anchorRef.current;
    const floating = floatingRef.current;
    if (!anchor || !floating) return;

    const place = () => {
      const rect = anchor.getBoundingClientRect();
      floating.style.bottom = `${window.innerHeight - rect.top + 4}px`;
      floating.style.left = `${rect.left}px`;
    };

    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [enabled, anchorRef, floatingRef]);
}
