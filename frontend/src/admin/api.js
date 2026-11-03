/**
 * admin/api.js — 兼容旧引用路径，实现已统一到 src/api/client.js
 * （后台与个人空间共用一套令牌与请求层，避免两套刷新逻辑）
 */
export {
  api, publicApi, asList, errOf, login, logout,
  isAuthed, setTokens, clearTokens, accessToken,
} from '../api/client'
