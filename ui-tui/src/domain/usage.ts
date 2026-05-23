import type { Usage } from '../types.js'

export const ZERO: Usage = { calls: 0, input: 0, output: 0, total: 0 }

/** Merge usage snapshots without clobbering prior fields with `undefined`. */
export function mergeUsage(base: Usage, patch: Partial<Usage>): Usage {
  const defined = Object.fromEntries(
    Object.entries(patch).filter(([, value]) => value !== undefined)
  ) as Partial<Usage>

  return { ...base, ...defined }
}

export function usageFromPartial(partial?: Partial<Usage> | null, base: Usage = ZERO): Usage {
  return partial ? mergeUsage(base, partial) : base
}

export function formatStatusBarCost(usage: Pick<Usage, 'cost_status' | 'cost_usd'>): string | null {
  if (typeof usage.cost_usd !== 'number') {
    return null
  }

  const prefix = usage.cost_status === 'estimated' ? '~' : ''

  return `${prefix}$${usage.cost_usd.toFixed(4)}`
}

export function shouldShowStatusBarCost(showCost: boolean, usage: Pick<Usage, 'cost_usd'>): boolean {
  return showCost && typeof usage.cost_usd === 'number'
}
