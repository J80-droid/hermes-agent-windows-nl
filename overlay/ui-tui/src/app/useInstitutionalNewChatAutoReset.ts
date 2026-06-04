import { watch } from 'node:fs'
import { basename, dirname } from 'node:path'
import { useEffect } from 'react'

import {
  clearNewChatNotice,
  formatNewChatNoticeSysMessage,
  getNewChatNoticePath,
  hasPendingNewChatNotice
} from '../lib/newChatNotice.js'

/** Live /new when sync writes institutional_new_chat_required.json while TUI is open. */
export function useInstitutionalNewChatAutoReset(newSession: (msg?: string) => Promise<void> | void) {
  useEffect(() => {
    const noticePath = getNewChatNoticePath()
    const dir = dirname(noticePath)
    const file = basename(noticePath)
    let debounce: null | ReturnType<typeof setTimeout> = null

    const maybeReset = () => {
      if (!hasPendingNewChatNotice()) {
        return
      }

      void Promise.resolve(newSession(formatNewChatNoticeSysMessage())).then(() => {
        clearNewChatNotice()
      })
    }

    let watcher: ReturnType<typeof watch> | undefined

    try {
      watcher = watch(dir, (_event, changed) => {
        if (changed && changed !== file) {
          return
        }

        if (debounce) {
          clearTimeout(debounce)
        }

        debounce = setTimeout(maybeReset, 300)
      })
    } catch {
      return undefined
    }

    return () => {
      watcher?.close()

      if (debounce) {
        clearTimeout(debounce)
      }
    }
  }, [newSession])
}
