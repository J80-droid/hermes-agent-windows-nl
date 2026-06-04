import { describe, expect, it } from 'vitest'

import {
  computeCallTps,
  computeLiveTps,
  formatStatusBarTps,
  resolveStatusBarThroughputLabel,
  sumLiveGenerationTokens
} from '../domain/statusBarThroughput.js'

describe('statusBarThroughput', () => {
  it('computeLiveTps enforces min elapsed', () => {
    expect(computeLiveTps(100, 1000, 1200)).toBeNull()
    expect(computeLiveTps(100, 1000, 2000)).toBe(100)
  })

  it('computeCallTps clamps short generations', () => {
    expect(computeCallTps(10, 0.1)).toBe(20)
    expect(computeCallTps(0, 2)).toBeNull()
  })

  it('formatStatusBarTps rounds', () => {
    expect(formatStatusBarTps(41.6)).toBe('42 tok/s')
    expect(formatStatusBarTps(0.2)).toBeNull()
    expect(formatStatusBarTps(Number.NaN)).toBeNull()
  })

  it('sumLiveGenerationTokens includes reasoning and tool tokens', () => {
    expect(
      sumLiveGenerationTokens({
        streamOutputTokens: 10,
        reasoningTokens: 5,
        toolTokens: 3
      })
    ).toBe(18)
  })

  it('resolveStatusBarThroughputLabel prefers live while busy', () => {
    const label = resolveStatusBarThroughputLabel({
      showStatusBarTps: true,
      width: 120,
      busy: true,
      signals: {
        streamGenStartedAt: 1000,
        streamOutputTokens: 200,
        reasoningTokens: 0,
        toolTokens: 0,
        lastCallTps: 10
      },
      nowMs: 3000
    })

    expect(label).toBe('100 tok/s')
  })

  it('resolveStatusBarThroughputLabel shows frozen when idle', () => {
    const label = resolveStatusBarThroughputLabel({
      showStatusBarTps: true,
      width: 120,
      busy: false,
      signals: {
        streamGenStartedAt: null,
        streamOutputTokens: 0,
        reasoningTokens: 0,
        toolTokens: 0,
        lastCallTps: 55
      }
    })

    expect(label).toBe('55 tok/s')
  })
})
