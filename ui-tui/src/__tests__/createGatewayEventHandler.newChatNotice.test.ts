import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Msg } from '../types.js'
import { createGatewayEventHandler } from '../app/createGatewayEventHandler.js'

const ref = <T>(current: T) => ({ current })

const buildCtx = (appended: Msg[]) =>
  ({
    composer: { setInput: vi.fn() },
    gateway: { rpc: vi.fn(async () => null) },
    session: {
      STARTUP_RESUME_ID: '',
      colsRef: ref(80),
      newSession: vi.fn(),
      resetSession: vi.fn(),
      resumeById: vi.fn(),
      setCatalog: vi.fn()
    },
    submission: { submitRef: { current: vi.fn() } },
    system: { bellOnComplete: false, sys: vi.fn() },
    transcript: {
      appendMessage: (msg: Msg) => appended.push(msg),
      panel: vi.fn(),
      setHistoryItems: vi.fn()
    },
    voice: {
      setProcessing: vi.fn(),
      setRecording: vi.fn(),
      setVoiceEnabled: vi.fn()
    }
  }) as any

describe('createGatewayEventHandler institutional /new', () => {
  let dir: string

  beforeEach(() => {
    dir = join(tmpdir(), `hermes-ready-${process.pid}-${Date.now()}`)
    mkdirSync(join(dir, 'hermes'), { recursive: true })
    vi.stubEnv('LOCALAPPDATA', dir)
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    rmSync(dir, { recursive: true, force: true })
  })

  it('on gateway.ready with pending notice, forges session and skips resume', async () => {
    const path = join(dir, 'hermes', 'institutional_new_chat_required.json')

    writeFileSync(path, JSON.stringify({ reason: 'Trust sync' }), 'utf8')

    const appended: Msg[] = []
    const newSession = vi.fn().mockResolvedValue(undefined)
    const resumeById = vi.fn()
    const ctx = buildCtx(appended)

    ctx.session.newSession = newSession
    ctx.session.resumeById = resumeById
    ctx.session.STARTUP_RESUME_ID = 'env-explicit'
    ctx.gateway.rpc = vi.fn(async () => null)

    createGatewayEventHandler(ctx)({ payload: {}, type: 'gateway.ready' } as any)

    await vi.waitFor(() => expect(newSession).toHaveBeenCalled())
    expect(newSession.mock.calls[0]?.[0]).toContain('Trust sync')
    expect(resumeById).not.toHaveBeenCalled()
    expect(ctx.gateway.rpc).not.toHaveBeenCalled()
  })
})
