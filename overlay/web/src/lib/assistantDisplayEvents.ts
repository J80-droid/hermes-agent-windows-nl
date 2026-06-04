/** Notify Web UI that display.assistant_* config changed (after Config save). */
export const ASSISTANT_DISPLAY_CHANGED = "hermes:assistant-display-changed";

export function notifyAssistantDisplayChanged(): void {
  window.dispatchEvent(new Event(ASSISTANT_DISPLAY_CHANGED));
}
