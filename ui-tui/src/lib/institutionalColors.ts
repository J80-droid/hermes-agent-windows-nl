/** Assistant answer palette (Rich demo parity; independent of Hermes UI gold).
 *
 * NOTE: These are the built-in "demo" palette colours.  In the future the TUI
 * could read the active palette from the gateway payload; until then we keep
 * parity with the Python default (demo = Monokai-inspired).
 */

export const ASSISTANT_TABLE_HEADERS = ['cyan', 'green', 'white', 'magenta'] as const

export const ASSISTANT_HEADING_COLORS = ['cyan', 'green', 'magenta', 'yellow', 'white', 'grey'] as const

export const ASSISTANT_LABEL_COLOR = 'magenta'

export const assistantTableHeaderColor = (index: number): string =>
  ASSISTANT_TABLE_HEADERS[index % ASSISTANT_TABLE_HEADERS.length]!

export const assistantHeadingColor = (level: number): string =>
  ASSISTANT_HEADING_COLORS[Math.min(Math.max(level - 1, 0), ASSISTANT_HEADING_COLORS.length - 1)]!

/** Palette-aware wrapper (stub for future gateway-driven palette names). */
export const assistantPaletteForName = (paletteName: string | undefined): string => {
  // Currently only "demo" is supported in the TUI; future: map paletteName to colours.
  return paletteName || 'demo'
}
