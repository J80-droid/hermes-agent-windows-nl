/**
 * Dashboard session token — kanban-patroon met cookie-fallback.
 */
export function getSessionToken() {
  if (typeof window !== 'undefined' && window.__HERMES_SESSION_TOKEN__) {
    return String(window.__HERMES_SESSION_TOKEN__);
  }
  try {
    const cookie = document.cookie
      .split('; ')
      .find((r) => r.startsWith('hermes_session_token='));
    if (cookie) {
      return decodeURIComponent(cookie.split('=').slice(1).join('='));
    }
  } catch (_e) { /* ignore */ }
  return '';
}
