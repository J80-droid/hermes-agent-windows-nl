import { describe, expect, it } from 'vitest'

import {
  joinStatusBarSegments,
  normalizeStatusRuleLeftWidth,
  resolveStatusRuleLineCount,
  shouldUseStatusRuleSecondLine,
  STATUS_RULE_MAX_LINES,
  truncateStatusBarEnd
} from '../domain/statusRuleLines.js'

describe('statusRuleLines', () => {
  it('exposes a two-line maximum', () => {
    expect(STATUS_RULE_MAX_LINES).toBe(2)
  })

  it('joins metric segments with separators', () => {
    expect(joinStatusBarSegments([{ text: '$0.12' }, { text: '42 tok' }])).toBe('$0.12 │ 42 tok')
  })

  it('uses a second row when line 1 alone exceeds left width', () => {
    expect(
      shouldUseStatusRuleSecondLine({
        leftWidth: 40,
        line1Text: '─ ready │ provider/vendor/model-name-that-is-very-long',
        metricsText: '$0.01 │ 12/128k'
      })
    ).toBe(true)
    expect(resolveStatusRuleLineCount({
      leftWidth: 40,
      line1Text: '─ ready │ provider/vendor/model-name-that-is-very-long',
      metricsText: '$0.01 │ 12/128k'
    })).toBe(2)
  })

  it('stays on one row when model and metrics fit', () => {
    expect(
      shouldUseStatusRuleSecondLine({
        leftWidth: 120,
        line1Text: '─ ready │ gpt-4',
        metricsText: '$0.01 │ 12/128k'
      })
    ).toBe(false)
    expect(resolveStatusRuleLineCount({
      leftWidth: 120,
      line1Text: '─ ready │ gpt-4',
      metricsText: '$0.01 │ 12/128k'
    })).toBe(1)
  })

  it('clamps invalid leftWidth to at least 1', () => {
    expect(normalizeStatusRuleLeftWidth(Number.NaN)).toBe(1)
    expect(normalizeStatusRuleLeftWidth(0)).toBe(1)
    expect(normalizeStatusRuleLeftWidth(40.9)).toBe(40)
  })

  it('truncates overflowing text with an ellipsis', () => {
    const long = 'x'.repeat(80)
    const trimmed = truncateStatusBarEnd(long, 20)

    expect(trimmed.endsWith('…')).toBe(true)
    expect(trimmed.length).toBeLessThan(long.length)
  })
})
