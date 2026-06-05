import {
  clearNewChatNotice,
  formatNewChatNoticeSysMessage,
  hasPendingNewChatNotice
} from '../lib/newChatNotice.js'

/** Handle ``gateway.ready``: auto ``/new`` when sync wrote institutional_new_chat_required.json. */
export function handleGatewayReadyNewChatNotice(
  newSession: (msg?: string) => Promise<void> | void,
  scheduleStartupPrompt: () => void,
  patchStatus: (status: string) => void
): boolean {
  if (!hasPendingNewChatNotice()) {
    return false
  }

  patchStatus('forging session (sync)…')
  void Promise.resolve(newSession(formatNewChatNoticeSysMessage())).then(() => {
    clearNewChatNotice()
    scheduleStartupPrompt()
  })

  return true
}
