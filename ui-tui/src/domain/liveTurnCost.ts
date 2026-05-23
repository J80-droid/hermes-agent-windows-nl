import type { Usage } from '../types.js'

export type TokenCostRates = {
  blended: number
  cacheRead: number
  cacheWrite: number
  input: number
  output: number
}

export type LiveTurnTokenSignals = {
  reasoningTokens: number
  streamOutputTokens: number
  toolTokens: number
  toolsExecutedDelta: number
}

const rate = (usd: number | undefined, tokens: number) => (usd && tokens > 0 ? usd / tokens : 0)

function sumBreakdownUsd(breakdown: NonNullable<Usage['cost_breakdown_usd']>): number {
  return (
    (breakdown.input ?? 0) +
    (breakdown.output ?? 0) +
    (breakdown.cache_read ?? 0) +
    (breakdown.cache_write ?? 0)
  )
}

function resolveSessionCostUsd(
  usage: Pick<Usage, 'cost_breakdown_usd' | 'cost_usd'>
): number | null {
  if (typeof usage.cost_usd === 'number' && usage.cost_usd > 0) {
    return usage.cost_usd
  }

  const breakdown = usage.cost_breakdown_usd
  if (!breakdown) {
    return null
  }

  const total = sumBreakdownUsd(breakdown)

  return total > 0 ? total : null
}

/** Derive USD-per-token rates from the session usage snapshot (no gateway pricing table). */
export function deriveTokenCostRates(
  usage: Pick<Usage, 'cost_breakdown_usd' | 'cost_usd' | 'input' | 'output' | 'total'> & {
    cache_read?: number
    cache_write?: number
  }
): TokenCostRates | null {
  const sessionCost = resolveSessionCostUsd(usage)

  if (sessionCost == null || sessionCost <= 0) {
    return null
  }

  const input = usage.input ?? 0
  const output = usage.output ?? 0
  const total = usage.total ?? input + output
  const blended = total > 0 ? sessionCost / total : 0
  const breakdown = usage.cost_breakdown_usd

  if (!breakdown) {
    return { blended, cacheRead: blended, cacheWrite: blended, input: blended, output: blended }
  }

  const inputRate = rate(breakdown.input, input)
  const outputRate = rate(breakdown.output, output)

  return {
    blended,
    cacheRead: rate(breakdown.cache_read, usage.cache_read ?? 0) || blended,
    cacheWrite: rate(breakdown.cache_write, usage.cache_write ?? 0) || blended,
    input: inputRate || blended,
    output: outputRate || blended
  }
}

/**
 * Client-side turn $ estimate during streaming (replaced by exact delta on message.complete).
 */
export function estimateLiveTurnCostUsd(
  usage: Usage,
  signals: LiveTurnTokenSignals
): number | null {
  const rates = deriveTokenCostRates(usage)

  if (!rates) {
    return null
  }

  const output = Math.max(
    0,
    signals.streamOutputTokens + signals.reasoningTokens + signals.toolTokens
  )
  const calls = Math.max(1, 1 + signals.toolsExecutedDelta)
  const sessionCalls = Math.max(usage.calls ?? 0, calls)
  const avgInputPerCall = (usage.input ?? 0) > 0 ? (usage.input ?? 0) / sessionCalls : 0
  const input = avgInputPerCall * calls

  if (rates.input > 0 || rates.output > 0) {
    return input * rates.input + output * rates.output
  }

  return (input + output) * rates.blended
}

export function formatTurnCostUsd(amount: number, estimated = false): string {
  return `${estimated ? '~' : ''}$${amount.toFixed(2)}`
}

export function formatTurnLiveTokens(tokens: number): string {
  if (tokens >= 1_000_000) {
    return `~${(tokens / 1_000_000).toFixed(1).replace(/\.0$/, '')}M tok`
  }

  if (tokens >= 1000) {
    return `~${(tokens / 1000).toFixed(1).replace(/\.0$/, '')}K tok`
  }

  return `~${tokens} tok`
}

export function sumLiveTurnTokens(signals: LiveTurnTokenSignals): number {
  return Math.max(
    0,
    signals.streamOutputTokens + signals.reasoningTokens + signals.toolTokens
  )
}
