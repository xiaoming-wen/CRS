import axios from 'axios'

/**
 * 第二套身份 /api/alt-identity/* — 与主站 axios 拦截器隔离，不自动附带主站 JWT。
 */
// eslint-disable-next-line no-undef
const baseURL = process.env.VUE_APP_API_BASE_URL || '/api'

const altClient = axios.create({
  baseURL,
  timeout: 24000
})

altClient.interceptors.response.use(
  response => response.data,
  err => Promise.reject(err.response != null ? err.response : err)
)

function unwrapError (resp) {
  if (!resp) return new Error('网络错误')
  const data = resp.data || {}
  const d = data.detail
  if (typeof d === 'string') return new Error(d)
  if (Array.isArray(d) && d.length) {
    const first = d[0]
    if (first && first.msg) return new Error(String(first.msg))
  }
  if (d && typeof d === 'object' && d.error_code != null) {
    return new Error(d.detail || d.error_code || String(d.msg || '请求失败'))
  }
  return new Error(data.message || resp.statusText || '请求失败')
}

/**
 * 8.0.1 注册 POST /api/alt-identity/register
 * body 与主站注册字段对齐，并含 school（学校名称）。
 */
export async function altIdentityRegister (body) {
  try {
    return await altClient.post('alt-identity/register', body, {
      headers: { 'Content-Type': 'application/json' }
    })
  } catch (e) {
    throw unwrapError(e)
  }
}

/**
 * 8.0.2 登录 POST /api/alt-identity/session
 */
export async function altIdentitySession (body) {
  try {
    return await altClient.post('alt-identity/session', body, {
      headers: { 'Content-Type': 'application/json' }
    })
  } catch (e) {
    throw unwrapError(e)
  }
}

/**
 * 8.0.3 刷新第二套访问令牌 `POST /api/alt-identity/refresh-token`
 * 权限：请求头须携带 **未过期** 的第二套 `Authorization: Bearer <alt_access_token>`（与主站 refresh 策略一致）。
 * 请求体：可不传或空 JSON，服务端不读 body。
 * 响应（200）：与 **8.0.2 登录** 相同字段（`access_token`、`token_type`、`user_id`、`role`、`full_name`、`school`）。
 */
export async function altIdentityRefreshToken () {
  const t = getStoredAltToken()
  if (!t) throw new Error('缺少第二套令牌')
  try {
    return await altClient.post(
      'alt-identity/refresh-token',
      {},
      { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${t}` } }
    )
  } catch (e) {
    throw unwrapError(e)
  }
}

/**
 * 8.0.4 当前第二套身份与权限 `GET /api/alt-identity/me`
 * 权限：请求头须携带第二套 `Authorization: Bearer <alt_access_token>`（与主站 Token **不可互换**）。
 * 响应（200）：`id`、`username`、`email`、`full_name`、`role`、`is_active`、`student_id`、`teacher_id`、`school`、`created_at`，
 * 以及 **`effective_permissions`**（字符串数组，即 `ROLE_PERMISSIONS[role]` 展开）。
 */
export async function fetchAltIdentityMe () {
  const t = getStoredAltToken()
  if (!t) throw new Error('缺少第二套令牌')
  try {
    return await altClient.get('alt-identity/me', {
      headers: { Authorization: `Bearer ${t}` }
    })
  } catch (e) {
    throw unwrapError(e)
  }
}

export const ALT_ACCESS_TOKEN_KEY = 'alt_access_token'
export const ALT_PROFILE_KEY = 'alt_identity_profile'

export function getStoredAltToken () {
  return localStorage.getItem(ALT_ACCESS_TOKEN_KEY) || ''
}

function notifyAltIdentityStorageChanged () {
  try {
    window.dispatchEvent(new CustomEvent('alt-identity-changed'))
  } catch (e) {
    /* SSR 或无 window */
  }
}

export function clearAltIdentityStorage () {
  localStorage.removeItem(ALT_ACCESS_TOKEN_KEY)
  localStorage.removeItem(ALT_PROFILE_KEY)
  notifyAltIdentityStorageChanged()
}

/**
 * 将 GET /alt-identity/me 的响应合并进本地资料（不替换令牌，除非 payload 中含 access_token）。
 */
export function applyAltIdentityMeToStorage (me) {
  if (!me || typeof me !== 'object') return
  const prev = getAltProfileFromStorage()
  const profile = {
    ...prev,
    user_id: me.id != null ? me.id : (me.user_id != null ? me.user_id : prev.user_id),
    username: me.username != null ? me.username : prev.username,
    email: me.email != null ? me.email : prev.email,
    full_name: me.full_name != null ? me.full_name : prev.full_name,
    role: me.role != null ? me.role : prev.role,
    school: me.school !== undefined ? me.school : prev.school,
    student_id: me.student_id != null ? me.student_id : prev.student_id,
    teacher_id: me.teacher_id != null ? me.teacher_id : prev.teacher_id,
    is_active: me.is_active !== undefined ? me.is_active : prev.is_active,
    created_at: me.created_at != null ? me.created_at : prev.created_at,
    effective_permissions: Array.isArray(me.effective_permissions)
      ? me.effective_permissions
      : prev.effective_permissions
  }
  localStorage.setItem(ALT_PROFILE_KEY, JSON.stringify(profile))
  notifyAltIdentityStorageChanged()
}

/**
 * 与主站 Token 形态一致，并含 school；登录响应可能无 username，可辅以 extras
 */
export function saveAltSession (payload, extras = {}) {
  if (payload && payload.access_token) {
    localStorage.setItem(ALT_ACCESS_TOKEN_KEY, payload.access_token)
  }
  const p = payload || {}
  const prev = getAltProfileFromStorage()
  const profile = {
    ...prev,
    user_id: p.user_id != null ? p.user_id : (extras.user_id != null ? extras.user_id : prev.user_id),
    username: p.username != null ? p.username : (extras.username != null ? extras.username : prev.username),
    email: p.email != null ? p.email : (extras.email != null ? extras.email : prev.email),
    full_name: p.full_name != null ? p.full_name : (extras.full_name != null ? extras.full_name : prev.full_name),
    role: p.role != null ? p.role : (extras.role != null ? extras.role : prev.role),
    school: p.school !== undefined ? p.school : (extras.school !== undefined ? extras.school : prev.school),
    student_id: p.student_id != null ? p.student_id : (extras.student_id != null ? extras.student_id : prev.student_id),
    teacher_id: p.teacher_id != null ? p.teacher_id : (extras.teacher_id != null ? extras.teacher_id : prev.teacher_id),
    effective_permissions: Array.isArray(p.effective_permissions)
      ? p.effective_permissions
      : (Array.isArray(extras.effective_permissions)
        ? extras.effective_permissions
        : prev.effective_permissions)
  }
  localStorage.setItem(ALT_PROFILE_KEY, JSON.stringify(profile))
  notifyAltIdentityStorageChanged()
}

/** 从本地读取竞赛独立账号资料（登录 /saveAltSession 写入） */
export function getAltProfileFromStorage () {
  try {
    const raw = localStorage.getItem(ALT_PROFILE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch (e) {
    return {}
  }
}

/**
 * 竞赛独立账号 role 小写（与注册/登录接口一致：student | teacher）
 * 未设置时返回 ''。
 */
export function getAltRoleNormalized () {
  const p = getAltProfileFromStorage()
  const r = p.role
  if (r == null || String(r).trim() === '') return ''
  return String(r).trim().toLowerCase()
}

/** 竞赛端「教师/管理员」能力：创建竞赛、评阅等（教师或超管） */
export function isAltCompetitionTeacherOrAdmin () {
  const r = getAltRoleNormalized()
  return r === 'teacher' || r === 'super_admin'
}

/**
 * 竞赛端「学生」能力：报名、提交作品等。
 * 无 role 记录时按学生端展示，避免误显管理操作。
 */
export function isAltCompetitionStudent () {
  const r = getAltRoleNormalized()
  if (r === '') return true
  return r === 'student'
}
