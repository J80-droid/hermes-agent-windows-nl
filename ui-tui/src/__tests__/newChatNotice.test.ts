import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('newChatNotice', () => {
  let dir: string

  beforeEach(() => {
    dir = join(tmpdir(), `hermes-notice-${process.pid}-${Date.now()}`)
    mkdirSync(join(dir, 'hermes'), { recursive: true })
    vi.stubEnv('LOCALAPPDATA', dir)
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    rmSync(dir, { recursive: true, force: true })
  })

  it('detects, reads reason, and clears notice file', async () => {
    const mod = await import('../lib/newChatNotice.js')
    const path = join(dir, 'hermes', 'institutional_new_chat_required.json')

    writeFileSync(path, JSON.stringify({ reason: 'Memory sync' }), 'utf8')
    expect(mod.hasPendingNewChatNotice()).toBe(true)
    expect(mod.readNewChatNoticeReason()).toBe('Memory sync')
    expect(mod.clearNewChatNotice()).toBe(true)
    expect(mod.hasPendingNewChatNotice()).toBe(false)
  })
})
