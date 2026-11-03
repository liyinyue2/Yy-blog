/**
 * client.js — 全站统一请求层
 * JWT 双令牌：访问令牌过期时用刷新令牌静默续期并重试一次；
 * 刷新走 POST /api/auth/refresh（body 带 refresh_token），后端会轮换刷新令牌。
 * 令牌键名与 v2 后台一致（admin-access / admin-refresh），两处可共享会话。
 */
const K_ACCESS = 'admin-access'
const K_REFRESH = 'admin-refresh'

let access = sessionStorage.getItem(K_ACCESS) || ''
let refresh = sessionStorage.getItem(K_REFRESH) || ''

export const isAuthed = () => !!access
export const accessToken = () => access

export const setTokens = (a, r) => {
  access = a
  refresh = r || refresh
  sessionStorage.setItem(K_ACCESS, access)
  sessionStorage.setItem(K_REFRESH, refresh)
}

export const clearTokens = () => {
  access = ''
  refresh = ''
  sessionStorage.removeItem(K_ACCESS)
  sessionStorage.removeItem(K_REFRESH)
}

const send = (path, options = {}, token) => fetch(path, {
  ...options,
  headers: {
    // 只在 JSON 体上设 Content-Type：FormData 必须留给浏览器写 multipart 边界
    ...(options.body && !(options.body instanceof FormData)
      ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: 'Bearer ' + token } : {}),
    ...(options.headers || {}),
  },
})

const renew = async () => {
  if (!refresh) return false
  try {
    const r = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!r.ok) return false
    const d = await r.json().catch(() => ({}))
    if (!d.access_token) return false
    setTokens(d.access_token, d.refresh_token)
    return true
  } catch {
    return false
  }
}

const toResult = async res => ({
  ok: res.ok,
  status: res.status,
  data: await res.json().catch(() => ({})),
})

/** 鉴权请求：401 自动续期一次；续期失败即清令牌并回 401，由界面回到登录门。 */
export const api = async (path, options = {}) => {
  if (!access) return { ok: false, status: 401, data: { error: '未登录' } }
  let res = await send(path, options, access)
  if (res.status === 401 && !path.startsWith('/api/auth/')) {
    if (!(await renew())) {
      clearTokens()
      return { ok: false, status: 401, data: { error: '登录已过期' } }
    }
    res = await send(path, options, access)
  }
  return toResult(res)
}

/** 公开请求：不带令牌，也不触发续期。 */
export const publicApi = async (path, options = {}) =>
  toResult(await send(path, options, ''))

/** 后端多数列表接口直接返回裸数组，少数返回 {items|notes|files|tracks|logs}；统一成数组。 */
export const asList = d => Array.isArray(d) ? d
  : (d.items || d.notes || d.files || d.tracks || d.logs || d.messages || d.articles || [])

export const errOf = (d, fallback = '操作失败') => {
  if (!d) return fallback
  if (typeof d === 'string') return d
  return d.error || (typeof d.detail === 'string' ? d.detail : fallback)
}

export const login = async (username, password) => {
  const res = await send('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) return { ok: false, error: errOf(data, '登录失败') }
  setTokens(data.access_token, data.refresh_token)
  return { ok: true }
}

export const logout = () => clearTokens()
