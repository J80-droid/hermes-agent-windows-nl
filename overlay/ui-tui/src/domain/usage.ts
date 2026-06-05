import type { Usage } from '../types.js'

export const ZERO: Usage = { calls: 0, input: 0, output: 0, total: 0 }

type PartialUsage = Partial<Usage> & {
  cost_status?: string
  cost_usd?: number
  turn_cost_usd?: number
}

export function mergeUsage(base: Usage, patch: PartialUsage): Usage {
  const out: Usage = { ...base }
  for (const [key, value] of Object.entries(patch)) {
    if (value !== undefined) {
      ;(out as Record<string, unknown>)[key] = value
    }
  }
  return out
}

export function usageFromPartial(partial: PartialUsage): Usage {
  return mergeUsage(ZERO, partial)
}

export function formatStatusBarCost(usage: {
  cost_status?: string
  cost_usd?: number
}): string | null {
  if (usage.cost_usd === undefined || usage.cost_usd === null) {
    return null
  }
  const prefix = usage.cost_status === 'estimated' ? '~' : ''
  return `${prefix}$${usage.cost_usd.toFixed(4)}`
}

export function shouldShowStatusBarCost(
  showCost: boolean,
  usage: { cost_usd?: number }
): boolean {
  return showCost && typeof usage.cost_usd === 'number' && !Number.isNaN(usage.cost_usd)
}
