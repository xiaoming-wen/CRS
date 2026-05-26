import { getStoredAltToken } from '@/api/altIdentity'

/** 竞赛模块 API 路径（相对 baseURL /api，形如 /v1/competitions/...） */
export function isCompetitionApiPath (url) {
  const u = String(url || '')
  return /\/v1\/competitions(\/|$)/.test(u)
}

/**
 * 解析请求应使用的 Bearer：竞赛接口优先 Alt JWT，否则主站 token；其它接口仅主站。
 * @param {string} url 相对路径，如 /v1/competitions/
 * @param {() => (string|null|undefined)} getMainToken
 * @returns {{ token: string|null, source: 'alt'|'main'|null }}
 */
export function resolveRequestBearer (url, getMainToken) {
  const main = getMainToken() || null
  const alt = getStoredAltToken() || null

  if (isCompetitionApiPath(url)) {
    if (alt) return { token: alt, source: 'alt' }
    if (main) return { token: main, source: 'main' }
    return { token: null, source: null }
  }
  if (main) return { token: main, source: 'main' }
  return { token: null, source: null }
}
