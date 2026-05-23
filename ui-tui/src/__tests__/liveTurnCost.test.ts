import { describe, expect, it } from 'vitest'

import {
  deriveTokenCostRates,
  estimateLiveTurnCostUsd,
  formatTurnCostUsd
} from '../domain/liveTurnCost.js'

describe('liveTurnCost', () => {
  const usage = {
    calls: 4,
    cost_breakdown_usd: { input: 0.8, output: 1.2 },
    cost_status: 'estimated',
    cost_usd: 2,
    input: 8000,
    output: 4000,
    total: 12000
  }

  it('deriveTokenCostRates splits input/output from session breakdown', () => {
    const rates = deriveTokenCostRates(usage)

    expect(rates?.input).toBeCloseTo(0.8 / 8000, 10)
    expect(rates?.output).toBeCloseTo(1.2 / 4000, 10)
  })

  it('estimateLiveTurnCostUsd scales streamed output and prompt overhead', () => {
    const cost = estimateLiveTurnCostUsd(usage, {
      reasoningTokens: 100,
      streamOutputTokens: 300,
      toolTokens: 50,
      toolsExecutedDelta: 1
    })

    expect(cost).not.toBeNull()
    // input: 2 calls × 2000 tok × $0.0001; output: 450 tok × $0.0003
    expect(cost!).toBeCloseTo(0.8 / 8000 * 4000 + 1.2 / 4000 * 450, 8)
  })

  it('estimateLiveTurnCostUsd falls back to blended rate without breakdown', () => {
    const blended = estimateLiveTurnCostUsd(
      { ...usage, cost_breakdown_usd: undefined },
      {
        reasoningTokens: 0,
        streamOutputTokens: 1200,
        toolTokens: 0,
        toolsExecutedDelta: 0
      }
    )

    expect(blended).toBeCloseTo((2 / 12000) * (2000 + 1200), 8)
  })

  it('formatTurnCostUsd marks live estimates with tilde', () => {
    expect(formatTurnCostUsd(0.23, true)).toBe('~$0.23')
    expect(formatTurnCostUsd(0.23, false)).toBe('$0.23')
  })
})
