/**
 * 主站 JWT 过期后：先在大模型教学平台登录，再在竞赛报名系统登录独立账号，最后回到原页。
 * 以下路径在「主站登录成功」后需先经 /manu/competition-list 的独立账号门禁。
 */
const COMPETITION_ALT_GATE_ROUTES = [
  '/manu/competition-list',
  '/manu/competition-detail',
  '/manu/competition-register',
  '/manu/my-enrollments'
]

/**
 * 学生 / 指导老师主页登录成功后的默认竞赛详情
 * 对应：/#/manu/competition-detail?id=…&share=1
 * 改此常量即可热更新生效；仅改 .env 需重启 devServer
 */
const STUDENT_ADVISOR_LANDING_COMPETITION_ID = 80024817

export function getStudentAdvisorLandingCompetitionId () {
  return STUDENT_ADVISOR_LANDING_COMPETITION_ID
}

/** @returns {{ path: string, query: { id: string, share: string } }} */
export function getStudentAdvisorLandingRouteLocation () {
  return {
    path: '/manu/competition-detail',
    query: {
      id: String(getStudentAdvisorLandingCompetitionId()),
      share: '1'
    }
  }
}

/** @returns {string} 如 /manu/competition-detail?id=80024817&share=1 */
export function getStudentAdvisorLandingFullPath () {
  const loc = getStudentAdvisorLandingRouteLocation()
  return `${loc.path}?id=${encodeURIComponent(loc.query.id)}&share=1`
}

/** 进入分享详情前标记本会话已认证，避免 share=1 首屏清掉主页刚写入的令牌 */
export function markCompetitionShareSessionAuthed (competitionId, division = '') {
  const id = competitionId != null ? String(competitionId) : 'x'
  const div = division != null ? String(division) : ''
  try {
    sessionStorage.setItem(`competition_share_authed_${id}_${div}`, '1')
  } catch (e) {
    /* ignore */
  }
}

function pathOnly (fullPath) {
  const s = String(fullPath || '').trim()
  const i = s.indexOf('?')
  const j = s.indexOf('#')
  if (i < 0 && j < 0) return s
  const cut = [i >= 0 ? i : Infinity, j >= 0 ? j : Infinity].reduce((a, b) => Math.min(a, b))
  return s.slice(0, cut)
}

/**
 * 是否应在主站登录成功后，先到竞赛独立账号登录页再回跳
 * @param {string} fullPath 如 /manu/competition-detail?id=1
 */
export function needsCompetitionAltGateAfterMainLogin (fullPath) {
  const base = pathOnly(fullPath)
  return COMPETITION_ALT_GATE_ROUTES.some(r => base === r)
}

/**
 * 独立账号登录完成后，仅允许跳回竞赛模块内路径（防开放重定向）
 */
export function sanitizeCompetitionReturnPath (raw) {
  if (raw == null) return ''
  let s = String(raw).trim()
  try {
    s = decodeURIComponent(s)
  } catch (e) {
    /* 已是明文 */
  }
  if (!s.startsWith('/') || s.startsWith('//')) return ''
  const base = pathOnly(s)
  if (!COMPETITION_ALT_GATE_ROUTES.includes(base)) return ''
  return s
}

/**
 * 是否为竞赛模块全屏壳路由（与 COMPETITION_ALT_GATE_ROUTES 一致）。
 * 用于路由守卫：已登录独立账号时可跳过主站 GetInfo，减轻新标签页主站 JWT 过期误报。
 * @param {string} pathOrFullPath 如 /manu/competition-detail 或带 query 的 fullPath
 */
export function isCompetitionAltShellPath (pathOrFullPath) {
  const base = pathOnly(pathOrFullPath)
  return COMPETITION_ALT_GATE_ROUTES.includes(base)
}

/** 登录/注册页：锁定 html/body，避免出现页面级滚动条 */
export function lockAuthViewport () {
  document.documentElement.style.overflow = 'hidden'
  document.body.style.overflow = 'hidden'
  document.body.classList.add('userLayout')
}

/** 离开登录/注册页时恢复滚动 */
export function unlockAuthViewport () {
  document.documentElement.style.overflow = ''
  document.body.style.overflow = ''
  document.body.classList.remove('userLayout')
}
