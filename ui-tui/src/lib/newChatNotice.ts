import { existsSync, readFileSync, unlinkSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

const NOTICE_BASENAME = 'institutional_new_chat_required.json'

/** Mirrors hermes_cli/institutional_new_chat_notice.py state dir. */
export const getNewChatNoticePath = (): string => {
  const local = process.env.LOCALAPPDATA?.trim()

  if (local) {
    return join(local, 'hermes', NOTICE_BASENAME)
  }

  return join(homedir(), '.hermes', NOTICE_BASENAME)
}

export const hasPendingNewChatNotice = (): boolean => existsSync(getNewChatNoticePath())

export const readNewChatNoticeReason = (): string | null => {
  try {
    const raw = readFileSync(getNewChatNoticePath(), 'utf8')
    const data = JSON.parse(raw) as { reason?: unknown }
    const reason = data.reason

    return typeof reason === 'string' && reason.trim() ? reason.trim() : null
  } catch {
    return null
  }
}

/** Clear reminder after /new or auto-reset. Returns true if a file was removed. */
export const clearNewChatNotice = (): boolean => {
  const path = getNewChatNoticePath()

  if (!existsSync(path)) {
    return false
  }

  try {
    unlinkSync(path)

    return true
  } catch {
    return false
  }
}

export const formatNewChatNoticeSysMessage = (): string => {
  const reason = readNewChatNoticeReason()

  return reason
    ? `Nieuwe sessie na sync (${reason}) — system prompt vernieuwd`
    : 'Nieuwe sessie na sync — system prompt vernieuwd'
}
