import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Palette, Check } from "lucide-react";
import { Button } from "@nous-research/ui/ui/components/button";
import { BottomSheet } from "@nous-research/ui/ui/components/bottom-sheet";
import { Typography } from "@nous-research/ui/ui/components/typography/index";
import { useBelowBreakpoint } from "@nous-research/ui/hooks/use-below-breakpoint";
import { BUILTIN_THEMES, useTheme } from "@/themes";
import type { DashboardTheme } from "@/themes";
import { useI18n } from "@/i18n";
import { useDropUpFixedPosition } from "@/hooks/useDropUpFixedPosition";
import { cn } from "@/lib/utils";

/**
 * Compact theme picker mounted next to the language switcher in the header.
 * Each dropdown row shows a 3-stop swatch (background / midground / warm
 * glow) so users can preview the palette before committing. User-defined
 * themes from `~/.hermes/dashboard-themes/*.yaml` use their API-provided
 * definitions so they show real palette swatches just like built-ins.
 *
 * When placed at the bottom of a container (e.g. the sidebar rail), pass
 * `dropUp` so the menu opens above the trigger instead of clipping below
 * the viewport. On viewports below the `sm` breakpoint, `dropUp` uses a
 * bottom sheet portaled to `document.body` so the picker is not clipped by
 * the sidebar (same idea as a responsive Drawer).
 */
export function ThemeSwitcher({ collapsed = false, dropUp = false }: ThemeSwitcherProps) {
  const { themeName, availableThemes, setTheme } = useTheme();
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const narrowViewport = useBelowBreakpoint(640);
  const useMobileSheet = Boolean(dropUp && narrowViewport);

  const close = useCallback(() => setOpen(false), []);

  useDropUpFixedPosition(
    Boolean(dropUp && open && !useMobileSheet),
    wrapperRef,
    dropdownRef,
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  useEffect(() => {
    if (!open || useMobileSheet) return;
    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (wrapperRef.current?.contains(target)) return;
      if (dropdownRef.current?.contains(target)) return;
      close();
    };
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [open, close, useMobileSheet]);

  const current = availableThemes.find((th) => th.name === themeName);
  const label = current?.label ?? themeName;
  const sheetTitle = t.theme?.title ?? "Theme";

  const selectTheme = useCallback(
    (name: string) => {
      setTheme(name);
      close();
    },
    [close, setTheme],
  );

  return (
    <div ref={wrapperRef} className="relative">
      <Button
        ghost
        size={collapsed ? "icon" : undefined}
        onClick={() => setOpen((o) => !o)}
        className={cn(
          collapsed
            ? "text-text-secondary hover:text-foreground hover:bg-transparent"
            : "px-2 py-1 normal-case tracking-normal font-normal text-xs text-text-secondary hover:text-foreground",
        )}
        title={`${t.theme?.switchTheme ?? "Switch theme"}: ${label}`}
        aria-label={t.theme?.switchTheme ?? "Switch theme"}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="inline-flex items-center gap-1.5">
          <Palette className="h-3.5 w-3.5" />

          {!collapsed && (
            <Typography
              mondwest
              className="hidden sm:inline text-display tracking-wide text-xs"
            >
              {label}
            </Typography>
          )}
        </span>
      </Button>

      {useMobileSheet && (
        <BottomSheet
          backdropDismissLabel={t.common.close}
          onClose={close}
          open={open}
          title={sheetTitle}
        >
          <div>
            <div className="border-b border-current/20 px-3 py-2">
              <Typography
                mondwest
                className="text-display text-xs tracking-[0.12em] text-text-tertiary"
              >
                {sheetTitle}
              </Typography>
            </div>
            <div aria-label={sheetTitle} role="listbox">
              {availableThemes.map((th) => {
                const isActive = th.name === themeName;
                const paletteTheme = BUILTIN_THEMES[th.name] ?? th.definition;
                const optionClassName = cn(
                  "w-full text-left px-3 py-2 flex items-center gap-3 cursor-pointer",
                  "hover:bg-accent hover:text-accent-foreground transition-colors",
                  isActive && "bg-accent/50",
                );
                const optionContent = (
                  <ThemeOptionContent
                    description={th.description}
                    isActive={isActive}
                    label={th.label}
                    paletteTheme={paletteTheme}
                  />
                );

                if (isActive) {
                  return (
                    <button
                      aria-label={th.label}
                      aria-selected="true"
                      className={optionClassName}
                      key={th.name}
                      onClick={() => selectTheme(th.name)}
                      role="option"
                      type="button"
                    >
                      {optionContent}
                    </button>
                  );
                }

                return (
                  <button
                    aria-label={th.label}
                    className={optionClassName}
                    key={th.name}
                    onClick={() => selectTheme(th.name)}
                    role="option"
                    type="button"
                  >
                    {optionContent}
                  </button>
                );
              })}
            </div>
          </div>
        </BottomSheet>
      )}

      {open && !useMobileSheet && (() => {
        const dropdown = (
          <div
            ref={dropdownRef}
            aria-label={sheetTitle}
            className={cn(
              "min-w-[240px] max-h-[70dvh] overflow-y-auto",
              "border border-current/20 bg-background-base/95 backdrop-blur-sm",
              "shadow-[0_12px_32px_-8px_rgba(0,0,0,0.6)]",
              dropUp ? "fixed z-[100]" : "absolute z-50 right-0 top-full mt-1",
            )}
          >
            <div className="border-b border-current/20 px-3 py-2">
              <Typography
                mondwest
                className="text-display text-xs tracking-[0.12em] text-text-tertiary"
              >
                {sheetTitle}
              </Typography>
            </div>

            <div aria-label={sheetTitle} role="listbox">
              {availableThemes.map((th) => {
                const isActive = th.name === themeName;
                const paletteTheme = BUILTIN_THEMES[th.name] ?? th.definition;
                const optionClassName = cn(
                  "w-full text-left px-3 py-2 flex items-center gap-3 cursor-pointer",
                  "hover:bg-accent hover:text-accent-foreground transition-colors",
                  isActive && "bg-accent/50",
                );
                const optionContent = (
                  <ThemeOptionContent
                    description={th.description}
                    isActive={isActive}
                    label={th.label}
                    paletteTheme={paletteTheme}
                  />
                );

                if (isActive) {
                  return (
                    <button
                      aria-label={th.label}
                      aria-selected="true"
                      className={optionClassName}
                      key={th.name}
                      onClick={() => selectTheme(th.name)}
                      role="option"
                      type="button"
                    >
                      {optionContent}
                    </button>
                  );
                }

                return (
                  <button
                    aria-label={th.label}
                    className={optionClassName}
                    key={th.name}
                    onClick={() => selectTheme(th.name)}
                    role="option"
                    type="button"
                  >
                    {optionContent}
                  </button>
                );
              })}
            </div>
          </div>
        );
        return dropUp ? createPortal(dropdown, document.body) : dropdown;
      })()}
    </div>
  );
}

function ThemeOptionContent({
  description,
  isActive,
  label,
  paletteTheme,
}: {
  description?: string;
  isActive: boolean;
  label: string;
  paletteTheme?: DashboardTheme;
}) {
  return (
    <>
      {paletteTheme ? (
        <ThemeSwatch theme={paletteTheme} />
      ) : (
        <PlaceholderSwatch />
      )}

      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <Typography
          mondwest
          className="truncate text-display text-xs tracking-wide"
        >
          {label}
        </Typography>
        {description && (
          <Typography className="truncate text-xs tracking-normal text-text-tertiary">
            {description}
          </Typography>
        )}
      </div>

      <Check
        className={cn(
          "h-3 w-3 shrink-0 text-midground",
          isActive ? "opacity-100" : "opacity-0",
        )}
      />
    </>
  );
}

function ThemeSwatch({ theme }: { theme: DashboardTheme }) {
  // Inverted themes (Nous Blue / future lens themes) author their palette
  // pre-inversion — `#FFAC02` reads as `#0053FD` blue once the foreground-
  // difference layer flips the page. The picker can't replay that math
  // cheaply, so themes opt-in to an explicit `swatchColors` triplet that
  // mirrors the on-screen result. Falls back to the raw palette hexes for
  // every other theme so existing dark-theme swatches are untouched.
  const [c1, c2, c3] = theme.swatchColors ?? [
    theme.palette.background.hex,
    theme.palette.midground.hex,
    theme.palette.warmGlow,
  ];
  const swatchRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = swatchRef.current;
    if (!el) return;
    el.style.setProperty("--theme-swatch-1", c1);
    el.style.setProperty("--theme-swatch-2", c2);
    el.style.setProperty("--theme-swatch-3", c3);
  }, [c1, c2, c3]);

  return (
    <div
      ref={swatchRef}
      aria-hidden
      className="flex h-4 w-9 shrink-0 overflow-hidden border border-current/20"
    >
      <span className="theme-swatch-stop flex-1" />
      <span className="theme-swatch-stop flex-1" />
      <span className="theme-swatch-stop flex-1" />
    </div>
  );
}

function PlaceholderSwatch() {
  return (
    <div
      aria-hidden
      className="h-4 w-9 shrink-0 border border-dashed border-current/20"
    />
  );
}

interface ThemeSwitcherProps {
  collapsed?: boolean;
  dropUp?: boolean;
}
