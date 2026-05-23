import type { Usage } from '../types.js'

import { formatStatusBarCost } from './usage.js'

export type CostBarMode = 'minimal' | 'rich'

export type CostBreakdownPct = NonNullable<Usage['cost_breakdown_pct']>

export type StatusBarCostUsage = Pick<
  Usage,
  'calls' | 'cost_breakdown_pct' | 'cost_status' | 'cost_usd' | 'session_tools_executed' | 'turn_cost_usd'
>

const FULL_MIN_WIDTH = 96
const COSTS_MIN_WIDTH = 58

export function formatUsdCompact(amount: number): string {
  return `$${amount.toFixed(2)}`
}

export function formatCostBreakdownPct(pct: CostBreakdownPct | undefined): string | null {
  if (!pct) {
    return null
  }

  const parts: string[] = []

  if (typeof pct.cw === 'number') {
    parts.push(`cw ${pct.cw}%`)
  }
  if (typeof pct.out === 'number') {
    parts.push(`out ${pct.out}%`)
  }
  if (typeof pct.in === 'number') {
    parts.push(`in ${pct.in}%`)
  }
  if (typeof pct.cr === 'number') {
    parts.push(`cr ${pct.cr}%`)
  }

  return parts.length ? parts.join(' │ ') : null
}

export function resolveCostBarTier(width: number, mode: CostBarMode): 'costs' | 'full' | 'session' {
  if (mode !== 'rich') {
    return 'session'
  }

  if (width >= FULL_MIN_WIDTH) {
    return 'full'
  }

  if (width >= COSTS_MIN_WIDTH) {
    return 'costs'
  }

  return 'session'
}

export function formatStatusBarCostRich(
  usage: StatusBarCostUsage,
  opts: { mode?: CostBarMode; width?: number } = {}
): string | null {
  const mode = opts.mode ?? 'rich'
  const width = opts.width ?? FULL_MIN_WIDTH

  if (typeof usage.cost_usd !== 'number') {
    return null
  }

  if (mode === 'minimal') {
    return formatStatusBarCost(usage)
  }

  const session = formatUsdCompact(usage.cost_usd)
  const turn =
    typeof usage.turn_cost_usd === 'number' ? formatUsdCompact(usage.turn_cost_usd) : null
  const tier = resolveCostBarTier(width, mode)

  if (tier === 'session') {
    return session
  }

  const costPair = turn ? `${turn} / ${session}` : session
  const calls = typeof usage.calls === 'number' && usage.calls > 0 ? `${usage.calls} calls` : null
  const tools =
    typeof usage.session_tools_executed === 'number' && usage.session_tools_executed > 0
      ? `${usage.session_tools_executed} tools`
      : null

  if (tier === 'costs') {
    const tail = [calls, tools].filter(Boolean).join(' │ ')

    return tail ? `${costPair} │ ${tail}` : costPair
  }

  const breakdown = formatCostBreakdownPct(usage.cost_breakdown_pct)
  const segments = [costPair, breakdown, calls, tools].filter(Boolean)

  return segments.join(' │ ')
}

export function shouldShowStatusBarCostRich(
  showCost: boolean,
  usage: Pick<Usage, 'cost_usd'>
): boolean {
  return showCost && typeof usage.cost_usd === 'number'
}
