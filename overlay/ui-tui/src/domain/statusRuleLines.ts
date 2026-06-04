import { stringWidth } from '@hermes/ink'

/** Maximum status-rule rows (composer chrome). */
export const STATUS_RULE_MAX_LINES = 2

export type StatusBarTextSegment = { text: string }

/** Clamp layout width from terminal cols (guards NaN / non-positive). */
export function normalizeStatusRuleLeftWidth(leftWidth: number): number {
  if (!Number.isFinite(leftWidth) || leftWidth < 1) {
    return 1
  }

  return Math.floor(leftWidth)
}

export function joinStatusBarSegments(segments: StatusBarTextSegment[], separator = ' │ '): string {
  const parts = segments.map(s => s.text).filter(Boolean)

  return parts.join(separator)
}

export function truncateStatusBarEnd(text: string, maxWidth: number): string {
  if (maxWidth <= 0) {
    return ''
  }

  if (stringWidth(text) <= maxWidth) {
    return text
  }

  const ellipsis = '…'
  const ellipsisWidth = stringWidth(ellipsis)

  if (maxWidth <= ellipsisWidth) {
    return ellipsis.slice(0, maxWidth)
  }

  let width = 0
  let out = ''

  for (const ch of text) {
    const chWidth = stringWidth(ch)

    if (width + chWidth + ellipsisWidth > maxWidth) {
      break
    }

    out += ch
    width += chWidth
  }

  return `${out}${ellipsis}`
}

/**
 * Decide whether metrics should move to a second status row.
 * Line 1 keeps status + model (+ cwd is rendered separately on the right).
 * Line 2 uses the full composer width (`ruleCols`), not `leftWidth`.
 */
export function shouldUseStatusRuleSecondLine(opts: {
  leftWidth: number
  line1Text: string
  metricsText: string
}): boolean {
  const budget = normalizeStatusRuleLeftWidth(opts.leftWidth)
  const line1 = opts.line1Text ?? ''
  const metrics = opts.metricsText ?? ''
  const line1Width = stringWidth(line1)
  const metricsWidth = stringWidth(metrics)

  if (!metricsWidth) {
    return false
  }

  if (line1Width > budget) {
    return true
  }

  const combined = `${line1} │ ${metrics}`

  return stringWidth(combined) > budget
}

export function resolveStatusRuleLineCount(opts: {
  leftWidth: number
  line1Text: string
  metricsText: string
}): 1 | 2 {
  return shouldUseStatusRuleSecondLine(opts) ? 2 : 1
}
