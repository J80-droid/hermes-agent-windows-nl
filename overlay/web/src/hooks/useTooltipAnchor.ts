import { useLayoutEffect, useState, type RefObject } from "react";

/** Sync a ref's current element into state for render-safe tooltip anchoring. */
export function useTooltipAnchor(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
): HTMLElement | null {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  useLayoutEffect(() => {
    setAnchor(active ? ref.current : null);
  }, [active, ref]);

  return anchor;
}
