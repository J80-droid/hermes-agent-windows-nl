import {
  useLayoutEffect,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";

function measureDropUpStyle(
  triggerRef: RefObject<HTMLElement | null>,
): CSSProperties | undefined {
  const rect = triggerRef.current?.getBoundingClientRect();
  if (!rect) return undefined;
  return {
    bottom: window.innerHeight - rect.top + 4,
    left: rect.left,
  };
}

/** Fixed positioning for a drop-up menu anchored to a trigger element. */
export function useDropUpFixedStyle(
  triggerRef: RefObject<HTMLElement | null>,
  enabled: boolean,
): CSSProperties | undefined {
  const [style, setStyle] = useState<CSSProperties | undefined>();

  useLayoutEffect(() => {
    if (!enabled) {
      queueMicrotask(() => setStyle(undefined));
      return;
    }

    const update = () => setStyle(measureDropUpStyle(triggerRef));
    queueMicrotask(update);

    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [enabled, triggerRef]);

  return style;
}

/** Maps measured drop-up coords to CSS custom properties (see `.drop-up-menu-positioned`). */
export function dropUpMenuCssVars(
  fixedStyle: CSSProperties | undefined,
): CSSProperties | undefined {
  if (!fixedStyle) {
    return { visibility: "hidden" };
  }
  return {
    "--drop-up-bottom": `${fixedStyle.bottom}px`,
    "--drop-up-left": `${fixedStyle.left}px`,
  } as CSSProperties;
}
