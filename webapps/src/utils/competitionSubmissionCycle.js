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
