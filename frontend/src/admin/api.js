/**
 * admin/api.js — 后台认证与请求封装
 * JWT 双令牌：access 过期自动用 refresh 续期并重试一次（与原版 admin.js 行为一致）。
 */
let access = sessionStorage.getItem('admin-access') || ''
let refresh = sessionStorage.getItem('admin-refresh') || ''

export const isAuthed = () => !!access

export const setTokens = (a, r) => {
  access = a; refresh = r
  sessionStorage.setItem('admin-access', a)
  sessionStorage.setItem('admin-refresh', r)
}

export const clearTokens = () => {
  access = ''; refresh = ''
  sessionStorage.removeItem('admin-access')
  sessionStorage.removeItem('admin-refresh')
}

const raw = (path, options = {}, token) => fetch(path, {
  ...options,
  headers: {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: 'Bearer ' + token } : {}),
    ...(options.headers || {}),
  },
})

const withRetry = async path => {
  const r = await raw(path, {}, refresh)
  if (!r.ok) return { ok: false }
  const d = await r.json()
  if (!d.access_token) return { ok: false }
  setTokens(d.access_token, refresh)
  return { ok: true }
}

export const api = async (path, options = {}) => {
  if (!access) return { ok: false, status: 401, data: { error: '未登录' } }
  let r = await raw(path, options, access)
  if (r.status === 401) {
    const renewed = await withRetry(path)
    if (!renewed.ok) { clearTokens(); return { ok: false, status: 401, data: { error: '登录已过期' } } }
    r = await raw(path, options, access)
  }
  let data = null
  try { data = await r.json() } catch { data = {} }
  return { ok: r.ok, status: r.status, data }
}

export const login = async (username, password) => {
  const r = await fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) return { ok: false, error: data.error || '登录失败' }
  setTokens(data.access_token, data.refresh_token)
  return { ok: true }
}
