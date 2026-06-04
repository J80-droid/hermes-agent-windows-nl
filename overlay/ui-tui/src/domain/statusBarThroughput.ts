/** Status-bar throughput formatting (parity with hermes_cli/status_bar_throughput.py).
 * Ink: use theme.color.statusTps (dimmed white), not muted (gold). */

export const MIN_ELAPSED_SEC = 0.5
export const MIN_TPS = 1
export const THROUGHPUT_MIN_WIDTH = 76

export type ThroughputSignals = {
  streamGenStartedAt: number | null
  streamOutputTokens: number
  reasoningTokens: number
  toolTokens: number
  lastCallTps: number | null
}

export function sumLiveGenerationTokens(signals: Pick<ThroughputSignals, 'streamOutputTokens' | 'reasoningTokens' | 'toolTokens'>): number {
  return Math.max(0, signals.streamOutputTokens + signals.reasoningTokens + signals.toolTokens)
}

function coerceFiniteRate(value: number | null | undefined): number | null {
  if (value == null || !Number.isFinite(value) || value < MIN_TPS) {
    return null
  }

  return value
}

export function computeLiveTps(
  tokens: number,
  startedAtMs: number | null,
  nowMs: number = Date.now(),
  minElapsedSec = MIN_ELAPSED_SEC
): number | null {
  if (startedAtMs == null || !Number.isFinite(startedAtMs) || tokens < 1) {
    return null
  }

  const elapsed = (nowMs - startedAtMs) / 1000
  if (!Number.isFinite(elapsed) || elapsed < minElapsedSec) {
    return null
  }

  return coerceFiniteRate(tokens / elapsed)
}

export function computeCallTps(
  completionTokens: number,
  genSeconds: number,
  minElapsedSec = MIN_ELAPSED_SEC
): number | null {
  if (completionTokens < 1 || !Number.isFinite(genSeconds) || genSeconds <= 0) {
    return null
  }

  const elapsed = Math.max(genSeconds, minElapsedSec)

  return coerceFiniteRate(completionTokens / elapsed)
}

export function formatStatusBarTps(tps: number | null | undefined): string | null {
  const rate = coerceFiniteRate(tps)

  return rate == null ? null : `${Math.round(rate)} tok/s`
}

export function resolveStatusBarThroughputLabel(opts: {
  showStatusBarTps: boolean
  width: number
  busy: boolean
  signals: ThroughputSignals
  nowMs?: number
}): string | null {
  if (!opts.showStatusBarTps || opts.width < THROUGHPUT_MIN_WIDTH) {
    return null
  }

  const tokens = sumLiveGenerationTokens(opts.signals)
  if (opts.busy && opts.signals.streamGenStartedAt) {
    const live = computeLiveTps(tokens, opts.signals.streamGenStartedAt, opts.nowMs)
    const liveLabel = formatStatusBarTps(live)

    if (liveLabel) {
      return liveLabel
    }
  }

  return formatStatusBarTps(opts.signals.lastCallTps)
}

/** Extra display columns to reserve beside the cost segment when TPS is enabled. */
export const STATUS_RULE_TPS_RESERVE = 12
