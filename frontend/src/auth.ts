// Token storage for this prototype.
//
// NOTE (security tradeoff, documented honestly rather than silently assumed):
// the access token is kept in localStorage so a plain fetch() can attach it.
// That's simple but vulnerable to theft via XSS. A production build should
// move to an httpOnly, SameSite cookie issued by the backend instead, which
// JS can't read at all — see Agents.md's note on this before shipping.

const TOKEN_KEY = 'imprint_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
