/** Assistant answer palette (Rich demo parity; independent of Hermes UI gold). */

export const ASSISTANT_TABLE_HEADERS = ['cyan', 'green', 'magenta', 'yellow'] as const

export const ASSISTANT_HEADING_COLORS = ['cyan', 'green', 'magenta', 'yellow', 'white', 'grey'] as const

export const ASSISTANT_LABEL_COLOR = 'magenta'

export const assistantTableHeaderColor = (index: number): string =>
  ASSISTANT_TABLE_HEADERS[index % ASSISTANT_TABLE_HEADERS.length]!

export const assistantHeadingColor = (level: number): string =>
  ASSISTANT_HEADING_COLORS[Math.min(Math.max(level - 1, 0), ASSISTANT_HEADING_COLORS.length - 1)]!
