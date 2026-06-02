import { describe, expect, it } from 'vitest'

import { busyIndicatorWidth, statusBarSegments, statusRuleWidths } from '../components/appChrome.js'

function expectFitsTerminal(
  cols: number,
  widths: ReturnType<typeof statusRuleWidths>
): void {
  expect(widths.leftWidth + widths.separatorWidth + widths.rightWidth).toBeLessThanOrEqual(cols)
  expect(widths.leftWidth).toBeGreaterThan(0)
}

describe('statusRuleWidths', () => {
  it('keeps the status rule within the terminal width', () => {
    for (const cols of [8, 12, 20, 40, 100]) {
      const widths = statusRuleWidths(cols, '~/src/hermes-agent/main (some-long-branch-name)')

      expect(widths.leftWidth + widths.separatorWidth + widths.rightWidth).toBeLessThanOrEqual(cols)
      expect(widths.leftWidth).toBeGreaterThan(0)
    }
  })

  it('truncates the cwd segment before it can wrap in skinny terminals', () => {
    const widths = statusRuleWidths(24, '~/src/hermes-agent/main (bb/some-extremely-long-branch)')

    expect(widths.rightWidth).toBeLessThan('~/src/hermes-agent/main (bb/some-extremely-long-branch)'.length)
    expect(widths.leftWidth).toBeGreaterThanOrEqual(8)
  })

  it('omits the cwd segment when there is no room for it', () => {
    expect(statusRuleWidths(2, 'abcdef')).toEqual({ leftWidth: 2, rightWidth: 0, separatorWidth: 0 })
  })

  it('budgets the cwd segment by display width, not utf-16 length', () => {
    const widths = statusRuleWidths(30, '目录/分支')

    expect(widths.leftWidth + widths.separatorWidth + widths.rightWidth).toBeLessThanOrEqual(30)
    expect(widths.rightWidth).toBeGreaterThan('目录/分支'.length)
  })

  it('reserves the high-priority left content so the cwd/branch yields first', () => {
    const cwd = '~/src/hermes-agent/apps/desktop (bb/tui-statusbar-responsive)'

    const greedy = statusRuleWidths(70, cwd) // legacy behaviour: cwd hogs the row
    const reserved = statusRuleWidths(70, cwd, 40) // reserve indicator+model+ctx

    expect(reserved.leftWidth).toBeGreaterThanOrEqual(40)
    expect(reserved.leftWidth).toBeGreaterThan(greedy.leftWidth)
    expect(reserved.rightWidth).toBeLessThan(greedy.rightWidth)
    expect(reserved.leftWidth + reserved.separatorWidth + reserved.rightWidth).toBeLessThanOrEqual(70)
  })

  it('drops the cwd entirely when the essential left content needs the whole row', () => {
    expect(statusRuleWidths(40, '~/some/cwd (branch)', 60)).toEqual({
      leftWidth: 40,
      rightWidth: 0,
      separatorWidth: 0
    })
  })

  it('keeps the default (no reservation) behaviour identical for legacy callers', () => {
    const cwd = '~/src/hermes-agent/main (some-long-branch-name)'

    expect(statusRuleWidths(80, cwd, 0)).toEqual(statusRuleWidths(80, cwd))
  })
})

describe('statusBarSegments', () => {
  it('shows every segment on a wide terminal', () => {
    const s = statusBarSegments(120)

    expect(s).toEqual({
      compactCtx: false,
      bar: true,
      duration: true,
      compressions: true,
      voice: true,
      bg: true,
      cost: true
    })
  })

  it('collapses the context bar to a token count on narrow terminals', () => {
    const s = statusBarSegments(60)

    expect(s.compactCtx).toBe(true)
    expect(s.bar).toBe(false)
    expect(s.duration).toBe(false)
    expect(s.cost).toBe(false)
  })

  it('sheds tail segments in priority order as the terminal narrows', () => {
    // cost is the first to go, the context bar the last of the tail.
    const order: (keyof ReturnType<typeof statusBarSegments>)[] = [
      'bar',
      'duration',
      'compressions',
      'voice',
      'bg',
      'cost'
    ]

    let prevCount = Infinity

    for (const cols of [120, 95, 87, 83, 79, 75, 71]) {
      const s = statusBarSegments(cols)
      const visible = order.filter(k => s[k]).length

      expect(visible).toBeLessThanOrEqual(prevCount)
      prevCount = visible
    }
  })
})

describe('busyIndicatorWidth', () => {
  it('reserves a bare spinner for the verb-less unicode style', () => {
    // unicode is a 1-col braille spinner with no verb; far slimmer than the
    // kaomoji face which carries a wide glyph + rotating verb.
    expect(busyIndicatorWidth('unicode', false)).toBeLessThan(busyIndicatorWidth('kaomoji', false))
    expect(busyIndicatorWidth('unicode', false)).toBe(1)
  })

  it('reserves room for the elapsed-time tail only when a turn is timed', () => {
    for (const style of ['kaomoji', 'emoji', 'ascii', 'unicode'] as const) {
      expect(busyIndicatorWidth(style, true)).toBeGreaterThan(busyIndicatorWidth(style, false))
    }
  })
})

describe('statusRuleWidths happy path', () => {
  it('allocates a 3-column separator at width >= 24', () => {
    const widths = statusRuleWidths(40, '~/project')
    expect(widths.separatorWidth).toBe(3)
    expect(widths.rightWidth).toBeGreaterThan(0)
    expectFitsTerminal(40, widths)
  })

  it('uses 1-column separator below width 24', () => {
    const widths = statusRuleWidths(20, '~/p')
    expect(widths.separatorWidth).toBeLessThanOrEqual(1)
    expectFitsTerminal(20, widths)
  })
})

describe('statusRuleWidths edge cases', () => {
  it('treats falsy cols as width 1', () => {
    expect(statusRuleWidths(0, 'cwd')).toEqual({ leftWidth: 1, rightWidth: 0, separatorWidth: 0 })
    expect(statusRuleWidths(NaN, 'cwd')).toEqual({ leftWidth: 1, rightWidth: 0, separatorWidth: 0 })
  })

  it('floors fractional cols', () => {
    const widths = statusRuleWidths(24.9, '~/x')
    expectFitsTerminal(24, widths)
  })

  it('omits cwd when label is empty', () => {
    expect(statusRuleWidths(50, '')).toEqual({ leftWidth: 50, rightWidth: 0, separatorWidth: 0 })
  })

  it('uses minLeftWidth 1 below 24 cols and may still show truncated cwd', () => {
    const widths = statusRuleWidths(8, 'very-long-path')
    expect(widths.leftWidth).toBe(1)
    expect(widths.rightWidth).toBeGreaterThan(0)
    expect(widths.separatorWidth).toBe(1)
    expectFitsTerminal(8, widths)
  })

  it('never assigns negative segment widths', () => {
    for (const cols of [-5, 1, 3, 10, 23, 24, 200]) {
      const widths = statusRuleWidths(cols, '~/a/b/c/d/e/f')
      expect(widths.leftWidth).toBeGreaterThanOrEqual(1)
      expect(widths.rightWidth).toBeGreaterThanOrEqual(0)
      expect(widths.separatorWidth).toBeGreaterThanOrEqual(0)
    }
  })

  it('truncates cwd to maxRightWidth on very narrow terminals', () => {
    const widths = statusRuleWidths(9, '123456789012345')
    expect(widths.rightWidth).toBe(7)
    expect(widths.separatorWidth).toBe(1)
    expect(widths.leftWidth).toBe(1)
    expectFitsTerminal(9, widths)
  })
})

describe('statusRuleWidths negative / invalid input', () => {
  it('handles negative cols via Math.max(1, floor)', () => {
    const widths = statusRuleWidths(-10, '~/x')
    expect(widths.leftWidth).toBe(1)
    expect(widths.rightWidth).toBe(0)
  })

  it('handles whitespace-only cwd as non-empty string width', () => {
    const widths = statusRuleWidths(40, '   ')
    expect(widths.rightWidth).toBeGreaterThan(0)
    expectFitsTerminal(40, widths)
  })
})

describe('statusRuleWidths boundary at width 24', () => {
  it('switches separator budget across the 24-column threshold', () => {
    const narrow = statusRuleWidths(23, '~/repo')
    const wide = statusRuleWidths(24, '~/repo')
    expect(narrow.separatorWidth).toBeLessThanOrEqual(1)
    expect(wide.separatorWidth).toBe(3)
  })

  it('enforces minLeftWidth 8 only when width >= 24', () => {
    expect(statusRuleWidths(24, '~/x').leftWidth).toBeGreaterThanOrEqual(8)
    expect(statusRuleWidths(10, '~/x').leftWidth).toBeGreaterThanOrEqual(1)
  })
})
