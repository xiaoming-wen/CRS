/**
 * 学生退赛后再次报名须重新提交作品：按竞赛 ID 记录退赛时间戳，
 * 用于在详情页/报名弹窗排除退赛前的旧作品（与 enrollment_id 互补）。
 */
const STORAGE_KEY = 'competition_withdraw_submission_cutoff_v1'

function readMap () {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (_) {
    return {}
  }
}

function writeMap (map) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map || {}))
  } catch (_) {
    /* ignore quota */
  }
}

function normalizeCompetitionId (competitionId) {
  if (competitionId == null || competitionId === '') return null
  const n = Number(competitionId)
  return Number.isFinite(n) && n > 0 ? String(n) : String(competitionId)
}

/** 退赛成功后调用（「我报名的竞赛」或详情报名弹窗） */
export function markCompetitionWithdrawnForResubmit (competitionId, atMs) {
  const key = normalizeCompetitionId(competitionId)
  if (!key) return
  const ts = typeof atMs === 'number' && atMs > 0 ? atMs : Date.now()
  const map = readMap()
  map[key] = ts
  writeMap(map)
}

export function getCompetitionWithdrawSubmissionCutoff (competitionId) {
  const key = normalizeCompetitionId(competitionId)
  if (!key) return null
  const map = readMap()
  const v = map[key]
  return typeof v === 'number' && v > 0 ? v : null
}

export function clearCompetitionWithdrawSubmissionCutoff (competitionId) {
  const key = normalizeCompetitionId(competitionId)
  if (!key) return
  const map = readMap()
  if (!(key in map)) return
  delete map[key]
  writeMap(map)
}

/** dual 竞赛报名组别：enrollments/me 未返回 division 时，用本机缓存补全（报名成功时写入） */
const ENROLL_DIVISION_STORAGE_KEY = 'competition_enroll_division_v1'

function readEnrollDivisionMap () {
  try {
    const raw = localStorage.getItem(ENROLL_DIVISION_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (_) {
    return {}
  }
}

function writeEnrollDivisionMap (map) {
  try {
    localStorage.setItem(ENROLL_DIVISION_STORAGE_KEY, JSON.stringify(map || {}))
  } catch (_) {
    /* ignore quota */
  }
}

function enrollDivisionStorageKey (competitionId, track) {
  const cid = normalizeCompetitionId(competitionId)
  if (!cid) return null
  const t = track === 'team' ? 'team' : 'individual'
  return `${cid}:${t}`
}

/** 从报名记录或 POST enroll 响应解析 division */
export function resolveEnrollmentDivision (row) {
  if (!row || typeof row !== 'object') return null
  const candidates = [row.division, row.enrollment_division, row.education_division]
  for (const c of candidates) {
    if (c == null || String(c).trim() === '') continue
    const s = String(c).trim().toLowerCase()
    if (s === 'undergraduate' || s === 'vocational') return s
  }
  return null
}

export function divisionToLabel (division) {
  const s = division != null ? String(division).trim().toLowerCase() : ''
  if (s === 'undergraduate') return '本科组'
  if (s === 'vocational') return '高职组'
  return null
}

export function saveCompetitionEnrollmentDivision (competitionId, track, division) {
  const storageKey = enrollDivisionStorageKey(competitionId, track)
  if (!storageKey) return
  const s = division != null ? String(division).trim().toLowerCase() : ''
  if (s !== 'undergraduate' && s !== 'vocational') return
  const map = readEnrollDivisionMap()
  map[storageKey] = s
  writeEnrollDivisionMap(map)
}

export function getCompetitionEnrollmentDivision (competitionId, track) {
  const storageKey = enrollDivisionStorageKey(competitionId, track)
  if (!storageKey) return null
  const v = readEnrollDivisionMap()[storageKey]
  if (v === 'undergraduate' || v === 'vocational') return v
  return null
}

/**
 * 本竞赛任一条报名赛道缓存的 division（dual 下学生仅属一个组别，个人/组队应一致）
 */
export function getCompetitionEnrollmentDivisionAnyTrack (competitionId) {
  return (
    getCompetitionEnrollmentDivision(competitionId, 'individual') ||
    getCompetitionEnrollmentDivision(competitionId, 'team')
  )
}

/**
 * 「我报名的竞赛」等列表：组别解析顺序与赛道无关（个人/组队同源）
 */
export function resolveEnrollmentDivisionLabelForList (row, competitionDetail, detailLoaded) {
  if (!row || typeof row !== 'object') return '-'

  const fromApi = resolveEnrollmentDivision(row)
  if (fromApi) {
    const label = divisionToLabel(fromApi)
    if (label) return label
  }

  const cid = row.competition_id
  let cached = getCompetitionEnrollmentDivisionAnyTrack(cid)
  if (!cached && cid && row.team_id != null && row.team_id !== '') {
    cached = getCompetitionTeamDivision(cid, row.team_id)
  }
  if (cached) {
    const label = divisionToLabel(cached)
    if (label) return label
  }

  const comp = competitionDetail || row.competition || {}
  const mode = String(comp.division_mode || comp.divisionMode || 'single').toLowerCase()
  if (mode !== 'dual') return '不分组'

  if (!detailLoaded) return '…'
  return '-'
}

/** 报名资料字段：同一竞赛下个人/组队赛道共用（优先 enrollments/me 非空值） */
const ENROLLMENT_PROFILE_FIELD_KEYS = [
  'student_no',
  'real_name',
  'contact',
  'school_info',
  'school',
  'college'
]

function enrollmentProfileFieldPresent (v) {
  return v != null && String(v).trim() !== ''
}

/**
 * 按 competition_id 合并各赛道报名记录中的学生资料（学号/姓名/联系方式/学校等）
 * @param {Array<object>} enrollments
 * @returns {Record<string, object>}
 */
export function buildEnrollmentProfileByCompetitionId (enrollments) {
  const map = {}
  for (const row of enrollments || []) {
    if (!row || typeof row !== 'object') continue
    const cid = row.competition_id
    if (cid == null || cid === '') continue
    const key = String(cid)
    if (!map[key]) map[key] = {}
    const bucket = map[key]
    for (const field of ENROLLMENT_PROFILE_FIELD_KEYS) {
      const v = row[field]
      if (enrollmentProfileFieldPresent(v) && !enrollmentProfileFieldPresent(bucket[field])) {
        bucket[field] = v
      }
    }
  }
  return map
}

/** 当前行资料为空时，用同竞赛另一条赛道（通常为个人报名）已填写的资料补全 */
export function mergeEnrollmentRowWithCompetitionProfile (row, profileByCompetitionId) {
  if (!row || typeof row !== 'object') return row
  const cid = row.competition_id
  if (cid == null || cid === '') return row
  const shared = profileByCompetitionId && profileByCompetitionId[String(cid)]
  if (!shared) return row
  const merged = { ...row }
  for (const field of ENROLLMENT_PROFILE_FIELD_KEYS) {
    if (!enrollmentProfileFieldPresent(merged[field]) && enrollmentProfileFieldPresent(shared[field])) {
      merged[field] = shared[field]
    }
  }
  return merged
}

/**
 * 将本地 Alt 账号资料映射为报名展示字段（仅用于 enrollments/me 缺省时的展示兜底，不写回接口）
 * student_id → student_no；full_name → real_name；email/contact/phone → contact；school/college → 学校信息
 */
export function buildAltProfileEnrollmentFallback (altProfile) {
  const p = altProfile && typeof altProfile === 'object' ? altProfile : {}
  const out = {}
  if (enrollmentProfileFieldPresent(p.student_id)) {
    out.student_no = String(p.student_id).trim()
  }
  if (enrollmentProfileFieldPresent(p.full_name)) {
    out.real_name = String(p.full_name).trim()
  }
  // 与报名表单一致：Alt 仅有 school 时写入 college，避免 school+college 同值拼接成「111 · 111」
  if (enrollmentProfileFieldPresent(p.college)) {
    out.college = String(p.college).trim()
  } else if (enrollmentProfileFieldPresent(p.school)) {
    out.college = String(p.school).trim()
  }
  const contact = p.email != null && String(p.email).trim() !== ''
    ? p.email
    : (p.contact != null && String(p.contact).trim() !== ''
      ? p.contact
      : p.phone)
  if (enrollmentProfileFieldPresent(contact)) {
    out.contact = String(contact).trim()
  }
  return out
}

/** enrollments/me 字段仍为空时，用本地 Alt 资料补全展示（不覆盖接口已有非空值） */
export function mergeEnrollmentRowWithAltProfileFallback (row, altProfile) {
  if (!row || typeof row !== 'object') return row
  const fallback = buildAltProfileEnrollmentFallback(altProfile)
  if (!fallback || !Object.keys(fallback).length) return row
  const merged = { ...row }
  for (const field of ENROLLMENT_PROFILE_FIELD_KEYS) {
    if (!enrollmentProfileFieldPresent(merged[field]) && enrollmentProfileFieldPresent(fallback[field])) {
      merged[field] = fallback[field]
    }
  }
  return merged
}

/** 从队伍对象解析 division（字段与报名记录一致） */
export function resolveTeamDivision (team) {
  return resolveEnrollmentDivision(team)
}

const TEAM_DIVISION_STORAGE_KEY = 'competition_team_division_v1'

function readTeamDivisionMap () {
  try {
    const raw = localStorage.getItem(TEAM_DIVISION_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (_) {
    return {}
  }
}

function writeTeamDivisionMap (map) {
  try {
    localStorage.setItem(TEAM_DIVISION_STORAGE_KEY, JSON.stringify(map || {}))
  } catch (_) {
    /* ignore quota */
  }
}

function teamDivisionStorageKey (competitionId, teamId) {
  const cid = normalizeCompetitionId(competitionId)
  const tid = teamId != null && teamId !== '' ? String(teamId) : ''
  if (!cid || !tid) return null
  return `${cid}:${tid}`
}

/** 建队成功且接口未返回 division 时，按详情页组别写入本机缓存 */
export function saveCompetitionTeamDivision (competitionId, teamId, division) {
  const storageKey = teamDivisionStorageKey(competitionId, teamId)
  if (!storageKey) return
  const s = division != null ? String(division).trim().toLowerCase() : ''
  if (s !== 'undergraduate' && s !== 'vocational') return
  const map = readTeamDivisionMap()
  map[storageKey] = s
  writeTeamDivisionMap(map)
}

export function getCompetitionTeamDivision (competitionId, teamId) {
  const storageKey = teamDivisionStorageKey(competitionId, teamId)
  if (!storageKey) return null
  const v = readTeamDivisionMap()[storageKey]
  if (v === 'undergraduate' || v === 'vocational') return v
  return null
}

/** §8.16.2 列表项 division 与当前详情页组别一致（接口未筛时前端兜底） */
export function filterSubmissionsByViewDivision (list, viewDivision) {
  const div =
    viewDivision != null ? String(viewDivision).trim().toLowerCase() : ''
  if (div !== 'undergraduate' && div !== 'vocational') {
    return Array.isArray(list) ? list : []
  }
  return (list || []).filter((row) => {
    const d = resolveEnrollmentDivision(row)
    if (!d) return true
    return d === div
  })
}

export function normalizeCompetitionApiList (res) {
  if (Array.isArray(res)) return res
  if (res && Array.isArray(res.items)) return res.items
  if (res && Array.isArray(res.data)) return res.data
  if (res && Array.isArray(res.submissions)) return res.submissions
  return []
}

function parseTimeMs (value) {
  if (value == null || value === '') return null
  const t = new Date(value).getTime()
  return Number.isFinite(t) ? t : null
}

export function isWithdrawnOrSupersededSubmission (row) {
  if (!row || typeof row !== 'object') return true
  const st = row.status != null ? String(row.status).toLowerCase() : ''
  if (['withdrawn', 'cancelled', 'voided', 'superseded', 'archived', 'inactive'].includes(st)) return true
  if (row.voided === true || row.is_active === false) return true
  return false
}

function isActiveEnrollmentStatus (status) {
  const s = status != null ? String(status).toLowerCase() : ''
  return s === 'enrolled' || s === 'active'
}

/**
 * §8.7 报名记录赛道：优先 enrollment_scope，否则按 team_id 推断。
 * @returns {'individual'|'team'}
 */
export function getEnrollmentScope (row) {
  if (!row || typeof row !== 'object') return 'individual'
  const scope = row.enrollment_scope != null ? String(row.enrollment_scope).trim().toLowerCase() : ''
  if (scope === 'team' || scope === 'individual') return scope
  const hasTeam = row.team_id !== null && row.team_id !== undefined && row.team_id !== ''
  return hasTeam ? 'team' : 'individual'
}

/** 将同一竞赛下 enrolled 记录拆分为个人 / 队伍赛道（各保留一条） */
export function splitEnrollmentsByTrack (rows) {
  let individual = null
  const teams = []
  const teamsByWorkTrack = {}
  const list = Array.isArray(rows) ? rows : []
  for (const row of list) {
    if (!row || !isActiveEnrollmentStatus(row.status)) continue
    const scope = getEnrollmentScope(row)
    if (scope === 'team') {
      teams.push(row)
      const wt = row.work_track != null ? String(row.work_track).trim().toLowerCase() : ''
      if (wt && !teamsByWorkTrack[wt]) teamsByWorkTrack[wt] = row
    } else if (!individual) {
      individual = row
    }
  }
  // 兼容旧调用：team 取第一条组队报名
  return { individual, team: teams[0] || null, teams, teamsByWorkTrack }
}

/**
 * 教师端作品列表：当前有效报名（个人 + 队伍）索引，用于隐藏退赛前的旧作品。
 */
export function buildEnrollmentVisibilityIndex (individualRows, teamRows) {
  const activeEnrollmentIds = new Set()
  const studentCurrent = new Map()
  const teamCurrent = new Map()

  const upsertStudent = (studentId, enrollmentId, enrolledAtMs) => {
    if (studentId == null || !Number.isFinite(Number(studentId))) return
    const sid = Number(studentId)
    const prev = studentCurrent.get(sid)
    if (!prev || (enrolledAtMs != null && (prev.enrolledAtMs == null || enrolledAtMs >= prev.enrolledAtMs))) {
      studentCurrent.set(sid, {
        enrollmentId: enrollmentId != null ? Number(enrollmentId) : null,
        enrolledAtMs: enrolledAtMs != null ? enrolledAtMs : (prev ? prev.enrolledAtMs : null)
      })
    }
  }

  const upsertTeam = (teamId, enrollmentId, enrolledAtMs) => {
    if (teamId == null || !Number.isFinite(Number(teamId))) return
    const tid = Number(teamId)
    const prev = teamCurrent.get(tid)
    if (!prev || (enrolledAtMs != null && (prev.enrolledAtMs == null || enrolledAtMs >= prev.enrolledAtMs))) {
      teamCurrent.set(tid, {
        enrollmentId: enrollmentId != null ? Number(enrollmentId) : null,
        enrolledAtMs: enrolledAtMs != null ? enrolledAtMs : (prev ? prev.enrolledAtMs : null)
      })
    }
  }

  for (const row of individualRows || []) {
    if (!row || !isActiveEnrollmentStatus(row.status)) continue
    const eid = row.enrollment_id
    if (eid != null) activeEnrollmentIds.add(Number(eid))
    const enrolledAtMs = parseTimeMs(row.created_at || row.enrolled_at)
    const sid = row.student_id != null ? row.student_id : row.user_id
    upsertStudent(sid, eid, enrolledAtMs)
  }

  for (const row of teamRows || []) {
    if (!row || !isActiveEnrollmentStatus(row.status)) continue
    const teamId = row.team_id != null ? row.team_id : row.id
    const eid = row.enrollment_id
    if (eid != null) activeEnrollmentIds.add(Number(eid))
    const enrolledAtMs = parseTimeMs(row.created_at || row.enrolled_at)
    upsertTeam(teamId, eid, enrolledAtMs)
    const captainId = row.captain_id
    if (captainId != null) upsertStudent(captainId, eid, enrolledAtMs)
    const members = Array.isArray(row.members) ? row.members : []
    for (const m of members) {
      if (!m) continue
      const uid = m.user_id != null ? m.user_id : m.student_id
      if (uid != null) upsertStudent(uid, eid, enrolledAtMs)
    }
  }

  return { activeEnrollmentIds, studentCurrent, teamCurrent }
}

/** 教师端「作品列表（竞赛维度）」：仅保留当前报名周期内的作品 */
export function isSubmissionVisibleInAdminList (sub, index) {
  if (!sub || typeof sub !== 'object') return false
  if (isWithdrawnOrSupersededSubmission(sub)) return false
  if (!index) return true

  const { activeEnrollmentIds, studentCurrent, teamCurrent } = index
  const submittedAtMs = parseTimeMs(sub.submitted_at || sub.created_at)

  if (sub.enrollment_id != null) {
    return activeEnrollmentIds.has(Number(sub.enrollment_id))
  }

  const sid = sub.student_id != null
    ? Number(sub.student_id)
    : (sub.submitter_id != null ? Number(sub.submitter_id) : null)
  if (sid != null && Number.isFinite(sid)) {
    const cur = studentCurrent.get(sid)
    if (!cur) return false
    if (submittedAtMs == null) return false
    if (cur.enrolledAtMs == null) return true
    return submittedAtMs >= cur.enrolledAtMs
  }

  if (sub.team_id != null) {
    const tid = Number(sub.team_id)
    const cur = teamCurrent.get(tid)
    if (!cur) return false
    if (submittedAtMs == null) return false
    if (cur.enrolledAtMs == null) return true
    return submittedAtMs >= cur.enrolledAtMs
  }

  return true
}

export function filterAdminSubmissionsByActiveEnrollments (submissions, index) {
  const arr = Array.isArray(submissions) ? submissions : []
  return arr.filter(s => isSubmissionVisibleInAdminList(s, index))
}

/**
 * 同一队伍只保留最新一条提交；个人提交（无 team_id）按 student_id 去重。
 * 列表应按 submitted_at 倒序传入，或本函数会按时间排序后再去重。
 */
export function keepLatestSubmissionPerTeam (list) {
  const arr = Array.isArray(list) ? list.slice() : []
  arr.sort((a, b) => {
    const ta = parseTimeMs(a && (a.submitted_at || a.created_at)) || 0
    const tb = parseTimeMs(b && (b.submitted_at || b.created_at)) || 0
    if (tb !== ta) return tb - ta
    return Number((b && b.id) || 0) - Number((a && a.id) || 0)
  })
  const seen = new Set()
  const out = []
  for (const s of arr) {
    if (!s || typeof s !== 'object') continue
    let key
    if (s.team_id != null && s.team_id !== '') {
      key = `team:${Number(s.team_id)}`
    } else {
      const sid = s.student_id != null ? s.student_id : s.submitter_id
      if (sid == null) continue
      key = `student:${Number(sid)}`
    }
    if (seen.has(key)) continue
    seen.add(key)
    out.push(s)
  }
  return out
}

function hasTeamIdOnSubmission (sub) {
  return sub.team_id !== null && sub.team_id !== undefined && sub.team_id !== ''
}

/** 作品是否属于指定赛道（个人：无 team_id；队伍：有 team_id，可选匹配队伍 ID） */
export function submissionMatchesEnrollmentTrack (sub, ctx) {
  if (!sub || typeof sub !== 'object' || isWithdrawnOrSupersededSubmission(sub)) return false
  const scope = ctx && ctx.scope === 'team' ? 'team' : 'individual'
  const enrollmentId = ctx && ctx.enrollmentId != null ? Number(ctx.enrollmentId) : null
  const teamId = ctx && ctx.teamId != null ? Number(ctx.teamId) : null
  const cutoffMs =
    ctx && typeof ctx.cutoffMs === 'number' && ctx.cutoffMs > 0 ? ctx.cutoffMs : null

  if (enrollmentId != null && sub.enrollment_id != null) {
    if (Number(sub.enrollment_id) !== enrollmentId) return false
    return true
  }

  const isTeamSub = hasTeamIdOnSubmission(sub)
  if (scope === 'individual') {
    if (isTeamSub) return false
  } else {
    if (!isTeamSub) return false
    if (teamId != null && Number.isFinite(teamId) && Number(sub.team_id) !== teamId) return false
  }

  if (cutoffMs != null) {
    const submittedAtMs = parseTimeMs(sub.submitted_at || sub.created_at)
    if (submittedAtMs == null) return false
    return submittedAtMs >= cutoffMs
  }

  return true
}

/** 当前报名赛道（个人/队伍）下、计入「本周期已提交」的作品 */
export function filterSubmissionsForEnrollmentTrack (list, ctx) {
  const arr = Array.isArray(list) ? list : []
  return arr.filter(s => submissionMatchesEnrollmentTrack(s, ctx))
}

/** §8.17 / §8.17.1 ReviewResponse 本地缓存（作品 GET 不含 score 时供教师列表展示） */
const REVIEW_SCORE_STORAGE_KEY = 'competition_submission_review_scores_v1'

function readReviewScoreMap () {
  try {
    const raw = localStorage.getItem(REVIEW_SCORE_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (_) {
    return {}
  }
}

function writeReviewScoreMap (map) {
  try {
    localStorage.setItem(REVIEW_SCORE_STORAGE_KEY, JSON.stringify(map || {}))
  } catch (_) {
    /* ignore */
  }
}

function normalizeSubmissionIdKey (submissionId) {
  if (submissionId == null || submissionId === '') return null
  const n = Number(submissionId)
  return Number.isFinite(n) ? String(n) : String(submissionId)
}

/** 保存 PUT/PATCH review-grade 返回的 score / feedback / reviewed_at */
export function saveSubmissionReviewGradeCache (submissionId, review) {
  const key = normalizeSubmissionIdKey(submissionId)
  if (!key || !review || typeof review !== 'object') return
  if (review.score == null || review.score === '') return
  const map = readReviewScoreMap()
  map[key] = {
    score: review.score,
    feedback: review.feedback != null ? review.feedback : '',
    reviewed_at: review.reviewed_at != null ? review.reviewed_at : null
  }
  writeReviewScoreMap(map)
}

export function getSubmissionReviewGradeCache (submissionId) {
  const key = normalizeSubmissionIdKey(submissionId)
  if (!key) return null
  const map = readReviewScoreMap()
  const v = map[key]
  return v && typeof v === 'object' ? v : null
}
